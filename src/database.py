#!/usr/bin/env python3
"""
Database module for the investigation system.

This module handles all database operations for the investigation.db,
including schema creation, file tracking, leads management, and document flagging.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class InvestigationDB:
    """Manages the investigation database."""
    
    def __init__(self, db_path: str = "investigation.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """Establish database connection and create schema if needed."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()
        
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            
    def _create_schema(self):
        """Create database schema if it doesn't exist."""
        cursor = self.conn.cursor()
        
        # Files table - tracks all ingested files
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                file_size INTEGER,
                checksum TEXT
            )
        ''')
        
        # Leads table - tracks entities of interest
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_name TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'NEW',
                discovered_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                notes TEXT
            )
        ''')
        
        # Documents table - tracks document analysis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'NORMAL',
                benford_score REAL,
                analyzed_at TEXT,
                FOREIGN KEY (file_id) REFERENCES files(id)
            )
        ''')
        
        # Entities table - tracks extracted entities from documents
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                entity_name TEXT NOT NULL,
                entity_type TEXT,
                confidence REAL,
                FOREIGN KEY (file_id) REFERENCES files(id)
            )
        ''')
        
        # Connections table - tracks relationships between entities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity1 TEXT NOT NULL,
                entity2 TEXT NOT NULL,
                connection_type TEXT,
                strength REAL,
                source_file_id INTEGER,
                FOREIGN KEY (source_file_id) REFERENCES files(id)
            )
        ''')
        
        self.conn.commit()
        
    def is_file_ingested(self, filepath: str) -> bool:
        """
        Check if a file has already been ingested.
        
        Args:
            filepath: Path to the file
            
        Returns:
            True if file exists in database, False otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM files WHERE filepath = ?', (filepath,))
        return cursor.fetchone() is not None
        
    def add_file(self, filepath: str, filename: str, file_size: int = None, 
                 checksum: str = None) -> int:
        """
        Add a new file to the database.
        
        Args:
            filepath: Full path to the file
            filename: Name of the file
            file_size: Size of the file in bytes
            checksum: File checksum (optional)
            
        Returns:
            ID of the newly inserted file
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO files (filepath, filename, ingested_at, file_size, checksum)
            VALUES (?, ?, ?, ?, ?)
        ''', (filepath, filename, now, file_size, checksum))
        
        self.conn.commit()
        return cursor.lastrowid
        
    def get_all_leads(self) -> List[Dict]:
        """
        Get all leads from the database.
        
        Returns:
            List of lead records as dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM leads ORDER BY discovered_at DESC')
        return [dict(row) for row in cursor.fetchall()]
        
    def add_lead(self, entity_name: str, status: str = 'NEW', notes: str = None) -> int:
        """
        Add a new lead to the database.
        
        Args:
            entity_name: Name of the entity
            status: Status of the lead (default: 'NEW')
            notes: Additional notes
            
        Returns:
            ID of the newly inserted lead, or existing lead ID if already exists
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # Check if lead already exists
        cursor.execute('SELECT id FROM leads WHERE entity_name = ?', (entity_name,))
        existing = cursor.fetchone()
        
        if existing:
            return existing['id']
        
        cursor.execute('''
            INSERT INTO leads (entity_name, status, discovered_at, last_updated, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (entity_name, status, now, now, notes))
        
        self.conn.commit()
        return cursor.lastrowid
        
    def mark_document_suspicious(self, file_id: int, benford_score: float = None):
        """
        Mark a document as suspicious.
        
        Args:
            file_id: ID of the file in the database
            benford_score: Benford's Law violation score
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # Check if document record exists
        cursor.execute('SELECT id FROM documents WHERE file_id = ?', (file_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE documents 
                SET status = 'SUSPICIOUS', benford_score = ?, analyzed_at = ?
                WHERE file_id = ?
            ''', (benford_score, now, file_id))
        else:
            cursor.execute('''
                INSERT INTO documents (file_id, status, benford_score, analyzed_at)
                VALUES (?, 'SUSPICIOUS', ?, ?)
            ''', (file_id, benford_score, now))
        
        self.conn.commit()
        
    def get_suspicious_documents(self) -> List[Dict]:
        """
        Get all suspicious documents.
        
        Returns:
            List of suspicious document records with file information
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT d.*, f.filepath, f.filename, f.ingested_at
            FROM documents d
            JOIN files f ON d.file_id = f.id
            WHERE d.status = 'SUSPICIOUS'
            ORDER BY d.analyzed_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]
        
    def add_entity(self, file_id: int, entity_name: str, 
                   entity_type: str = None, confidence: float = None) -> int:
        """
        Add an entity extracted from a document.
        
        Args:
            file_id: ID of the file
            entity_name: Name of the entity
            entity_type: Type of entity (PERSON, ORGANIZATION, etc.)
            confidence: Confidence score
            
        Returns:
            ID of the newly inserted entity
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO entities (file_id, entity_name, entity_type, confidence)
            VALUES (?, ?, ?, ?)
        ''', (file_id, entity_name, entity_type, confidence))
        
        self.conn.commit()
        return cursor.lastrowid
        
    def add_connection(self, entity1: str, entity2: str, 
                      connection_type: str = None, strength: float = None,
                      source_file_id: int = None) -> int:
        """
        Add a connection between two entities.
        
        Args:
            entity1: First entity name
            entity2: Second entity name
            connection_type: Type of connection
            strength: Connection strength score
            source_file_id: ID of the source file
            
        Returns:
            ID of the newly inserted connection
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO connections (entity1, entity2, connection_type, strength, source_file_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (entity1, entity2, connection_type, strength, source_file_id))
        
        self.conn.commit()
        return cursor.lastrowid
        
    def get_all_entities(self) -> List[str]:
        """
        Get all unique entity names.
        
        Returns:
            List of entity names
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT entity_name FROM entities ORDER BY entity_name')
        return [row['entity_name'] for row in cursor.fetchall()]
        
    def get_statistics(self) -> Dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary containing various statistics
        """
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Total files
        cursor.execute('SELECT COUNT(*) as count FROM files')
        stats['total_files'] = cursor.fetchone()['count']
        
        # Total leads
        cursor.execute('SELECT COUNT(*) as count FROM leads')
        stats['total_leads'] = cursor.fetchone()['count']
        
        # New leads
        cursor.execute("SELECT COUNT(*) as count FROM leads WHERE status = 'NEW'")
        stats['new_leads'] = cursor.fetchone()['count']
        
        # Suspicious documents
        cursor.execute("SELECT COUNT(*) as count FROM documents WHERE status = 'SUSPICIOUS'")
        stats['suspicious_docs'] = cursor.fetchone()['count']
        
        # Total entities
        cursor.execute('SELECT COUNT(*) as count FROM entities')
        stats['total_entities'] = cursor.fetchone()['count']
        
        # Total connections
        cursor.execute('SELECT COUNT(*) as count FROM connections')
        stats['total_connections'] = cursor.fetchone()['count']
        
        return stats
