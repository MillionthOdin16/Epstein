#!/usr/bin/env python3
"""
File ingestion module for the investigation system.

This module scans for new files in the data directory and adds them to the database.
It extracts basic metadata and content hashes to track which files have been processed.
"""

import hashlib
import re
from pathlib import Path
from typing import Set, List, Tuple
from database import InvestigationDB


def calculate_file_hash(filepath: Path) -> str:
    """Calculate SHA256 hash of a file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Hex digest of the file hash
    """
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read in chunks for large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def extract_metadata_from_filename(filename: str) -> Tuple[str, str]:
    """Extract category and source from filename.
    
    Expected format: CATEGORY-SOURCE-IDENTIFIER.txt
    Example: IMAGES-005-HOUSE_OVERSIGHT_020367.txt
    
    Args:
        filename: Name of the file
        
    Returns:
        Tuple of (category, source)
    """
    parts = filename.rsplit('.', 1)[0].split('-')
    if len(parts) >= 2:
        category = parts[0]
        source = parts[1]
        return category, source
    return "UNKNOWN", "000"


def scan_for_new_files(data_dir: str = "data/processed/files") -> List[Path]:
    """Scan the data directory for text files.
    
    Args:
        data_dir: Directory to scan for files
        
    Returns:
        List of Path objects for all .txt files
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"Warning: Data directory {data_dir} does not exist")
        return []
    
    return list(data_path.rglob('*.txt'))


def ingest_new_files(db: InvestigationDB, data_dir: str = "data/processed/files") -> Tuple[int, int]:
    """Ingest new files into the database.
    
    This function:
    1. Scans for all text files in the data directory
    2. Checks which ones are already in the database
    3. Adds new files to the database with metadata
    
    Args:
        db: InvestigationDB instance
        data_dir: Directory to scan for files
        
    Returns:
        Tuple of (new_files_count, total_files_scanned)
    """
    print(f"Scanning for files in {data_dir}...")
    all_files = scan_for_new_files(data_dir)
    print(f"Found {len(all_files)} total files")
    
    new_count = 0
    for filepath in all_files:
        filename = filepath.name
        
        # Check if already in database
        existing_doc = db.get_document_by_filename(filename)
        if existing_doc:
            continue
        
        # Extract metadata
        category, source = extract_metadata_from_filename(filename)
        
        # Calculate content hash
        try:
            content_hash = calculate_file_hash(filepath)
        except Exception as e:
            print(f"Warning: Could not hash file {filename}: {e}")
            content_hash = None
        
        # Add to database
        doc_id = db.add_document(
            filename=filename,
            filepath=str(filepath.absolute()),
            category=category,
            source=source,
            content_hash=content_hash
        )
        
        if doc_id:
            new_count += 1
            if new_count % 100 == 0:
                print(f"  Ingested {new_count} new files...")
    
    print(f"Ingestion complete: {new_count} new files added")
    return new_count, len(all_files)


def extract_entities_from_file(filepath: Path) -> List[Tuple[str, str]]:
    """Extract potential entities from a file using simple heuristics.
    
    This is a basic implementation that looks for:
    - Capitalized words (potential names)
    - Common patterns
    
    Args:
        filepath: Path to the file
        
    Returns:
        List of tuples (entity_name, entity_type)
    """
    entities = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Find sequences of capitalized words (potential names)
        # Pattern: 2-3 capitalized words in a row
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b'
        potential_names = re.findall(name_pattern, content)
        
        # Filter out common non-names
        common_words = {'The', 'This', 'That', 'These', 'Those', 'There', 'Here', 
                       'When', 'Where', 'What', 'Which', 'Who', 'Whom', 'How', 'Why',
                       'Document', 'File', 'Page', 'Court', 'Date', 'Time'}
        
        seen_names = set()
        for name in potential_names:
            # Skip if starts with common word
            if name.split()[0] in common_words:
                continue
            # Skip if too short
            if len(name) < 5:
                continue
            # Skip duplicates
            if name in seen_names:
                continue
            
            seen_names.add(name)
            entities.append((name, 'PERSON'))
        
        # Limit to most frequent entities (top 20 per document)
        if len(entities) > 20:
            entities = entities[:20]
    
    except Exception as e:
        print(f"Warning: Could not extract entities from {filepath}: {e}")
    
    return entities


if __name__ == '__main__':
    # Test the ingestion
    print("Testing file ingestion...")
    
    with InvestigationDB() as db:
        new_files, total_files = ingest_new_files(db)
        print(f"\nResults:")
        print(f"  Total files scanned: {total_files}")
        print(f"  New files ingested: {new_files}")
        print(f"  Already in database: {total_files - new_files}")
        
        stats = db.get_statistics()
        print(f"\nDatabase statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
