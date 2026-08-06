"""
File utility functions
"""

import os
import hashlib
from pathlib import Path
from typing import Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_file_hash(file_path: str) -> str:
    """
    Calculate MD5 hash of a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        MD5 hash string
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(file_path)


def ensure_directory(directory: str) -> Path:
    """
    Ensure directory exists, create if it doesn't
    
    Args:
        directory: Directory path
        
    Returns:
        Path object
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_file_extension(file_path: str) -> str:
    """
    Get file extension
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension (with dot)
    """
    return Path(file_path).suffix.lower()


def extension_to_document_type(file_path: str) -> str:
    """
    Map a file extension to a DocumentType enum value (pdf, docx, pptx, image, excel, text).
    """
    ext = get_file_extension(file_path)

    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    if ext == ".pptx":
        return "pptx"
    if ext in (".xlsx", ".xls"):
        return "excel"
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"):
        return "image"
    if ext in (".txt", ".md", ".csv", ".log", ".text", ".rst"):
        return "text"

    raise ValueError(f"Unsupported file type: {ext}")


def is_supported_file(file_path: str, supported_extensions: list) -> bool:
    """
    Check if file is supported
    
    Args:
        file_path: Path to the file
        supported_extensions: List of supported extensions (with dots)
        
    Returns:
        True if file is supported
    """
    return get_file_extension(file_path) in supported_extensions


def clean_filename(filename: str) -> str:
    """
    Clean filename by removing special characters
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Remove special characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    return filename


def get_unique_filename(directory: str, filename: str) -> str:
    """
    Get a unique filename in directory
    
    Args:
        directory: Directory path
        filename: Desired filename
        
    Returns:
        Unique filename
    """
    dir_path = Path(directory)
    file_path = dir_path / filename
    
    if not file_path.exists():
        return filename
    
    # Add counter
    base_name = file_path.stem
    extension = file_path.suffix
    counter = 1
    
    while True:
        new_filename = f"{base_name}_{counter}{extension}"
        new_path = dir_path / new_filename
        if not new_path.exists():
            return new_filename
        counter += 1


def delete_file(file_path: str) -> bool:
    """
    Delete a file safely
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if successful
    """
    try:
        Path(file_path).unlink()
        logger.info(f"Deleted file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False
