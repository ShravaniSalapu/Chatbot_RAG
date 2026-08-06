"""
Ingestion pipeline for document processing
"""

from typing import Dict, Any, Optional
from app.utils.file_utils import extension_to_document_type
from app.ingestion.loaders.pdf_loader import PDFLoader
from app.ingestion.loaders.docx_loader import DOCXLoader
from app.ingestion.loaders.pptx_loader import PPTXLoader
from app.ingestion.loaders.excel_loader import ExcelLoader
from app.ingestion.loaders.image_loader import ImageLoader
from app.ingestion.loaders.text_loader import TextLoader
from app.ingestion.content_extractor import MultimodalContentExtractor
from app.ingestion.parsers.docling_parser import DoclingParser
from app.ingestion.parsers.unstructured_parser import UnstructuredParser
from app.ingestion.parsers.layout_parser import LayoutParser
from app.ingestion.parsers.ocr_parser import OCRParser
from app.document_structure.heading_detector import HeadingDetector
from app.document_structure.section_detector import SectionDetector
from app.document_structure.caption_linker import CaptionLinker
from app.document_structure.table_context_linker import TableContextLinker
from app.document_structure.image_context_linker import ImageContextLinker
from app.document_structure.metadata_builder import MetadataBuilder
from app.utils.logger import setup_logger
import uuid
from pathlib import Path
import os

logger = setup_logger(__name__)


