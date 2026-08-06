"""
Plain text document loader
"""

from pathlib import Path
from typing import Any, Dict

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TextLoader:
    """Loader for plain text files (.txt, .md, .csv, .log, etc.)"""

    def __init__(self):
        self.supported_extensions = [".txt", ".md", ".csv", ".log", ".text", ".rst"]

    def load(self, file_path: str) -> Dict[str, Any]:
        logger.info(f"Loading text file: {file_path}")

        path = Path(file_path)
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        content = ""

        for encoding in encodings:
            try:
                content = path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

        if not content and path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")

        return {
            "paragraphs": [{"text": line, "style": "Normal", "level": 0} for line in content.splitlines() if line.strip()],
            "raw_content": content,
            "tables": [],
            "images": [],
            "metadata": {"filename": path.name, "encoding": "utf-8"},
        }

    def is_supported(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.supported_extensions
