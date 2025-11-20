"""
Database module for storing and querying analyzed data from Epstein Files.

This module provides functions to:
- Initialize the SQLite database schema
- Load documents from CSV into the database
- Query documents for analysis
"""

import sqlite3
import csv
import sys
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def get_db_connection(db_path: str = "data/epstein_analysis.db") -> sqlite3.Connection:
    """
    Get a connection to the SQLite database.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        SQLite connection object
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def init_database(db_path: str = "data/epstein_analysis.db") -> None:
    """
    Initialize the database schema.
    
    Args:
        db_path: Path to the SQLite database file
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Create documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            source_document_hash TEXT NOT NULL,
            category TEXT,
            source TEXT,
            text TEXT NOT NULL,
            page_number INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create entities table (for graph analysis)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            entity_type TEXT,
            first_seen_doc_id INTEGER,
            FOREIGN KEY (first_seen_doc_id) REFERENCES documents(id)
        )
    """)
    
    # Create entity co-occurrences table (for graph edges)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entity_cooccurrences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity1_id INTEGER NOT NULL,
            entity2_id INTEGER NOT NULL,
            document_id INTEGER NOT NULL,
            count INTEGER DEFAULT 1,
            FOREIGN KEY (entity1_id) REFERENCES entities(id),
            FOREIGN KEY (entity2_id) REFERENCES entities(id),
            FOREIGN KEY (document_id) REFERENCES documents(id),
            UNIQUE(entity1_id, entity2_id, document_id)
        )
    """)
    
    # Create financial data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            context TEXT,
            page_number INTEGER,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
    """)
    
    # Create locations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            location_name TEXT NOT NULL,
            location_type TEXT,
            airport_code TEXT,
            latitude REAL,
            longitude REAL,
            date_mentioned TEXT,
            page_number INTEGER,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
    """)
    
    # Create dates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dates_extracted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            date_value TEXT NOT NULL,
            date_context TEXT,
            page_number INTEGER,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
    """)
    
    # Create indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(source_document_hash)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_financial_amount ON financial_data(amount)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_date ON locations(date_mentioned)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dates_value ON dates_extracted(date_value)")
    
    conn.commit()
    conn.close()
    print(f"Database initialized at: {db_path}")


def compute_document_hash(filename: str, text: str) -> str:
    """
    Compute a unique hash for a document based on its filename and content.
    
    Args:
        filename: Document filename
        text: Document text content
        
    Returns:
        SHA256 hash of the document
    """
    content = f"{filename}:{text[:1000]}"  # Use filename and first 1000 chars
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def load_documents_from_csv(
    csv_path: str = "data/raw/EPS_FILES_20K_NOV2025.csv",
    db_path: str = "data/epstein_analysis.db",
    limit: Optional[int] = None
) -> int:
    """
    Load documents from CSV file into the database.
    
    Args:
        csv_path: Path to the CSV file
        db_path: Path to the SQLite database
        limit: Optional limit on number of documents to load (for testing)
        
    Returns:
        Number of documents loaded
    """
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    # Increase field size limit for large text fields
    csv.field_size_limit(sys.maxsize)
    
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    count = 0
    skipped = 0
    
    print(f"Loading documents from: {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            filename = row['filename']
            text = row['text']
            
            # Parse filename to extract category and source
            # Format: CATEGORY-SOURCE-IDENTIFIER.txt
            parts = filename.rsplit('.', 1)[0].split('-')
            category = parts[0] if len(parts) >= 1 else 'UNKNOWN'
            source = parts[1] if len(parts) >= 2 else '000'
            
            # Compute document hash
            doc_hash = compute_document_hash(filename, text)
            
            try:
                cursor.execute("""
                    INSERT INTO documents (filename, source_document_hash, category, source, text)
                    VALUES (?, ?, ?, ?, ?)
                """, (filename, doc_hash, category, source, text))
                count += 1
                
                if count % 1000 == 0:
                    print(f"Loaded {count} documents...")
                    conn.commit()
                
                if limit and count >= limit:
                    break
                    
            except sqlite3.IntegrityError:
                # Document already exists
                skipped += 1
    
    conn.commit()
    conn.close()
    
    print(f"Loaded {count} documents (skipped {skipped} duplicates)")
    return count


def get_all_documents(db_path: str = "data/epstein_analysis.db") -> List[Dict]:
    """
    Get all documents from the database.
    
    Args:
        db_path: Path to the SQLite database
        
    Returns:
        List of document dictionaries
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM documents")
    documents = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return documents


def get_document_by_id(doc_id: int, db_path: str = "data/epstein_analysis.db") -> Optional[Dict]:
    """
    Get a specific document by ID.
    
    Args:
        doc_id: Document ID
        db_path: Path to the SQLite database
        
    Returns:
        Document dictionary or None if not found
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None


def get_documents_sample(n: int = 100, db_path: str = "data/epstein_analysis.db") -> List[Dict]:
    """
    Get a random sample of documents.
    
    Args:
        n: Number of documents to sample
        db_path: Path to the SQLite database
        
    Returns:
        List of document dictionaries
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM documents ORDER BY RANDOM() LIMIT ?", (n,))
    documents = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return documents
