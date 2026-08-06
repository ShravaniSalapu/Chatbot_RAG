"""
Boost retrieval scores using query term and phrase overlap.
"""

from typing import List, Dict, Any
import re

_STOP_WORDS = frozenset({
    "what", "is", "the", "a", "an", "how", "why", "when", "where", "who",
    "are", "does", "do", "explain", "describe", "tell", "me", "about", "of",
    "in", "for", "and", "or", "to", "with", "from", "this", "that", "be",
})

_TEXT_CHUNK_TYPES = frozenset({"text", "child", "semantic", "section", "table", "multimodal"})
_IMAGE_CHUNK_TYPES = frozenset({"image"})
_QA_CHUNK_TYPES = _TEXT_CHUNK_TYPES


def normalize_query(query: str) -> str:
    """Strip smart quotes and normalize whitespace (no domain-specific rewrites)."""
    cleaned = query.strip().strip("\"'“”‘’`").lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


# Query-shape cues only (not business column names or domain vocabulary)
_AGGREGATION_CUES = frozenset({
    "total", "sum", "average", "mean", "min", "max", "count",
})
_TABLE_STRUCTURE_CUES = frozenset({
    "table", "row", "rows", "column", "columns", "cell", "worksheet",
    "spreadsheet", "header", "headers", "field", "fields", "record", "entry",
})

_ROW_KEY_PATTERNS = [
    re.compile(r"\b[A-Z]{1,6}[-_]?\d{2,6}\b", re.I),   # TC005, REQ-12, US-101
    re.compile(r"\b[A-Z]\d{2,6}\b", re.I),             # A12, R42
]


def extract_row_keys(query: str) -> List[str]:
    """Extract row/record identifiers from any document table (not just test cases)."""
    keys: List[str] = []
    for pattern in _ROW_KEY_PATTERNS:
        keys.extend(m.upper() for m in pattern.findall(query))

    for match in re.finditer(
        r"\b(?:row|item|entry|record|case|id|#)\s*#?\s*(\d{1,6})\b",
        query,
        re.I,
    ):
        keys.append(f"ROW-{match.group(1)}")

    return list(dict.fromkeys(k for k in keys if k))


def extract_test_case_ids(query: str) -> List[str]:
    """Backward-compatible alias — returns generic row keys from the query."""
    return extract_row_keys(query)


def extract_table_column_terms(query: str) -> List[str]:
    """Column-related terms inferred from query phrasing (no fixed vocabulary)."""
    q = normalize_query(query).lower()
    terms: List[str] = []

    for pattern in (
        r"(?:column|field|header)\s+(?:named\s+)?['\"]?([^'\"?,]+)['\"]?",
        r"what is the\s+([^?,]+?)\s+(?:for|in|of|column|field)\b",
        r"(?:what|which)\s+([^?,]+?)\s+(?:column|field)\b",
    ):
        for match in re.finditer(pattern, q):
            terms.extend(_content_terms(match.group(1)))

    if not terms:
        terms = _content_terms(query)
    return list(dict.fromkeys(terms))


def is_table_lookup_query(query: str) -> bool:
    """True when the user is asking about a specific row/column in a table."""
    if extract_row_keys(query):
        return True

    q = normalize_query(query).lower()
    if any(cue in q for cue in ("from table", "in the table", "from the table", "table row")):
        return True
    if any(cue in q for cue in _TABLE_STRUCTURE_CUES):
        return True

    if "how many" in q and any(w in q for w in ("row", "rows", "entry", "record", "column")):
        return True

    # "for <identifier> what is <field>" — row lookup shape, no domain terms
    if re.search(r"\bfor\s+(?:the\s+)?\S+", q) and re.search(r"\bwhat is\b", q):
        return True

    terms = set(_content_terms(query))
    id_terms = terms & {"row", "entry", "record", "case", "id", "code", "item", "no", "number"}
    return bool(terms) and bool(id_terms or extract_row_keys(query))


