"""
Investigative Suite

A Python-based investigative framework for analyzing documents with OCR and entity extraction.
"""

__version__ = "1.0.0"

from .db import InvestigationDB
from .librarian import ingest_documents, detect_duplicates
from .detective import extract_entities, find_relationships

__all__ = [
    'InvestigationDB',
    'ingest_documents',
    'detect_duplicates',
    'extract_entities',
    'find_relationships',
]
