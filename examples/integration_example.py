#!/usr/bin/env python3
"""
Example integration script demonstrating the autonomous investigative architecture.

This script shows how to use the database and ingestion modules together
to build a complete document investigation pipeline.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import DatabaseManager
from src.ingest import DocumentIngester


def main():
    """Main function demonstrating the investigation pipeline."""
    
    print("=" * 70)
    print("Autonomous Investigative Architecture - Integration Example")
    print("=" * 70)
    print()
    
    # Configuration
    db_path = "investigation.db"
    documents_dir = "data/processed/files" if len(sys.argv) < 2 else sys.argv[1]
    
    print(f"Database: {db_path}")
    print(f"Documents directory: {documents_dir}")
    print()
    
    # Check if directory exists
    if not os.path.exists(documents_dir):
        print(f"⚠ Warning: Directory '{documents_dir}' does not exist.")
        print("Creating example with test data...")
        print()
        
        # Create a demo with synthetic data
        demo_with_synthetic_data(db_path)
        return
    
    # Initialize components
    print("Initializing components...")
    try:
        db = DatabaseManager(db_path)
        ingester = DocumentIngester()
        print("✓ Components initialized successfully")
        print()
    except Exception as e:
        print(f"✗ Error initializing components: {e}")
        print(f"  Check error.log for details")
        return
    
    # Get initial statistics
    print("Database Statistics (before ingestion):")
    stats = db.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    # Scan for documents
    print(f"Scanning directory: {documents_dir}")
    files = ingester.scan_directory(documents_dir, recursive=True)
    print(f"✓ Found {len(files)} supported files")
    print()
    
    if not files:
        print("No files to process. Example complete.")
        db.close()
        return
    
    # Process a limited number of files for demo
    max_files = 5
    print(f"Processing up to {max_files} files (demo mode)...")
    print()
    
    processed_count = 0
    for i, file_path in enumerate(files[:max_files], 1):
        try:
            print(f"[{i}/{min(max_files, len(files))}] Processing: {os.path.basename(file_path)}")
            
            # Process file
            file_hash, cleaned_text = ingester.process_file(file_path)
            
            if not file_hash:
                print(f"  ✗ Failed to process file")
                continue
            
            if not cleaned_text:
                print(f"  ⚠ Duplicate or no text extracted")
                continue
            
            # Insert into database
            doc_id = db.insert_document(file_hash, file_path, cleaned_text)
            
            if doc_id:
                print(f"  ✓ Ingested (ID: {doc_id}, {len(cleaned_text)} chars)")
                processed_count += 1
                
                # Simulate entity extraction (in real use, you'd use NLP here)
                # For demo purposes, we'll add a synthetic entity
                db.insert_entity(
                    doc_id=doc_id,
                    entity_type='PERSON',
                    value=f'Entity-{doc_id}',
                    confidence=0.85
                )
            else:
                print(f"  ⚠ Already in database")
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue
    
    print()
    print(f"✓ Processed {processed_count} new files")
    print()
    
    # Create a sample lead
    if processed_count > 0:
        print("Creating sample investigative lead...")
        lead_id = db.insert_lead(
            entity_value='Sample Investigation Target',
            suspicion_score=0.75,
            status='NEW'
        )
        print(f"✓ Lead created (ID: {lead_id})")
        print()
    
    # Display final statistics
    print("Database Statistics (after ingestion):")
    stats = db.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    # Show some sample queries
    print("Sample Queries:")
    print("-" * 70)
    
    # Get a sample document
    print("\n1. Recently ingested documents:")
    cursor = db.conn.cursor()
    cursor.execute("SELECT id, path, LENGTH(raw_text) as text_len FROM documents ORDER BY ingested_at DESC LIMIT 3")
    for row in cursor.fetchall():
        print(f"   ID {row[0]}: {os.path.basename(row[1])} ({row[2]} chars)")
    
    # Get entities
    print("\n2. Extracted entities (sample):")
    cursor.execute("SELECT type, value, confidence FROM entities LIMIT 5")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} (confidence: {row[2]:.2f})")
    
    # Get leads
    print("\n3. Active leads:")
    leads = db.get_leads_by_status('NEW')
    for lead in leads[:3]:
        print(f"   Lead #{lead['id']}: {lead['entity_value']} (score: {lead['suspicion_score']:.2f})")
    
    print()
    print("-" * 70)
    
    # Close database
    db.close()
    print("\n✅ Integration example complete!")
    print(f"\nDatabase saved to: {db_path}")
    print(f"Error log available at: error.log")
    print()


def demo_with_synthetic_data(db_path):
    """
    Run a demonstration with synthetic data.
    
    Args:
        db_path: Path to database file
    """
    print("Running demonstration with synthetic data...")
    print()
    
    try:
        # Initialize database
        db = DatabaseManager(db_path)
        print("✓ Database initialized")
        print()
        
        # Insert sample documents
        print("Creating sample documents...")
        documents = [
            ("abc123", "/sample/doc1.txt", "This is a sample investigation document mentioning John Doe."),
            ("def456", "/sample/doc2.txt", "Financial records from ACME Corporation in New York."),
            ("ghi789", "/sample/doc3.txt", "Communications between Jane Smith and Robert Johnson."),
        ]
        
        for hash_val, path, text in documents:
            doc_id = db.insert_document(hash_val, path, text)
            if doc_id:
                print(f"  ✓ Document {doc_id}: {os.path.basename(path)}")
                
                # Add sample entities
                if "John Doe" in text:
                    db.insert_entity(doc_id, 'PERSON', 'John Doe', 0.95)
                if "Jane Smith" in text:
                    db.insert_entity(doc_id, 'PERSON', 'Jane Smith', 0.92)
                if "Robert Johnson" in text:
                    db.insert_entity(doc_id, 'PERSON', 'Robert Johnson', 0.88)
                if "ACME Corporation" in text:
                    db.insert_entity(doc_id, 'ORG', 'ACME Corporation', 0.90)
                if "New York" in text:
                    db.insert_entity(doc_id, 'LOC', 'New York', 0.93)
        
        print()
        
        # Create sample leads
        print("Creating investigative leads...")
        leads = [
            ("John Doe", 0.85, "NEW"),
            ("ACME Corporation", 0.72, "NEW"),
            ("Jane Smith", 0.68, "INVESTIGATING"),
        ]
        
        for entity, score, status in leads:
            lead_id = db.insert_lead(entity, score, status)
            print(f"  ✓ Lead {lead_id}: {entity} (score: {score}, status: {status})")
        
        print()
        
        # Display statistics
        print("Final Statistics:")
        stats = db.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print()
        print("✅ Demo complete!")
        print(f"\nDatabase saved to: {db_path}")
        print("You can inspect it using: sqlite3 investigation.db")
        print()
        
        db.close()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("Check error.log for details")


if __name__ == "__main__":
    main()