def is_test_case_query(query: str) -> bool:
    """Backward-compatible alias for table row lookups."""
    return is_table_lookup_query(query)


def is_table_metric_query(query: str) -> bool:
    """True when the user is likely asking about numbers in a table."""
    if is_table_lookup_query(query):
        return True
    q = normalize_query(query).lower()
    if any(cue in q for cue in _AGGREGATION_CUES):
        return True
    if "how many" in q:
        return True
    return any(cue in q for cue in ("table", "spreadsheet", "worksheet"))


def is_list_query(query: str) -> bool:
    """True when the user wants a full list from the document."""
    if is_counting_query(query):
        return True
    q = normalize_query(query).lower()
    list_cues = (
        "what are the", "what are", "list all", "list the", "enumerate",
        "types of", "examples of", "components of", "features of",
        "advantages", "disadvantages",
    )
    return any(cue in q for cue in list_cues) or ("how many" in q and "there" in q)


def is_counting_query(query: str) -> bool:
    """True for 'how many steps/modules/components' questions."""
    q = normalize_query(query).lower()
    return bool(
        re.search(
            r"how many\s+(steps?|modules?|components?|layers?|stages?|phases?|metrics?|models?)",
            q,
        )
    )


_SUPERLATIVE_WORDS = frozenset({
    "highest", "best", "top", "greatest", "maximum", "max", "lowest", "minimum",
    "min", "most", "least", "largest", "smallest", "fastest", "slowest",
})

_COMPARISON_MARKERS = (
    "outperformed", "better than", "worse than", "compared to", "compared with",
    "higher than", "lower than", "best performance", "top performance",
    "achieved the highest", "ranked first", "leading", "superior to",
    "more effective", "less effective",
)

_SCOPE_CUES = (
    "out of all", "among all", "among the", "all the", "all ",
    "which ", "between", "compare", "comparison", "versus", " vs ",
)


def extract_focus_terms(query: str) -> List[str]:
    """Content terms from the query, excluding superlative and question scaffolding."""
    q = normalize_query(query).lower()
    for cue in _SCOPE_CUES:
        q = q.replace(cue, " ")
    for word in _SUPERLATIVE_WORDS:
        q = q.replace(word, " ")
    q = re.sub(r"\b(?:which|what|who|got|get|gets|have|has|had|were|was|are|is)\b", " ", q)
    return _content_terms(q)


def is_superlative_query(query: str) -> bool:
    """True when the user asks which item ranks best/highest among a set."""
    q = normalize_query(query).lower()
    has_superlative = any(word in q for word in _SUPERLATIVE_WORDS)
    has_scope = any(cue in q for cue in _SCOPE_CUES) or q.strip().startswith("which ")
    return has_superlative and has_scope


def is_model_comparison_query(query: str) -> bool:
    """Backward-compatible alias for ranking/superlative questions."""
    return is_superlative_query(query)


def extract_count_topic(query: str) -> str:
    """Topic anchor for counting questions, e.g. the subject after 'how many steps for ...'."""
    q = normalize_query(query).strip()
    q = re.sub(
        r"^how many\s+(?:steps?|modules?|components?|layers?|stages?|phases?|metrics?|models?)\s+"
        r"(?:for|in|of|does|are|were|there)?\s*",
        "",
        q,
        flags=re.I,
    )
    return q.strip(" ?.")


def is_requirements_list_query(query: str) -> bool:
    """True when the user asks for a requirements-style list from the document."""
    q = normalize_query(query).lower()
    return "requirements" in q and is_list_query(query)


