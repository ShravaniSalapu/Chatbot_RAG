"""
Text utility functions
"""

import re
from typing import List, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing
    
    Args:
        text: Input text
        
    Returns:
        Cleaned text
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences
    
    Args:
        text: Input text
        
    Returns:
        List of sentences
    """
    # Simple sentence splitting
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def count_words(text: str) -> int:
    """
    Count words in text
    
    Args:
        text: Input text
        
    Returns:
        Word count
    """
    return len(text.split())


def estimate_tokens(text: str) -> int:
    """
    Estimate token count (roughly 0.75 words per token)
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    word_count = count_words(text)
    return int(word_count / 0.75)


def remove_citations(text: str) -> str:
    """
    Remove citation markers from text
    
    Args:
        text: Input text with citations
        
    Returns:
        Text without citations
    """
    # Remove [1], [2], etc.
    text = re.sub(r'\[\d+\]', '', text)
    return clean_text(text)


def extract_citations(text: str) -> List[int]:
    """
    Extract citation numbers from text
    
    Args:
        text: Input text with citations
        
    Returns:
        List of citation numbers
    """
    citations = re.findall(r'\[(\d+)\]', text)
    return [int(c) for c in citations]


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text
    
    Args:
        text: Input text
        
    Returns:
        Text with normalized whitespace
    """
    # Replace newlines with spaces
    text = text.replace('\n', ' ')
    # Replace tabs with spaces
    text = text.replace('\t', ' ')
    # Remove multiple spaces
    text = re.sub(r' +', ' ', text)
    return text.strip()


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """
    Extract top keywords from text (simple frequency-based)
    
    Args:
        text: Input text
        top_n: Number of top keywords to return
        
    Returns:
        List of keywords
    """
    # Simple word frequency
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Remove common words
    stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been', 'will', 'with', 'that', 'this', 'from', 'they', 'would', 'there', 'their', 'what', 'about', 'which', 'when', 'make', 'like', 'into', 'year', 'your', 'just', 'over', 'also', 'such', 'because', 'these', 'first', 'being', 'through', 'most', 'must', 'some', 'after', 'back', 'only', 'could', 'under', 'should', 'into'}
    
    words = [w for w in words if w not in stop_words]
    
    # Count frequency
    from collections import Counter
    word_counts = Counter(words)
    
    # Return top N
    return [word for word, count in word_counts.most_common(top_n)]


def merge_texts(texts: List[str], separator: str = "\n\n") -> str:
    """
    Merge multiple texts with separator
    
    Args:
        texts: List of texts to merge
        separator: Separator between texts
        
    Returns:
        Merged text
    """
    return separator.join(filter(None, texts))
