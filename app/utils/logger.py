"""
Logger configuration for the application
"""

from loguru import logger
import sys
import os
from pathlib import Path


def setup_logger(name: str):
    """
    Set up logger for a module
    
    Args:
        name: Module name
        
    Returns:
        Logger instance
    """
    # Remove default handler
    logger.remove()
    
    # Add console handler with format
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    # Add file handler
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / "app.log",
        rotation="500 MB",
        retention="10 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    return logger
