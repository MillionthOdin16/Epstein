#!/usr/bin/env python3
"""
File ingestion module for the investigation system.

This module scans for new files in the data directories and ingests them
into the database. It performs basic text extraction and entity detection.
"""

import os
import re
import hashlib
from pathlib import Path
from typing import List, Set, Tuple, Dict
from database import InvestigationDB


class FileIngestor:
    """Handles file scanning and ingestion."""
    
    def __init__(self, db: InvestigationDB):
        """
        Initialize the file ingestor.
        
        Args:
            db: InvestigationDB instance
        """
        self.db = db
        self.data_dirs = [
            Path("data/processed/files"),
            Path("data/raw")
        ]
        
    def scan_for_new_files(self) -> List[Path]:
        """
        Scan data directories for files not yet in the database.
        
        Returns:
            List of Path objects for new files
        """
        new_files = []
        
        for data_dir in self.data_dirs:
            if not data_dir.exists():
                print(f"⚠️  Directory not found: {data_dir}")
                continue
                
            # Scan for text and CSV files
            for pattern in ['**/*.txt', '**/*.csv']:
                for filepath in data_dir.glob(pattern):
                    if filepath.is_file():
                        filepath_str = str(filepath)
                        if not self.db.is_file_ingested(filepath_str):
                            new_files.append(filepath)
        
        return new_files
        
    def calculate_checksum(self, filepath: Path) -> str:
        """
        Calculate MD5 checksum of a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            MD5 checksum as hex string
        """
        md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5.update(chunk)
        return md5.hexdigest()
        
    def extract_text(self, filepath: Path) -> str:
        """
        Extract text content from a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Text content of the file
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")
            return ""
            
    def extract_entities(self, text: str) -> Set[str]:
        """
        Extract potential entity names from text.
        
        This is a simple extraction that looks for:
        - Capitalized words/phrases (potential names)
        - Common titles followed by names
        
        Args:
            text: Text content to analyze
            
        Returns:
            Set of potential entity names
        """
        entities = set()
        
        # Pattern for titles followed by names
        title_pattern = r'\b(?:Mr|Mrs|Ms|Dr|Prof|President|Director|CEO|CFO|Judge|Senator|Representative)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        for match in re.finditer(title_pattern, text):
            entities.add(match.group(1))
        
        # Pattern for capitalized names (at least 2 words)
        name_pattern = r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        for match in re.finditer(name_pattern, text):
            name = match.group(1)
            # Filter out common false positives
            if not any(word in name for word in ['The', 'This', 'That', 'These', 'Those', 'From', 'Dear', 'To']):
                entities.add(name)
        
        # Limit to reasonable entity names (2-4 words)
        entities = {e for e in entities if 2 <= len(e.split()) <= 4}
        
        return entities
        
    def extract_numbers(self, text: str) -> List[int]:
        """
        Extract numerical values from text for Benford's Law analysis.
        
        Args:
            text: Text content to analyze
            
        Returns:
            List of numerical values found in the text
        """
        numbers = []
        
        # Pattern for numbers (including currency, percentages, etc.)
        # We want leading digits, so we extract full numbers
        # Require at least 2 digits since Benford's Law is most applicable to multi-digit numbers
        number_pattern = r'\b\d{2,}\b'
        for match in re.finditer(number_pattern, text):
            try:
                num = int(match.group(0))
                # Benford's Law applies to numbers >= 10 (need at least 2 significant digits)
                # Single-digit numbers don't have a "first digit" in the Benford sense
                if num >= 10:
                    numbers.append(num)
            except ValueError:
                continue
        
        return numbers
        
    def ingest_file(self, filepath: Path) -> Tuple[int, Set[str], List[int]]:
        """
        Ingest a single file into the database.
        
        Args:
            filepath: Path to the file to ingest
            
        Returns:
            Tuple of (file_id, entities, numbers)
        """
        # Calculate file metadata
        file_size = filepath.stat().st_size
        checksum = self.calculate_checksum(filepath)
        
        # Add file to database
        file_id = self.db.add_file(
            filepath=str(filepath),
            filename=filepath.name,
            file_size=file_size,
            checksum=checksum
        )
        
        # Extract and analyze content
        text = self.extract_text(filepath)
        entities = self.extract_entities(text)
        numbers = self.extract_numbers(text)
        
        # Store entities
        for entity_name in entities:
            self.db.add_entity(
                file_id=file_id,
                entity_name=entity_name,
                entity_type='PERSON',
                confidence=0.5  # Basic confidence score
            )
        
        return file_id, entities, numbers
        
    def ingest_new_files(self) -> Tuple[int, Set[str], Dict[int, List[int]]]:
        """
        Scan for and ingest all new files.
        
        Returns:
            Tuple of (files_ingested, all_entities, numbers_by_file_id)
        """
        new_files = self.scan_for_new_files()
        
        if not new_files:
            print("✓ No new files to ingest")
            return 0, set(), {}
        
        print(f"📥 Found {len(new_files)} new files to ingest")
        
        all_entities = set()
        numbers_by_file = {}
        files_ingested = 0
        
        for i, filepath in enumerate(new_files, 1):
            try:
                file_id, entities, numbers = self.ingest_file(filepath)
                all_entities.update(entities)
                if numbers:
                    numbers_by_file[file_id] = numbers
                files_ingested += 1
                
                if i % 100 == 0:
                    print(f"   Progress: {i}/{len(new_files)} files ingested")
                    
            except Exception as e:
                print(f"⚠️  Error ingesting {filepath}: {e}")
                continue
        
        print(f"✓ Ingested {files_ingested} files")
        print(f"✓ Found {len(all_entities)} unique entities")
        
        return files_ingested, all_entities, numbers_by_file


def run_ingest(db_path: str = "investigation.db"):
    """
    Main function to run file ingestion.
    
    Args:
        db_path: Path to the investigation database
    """
    db = InvestigationDB(db_path)
    db.connect()
    
    try:
        ingestor = FileIngestor(db)
        files_ingested, entities, numbers = ingestor.ingest_new_files()
        return files_ingested, entities, numbers
    finally:
        db.close()


if __name__ == '__main__':
    run_ingest()
