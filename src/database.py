#!/usr/bin/env python3
"""
Database utilities for the investigation system.

This module provides database schema and utility functions for:
- Tracking ingested documents
- Storing extracted entities (people, organizations, locations)
- Managing leads and their status
- Recording suspicious documents
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class InvestigationDB:
    """Main database handler for the investigation system."""
    
    def __init__(self, db_path: str = "investigation.db"):
        """Initialize the database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.initialize_db()
    
    def initialize_db(self):
        """Create database tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Documents table - tracks all ingested files
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                filepath TEXT NOT NULL,
                category TEXT,
                source TEXT,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT,
                status TEXT DEFAULT 'NORMAL',
                last_analyzed TIMESTAMP
            )
        """)
        
        # Entities table - people, organizations, locations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                first_seen_doc_id INTEGER,
                occurrence_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (first_seen_doc_id) REFERENCES documents(id),
                UNIQUE(name, entity_type)
            )
        """)
        
        # Entity connections (bridges) - tracks co-occurrences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity1_id INTEGER NOT NULL,
                entity2_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity1_id) REFERENCES entities(id),
                FOREIGN KEY (entity2_id) REFERENCES entities(id),
                FOREIGN KEY (document_id) REFERENCES documents(id),
                UNIQUE(entity1_id, entity2_id, document_id)
            )
        """)
        
        # Leads table - tracks investigation leads
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'NEW',
                priority TEXT DEFAULT 'MEDIUM',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
        """)
        
        # Suspicious documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suspicious_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                severity TEXT DEFAULT 'LOW',
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
        """)
        
        # Statistics tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_date DATE DEFAULT CURRENT_DATE,
                total_documents INTEGER,
                total_entities INTEGER,
                total_leads INTEGER,
                new_leads_today INTEGER,
                suspicious_docs_today INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
    
    def add_document(self, filename: str, filepath: str, category: str = None, 
                     source: str = None, content_hash: str = None) -> Optional[int]:
        """Add a new document to the database.
        
        Args:
            filename: Name of the file
            filepath: Full path to the file
            category: Category of the document (IMAGES, TEXT, etc.)
            source: Source identifier
            content_hash: Hash of the document content
            
        Returns:
            Document ID if successful, None otherwise
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO documents (filename, filepath, category, source, content_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (filename, filepath, category, source, content_hash))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Document already exists
            return None
    
    def get_document_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get document information by filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            Document information as dict, or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE filename = ?", (filename,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def add_entity(self, name: str, entity_type: str, first_seen_doc_id: int) -> int:
        """Add a new entity or increment its occurrence count.
        
        Args:
            name: Entity name
            entity_type: Type of entity (PERSON, ORGANIZATION, LOCATION, etc.)
            first_seen_doc_id: Document ID where first seen
            
        Returns:
            Entity ID
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO entities (name, entity_type, first_seen_doc_id)
                VALUES (?, ?, ?)
            """, (name, entity_type, first_seen_doc_id))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Entity already exists, increment count
            cursor.execute("""
                UPDATE entities 
                SET occurrence_count = occurrence_count + 1
                WHERE name = ? AND entity_type = ?
            """, (name, entity_type))
            self.conn.commit()
            
            cursor.execute("""
                SELECT id FROM entities WHERE name = ? AND entity_type = ?
            """, (name, entity_type))
            return cursor.fetchone()[0]
    
    def add_entity_connection(self, entity1_id: int, entity2_id: int, 
                             document_id: int) -> Optional[int]:
        """Record a connection between two entities in a document.
        
        Args:
            entity1_id: First entity ID
            entity2_id: Second entity ID
            document_id: Document where connection was found
            
        Returns:
            Connection ID if successful, None otherwise
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO entity_connections (entity1_id, entity2_id, document_id)
                VALUES (?, ?, ?)
            """, (entity1_id, entity2_id, document_id))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Connection already recorded
            return None
    
    def add_lead(self, description: str, entity_id: Optional[int] = None, 
                 priority: str = "MEDIUM", notes: str = None) -> int:
        """Add a new lead to investigate.
        
        Args:
            description: Description of the lead
            entity_id: Related entity ID (optional)
            priority: Priority level (LOW, MEDIUM, HIGH)
            notes: Additional notes
            
        Returns:
            Lead ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO leads (entity_id, description, priority, notes)
            VALUES (?, ?, ?, ?)
        """, (entity_id, description, priority, notes))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_leads_by_status(self, status: str = "NEW") -> List[Dict[str, Any]]:
        """Get all leads with a specific status.
        
        Args:
            status: Lead status (NEW, IN_PROGRESS, RESOLVED)
            
        Returns:
            List of lead dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT l.*, e.name as entity_name, e.entity_type
            FROM leads l
            LEFT JOIN entities e ON l.entity_id = e.id
            WHERE l.status = ?
            ORDER BY l.created_at DESC
        """, (status,))
        return [dict(row) for row in cursor.fetchall()]
    
    def mark_document_suspicious(self, document_id: int, reason: str, 
                                 severity: str = "LOW") -> int:
        """Mark a document as suspicious.
        
        Args:
            document_id: Document ID
            reason: Reason for suspicion
            severity: Severity level (LOW, MEDIUM, HIGH)
            
        Returns:
            Suspicious document record ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO suspicious_docs (document_id, reason, severity)
            VALUES (?, ?, ?)
        """, (document_id, reason, severity))
        
        # Update document status
        cursor.execute("""
            UPDATE documents SET status = 'SUSPICIOUS' WHERE id = ?
        """, (document_id,))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_suspicious_documents(self, since_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get suspicious documents.
        
        Args:
            since_date: Only get documents flagged since this date (ISO format)
            
        Returns:
            List of suspicious document dictionaries
        """
        cursor = self.conn.cursor()
        if since_date:
            cursor.execute("""
                SELECT s.*, d.filename, d.filepath, d.category
                FROM suspicious_docs s
                JOIN documents d ON s.document_id = d.id
                WHERE DATE(s.detected_at) >= DATE(?)
                ORDER BY s.detected_at DESC
            """, (since_date,))
        else:
            cursor.execute("""
                SELECT s.*, d.filename, d.filepath, d.category
                FROM suspicious_docs s
                JOIN documents d ON s.document_id = d.id
                ORDER BY s.detected_at DESC
            """)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict[str, int]:
        """Get current database statistics.
        
        Returns:
            Dictionary with various counts
        """
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
        
        cursor.execute("SELECT COUNT(*) FROM suspicious_docs")
        stats['total_suspicious'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM entity_connections")
        stats['total_connections'] = cursor.fetchone()[0]
        
        return stats
    
    def update_document_analyzed(self, document_id: int):
        """Update the last_analyzed timestamp for a document.
        
        Args:
            document_id: Document ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE documents 
            SET last_analyzed = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (document_id,))
        self.conn.commit()
    
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
