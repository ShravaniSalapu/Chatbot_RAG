"""
Excel document loader
"""

from typing import Dict, List, Any
from pathlib import Path
from openpyxl import load_workbook
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ExcelLoader:
    """Loader for Excel documents"""
    
    def __init__(self):
        self.supported_extensions = ['.xlsx', '.xls']
    
    def load(self, file_path: str) -> Dict[str, Any]:
        """
        Load an Excel file and extract its content
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dictionary containing Excel content and metadata
        """
        logger.info(f"Loading Excel file: {file_path}")
        
        try:
            wb = load_workbook(file_path, data_only=True)
            
            sheets_data = []
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                sheet_data = {
                    'sheet_name': sheet_name,
                    'rows': [],
                    'tables': []
                }
                
                # Extract all rows
                for row in sheet.iter_rows(values_only=True):
                    sheet_data['rows'].append([str(cell) if cell is not None else '' for cell in row])
                
                sheets_data.append(sheet_data)
            
            # Extract metadata
            metadata = self._extract_metadata(wb)
            
            return {
                'sheets': sheets_data,
                'metadata': metadata,
                'total_sheets': len(sheets_data)
            }
            
        except Exception as e:
            logger.error(f"Error loading Excel file {file_path}: {str(e)}")
            raise
    
    def load_from_bytes(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Load an Excel file from bytes
        
        Args:
            file_bytes: Excel file as bytes
            
        Returns:
            Dictionary containing Excel content and metadata
        """
        logger.info("Loading Excel from bytes")
        
        try:
            import io
            wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
            
            sheets_data = []
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                sheet_data = {
                    'sheet_name': sheet_name,
                    'rows': [],
                    'tables': []
                }
                
                for row in sheet.iter_rows(values_only=True):
                    sheet_data['rows'].append([str(cell) if cell is not None else '' for cell in row])
                
                sheets_data.append(sheet_data)
            
            metadata = self._extract_metadata(wb)
            
            return {
                'sheets': sheets_data,
                'metadata': metadata,
                'total_sheets': len(sheets_data)
            }
            
        except Exception as e:
            logger.error(f"Error loading Excel from bytes: {str(e)}")
            raise
    
    def _extract_metadata(self, wb) -> Dict[str, Any]:
        """Extract metadata from Excel workbook"""
        try:
            return {
                'title': wb.properties.title if hasattr(wb.properties, 'title') else '',
                'author': wb.properties.creator if hasattr(wb.properties, 'creator') else '',
                'subject': wb.properties.subject if hasattr(wb.properties, 'subject') else '',
                'created': wb.properties.created if hasattr(wb.properties, 'created') else None,
                'modified': wb.properties.modified if hasattr(wb.properties, 'modified') else None
            }
        except Exception as e:
            logger.warning(f"Could not extract Excel metadata: {str(e)}")
            return {}
    
    def is_supported(self, file_path: str) -> bool:
        """Check if file is supported"""
        return Path(file_path).suffix.lower() in self.supported_extensions
