"""
PPTX document loader — recursively extracts text, tables, images, and charts.
"""

import base64
import uuid
from typing import Dict, List, Any, Optional, Iterator
from pathlib import Path
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class PPTXLoader:
    """Loader for PPTX documents"""

    def __init__(self):
        self.supported_extensions = ['.pptx']

    def load(self, file_path: str) -> Dict[str, Any]:
        return self._load_presentation(Presentation(file_path))

    def load_from_bytes(self, file_bytes: bytes) -> Dict[str, Any]:
        import io
        return self._load_presentation(Presentation(io.BytesIO(file_bytes)))

    def _load_presentation(self, prs: Presentation) -> Dict[str, Any]:
        logger.info("Loading PPTX presentation")

        slides_content = []
        all_tables: List[Dict[str, Any]] = []
        all_images: List[Dict[str, Any]] = []

        for slide_idx, slide in enumerate(prs.slides):
            slide_num = slide_idx + 1
            slide_data = {
                'slide_number': slide_num,
                'text': '',
                'shapes': [],
                'tables': [],
                'images': [],
            }

            for shape in self._iter_shapes(slide.shapes):
                self._process_shape(shape, slide_num, slide_data, all_tables, all_images)

            slides_content.append(slide_data)

        metadata = self._extract_metadata(prs)
        logger.info(
            f"PPTX loaded: {len(slides_content)} slides, "
            f"{len(all_tables)} tables, {len(all_images)} images/charts"
        )

        return {
            'slides': slides_content,
            'tables': all_tables,
            'images': all_images,
            'metadata': metadata,
            'total_slides': len(slides_content),
        }

    def _iter_shapes(self, shapes) -> Iterator:
        """Walk shapes recursively — pictures/tables/charts are often inside groups."""
        for shape in shapes:
            yield shape
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                yield from self._iter_shapes(shape.shapes)

    def _process_shape(
        self,
        shape,
        slide_num: int,
        slide_data: Dict[str, Any],
        all_tables: List[Dict[str, Any]],
        all_images: List[Dict[str, Any]],
    ) -> None:
        if hasattr(shape, "text") and shape.text and shape.text.strip():
            slide_data['shapes'].append({
                'text': shape.text,
                'shape_type': shape.shape_type,
            })
            slide_data['text'] += shape.text + '\n'

        if getattr(shape, "has_table", False):
            table_data = []
            for row in shape.table.rows:
                row_data = [cell.text for cell in row.cells]
                table_data.append(row_data)
            if table_data:
                inline_text = self._table_to_text(table_data)
                table_entry = {
                    'table_id': str(uuid.uuid4()),
                    'data': table_data,
                    'inline_text': inline_text,
                    'slide_number': slide_num,
                    'location': f"Slide {slide_num}",
                }
                slide_data['tables'].append(table_entry)
                all_tables.append(table_entry)
                slide_data['text'] += inline_text + '\n'

        image_entry = self._extract_shape_image(shape, slide_num)
        if image_entry:
            slide_data['images'].append(image_entry)
            all_images.append(image_entry)

        chart_entry = self._extract_chart_data(shape, slide_num)
        if chart_entry:
            slide_data['images'].append(chart_entry)
            all_images.append(chart_entry)
            slide_data['text'] += chart_entry.get('chart_data_text', '') + '\n'

    def _table_to_text(self, table_data: List[List[str]]) -> str:
        lines = []
        for row in table_data:
            if row:
                lines.append(" | ".join(str(cell or "") for cell in row))
        return "\n".join(lines)
    
    def _extract_metadata(self, prs: Presentation) -> Dict[str, Any]:
        """Extract metadata from PPTX"""
        try:
            core_props = prs.core_properties
            return {
                'title': core_props.title or '',
                'author': core_props.author or '',
                'subject': core_props.subject or '',
                'keywords': core_props.keywords or '',
                'created': core_props.created,
                'modified': core_props.modified,
                'last_modified_by': core_props.last_modified_by or ''
            }
        except Exception as e:
            logger.warning(f"Could not extract PPTX metadata: {str(e)}")
            return {}
    
    def _extract_shape_image(self, shape, slide_num: int) -> Optional[Dict[str, Any]]:
        """Extract embedded picture from a slide shape (including grouped shapes)."""
        if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
            return None
        if not hasattr(shape, "image"):
            return None

        try:
            blob = shape.image.blob
            if not blob or len(blob) < 100:
                return None
            caption = (shape.name or "").strip()
            return {
                'image_id': str(uuid.uuid4()),
                'image_bytes': base64.b64encode(blob).decode('utf-8'),
                'caption': caption,
                'slide_number': slide_num,
                'location': f"Slide {slide_num}",
                'is_chart': 'chart' in caption.lower(),
            }
        except Exception as exc:
            logger.debug(f"Could not extract image from slide {slide_num}: {exc}")
            return None

    def _extract_chart_data(self, shape, slide_num: int) -> Optional[Dict[str, Any]]:
        """Extract readable text/data from PowerPoint chart shapes."""
        if not getattr(shape, "has_chart", False):
            return None

        try:
            chart = shape.chart
            parts: List[str] = []

            if chart.has_title and chart.chart_title and chart.chart_title.has_text_frame:
                title = chart.chart_title.text_frame.text.strip()
                if title:
                    parts.append(f"Chart title: {title}")

            chart_type = str(getattr(chart, "chart_type", "chart"))
            parts.append(f"Chart type: {chart_type}")

            for plot in chart.plots:
                try:
                    categories = [cat.label for cat in plot.categories if getattr(cat, "label", None)]
                    if categories:
                        parts.append("Categories: " + ", ".join(str(c) for c in categories))
                except Exception:
                    pass

            for series in chart.series:
                series_name = getattr(series, "name", "") or "Series"
                try:
                    values = list(series.values)
                    if values:
                        parts.append(f"{series_name} values: " + ", ".join(str(v) for v in values))
                except Exception:
                    parts.append(f"{series_name}: (values unavailable)")

            chart_text = "\n".join(parts)
            if not chart_text.strip():
                return None

            return {
                'image_id': str(uuid.uuid4()),
                'caption': chart.chart_title.text_frame.text.strip() if chart.has_title and chart.chart_title else "Chart",
                'chart_data_text': chart_text,
                'description': chart_text,
                'slide_number': slide_num,
                'location': f"Slide {slide_num}",
                'is_chart': True,
                'chart_type': chart_type,
            }
        except Exception as exc:
            logger.warning(f"Could not extract chart from slide {slide_num}: {exc}")
            return None

    def is_supported(self, file_path: str) -> bool:
        """Check if file is supported"""
        return Path(file_path).suffix.lower() in self.supported_extensions
