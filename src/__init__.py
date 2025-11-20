"""
Autonomous Investigative Architecture Package

This package provides tools for document ingestion, entity extraction,
and investigative lead management.
"""

__version__ = "1.0.0"
__all__ = []

# Import modules conditionally to avoid dependency errors
try:
    from .database import DatabaseManager
    __all__.append("DatabaseManager")
except ImportError:
    pass

try:
    from .ingest import DocumentIngester
    __all__.append("DocumentIngester")
except ImportError:
    pass
