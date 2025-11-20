"""
Database module for storing investigation data.

This module handles SQLite database operations for storing documents
and extracted entities.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class InvestigationDB:
    """Manages the SQLite database for investigation data."""
    
    def __init__(self, db_path: str = "investigation.db"):
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Create the database and tables if they don't exist."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # Create documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL UNIQUE,
                    raw_text TEXT,
                    hash TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create entities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER NOT NULL,
                    entity_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    context_snippet TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_id) REFERENCES documents (id)
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_doc_id 
                ON entities(doc_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_type 
                ON entities(entity_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_hash 
                ON documents(hash)
            """)
            
            self.conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def document_exists(self, file_hash: str) -> bool:
        """
        Check if a document with the given hash already exists.
        
        Args:
            file_hash: Hash of the document
            
        Returns:
            True if document exists, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id FROM documents WHERE hash = ?",
                (file_hash,)
            )
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Error checking document existence: {e}")
            return False
    
    def insert_document(self, filename: str, raw_text: str, file_hash: str) -> Optional[int]:
        """
        Insert a new document into the database.
        
        Args:
            filename: Name of the document file
            raw_text: Extracted text content
            file_hash: Hash of the document
            
        Returns:
            Document ID if successful, None otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO documents (filename, raw_text, hash) VALUES (?, ?, ?)",
                (filename, raw_text, file_hash)
            )
            self.conn.commit()
            doc_id = cursor.lastrowid
            logger.debug(f"Inserted document: {filename} (ID: {doc_id})")
            return doc_id
        except sqlite3.IntegrityError:
            logger.warning(f"Document already exists: {filename}")
            return None
        except sqlite3.Error as e:
            logger.error(f"Error inserting document: {e}")
            return None
    
    def insert_entity(self, doc_id: int, entity_type: str, value: str, 
                     context_snippet: Optional[str] = None) -> Optional[int]:
        """
        Insert a new entity into the database.
        
        Args:
            doc_id: ID of the document containing the entity
            entity_type: Type of entity (PERSON, MONEY, DATE, etc.)
            value: The entity value/text
            context_snippet: Optional context around the entity
            
        Returns:
            Entity ID if successful, None otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO entities (doc_id, entity_type, value, context_snippet) 
                   VALUES (?, ?, ?, ?)""",
                (doc_id, entity_type, value, context_snippet)
            )
            self.conn.commit()
            entity_id = cursor.lastrowid
            logger.debug(f"Inserted entity: {entity_type} - {value} (ID: {entity_id})")
            return entity_id
        except sqlite3.Error as e:
            logger.error(f"Error inserting entity: {e}")
            return None
    
    def get_document_by_id(self, doc_id: int) -> Optional[Tuple]:
        """
        Retrieve a document by its ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Tuple of (id, filename, raw_text, hash, created_at) or None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM documents WHERE id = ?",
                (doc_id,)
            )
            return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error retrieving document: {e}")
            return None
    
    def get_entities_by_doc_id(self, doc_id: int) -> List[Tuple]:
        """
        Retrieve all entities for a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            List of entity tuples
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM entities WHERE doc_id = ?",
                (doc_id,)
            )
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error retrieving entities: {e}")
            return []
    
    def get_entities_by_type(self, entity_type: str) -> List[Tuple]:
        """
        Retrieve all entities of a specific type.
        
        Args:
            entity_type: Type of entity to retrieve
            
        Returns:
            List of entity tuples
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM entities WHERE entity_type = ?",
                (entity_type,)
            )
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error retrieving entities by type: {e}")
            return []
    
    def get_statistics(self) -> dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary with count statistics
        """
        try:
            cursor = self.conn.cursor()
            
            # Count documents
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            
            # Count entities
            cursor.execute("SELECT COUNT(*) FROM entities")
            entity_count = cursor.fetchone()[0]
            
            # Count entities by type
            cursor.execute("""
                SELECT entity_type, COUNT(*) 
                FROM entities 
                GROUP BY entity_type
            """)
            entity_by_type = dict(cursor.fetchall())
            
            return {
                'documents': doc_count,
                'entities': entity_count,
                'entities_by_type': entity_by_type
            }
        except sqlite3.Error as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
