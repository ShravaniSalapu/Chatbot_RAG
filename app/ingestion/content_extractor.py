"""
Extract and normalize text, tables, images, and charts from loaded documents.
"""

from __future__ import annotations

import base64
import io
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from app.utils.logger import setup_logger

if TYPE_CHECKING:
    from app.ingestion.parsers.ocr_parser import OCRParser

logger = setup_logger(__name__)

CHART_KEYWORDS = (
    "chart", "graph", "plot", "diagram", "figure", "bar", "line", "pie",
    "scatter", "histogram", "trend", "axis", "legend", "visualization",
)


class MultimodalContentExtractor:
    """Normalize tables/images from loader output and enrich with OCR/chart text."""

    def __init__(self, ocr_parser: Optional["OCRParser"] = None):
        self.ocr_parser = ocr_parser

    def extract(self, document_data: Dict[str, Any], file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Build normalized tables, images, and supplemental text from raw loader data.

        Returns:
            dict with keys: tables, images, supplemental_text
        """
        suffix = Path(file_path).suffix.lower() if file_path else ""
        tables = self._collect_tables(document_data, suffix)
        images = self._collect_images(document_data, suffix)

        normalized_tables = [self._normalize_table(table, idx) for idx, table in enumerate(tables)]
        normalized_images = []
        supplemental_parts: List[str] = []

        for idx, image in enumerate(images):
            normalized = self._normalize_image(image, idx, file_path)
            normalized_images.append(normalized)
            if normalized.get("ocr_text"):
                supplemental_parts.append(normalized["ocr_text"])
            if normalized.get("chart_data_text"):
                supplemental_parts.append(normalized["chart_data_text"])

        for table in normalized_tables:
            table_text = table.get("text_representation", "")
            if table_text:
                supplemental_parts.append(table_text)

        logger.info(
            f"Extracted {len(normalized_tables)} tables and {len(normalized_images)} images "
            f"({sum(1 for i in normalized_images if i.get('is_chart'))} charts)"
        )

        return {
            "tables": normalized_tables,
            "images": normalized_images,
            "supplemental_text": "\n\n".join(supplemental_parts),
        }

    def _collect_tables(self, document_data: Dict[str, Any], suffix: str) -> List[Dict[str, Any]]:
        if document_data.get("tables"):
            return list(document_data["tables"])

        tables: List[Dict[str, Any]] = []

        # Excel workbooks — each sheet is one table
        if "sheets" in document_data:
            for sheet in document_data["sheets"]:
                rows = sheet.get("rows") or []
                if not rows:
                    continue
                sheet_name = sheet.get("sheet_name") or "Sheet"
                tables.append(
                    {
                        "table_id": str(uuid.uuid4()),
                        "rows": rows,
                        "caption": sheet_name,
                        "title": sheet_name,
                        "location": f"Sheet: {sheet_name}",
                    }
                )
            if tables:
                return tables

        if "slides" in document_data:
            for slide in document_data["slides"]:
                slide_num = slide.get("slide_number", 0)
                for table in slide.get("tables", []):
                    entry = dict(table)
                    entry.setdefault("slide_number", slide_num)
                    entry.setdefault("location", f"Slide {slide_num}")
                    tables.append(entry)
        return tables

    def _collect_images(self, document_data: Dict[str, Any], suffix: str) -> List[Dict[str, Any]]:
        if document_data.get("images"):
            return list(document_data["images"])

        images: List[Dict[str, Any]] = []
        if "slides" in document_data:
            for slide in document_data["slides"]:
                slide_num = slide.get("slide_number", 0)
                for image in slide.get("images", []):
                    entry = dict(image)
                    entry.setdefault("slide_number", slide_num)
                    entry.setdefault("location", f"Slide {slide_num}")
                    images.append(entry)

        if document_data.get("image_bytes") and not images:
            images.append(
                {
                    "image_id": str(uuid.uuid4()),
                    "image_bytes": document_data["image_bytes"],
                    "location": "Image file",
                }
            )

        return images

    def _normalize_table(self, table: Dict[str, Any], index: int) -> Dict[str, Any]:
        table_id = table.get("table_id") or str(uuid.uuid4())
        raw_data = table.get("data") or table.get("rows") or []

        headers: List[str] = []
        rows: List[List[str]] = []

        if raw_data:
            cleaned = [[str(cell or "").strip() for cell in row] for row in raw_data if row]
            if cleaned:
                first_row = cleaned[0]
                if self._row_looks_like_header(first_row) and len(cleaned) > 1:
                    headers = first_row
                    rows = cleaned[1:]
                elif self._row_looks_like_header(first_row) and len(cleaned) == 1:
                    headers = first_row
                    rows = []
                else:
                    headers = [f"Column {i + 1}" for i in range(len(first_row))]
                    rows = cleaned

        # PDF tables often lose row data — recover from inline pipe text when available
        if not rows and table.get("inline_text"):
            parsed_headers, parsed_rows = self._parse_inline_table(table["inline_text"])
            if parsed_rows:
                headers = parsed_headers or headers
                rows = parsed_rows

        caption = table.get("caption") or table.get("title") or ""
        location = table.get("location") or self._table_location(table, index)
        text_repr = self._table_to_text(headers, rows, caption, location)
        summary = table.get("summary") or self._fallback_table_summary(headers, rows, caption)

        if headers and location.lower().startswith("sheet:"):
            col_count = len(headers)
            summary = (
                f"Spreadsheet {caption or location} has {col_count} columns: "
                f"{', '.join(headers)}. Contains {len(rows)} data rows."
            )
            schema_line = f"Column headers ({col_count}): {' | '.join(headers)}"
            text_repr = f"{schema_line}\n{text_repr}".strip()

        return {
            "table_id": table_id,
            "headers": headers,
            "rows": rows,
            "caption": caption,
            "summary": summary,
            "text_representation": text_repr,
            "page_number": table.get("page_number"),
            "slide_number": table.get("slide_number"),
            "table_index": table.get("table_index", index),
            "location": location,
            "context_before": table.get("context_before", ""),
            "context_after": table.get("context_after", ""),
        }

    def _normalize_image(self, image: Dict[str, Any], index: int, file_path: Optional[str]) -> Dict[str, Any]:
        image_id = image.get("image_id") or str(uuid.uuid4())
        caption = image.get("caption", "")
        location = image.get("location") or self._image_location(image, index)
        is_chart = bool(image.get("is_chart")) or self._looks_like_chart(image, caption)
        chart_type = image.get("chart_type", "chart" if is_chart else "")

        ocr_text = image.get("ocr_text", "")
        if not ocr_text and self.ocr_parser and (image.get("image_bytes") or image.get("file_path")):
            ocr_text = self._run_ocr(image)

        chart_data_text = image.get("chart_data_text", "")
        if is_chart and chart_data_text:
            description = chart_data_text
        elif ocr_text:
            description = ocr_text
        elif caption:
            description = caption
        elif image.get("description"):
            description = image["description"]
        else:
            description = f"Image at {location}"

        if is_chart and ocr_text and chart_data_text:
            description = f"{chart_data_text}\n{ocr_text}".strip()

        return {
            "image_id": image_id,
            "caption": caption,
            "description": description,
            "ocr_text": ocr_text,
            "chart_data_text": chart_data_text,
            "is_chart": is_chart,
            "chart_type": chart_type,
            "page_number": image.get("page_number"),
            "slide_number": image.get("slide_number"),
            "location": location,
            "context_before": image.get("context_before", ""),
            "context_after": image.get("context_after", ""),
            "image_bytes": image.get("image_bytes"),
        }

    def _run_ocr(self, image: Dict[str, Any]) -> str:
        if not self.ocr_parser or not self.ocr_parser.active_engine:
            return ""

        try:
            if image.get("image_bytes"):
                raw = image["image_bytes"]
                if isinstance(raw, str):
                    raw = base64.b64decode(raw)
                result = self.ocr_parser.parse_image_from_bytes(raw)
            elif image.get("file_path"):
                result = self.ocr_parser.parse_image(image["file_path"])
            else:
                return ""

            if result.get("success"):
                return (result.get("text") or "").strip()
        except Exception as exc:
            logger.warning(f"OCR failed for image {image.get('image_id')}: {exc}")

        return ""

    def _table_to_text(
        self,
        headers: List[str],
        rows: List[List[str]],
        caption: str,
        location: str,
    ) -> str:
        parts = []
        if caption:
            parts.append(f"Table: {caption}")
        if location:
            parts.append(f"Location: {location}")
        if headers:
            parts.append("Headers: " + " | ".join(headers))
        for row_idx, row in enumerate(rows[:50]):
            parts.append(f"Row {row_idx + 1}: " + " | ".join(row))
        if len(rows) > 50:
            parts.append(f"... and {len(rows) - 50} more rows")
        return "\n".join(parts)

    def _fallback_table_summary(self, headers: List[str], rows: List[List[str]], caption: str) -> str:
        parts = []
        if caption:
            parts.append(f"Table: {caption}")
        if headers:
            parts.append(f"Columns: {', '.join(headers)}")
        if rows:
            parts.append(f"Contains {len(rows)} rows")
        return ". ".join(parts) if parts else "Table data"

    def _parse_inline_table(self, inline_text: str) -> tuple[List[str], List[List[str]]]:
        """Parse pipe-separated table text (common in PDF/PPT exports)."""
        lines = [line.strip() for line in inline_text.splitlines() if line.strip()]
        if not lines:
            return [], []

        parsed = [self._split_table_line(line) for line in lines]
        parsed = [row for row in parsed if any(cell for cell in row)]
        if not parsed:
            return [], []

        if self._row_looks_like_header(parsed[0]) and len(parsed) > 1:
            return parsed[0], parsed[1:]
        return [], parsed

    @staticmethod
    def _split_table_line(line: str) -> List[str]:
        if "|" in line:
            return [cell.strip() for cell in line.split("|")]
        if "\t" in line:
            return [cell.strip() for cell in line.split("\t")]
        return [line.strip()]

    def _row_looks_like_header(self, row: List[str]) -> bool:
        if not row:
            return False
        non_empty = [cell for cell in row if cell]
        if not non_empty:
            return False
        numeric = sum(1 for cell in non_empty if self._is_numeric(cell))
        return numeric <= len(non_empty) / 2

    def _is_numeric(self, value: str) -> bool:
        cleaned = value.replace(",", "").replace("$", "").replace("%", "").strip()
        if not cleaned:
            return False
        try:
            float(cleaned)
            return True
        except ValueError:
            return False

    def _looks_like_chart(self, image: Dict[str, Any], caption: str) -> bool:
        if image.get("chart_type"):
            return True
        text = " ".join(
            [
                caption,
                image.get("description", ""),
                image.get("ocr_text", ""),
                image.get("chart_data_text", ""),
            ]
        ).lower()
        return any(keyword in text for keyword in CHART_KEYWORDS)

    def _table_location(self, table: Dict[str, Any], index: int) -> str:
        if table.get("page_number"):
            return f"Page {table['page_number']}"
        if table.get("slide_number"):
            return f"Slide {table['slide_number']}"
        return f"Table {index + 1}"

    def _image_location(self, image: Dict[str, Any], index: int) -> str:
        if image.get("page_number"):
            return f"Page {image['page_number']}"
        if image.get("slide_number"):
            return f"Slide {image['slide_number']}"
        return f"Image {index + 1}"


def save_temp_image(image_bytes: bytes, suffix: str = ".png") -> str:
    """Write image bytes to a temp file for OCR engines that need a path."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(image_bytes)
        return tmp.name