class IngestionPipeline:
    """Pipeline for ingesting and processing documents"""
    
    def __init__(
        self,
        use_docling: Optional[bool] = None,
        use_unstructured: Optional[bool] = None,
        ocr_engine: str = "auto",
    ):
        if use_docling is None:
            use_docling = os.getenv("USE_DOCLING", "false").lower() in ("1", "true", "yes")
        if use_unstructured is None:
            use_unstructured = os.getenv("USE_UNSTRUCTURED", "false").lower() in ("1", "true", "yes")

        self.pdf_loader = PDFLoader()
        self.docx_loader = DOCXLoader()
        self.pptx_loader = PPTXLoader()
        self.excel_loader = ExcelLoader()
        self.image_loader = ImageLoader()
        self.text_loader = TextLoader()
        
        self.docling_parser = DoclingParser() if use_docling else None
        self.unstructured_parser = UnstructuredParser() if use_unstructured else None
        self.layout_parser = LayoutParser()
        self._ocr_parser = None
        self._ocr_engine = ocr_engine
        
        self.heading_detector = HeadingDetector()
        self.section_detector = SectionDetector()
        self.caption_linker = CaptionLinker()
        self.table_context_linker = TableContextLinker()
        self.image_context_linker = ImageContextLinker()
        self.metadata_builder = MetadataBuilder()
        
        logger.info(f"Ingestion pipeline initialized with Docling: {use_docling}, Unstructured: {use_unstructured}, OCR: {ocr_engine} (lazy)")

    @property
    def ocr_parser(self) -> OCRParser:
        """Load OCR engines only when images need processing."""
        if self._ocr_parser is None:
            self._ocr_parser = OCRParser(ocr_engine=self._ocr_engine)
        return self._ocr_parser
    
    def ingest_document(self, file_path: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Ingest a document through the complete pipeline
        
        Args:
            file_path: Path to the document file
            document_id: Optional document ID
            
        Returns:
            Processed document data
        """
        logger.info(f"Starting ingestion pipeline for: {file_path}")
        
        document_id = document_id or str(uuid.uuid4())
        file_path = Path(file_path)
        
        # Step 1: Load document
        document_data = self._load_document(file_path)
        if not document_data:
            raise ValueError(f"Could not load document: {file_path}")
        
        # Step 2: Parse document structure
        parsed_data = self._parse_document(document_data, file_path)
        self._merge_parsed_content(document_data, parsed_data)

        # Attach nearby figure/table captions to PDF images for better chart Q&A
        document_data = self._enrich_pdf_images_with_captions(document_data)
        enable_ocr = os.getenv("ENABLE_OCR", "false").lower() in ("1", "true", "yes")
        needs_ocr = enable_ocr and (
            bool(document_data.get("images"))
            or any(slide.get("images") for slide in document_data.get("slides", []))
            or document_data.get("image_bytes")
        )
        extractor = MultimodalContentExtractor(
            ocr_parser=self.ocr_parser if needs_ocr else None
        )
        extracted = extractor.extract(document_data, str(file_path))
        document_data["tables"] = extracted["tables"]
        document_data["images"] = extracted["images"]
        
        # Step 3: Detect headings and sections
        text = self._extract_text(document_data)
        if extracted.get("supplemental_text"):
            text = f"{text}\n\n{extracted['supplemental_text']}".strip()
        headings = self.heading_detector.detect_headings(text)
        sections = self.section_detector.detect_sections(text, headings)
        
        # Step 4: Link captions
        captions = self.caption_linker.detect_captions(text)
        caption_links = self.caption_linker.link_all_captions(captions, document_data.get('tables', []) + document_data.get('images', []))
        
        # Step 5: Link context for tables and images
        tables = document_data.get('tables', [])
        images = document_data.get('images', [])
        
        tables = self.table_context_linker.link_table_context(tables, text)
        images = self.image_context_linker.link_image_context(images, text)
        
        # Step 6: Build metadata
        stored_name = file_path.name
        display_name = stored_name[len(document_id) + 1:] if stored_name.startswith(f"{document_id}_") else stored_name
        file_info = {
            'filename': display_name,
            'file_type': extension_to_document_type(str(file_path)),
            'file_size': file_path.stat().st_size
        }
        metadata = self.metadata_builder.build_document_metadata(document_data, file_info)
        
        # Step 7: Build document object
        from app.models.document_models import Document, DocumentMetadata
        document_obj = Document(
            document_id=document_id,
            metadata=DocumentMetadata(**metadata),
            elements=[],
            tables=tables,
            images=images,
            document_tree=parsed_data,
            raw_text=text
        )
        
        logger.info(f"Ingestion pipeline completed for document: {document_id}")
        
        return {
            'document': document_obj,
            'headings': headings,
            'sections': sections,
            'captions': captions,
            'caption_links': caption_links
        }
    
    def _load_document(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load document using appropriate loader"""
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return self.pdf_loader.load(str(file_path))
        elif suffix == '.docx':
            return self.docx_loader.load(str(file_path))
        elif suffix == '.pptx':
            return self.pptx_loader.load(str(file_path))
        elif suffix in ['.xlsx', '.xls']:
            return self.excel_loader.load(str(file_path))
        elif suffix in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff']:
            return self.image_loader.load(str(file_path))
        elif self.text_loader.is_supported(str(file_path)):
            return self.text_loader.load(str(file_path))
        else:
            logger.warning(f"Unsupported file type: {suffix}")
            return None
    
    def _parse_document(self, document_data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Parse document structure using both Docling and Unstructured"""
        parsed_results = {}
        
        # Try Docling first
        if self.docling_parser and self.docling_parser.docling_available:
            try:
                docling_result = self.docling_parser.parse(str(file_path))
                if docling_result.get('success'):
                    parsed_results['docling'] = docling_result['data']
                    logger.info("Docling parsing successful")
            except Exception as e:
                logger.warning(f"Docling parsing failed: {str(e)}")
        
        # Try Unstructured as well
        if self.unstructured_parser and self.unstructured_parser.unstructured_available:
            try:
                unstructured_result = self.unstructured_parser.parse(str(file_path))
                if unstructured_result.get('success'):
                    parsed_results['unstructured'] = unstructured_result['data']
                    logger.info("Unstructured parsing successful")
            except Exception as e:
                logger.warning(f"Unstructured parsing failed: {str(e)}")
        
        # Use layout parser as fallback
        if not parsed_results:
            layout_info = self.layout_parser.parse(document_data)
            parsed_results['layout'] = layout_info
            logger.info("Using layout parser as fallback")
        
        # Merge results if multiple parsers succeeded
        if 'docling' in parsed_results and 'unstructured' in parsed_results:
            # Use Docling as primary, supplement with Unstructured
            merged_data = parsed_results['docling'].copy()
            
            # Add any additional elements from Unstructured
            if 'tables' in parsed_results['unstructured']:
                if 'tables' not in merged_data:
                    merged_data['tables'] = []
                merged_data['tables'].extend(parsed_results['unstructured']['tables'])
            
            if 'images' in parsed_results['unstructured']:
                if 'images' not in merged_data:
                    merged_data['images'] = []
                merged_data['images'].extend(parsed_results['unstructured']['images'])
            
            return merged_data
        elif 'docling' in parsed_results:
            return parsed_results['docling']
        elif 'unstructured' in parsed_results:
            return parsed_results['unstructured']
        else:
            return parsed_results.get('layout', {})

    def _merge_parsed_content(self, document_data: Dict[str, Any], parsed_data: Dict[str, Any]) -> None:
        """Merge tables/images from layout/docling/unstructured parsers into loader output."""
        if not parsed_data:
            return

        for key in ("tables", "images"):
            extra = parsed_data.get(key) or []
            if not extra:
                continue
            existing = document_data.setdefault(key, [])
            existing_ids = {
                item.get("table_id") or item.get("image_id")
                for item in existing
                if item.get("table_id") or item.get("image_id")
            }
            for item in extra:
                item_id = item.get("table_id") or item.get("image_id")
                if item_id and item_id in existing_ids:
                    continue
                existing.append(item)
                if item_id:
                    existing_ids.add(item_id)

        if parsed_data.get("text") and not self._extract_text(document_data).strip():
            document_data["raw_content"] = parsed_data["text"]

    def _enrich_pdf_images_with_captions(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Copy figure/chart captions from PDF page text onto image metadata."""
        import re

        if "pages" not in document_data:
            return document_data

        caption_pattern = re.compile(
            r"(figure|fig\.?|table|chart)\s*[\d\.]+[:\.\-]?\s*.+",
            re.IGNORECASE,
        )

        for image in document_data.get("images", []):
            page_num = image.get("page_number")
            if not page_num:
                continue

            page_text = ""
            for page in document_data["pages"]:
                if page.get("page_number") == page_num:
                    page_text = page.get("text", "")
                    break

            if not page_text:
                continue

            captions = [line.strip() for line in page_text.splitlines() if caption_pattern.match(line.strip())]
            if captions:
                joined = " | ".join(captions[:3])
                image["caption"] = joined
                image["description"] = joined
                image["chart_data_text"] = joined

        return document_data
    
    def _extract_text(self, document_data: Dict[str, Any]) -> str:
        """Extract full text from document"""
        text_parts = []
        
        if 'pages' in document_data:
            for page in document_data['pages']:
                text_parts.append(page.get('text', ''))
        elif 'paragraphs' in document_data:
            for para in document_data['paragraphs']:
                text_parts.append(para.get('text', ''))
        elif 'slides' in document_data:
            for slide in document_data['slides']:
                text_parts.append(slide.get('text', ''))
        elif 'sheets' in document_data:
            for sheet in document_data['sheets']:
                sheet_name = sheet.get('sheet_name', 'Sheet')
                rows = sheet.get('rows') or []
                if not rows:
                    continue
                text_parts.append(f"Sheet: {sheet_name}")
                for row in rows:
                    text_parts.append(' | '.join(str(cell) for cell in row))
        elif document_data.get('raw_content'):
            text_parts.append(document_data['raw_content'])
        
        return ' '.join(text_parts)
