"""
Database module for the autonomous investigative architecture.

This module provides SQLite database operations for storing documents,
entities, and investigative leads with aggressive error handling.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# Configure module-specific logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler('error.log')
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)


class DatabaseManager:
    """Manages SQLite database operations for the investigation system."""
    
    def __init__(self, db_path: str = "investigation.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        try:
            self._initialize_database()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise
    
    def _initialize_database(self) -> None:
        """Create database tables if they don't exist."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            
            # Create documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash TEXT NOT NULL UNIQUE,
                    path TEXT NOT NULL,
                    raw_text TEXT,
                    ingested_at TIMESTAMP NOT NULL
                )
            """)
            
            # Create entities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('PERSON', 'ORG', 'LOC')),
                    value TEXT NOT NULL,
                    confidence REAL,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            
            # Create leads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_value TEXT NOT NULL,
                    suspicion_score REAL,
                    status TEXT NOT NULL DEFAULT 'NEW' CHECK(status IN ('NEW', 'INVESTIGATING', 'CLOSED')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_hash 
                ON documents(hash)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_doc_id 
                ON entities(doc_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_type 
                ON entities(type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_leads_status 
                ON leads(status)
            """)
            
            self.conn.commit()
            logger.info("Database initialized successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}", exc_info=True)
            raise
    
    def insert_document(self, hash_value: str, path: str, raw_text: str) -> Optional[int]:
        """
        Insert a document into the database.
        
        Args:
            hash_value: SHA-256 hash of the document
            path: File path of the document
            raw_text: Extracted text content
            
        Returns:
            Document ID if successful, None otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO documents (hash, path, raw_text, ingested_at)
                VALUES (?, ?, ?, ?)
            """, (hash_value, path, raw_text, datetime.now()))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Document already exists (duplicate hash)
            logger.info(f"Document with hash {hash_value} already exists, skipping")
            return None
        except sqlite3.Error as e:
            logger.error(f"Error inserting document: {e}", exc_info=True)
            return None
    
    def document_exists(self, hash_value: str) -> bool:
        """
        Check if a document with the given hash already exists.
        
        Args:
            hash_value: SHA-256 hash to check
            
        Returns:
            True if document exists, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM documents WHERE hash = ?", (hash_value,))
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Error checking document existence: {e}", exc_info=True)
            return False
    
    def insert_entity(self, doc_id: int, entity_type: str, value: str, 
                     confidence: float) -> Optional[int]:
        """
        Insert an entity extracted from a document.
        
        Args:
            doc_id: Document ID
            entity_type: Type of entity (PERSON, ORG, LOC)
            value: Entity value/name
            confidence: Confidence score (0-1)
            
        Returns:
            Entity ID if successful, None otherwise
        """
        try:
            if entity_type not in ('PERSON', 'ORG', 'LOC'):
                logger.error(f"Invalid entity type: {entity_type}")
                return None
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO entities (doc_id, type, value, confidence)
                VALUES (?, ?, ?, ?)
            """, (doc_id, entity_type, value, confidence))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error inserting entity: {e}", exc_info=True)
            return None
    
    def insert_lead(self, entity_value: str, suspicion_score: float, 
                   status: str = 'NEW') -> Optional[int]:
        """
        Insert a new investigative lead.
        
        Args:
            entity_value: Entity name/value for the lead
            suspicion_score: Suspicion score
            status: Lead status (NEW, INVESTIGATING, CLOSED)
            
        Returns:
            Lead ID if successful, None otherwise
        """
        try:
            if status not in ('NEW', 'INVESTIGATING', 'CLOSED'):
                logger.error(f"Invalid lead status: {status}")
                return None
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO leads (entity_value, suspicion_score, status)
                VALUES (?, ?, ?)
            """, (entity_value, suspicion_score, status))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error inserting lead: {e}", exc_info=True)
            return None
    
    def update_lead_status(self, lead_id: int, status: str) -> bool:
        """
        Update the status of a lead.
        
        Args:
            lead_id: Lead ID
            status: New status (NEW, INVESTIGATING, CLOSED)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if status not in ('NEW', 'INVESTIGATING', 'CLOSED'):
                logger.error(f"Invalid lead status: {status}")
                return False
            
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE leads 
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (status, datetime.now(), lead_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error updating lead status: {e}", exc_info=True)
            return False
    
    def get_document_by_hash(self, hash_value: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by its hash.
        
        Args:
            hash_value: SHA-256 hash
            
        Returns:
            Document data as dictionary, or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE hash = ?", (hash_value,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error retrieving document: {e}", exc_info=True)
            return None
    
    def get_entities_by_document(self, doc_id: int) -> List[Dict[str, Any]]:
        """
        Get all entities for a specific document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            List of entity dictionaries
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM entities WHERE doc_id = ?", (doc_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving entities: {e}", exc_info=True)
            return []
    
    def get_leads_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get all leads with a specific status.
        
        Args:
            status: Lead status to filter by
            
        Returns:
            List of lead dictionaries
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE status = ?", (status,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving leads: {e}", exc_info=True)
            return []
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with counts of documents, entities, and leads
        """
        try:
            cursor = self.conn.cursor()
            stats = {}
            
            cursor.execute("SELECT COUNT(*) FROM documents")
            stats['total_documents'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM entities")
            stats['total_entities'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM leads")
            stats['total_leads'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'NEW'")
            stats['new_leads'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'INVESTIGATING'")
            stats['investigating_leads'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'CLOSED'")
            stats['closed_leads'] = cursor.fetchone()[0]
            
            return stats
        except sqlite3.Error as e:
            logger.error(f"Error retrieving statistics: {e}", exc_info=True)
            return {}
    
    def close(self) -> None:
        """Close the database connection."""
        try:
            if self.conn:
                self.conn.close()
                logger.info("Database connection closed")
        except sqlite3.Error as e:
            logger.error(f"Error closing database: {e}", exc_info=True)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