def extract_section_phrases(query: str) -> List[str]:
    """Extract section/layer titles from definition-style questions."""
    q = normalize_query(query).strip()
    q = re.sub(
        r"^(?:what|who|how|why|when|where|explain|describe|tell(?:\s+me)?)\s+"
        r"(?:is|are|does|do|me\s+about)?\s*",
        "",
        q,
    )
    q = re.sub(r"^\d+\.?\s*", "", q)
    q = re.sub(r"^(?:the|a|an)\s+", "", q.strip())
    q = q.strip(" ?.")

    phrases: List[str] = []
    if len(q) >= 4:
        phrases.append(q)

    if " and " in q:
        for part in q.split(" and "):
            part = part.strip(" ?.")
            part = re.sub(r"^(?:the|a|an)\s+", "", part)
            if len(part) >= 4:
                phrases.append(part)

    expanded: List[str] = []
    for phrase in phrases:
        expanded.append(phrase)
        base = re.sub(r"\s+(layer|module|stage|phase|step)\s*$", "", phrase).strip()
        if base and base != phrase:
            expanded.append(base)
        if "-" in phrase:
            expanded.append(phrase.replace("-", " "))
            expanded.append(phrase.replace("-", ""))
            if base:
                expanded.append(base.replace("-", " "))

        # Only add structural suffix variants for short section titles (layers/modules).
        if any(word in phrase for word in ("requirements", "specification", "architecture", "introduction")):
            continue
        if base and base != phrase:
            expanded.append(f"{base} module")
            expanded.append(f"{base} and refinement")
        for suffix in (" layer", " module", " stage", " phase"):
            if not phrase.endswith(suffix.strip()):
                expanded.append(f"{phrase}{suffix}")
                if base:
                    expanded.append(f"{base}{suffix}")

    return list(dict.fromkeys(p for p in expanded if p and len(p) >= 4))


def is_section_definition_query(query: str) -> bool:
    """True for 'what is Post-Processing Layer' style questions."""
    if is_table_lookup_query(query) or is_visual_query(query):
        return False
    return bool(extract_section_phrases(query))


def expand_search_terms(query: str) -> List[str]:
    """Extra terms/phrases derived from the query itself (no fixed vocabulary)."""
    terms = list(_content_terms(query))
    extras: List[str] = []

    for match in re.finditer(r"['\"]([^'\"]+)['\"]", query):
        phrase = match.group(1).strip().lower()
        if phrase:
            extras.append(phrase)
            extras.extend(_content_terms(phrase))

    for match in re.finditer(r"\b[\w]+[-/][\w]+\b", query, re.I):
        token = match.group(0).lower()
        extras.extend([token, token.replace("-", " "), token.replace("-", ""), token.replace("/", " ")])

    for match in re.finditer(r"[A-Z][a-z]+(?:[A-Z][a-z]+)+", query):
        spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", match.group(0)).lower()
        extras.append(spaced)
        extras.extend(_content_terms(spaced))

    for term in terms:
        if term in _AGGREGATION_CUES and term not in extras:
            extras.append(term)

    return list(dict.fromkeys(terms + extras))


def _content_terms(query: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", normalize_query(query).lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 2]


_WORD_NUMBERS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
}


def is_visual_query(query: str) -> bool:
    """True when the user is asking about images, charts, or figures."""
    q = normalize_query(query).lower()
    visual_words = (
        "image", "chart", "figure", "diagram", "photo", "picture", "graph",
        "plot", "illustration", "visualization", "architecture", "confusion matrix",
    )
    if any(word in q for word in visual_words):
        return True
    if re.search(r"\bfig\.?\s*\d", q) or re.search(r"\bfigure\s+(\d+|\w+)", q):
        return True
    if "tells about" in q or "shows about" in q or "tell us" in q:
        return True
    return False


