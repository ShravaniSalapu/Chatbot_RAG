"""
BM25 sparse search implementation
"""

from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
import math
import re
import os

from app.retrieval.bm25_redis import get_bm25_redis
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class BM25Search:
    """BM25 sparse search implementation"""
    
    def __init__(self):
        self.indexes = {}  # document_id -> BM25 index
        self.corpus = {}  # document_id -> list of chunks
        self.document_tenants = {}  # document_id -> tenant_id
        self.k1 = float(os.getenv("BM25_K1", "1.5"))
        self.b = float(os.getenv("BM25_B", "0.75"))

    def _doc_ids_for_search(
        self,
        document_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Resolve which document indexes are visible for a tenant-scoped query."""
        if document_id:
            if tenant_id and self.document_tenants.get(document_id) != tenant_id:
                return []
            if allowed_document_ids is not None and document_id not in set(allowed_document_ids):
                return []
            return [document_id] if document_id in self.corpus else []

        doc_ids = list(self.corpus.keys())
        if tenant_id:
            # Only documents explicitly indexed for this tenant (excludes legacy/orphan indexes).
            doc_ids = [d for d in doc_ids if self.document_tenants.get(d) == tenant_id]
        elif os.getenv("REQUIRE_AUTH", "true").lower() in ("1", "true", "yes"):
            # Multi-tenant mode: never search across all tenants when tenant is unspecified.
            return []

        if allowed_document_ids is not None:
            allowed = set(allowed_document_ids)
            doc_ids = [d for d in doc_ids if d in allowed]
        return doc_ids
    
    def build_index(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        persist_redis: bool = True,
    ) -> bool:
        """
        Build BM25 index for a document
        
        Args:
            document_id: Document ID
            chunks: List of chunks
            
        Returns:
            True if successful
        """
        logger.info(f"Building BM25 index for document: {document_id}")
        
        try:
            # Tokenize chunks
            corpus = []
            for chunk in chunks:
                tokens = self._tokenize(chunk['content'])
                corpus.append(tokens)
            
            # Create BM25 index
            index = BM25Okapi(corpus, k1=self.k1, b=self.b)
            
            self.indexes[document_id] = index
            self.corpus[document_id] = chunks
            resolved_tenant = tenant_id or (chunks[0].get("tenant_id") if chunks else None)
            if resolved_tenant:
                self.document_tenants[document_id] = resolved_tenant

            if persist_redis:
                get_bm25_redis().save_index(document_id, chunks, resolved_tenant)
            
            logger.info(f"BM25 index built for {len(chunks)} chunks")
            return True
        except Exception as e:
            logger.error(f"Error building BM25 index: {str(e)}")
            return False
    
    def search(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5,
        exclude_image_chunks: bool = False,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform BM25 search
        
        Args:
            query: Search query
            document_id: Specific document to search (None for all)
            top_k: Number of results to return
            
        Returns:
            List of search results with scores
        """
        logger.info(f"Performing BM25 search for query: {query}")
        
        query_tokens = self._tokenize(query)
        results = []
        
        # Search in specific document or all documents
        doc_ids = self._doc_ids_for_search(document_id, tenant_id, allowed_document_ids)
        
        for doc_id in doc_ids:
            if doc_id not in self.indexes:
                continue
            
            index = self.indexes[doc_id]
            chunks = self.corpus[doc_id]
            
            # Get scores
            scores = index.get_scores(query_tokens)
            
            # Get top results
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            
            for idx in top_indices:
                if scores[idx] > 0:
                    chunk = chunks[idx]
                    if exclude_image_chunks and chunk.get("chunk_type") == "image":
                        continue
                    results.append({
                        'chunk_id': chunk['chunk_id'],
                        'document_id': doc_id,
                        'content': chunk['content'],
                        'score': float(scores[idx]),
                        'chunk_type': chunk['chunk_type'],
                        'metadata': chunk
                    })
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"Found {len(results)} BM25 results")
        return results[:top_k]

    def search_by_phrase(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find chunks containing the meaningful phrase from the query."""
        from app.retrieval.query_boost import expand_search_terms, extract_section_phrases, normalize_query

        cleaned = normalize_query(query)
        stop = {
            "what", "is", "the", "a", "an", "how", "why", "when", "where", "who",
            "are", "does", "do", "explain", "describe", "tell", "me", "about", "for", "of",
        }
        terms = [t for t in re.findall(r"[a-z0-9]+", cleaned) if t not in stop and len(t) > 2]
        phrases = list(dict.fromkeys(
            extract_section_phrases(query)
            + expand_search_terms(cleaned)
            + [" ".join(terms)]
        ))
        phrases = sorted([p for p in phrases if p and len(p) > 3], key=len, reverse=True)
        # Prefer specific multi-word phrases to avoid matching thousands of chunks
        strong = [p for p in phrases if len(p) >= 12 or (" " in p and len(p) >= 8)]
        phrases = (strong or phrases)[:8]

        if not phrases:
            return []

        def _phrase_matches(phrase: str, content: str) -> bool:
            if len(phrase) >= 12 or " " in phrase:
                return phrase in content
            return bool(re.search(rf"\b{re.escape(phrase)}\b", content))

        results = []
        doc_ids = self._doc_ids_for_search(document_id, tenant_id, allowed_document_ids)

        for doc_id in doc_ids:
            if doc_id not in self.corpus:
                continue
            for chunk in self.corpus[doc_id]:
                if chunk.get("chunk_type") == "image":
                    continue
                content = (chunk.get("content") or "").lower()
                for phrase in phrases:
                    if _phrase_matches(phrase, content):
                        score = 10.0 + content.count(phrase)
                        if len(phrase) > 12:
                            score += 6.0
                        results.append({
                            "chunk_id": chunk["chunk_id"],
                            "document_id": doc_id,
                            "content": chunk["content"],
                            "score": score,
                            "chunk_type": chunk.get("chunk_type", "text"),
                            "metadata": chunk,
                        })
                        break

        results.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Phrase search found {len(results)} chunks")
        return results[:top_k]

    def search_section_context(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 8,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find section chunks that contain a heading/list for the topic in the query."""
        from app.retrieval.query_boost import (
            extract_section_phrases,
            is_list_query,
            is_section_definition_query,
        )

        if not (is_list_query(query) or is_section_definition_query(query)):
            return []

        phrases = extract_section_phrases(query)
        if not phrases:
            return []

        phrases = sorted(phrases, key=len, reverse=True)
        list_re = re.compile(r"(?:^|\n)\s*\d+[\.\)]\s+|\n\s*[-•]\s+", re.I)
        results = []
        doc_ids = self._doc_ids_for_search(document_id, tenant_id, allowed_document_ids)

        def _phrase_variants(phrase: str) -> List[str]:
            variants = [phrase]
            if "-" in phrase:
                variants.append(phrase.replace("-", " "))
                variants.append(phrase.replace("-", ""))
            return list(dict.fromkeys(v for v in variants if v))

        def _distinct_section_match(content_lower: str, phrase: str, pos: int) -> bool:
            pl = phrase.lower()
            if "non-functional" in pl or "non functional" in pl:
                window = content_lower[max(0, pos - 8): pos + len(phrase) + 8]
                return "non-functional" in window or "non functional" in window
            if pl.startswith("functional requirement"):
                before = content_lower[max(0, pos - 6): pos]
                if before.endswith("non-") or before.endswith("non "):
                    return False
            return True

        for doc_id in doc_ids:
            if doc_id not in self.corpus:
                continue
            for chunk in self.corpus[doc_id]:
                if chunk.get("chunk_type") == "image":
                    continue
                content = chunk.get("content") or ""
                if not content or len(content) > 5000:
                    continue

                cl = content.lower()
                matched_phrase = None
                match_pos = -1
                for phrase in phrases:
                    for variant in _phrase_variants(phrase):
                        start = 0
                        while True:
                            pos = cl.find(variant, start)
                            if pos < 0:
                                break
                            if _distinct_section_match(cl, variant, pos):
                                matched_phrase = variant
                                match_pos = pos
                                break
                            start = pos + 1
                    if matched_phrase:
                        break
                if not matched_phrase:
                    continue

                score = 18.0
                score += max(0.0, 18.0 - match_pos / 40.0)

                section_window = content[max(0, match_pos - 30): match_pos + len(matched_phrase) + 10]
                if "non-functional" not in matched_phrase.lower() and re.search(
                    r"non-functional\s+requirements", section_window, re.I
                ):
                    continue

                heading = re.search(
                    rf"(?:^|\n)\s*(?:\d+(?:\.\d+)*)?\s*{re.escape(matched_phrase)}\s*:?",
                    content,
                    re.I,
                )
                if heading:
                    score += 22.0

                # Prefer canonical numbered document sections (e.g. 2.3.1 Title).
                if re.search(
                    rf"\d+(?:\.\d+)+\s+{re.escape(matched_phrase)}\b",
                    section_window,
                    re.I,
                ):
                    score += 32.0

                if "non-functional" in matched_phrase and not re.search(
                    r"non-functional\s+requirements\s*:?", content, re.I
                ):
                    score -= 35.0

                tail = content[match_pos: match_pos + 1800]
                numbered_items = re.findall(r"(?:^|\n)\s*(\d+)[\.\)]\s+\S", tail)
                if numbered_items:
                    unique_nums = len(set(numbered_items))
                    score += min(unique_nums * 7.0, 42.0)
                    if numbered_items[0] == "1":
                        score += 12.0
                else:
                    labeled_items = re.findall(
                        r"(?:^|\n)\s*([A-Z][A-Za-z\s/&-]{3,40}):\s",
                        tail,
                    )
                    if len(labeled_items) >= 3:
                        score += min(len(labeled_items) * 5.0, 30.0)
                    elif list_re.search(tail):
                        score += 14.0
                    elif re.search(r"[.;]\s+[A-Z][a-z]", tail):
                        score += 8.0

                label_hits = len(
                    re.findall(rf"{re.escape(matched_phrase)}\s*:", content, re.I)
                )
                if label_hits > 1:
                    score -= 16.0 * (label_hits - 1)
                if re.search(r"\d+\.\d+\s+\w[\w\s-]*\s+Module", content, re.I) and label_hits > 1:
                    score -= 20.0

                if 350 <= len(content) <= 2800:
                    score += 10.0
                elif len(content) > 3500:
                    score -= 8.0

                results.append({
                    "chunk_id": chunk["chunk_id"],
                    "document_id": doc_id,
                    "content": chunk["content"],
                    "score": score,
                    "chunk_type": chunk.get("chunk_type", "text"),
                    "metadata": chunk,
                    "page_number": chunk.get("page_number"),
                })

        results.sort(key=lambda x: x["score"], reverse=True)

        deduped: List[Dict[str, Any]] = []
        seen_prefixes: set = set()
        for hit in results:
            prefix = (hit.get("content") or "")[:350]
            if prefix in seen_prefixes:
                continue
            seen_prefixes.add(prefix)
            deduped.append(hit)
            if len(deduped) >= top_k:
                break

        logger.info(f"Section search found {len(deduped)} chunks for: {phrases[0]}")
        return deduped

    def search_section_continuations(
        self,
        section_hits: List[Dict[str, Any]],
        document_id: Optional[str] = None,
        top_k: int = 4,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find chunks that complete a section hit truncated mid-sentence."""
        if not section_hits:
            return []

        results: List[Dict[str, Any]] = []
        seen_ids = {h.get("chunk_id") for h in section_hits if h.get("chunk_id")}
        doc_ids = self._doc_ids_for_search(document_id, tenant_id, allowed_document_ids)

        for hit in section_hits[:3]:
            content = (hit.get("content") or "").rstrip()
            if not content or content.endswith((".", "!", "?", ";")):
                continue

            trailing = re.search(r"([A-Z][A-Za-z\s/&-]{2,30}):\s*(.+)$", content)
            partial_text = trailing.group(2).strip() if trailing else content.split()[-12:]
            partial_text = " ".join(partial_text) if isinstance(partial_text, list) else partial_text
            label = trailing.group(1).strip() if trailing else ""
            label_key = f"{label.lower()}:" if label else ""

            for doc_id in doc_ids:
                if doc_id not in self.corpus:
                    continue
                for chunk in self.corpus[doc_id]:
                    chunk_id = chunk.get("chunk_id")
                    if not chunk_id or chunk_id in seen_ids:
                        continue

                    c = chunk.get("content") or ""
                    if not c or len(c) > 5000:
                        continue
                    cl = c.lower()

                    matched = False
                    score = float(hit.get("score", 0)) + 14.0

                    if label_key:
                        idx = cl.find(label_key)
                        if idx >= 0:
                            section_body = c[idx + len(label_key): idx + len(label_key) + 500].strip()
                            if len(section_body) > len(partial_text) + 20:
                                if section_body.lower().startswith(partial_text.lower()[:40]):
                                    score += 8.0
                                matched = True

                    if not matched and len(partial_text) >= 15:
                        fragment = partial_text.lower()[-25:]
                        frag_idx = cl.find(fragment)
                        if (
                            frag_idx >= 0
                            and len(c) > frag_idx + len(fragment) + 40
                            and chunk_id != hit.get("chunk_id")
                        ):
                            matched = True
                            score += 6.0

                    if not matched:
                        continue

                    seen_ids.add(chunk_id)
                    results.append({
                        "chunk_id": chunk_id,
                        "document_id": doc_id,
                        "content": c,
                        "score": score,
                        "chunk_type": chunk.get("chunk_type", "text"),
                        "metadata": chunk,
                        "page_number": chunk.get("page_number"),
                    })
                    break  # one continuation per anchor hit

        results.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Section continuation search found {len(results)} chunks")
        return results[:top_k]

    def search_counting_context(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 8,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find chunks needed to count numbered steps, modules, or stages for a topic."""
        from app.retrieval.query_boost import extract_count_topic, is_counting_query, normalize_query

        if not is_counting_query(query):
            return []

        topic = extract_count_topic(query).lower()
        topic_terms = [t for t in re.findall(r"[a-z0-9]+", topic) if len(t) > 3]
        numbered_label_re = re.compile(
            r"\b(step|module|component|layer|stage|phase|item|section)\s+(\d+)\s*:",
            re.I,
        )
        results = []
        doc_ids = self._doc_ids_for_search(document_id, tenant_id, allowed_document_ids)

        for doc_id in doc_ids:
            if doc_id not in self.corpus:
                continue
            for chunk in self.corpus[doc_id]:
                if chunk.get("chunk_type") == "image":
                    continue
                content = chunk.get("content") or ""
                if not content:
                    continue
                cl = content.lower()
                score = 0.0

                if topic and topic in cl:
                    score += 25.0
                elif topic_terms:
                    overlap = sum(1 for term in topic_terms if term in cl)
                    if overlap >= max(1, len(topic_terms) // 2):
                        score += 12.0 + overlap * 3.0

                labels = numbered_label_re.findall(content)
                list_items = re.findall(r"(?:^|\n)\s*\d+[\.\)]\s+\S", content)
                if labels or list_items:
                    if score > 0 or (topic_terms and any(term in cl for term in topic_terms)):
                        unique_nums = {int(num) for _, num in labels}
                        score += 10.0 + len(unique_nums or list_items) * 4.0
                    else:
                        continue
                elif score <= 0:
                    continue

                results.append({
                    "chunk_id": chunk["chunk_id"],
                    "document_id": doc_id,
                    "content": chunk["content"],
                    "score": score,
                    "chunk_type": chunk.get("chunk_type", "text"),
                    "metadata": chunk,
                    "page_number": chunk.get("page_number"),
                })

        by_label: Dict[int, Dict[str, Any]] = {}
        extras: List[Dict[str, Any]] = []
        for hit in sorted(results, key=lambda x: x["score"], reverse=True):
            labels = [int(num) for _, num in numbered_label_re.findall(hit["content"])]
            if labels:
                for num in labels:
                    if num not in by_label or hit["score"] > by_label[num]["score"]:
                        by_label[num] = hit
            else:
                extras.append(hit)

        merged = list(by_label.values()) + extras
        merged.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Counting search found {len(merged)} chunks for topic: {topic or query}")
        return merged[:top_k]

    def search_superlative_context(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 6,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find chunks that answer which entity ranks best/highest among a set."""
        from app.retrieval.query_boost import (
            _COMPARISON_MARKERS,
            _SUPERLATIVE_WORDS,
            extract_focus_terms,
            is_superlative_query,
        )

        if not is_superlative_query(query):
            return []

        focus_terms = extract_focus_terms(query)
        results = []
        doc_ids = self._doc_ids_for_search(document_id, tenant_id, allowed_document_ids)

        for doc_id in doc_ids:
            if doc_id not in self.corpus:
                continue
            for chunk in self.corpus[doc_id]:
                if chunk.get("chunk_type") == "image":
                    continue
                content = chunk.get("content") or ""
                if not content or len(content) > 5000:
                    continue

                cl = content.lower()
                term_matches = sum(1 for term in focus_terms if term in cl) if focus_terms else 0
                has_comparison = any(marker in cl for marker in _COMPARISON_MARKERS)
                has_superlative = any(word in cl for word in _SUPERLATIVE_WORDS)

                if focus_terms and term_matches == 0:
                    continue
                if not (has_comparison or has_superlative):
                    continue

                score = term_matches * 6.0
                if has_comparison:
                    score += 16.0
                if has_superlative:
                    score += 10.0
                if term_matches >= 2 and (has_comparison or has_superlative):
                    score += 12.0
                if bool(re.search(r"\d+\.?\d*\s*%", cl)):
                    score += 5.0
                if chunk.get("chunk_type") == "table" and term_matches >= 1:
                    score += 4.0 if has_comparison else -4.0
                if len(content) > 2500:
                    score -= 8.0

                if score <= 0:
                    continue
                results.append({
                    "chunk_id": chunk["chunk_id"],
                    "document_id": doc_id,
                    "content": chunk["content"],
                    "score": score,
                    "chunk_type": chunk.get("chunk_type", "text"),
                    "metadata": chunk,
                    "page_number": chunk.get("page_number"),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Superlative search found {len(results)} chunks")
        return results[:top_k]

    def search_model_comparison(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 6,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Backward-compatible alias for superlative/ranking retrieval."""
        return self.search_superlative_context(
            query, document_id=document_id, top_k=top_k, tenant_id=tenant_id
        )

    def search_model_metric(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find table/text chunks that mention both content terms and aggregation cues."""
        from app.retrieval.query_boost import expand_search_terms, normalize_query, _AGGREGATION_CUES

        search_terms = expand_search_terms(normalize_query(query))
        aggregation_terms = set(_AGGREGATION_CUES)
        model_terms = [t for t in search_terms if t not in aggregation_terms and len(t) > 2]
        metric_terms = [t for t in search_terms if t in aggregation_terms]

        if not model_terms:
            return []

        results = []
        doc_ids = self._doc_ids_for_search(document_id, tenant_id, allowed_document_ids)

        for doc_id in doc_ids:
            if doc_id not in self.corpus:
                continue
            for chunk in self.corpus[doc_id]:
                if chunk.get("chunk_type") == "image":
                    continue
                content = (chunk.get("content") or "").lower()
                if not any(model in content for model in model_terms):
                    continue

                score = 5.0
                if chunk.get("chunk_type") == "table":
                    score += 5.0
                if metric_terms and any(m in content for m in metric_terms):
                    score += 6.0
                elif "%" in content or re.search(r"\b\d+(?:\.\d+)?\b", content):
                    score += 3.0
                else:
                    continue

                results.append({
                    "chunk_id": chunk["chunk_id"],
                    "document_id": doc_id,
                    "content": chunk["content"],
                    "score": score,
                    "chunk_type": chunk.get("chunk_type", "text"),
                    "metadata": chunk,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Model-metric search found {len(results)} chunks for: {model_terms}")
        return results[:top_k]

    def search_figure_caption(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find chunks describing a figure, graph, or chart."""
        from app.retrieval.query_boost import expand_figure_search_phrases, normalize_query

        phrases = expand_figure_search_phrases(normalize_query(query))
        if not phrases:
            return []

        results = []
        doc_ids = self._doc_ids_for_search(document_id, tenant_id, allowed_document_ids)

        for doc_id in doc_ids:
            if doc_id not in self.corpus:
                continue
            for chunk in self.corpus[doc_id]:
                if chunk.get("chunk_type") == "image" and not (chunk.get("content") or "").strip():
                    continue
                content = (chunk.get("content") or "").lower()
                for phrase in phrases:
                    if phrase in content:
                        score = 12.0
                        if chunk.get("chunk_type") == "table":
                            score += 2.0
                        if chunk.get("chunk_type") in ("image", "multimodal"):
                            score += 1.0
                        results.append({
                            "chunk_id": chunk["chunk_id"],
                            "document_id": doc_id,
                            "content": chunk["content"],
                            "score": score,
                            "chunk_type": chunk.get("chunk_type", "text"),
                            "metadata": chunk,
                            "page_number": chunk.get("page_number"),
                        })
                        break

        results.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Figure-caption search found {len(results)} chunks")
        return results[:top_k]

    def search_table_rows(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find table or text chunks that contain a specific row key or table listing."""
        import re
        from app.retrieval.query_boost import (
            extract_row_keys,
            extract_table_column_terms,
            is_table_lookup_query,
            normalize_query,
        )

        row_keys = extract_row_keys(query)
        column_terms = extract_table_column_terms(query)
        if not row_keys and not is_table_lookup_query(query):
            return []

        results = []
        doc_ids = self._doc_ids_for_search(document_id, tenant_id, allowed_document_ids)

        for doc_id in doc_ids:
            if doc_id not in self.corpus:
                continue
            for chunk in self.corpus[doc_id]:
                if chunk.get("chunk_type") == "image":
                    continue
                content = chunk.get("content") or ""
                if not content:
                    continue

                score = self._score_table_row_chunk(
                    content, chunk, row_keys, column_terms, query
                )
                if score <= 0:
                    continue
                results.append({
                    "chunk_id": chunk["chunk_id"],
                    "document_id": doc_id,
                    "content": chunk["content"],
                    "score": score,
                    "chunk_type": chunk.get("chunk_type", "text"),
                    "metadata": chunk,
                    "page_number": chunk.get("page_number"),
                    "slide_number": chunk.get("slide_number"),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Table-row search found {len(results)} chunks for keys: {row_keys or 'lookup'}")
        return results[:top_k]

    def search_test_case_id(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Backward-compatible alias for search_table_rows."""
        return self.search_table_rows(
            query, document_id=document_id, top_k=top_k, tenant_id=tenant_id
        )

    def _score_table_row_chunk(
        self,
        content: str,
        chunk: Dict[str, Any],
        row_keys: List[str],
        column_terms: List[str],
        query: str,
    ) -> float:
        """Score how well a chunk answers a table row/column lookup query."""
        import re
        from app.retrieval.query_boost import normalize_query

        content_lower = content.lower()
        score = 0.0

        if chunk.get("chunk_type") == "table":
            score += 4.0
        if chunk.get("table_row_index") is not None:
            score += 8.0
        if "|" in content:
            score += 3.0
        if "headers:" in content_lower or "table row" in content_lower:
            score += 2.0

        for key in row_keys:
            if key.startswith("ROW-"):
                row_num = key.split("-", 1)[1]
                if re.search(rf"\brow\s*{row_num}\b", content, re.I):
                    score += 28.0
                elif re.search(rf"\b{re.escape(row_num)}\b", content) and "|" in content:
                    score += 18.0
            elif re.search(rf"\b{re.escape(key)}\b", content, re.I):
                score += 25.0
                if f"{key} |" in content.upper() or f"{key}|" in content.upper():
                    score += 10.0
                if re.search(
                    rf"{re.escape(key)}\s*\|[^|\n]{{3,}}",
                    content,
                    re.I,
                ):
                    score += 12.0

        if column_terms:
            matched_cols = sum(1 for term in column_terms if term in content_lower)
            score += matched_cols * 2.5

        q = normalize_query(query).lower()
        if not row_keys and "how many" in q:
            pipe_rows = len(re.findall(r"(?:^|\n)\s*(?:row\s+\d+|[^|\n]+\|[^|\n]+)", content, re.I))
            id_like = len(re.findall(r"\b[A-Z]{1,6}[-_]?\d{2,6}\b", content))
            if pipe_rows >= 3:
                score += min(pipe_rows, 15) + 10.0
            elif id_like >= 3:
                score += min(id_like, 15) + 8.0
            if "header" in content_lower or re.search(r"\b\w+\s*\|\s*\w+\s*\|\s*\w+", content):
                score += 6.0

        return score
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text"""
        # Simple tokenization - split on whitespace and lowercase
        tokens = text.lower().split()
        # Remove punctuation
        tokens = [token.strip('.,!?;:()[]{}"\'') for token in tokens]
        # Filter empty tokens
        tokens = [token for token in tokens if token]
        return tokens
    
    def delete_index(self, document_id: str) -> bool:
        """
        Delete index for a document
        
        Args:
            document_id: Document ID
            
        Returns:
            True if successful
        """
        if document_id in self.indexes:
            del self.indexes[document_id]
        if document_id in self.corpus:
            del self.corpus[document_id]
        self.document_tenants.pop(document_id, None)
        get_bm25_redis().delete_index(document_id)
        
        logger.info(f"Deleted BM25 index for document: {document_id}")
        return True
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            'total_documents': len(self.indexes),
            'total_chunks': sum(len(chunks) for chunks in self.corpus.values())
        }
