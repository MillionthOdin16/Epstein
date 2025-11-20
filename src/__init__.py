"""
Autonomous Investigative Architecture Package

This package provides tools for document ingestion, entity extraction,
and investigative lead management.
"""

__version__ = "1.0.0"

# Import modules conditionally to avoid dependency errors
try:
    from .database import DatabaseManager
    __all__ = ["DatabaseManager"]
except ImportError:
    pass

try:
    from .ingest import DocumentIngester
    if "DatabaseManager" in dir():
        __all__.append("DocumentIngester")
    else:
        __all__ = ["DocumentIngester"]
except ImportError:
    pass