def expand_figure_search_phrases(query: str) -> List[str]:
    """Build caption-style phrases to find figure/graph descriptions in text."""
    q = normalize_query(query).lower()
    phrases: List[str] = []

    fig_match = re.search(r"figure\s+(\d+|\w+)", q)
    if fig_match:
        num = fig_match.group(1)
        num = _WORD_NUMBERS.get(num, num)
        phrases.extend([f"figure {num}", f"fig. {num}", f"fig {num}"])

    fig_match = re.search(r"\bfig\.?\s*(\d+)", q)
    if fig_match:
        num = fig_match.group(1)
        phrases.extend([f"figure {num}", f"fig. {num}"])

    # Keep meaningful multi-word phrases from the query (graph/chart questions)
    cleaned = re.sub(r"\b(what|does|do|tell|tells|about|the|is|are|show|shows|us|me)\b", " ", q)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > 8:
        phrases.append(cleaned)

    for token in ("graph", "chart", "diagram", "figure", "plot"):
        if token in q:
            parts = [p.strip() for p in q.split() if p not in _STOP_WORDS and len(p) > 2]
            if len(parts) >= 2:
                phrases.append(" ".join(parts[:8]))

    return list(dict.fromkeys(p for p in phrases if p and len(p) > 2))


def filter_qa_chunks(results: List[Dict[str, Any]], allow_images: bool = False) -> List[Dict[str, Any]]:
    """Remove image caption chunks from Q&A retrieval unless explicitly allowed."""
    if allow_images:
        return results
    filtered = []
    for result in results:
        chunk_type = result.get("chunk_type") or (result.get("metadata") or {}).get("chunk_type", "")
        if chunk_type in _IMAGE_CHUNK_TYPES:
            continue
        filtered.append(result)
    return filtered


