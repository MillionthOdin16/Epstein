#!/usr/bin/env python3
"""
Database module for forensic investigation.

This module manages the SQLite database for storing documents, entities,
and forensic analysis findings.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime


class InvestigationDB:
    """SQLite database manager for investigation data."""
    
    def __init__(self, db_path: str = "investigation.db"):
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
    
    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                content TEXT,
                category TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Entities table (people, organizations, locations mentioned)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                entity_type TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Document-Entity relationships (co-occurrence tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                entity_id INTEGER NOT NULL,
                mention_count INTEGER DEFAULT 1,
                FOREIGN KEY (document_id) REFERENCES documents(id),
                FOREIGN KEY (entity_id) REFERENCES entities(id),
                UNIQUE(document_id, entity_id)
            )
        """)
        
        # Findings table - stores anomalies detected by analytics engines
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                finding_type TEXT NOT NULL,
                severity TEXT DEFAULT 'medium',
                entity_id INTEGER,
                document_id INTEGER,
                description TEXT,
                metadata TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(id),
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_filename 
            ON documents(filename)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_name 
            ON entities(name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_findings_type 
            ON findings(finding_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_entities_doc 
            ON document_entities(document_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_entities_entity 
            ON document_entities(entity_id)
        """)
        
        self.conn.commit()
    
    def add_document(self, filename: str, content: str, 
                     category: Optional[str] = None, 
                     source: Optional[str] = None) -> int:
        """
        Add a document to the database.
        
        Args:
            filename: Document filename
            content: Document text content
            category: Document category (e.g., 'IMAGES', 'TEXT')
            source: Source identifier (e.g., '001', '002')
        
        Returns:
            Document ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO documents (filename, content, category, source)
            VALUES (?, ?, ?, ?)
        """, (filename, content, category, source))
        self.conn.commit()
        
        # Return the document ID
        cursor.execute("SELECT id FROM documents WHERE filename = ?", (filename,))
        result = cursor.fetchone()
        return result[0] if result else None
    
    def add_entity(self, name: str, entity_type: Optional[str] = None) -> int:
        """
        Add an entity to the database.
        
        Args:
            name: Entity name
            entity_type: Type of entity (e.g., 'person', 'organization', 'location')
        
        Returns:
            Entity ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO entities (name, entity_type)
            VALUES (?, ?)
        """, (name, entity_type))
        self.conn.commit()
        
        # Return the entity ID
        cursor.execute("SELECT id FROM entities WHERE name = ?", (name,))
        result = cursor.fetchone()
        return result[0] if result else None
    
    def add_document_entity(self, document_id: int, entity_id: int, 
                           mention_count: int = 1):
        """
        Link a document with an entity (co-occurrence).
        
        Args:
            document_id: Document ID
            entity_id: Entity ID
            mention_count: Number of times entity appears in document
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO document_entities 
            (document_id, entity_id, mention_count)
            VALUES (?, ?, ?)
        """, (document_id, entity_id, mention_count))
        self.conn.commit()
    
    def add_finding(self, finding_type: str, description: str,
                    severity: str = 'medium',
                    entity_id: Optional[int] = None,
                    document_id: Optional[int] = None,
                    metadata: Optional[str] = None) -> int:
        """
        Add a forensic finding to the database.
        
        Args:
            finding_type: Type of finding (e.g., 'bridge_entity', 'benfords_violation', 'silence_interval')
            description: Human-readable description of the finding
            severity: Severity level ('low', 'medium', 'high', 'critical')
            entity_id: Related entity ID (if applicable)
            document_id: Related document ID (if applicable)
            metadata: Additional metadata as JSON string
        
        Returns:
            Finding ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO findings 
            (finding_type, severity, entity_id, document_id, description, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (finding_type, severity, entity_id, document_id, description, metadata))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        Retrieve all documents from the database.
        
        Returns:
            List of documents as dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM documents")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_entities(self) -> List[Dict[str, Any]]:
        """
        Retrieve all entities from the database.
        
        Returns:
            List of entities as dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entities")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_document_entities(self, document_id: int) -> List[Dict[str, Any]]:
        """
        Get all entities mentioned in a document.
        
        Args:
            document_id: Document ID
        
        Returns:
            List of entities with mention counts
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT e.*, de.mention_count
            FROM entities e
            JOIN document_entities de ON e.id = de.entity_id
            WHERE de.document_id = ?
        """, (document_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_entity_documents(self, entity_id: int) -> List[Dict[str, Any]]:
        """
        Get all documents mentioning an entity.
        
        Args:
            entity_id: Entity ID
        
        Returns:
            List of documents
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT d.*, de.mention_count
            FROM documents d
            JOIN document_entities de ON d.id = de.document_id
            WHERE de.entity_id = ?
        """, (entity_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_findings(self, finding_type: Optional[str] = None,
                     severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve findings with optional filtering.
        
        Args:
            finding_type: Filter by finding type
            severity: Filter by severity level
        
        Returns:
            List of findings
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM findings WHERE 1=1"
        params = []
        
        if finding_type:
            query += " AND finding_type = ?"
            params.append(finding_type)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        query += " ORDER BY detected_at DESC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_entity_cooccurrences(self) -> List[Tuple[int, int, int]]:
        """
        Get entity co-occurrences (entities appearing in the same documents).
        
        Returns:
            List of tuples (entity1_id, entity2_id, co-occurrence_count)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                de1.entity_id as entity1_id,
                de2.entity_id as entity2_id,
                COUNT(DISTINCT de1.document_id) as cooccurrence_count
            FROM document_entities de1
            JOIN document_entities de2 
                ON de1.document_id = de2.document_id 
                AND de1.entity_id < de2.entity_id
            GROUP BY de1.entity_id, de2.entity_id
            HAVING cooccurrence_count > 0
        """)
        return cursor.fetchall()
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Example usage
    with InvestigationDB() as db:
        print("Database initialized successfully!")
        print(f"Tables created in: {db.db_path}")
