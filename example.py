#!/usr/bin/env python3
"""
Example script demonstrating the Investigative Suite functionality.

This script shows how to use the investigative suite programmatically
rather than through the command-line interface.
"""

import logging
from pathlib import Path
from src.db import InvestigationDB
from src.librarian import ingest_documents, detect_duplicates
from src.detective import extract_entities, find_relationships

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

def main():
    """Example demonstrating the investigative suite."""
    
    print("=" * 80)
    print("Investigative Suite - Example Usage")
    print("=" * 80)
    print()
    
    # 1. Create a sample document for testing
    test_dir = Path("/tmp/example_investigation")
    test_dir.mkdir(exist_ok=True)
    
    sample_doc = test_dir / "example.txt"
    sample_doc.write_text("""
    Investigation Report - Case #12345
    Date: January 15, 2024
    
    Investigators met with Alice Johnson and Bob Smith at the Manhattan office.
    The financial records showed a payment of $250,000.00 on 03/20/2023.
    
    Additional meeting scheduled for February 28, 2024 with Carol Davis.
    Total amount discussed: $1,500,000 USD.
    """)
    
    print(f"Created sample document: {sample_doc}")
    print()
    
    # 2. Initialize database
    db_path = test_dir / "example.db"
    print(f"Initializing database: {db_path}")
    db = InvestigationDB(str(db_path))
    print()
    
    # 3. Ingest documents
    print("Ingesting documents...")
    documents = ingest_documents(str(test_dir), extensions=['.txt'])
    print(f"Found {len(documents)} document(s)")
    print()
    
    # 4. Detect duplicates
    unique_docs, duplicates = detect_duplicates(documents)
    print(f"Unique documents: {len(unique_docs)}")
    print(f"Duplicates: {len(duplicates)}")
    print()
    
    # 5. Process documents
    print("Processing documents and extracting entities...")
    for filename, text, file_hash in unique_docs:
        # Insert document
        doc_id = db.insert_document(filename, text, file_hash)
        
        if doc_id:
            # Extract entities
            entities = extract_entities(text)
            
            print(f"\nDocument: {Path(filename).name}")
            print(f"  People found: {len(entities['PERSON'])}")
            print(f"  Money amounts: {len(entities['MONEY'])}")
            print(f"  Dates found: {len(entities['DATE'])}")
            
            # Display extracted entities
            if entities['PERSON']:
                print("\n  People:")
                for person, context in entities['PERSON'][:5]:  # Show first 5
                    print(f"    - {person}")
            
            if entities['MONEY']:
                print("\n  Money:")
                for amount, context in entities['MONEY'][:5]:
                    print(f"    - {amount}")
            
            if entities['DATE']:
                print("\n  Dates:")
                for date, context in entities['DATE'][:5]:
                    print(f"    - {date}")
            
            # Store entities
            for entity_type, entity_list in entities.items():
                for value, context in entity_list:
                    db.insert_entity(doc_id, entity_type, value, context)
            
            # Find relationships
            relationships = find_relationships(text, entities)
            if relationships:
                print(f"\n  Relationships found: {len(relationships)}")
                for rel in relationships[:3]:  # Show first 3
                    print(f"    - {rel['person1']} ↔ {rel['person2']} (distance: {rel['distance']} chars)")
    
    print()
    
    # 6. Display statistics
    print("=" * 80)
    print("Database Statistics")
    print("=" * 80)
    stats = db.get_statistics()
    print(f"Total documents: {stats['documents']}")
    print(f"Total entities: {stats['entities']}")
    print("\nEntities by type:")
    for entity_type, count in sorted(stats['entities_by_type'].items()):
        print(f"  {entity_type}: {count}")
    
    # 7. Close database
    db.close()
    
    print()
    print("=" * 80)
    print("Example completed successfully!")
    print(f"Database saved to: {db_path}")
    print("=" * 80)


if __name__ == '__main__':
    main()