def boost_results_by_query(query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Re-score results so chunks that literally contain the query win."""
    if not results or not query.strip():
        return results

    query_lower = normalize_query(query).lower()
    terms = _content_terms(query)
    key_phrase = " ".join(terms)

    for result in results:
        content = (result.get("content") or "").lower()
        base = float(result.get("combined_score", result.get("score", 0)))
        boost = 0.0

        if query_lower in content:
            boost += 8.0
        elif key_phrase and key_phrase in content:
            boost += 6.0

        if terms:
            matched = sum(1 for term in terms if term in content)
            boost += matched * 0.75

        chunk_type = result.get("chunk_type") or (result.get("metadata") or {}).get("chunk_type", "")
        visual_q = is_visual_query(query)

        if chunk_type == "image":
            if visual_q:
                boost += 3.0
                if any(p in content for p in expand_figure_search_phrases(query)):
                    boost += 6.0
            else:
                boost -= 10.0
        elif chunk_type == "table":
            boost += 2.5
            if is_table_metric_query(query) or is_table_lookup_query(query):
                boost += 4.0
        elif chunk_type in _TEXT_CHUNK_TYPES:
            boost += 1.0
            if visual_q:
                for phrase in expand_figure_search_phrases(query):
                    if phrase in content:
                        boost += 7.0
                        break

        # Boost section/layer title matches (Post-Processing Layer, Refinement, etc.)
        for phrase in extract_section_phrases(query):
            if phrase in content:
                boost += 14.0
            elif phrase.replace("-", " ") in content:
                boost += 12.0
            elif phrase.replace("-", "") in content.replace("-", ""):
                boost += 10.0
            if re.search(rf"\d+(?:\.\d+)+\s+{re.escape(phrase)}\b", content, re.I):
                boost += 18.0
            numbered_after = re.search(
                rf"{re.escape(phrase)}.*?(?:^|\n)\s*1[\.\)]\s+",
                content,
                re.I | re.S,
            )
            if numbered_after:
                boost += 12.0

        if is_counting_query(query):
            if re.search(r"\bstep\s+\d+\s*:", content, re.I):
                boost += 12.0
            topic = extract_count_topic(query).lower()
            if topic and topic in content:
                boost += 10.0

        if is_list_query(query) and len(content) > 5000:
            boost -= 20.0

        if is_superlative_query(query):
            focus_terms = extract_focus_terms(query)
            if any(marker in content for marker in _COMPARISON_MARKERS):
                boost += 10.0
            if any(word in content for word in _SUPERLATIVE_WORDS):
                boost += 6.0
            if focus_terms:
                matched_focus = sum(1 for term in focus_terms if term in content)
                boost += matched_focus * 2.0
                if matched_focus >= 2:
                    boost += 4.0

        # Strong boost when a row key from the query appears in a table-style chunk
        row_keys = extract_row_keys(query)
        if row_keys:
            for key in row_keys:
                if key.startswith("ROW-"):
                    row_num = key.split("-", 1)[1]
                    if re.search(rf"\brow\s*{row_num}\b", content, re.I):
                        boost += 15.0
                        break
                    if re.search(rf"\b{re.escape(row_num)}\b", content) and "|" in content:
                        boost += 10.0
                        break
                elif re.search(rf"\b{re.escape(key)}\b", content, re.I):
                    boost += 15.0
                    if "|" in content:
                        boost += 5.0
                    break

        # Boost when content terms and aggregation cues both appear (table-style answers)
        search_terms = expand_search_terms(query)
        aggregation_terms = set(_AGGREGATION_CUES)
        model_terms = [t for t in search_terms if t not in aggregation_terms and len(t) > 2]
        metric_terms = [t for t in search_terms if t in aggregation_terms]
        if model_terms and metric_terms:
            has_model = any(t in content for t in model_terms)
            has_metric = any(t in content for t in metric_terms)
            if has_model and has_metric:
                boost += 8.0
            elif has_model and "%" in content:
                boost += 5.0

        result["score"] = base + boost
        result["combined_score"] = result["score"]

    results.sort(key=lambda item: item.get("combined_score", item.get("score", 0)), reverse=True)
    return results


def prefer_substantive_chunks(
    query: str,
    results: List[Dict[str, Any]],
    min_chars: int = 120,
) -> List[Dict[str, Any]]:
    """Drop tiny caption-only chunks unless they match the query well."""
    if not results:
        return results

    terms = _content_terms(query)
    key_phrase = " ".join(terms)
    visual_q = is_visual_query(query)
    row_keys = extract_row_keys(query)
    column_terms = extract_table_column_terms(query)
    section_phrases = extract_section_phrases(query)
    list_q = is_list_query(query)
    if list_q or section_phrases:
        min_chars = min(min_chars, 50)
    figure_phrases = expand_figure_search_phrases(query) if visual_q else []
    kept: List[Dict[str, Any]] = []

    def _matches_section(text: str) -> bool:
        lower = text.lower()
        for phrase in section_phrases:
            if phrase in lower or phrase.replace("-", " ") in lower:
                return True
        return False

    def _has_numbered_list(text: str) -> bool:
        return bool(re.search(r"(?:^|\n)\s*\d+[\.\)]\s+\S", text))

    def _matches_row_key(text: str) -> bool:
        for key in row_keys:
            if key.startswith("ROW-"):
                row_num = key.split("-", 1)[1]
                if re.search(rf"\brow\s*{row_num}\b", text, re.I):
                    return True
                if re.search(rf"\b{re.escape(row_num)}\b", text) and "|" in text:
                    return True
            elif re.search(rf"\b{re.escape(key)}\b", text, re.I):
                return True
        return False

    for result in results:
        chunk_type = result.get("chunk_type") or (result.get("metadata") or {}).get("chunk_type", "")
        if chunk_type == "image" and not visual_q:
            continue

        content = result.get("content") or ""
        content_lower = content.lower()
        is_match = (
            key_phrase in content_lower
            or any(term in content_lower for term in terms)
            or any(phrase in content_lower for phrase in figure_phrases)
            or _matches_row_key(content)
            or (column_terms and any(term in content_lower for term in column_terms) and "|" in content)
            or _matches_section(content)
        )

        if section_phrases and _matches_section(content):
            kept.append(result)
            continue
        if list_q and (_has_numbered_list(content) or len(content) >= min_chars):
            kept.append(result)
            continue
        if row_keys and _matches_row_key(content):
            kept.append(result)
            continue
        if chunk_type == "table" and (is_table_metric_query(query) or is_table_lookup_query(query)):
            kept.append(result)
            continue
        if visual_q and is_match:
            kept.append(result)
            continue
        if len(content) >= min_chars or is_match:
            kept.append(result)

    return kept
