#!/usr/bin/env python3
"""
Query Script - Explore Investigation Database

This script provides utilities to query and analyze the investigation database.
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple


def connect_db(db_path: str) -> sqlite3.Connection:
    """Connect to the database."""
    if not Path(db_path).exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
    return sqlite3.connect(db_path)


def list_documents(conn: sqlite3.Connection, limit: int = 10):
    """List all documents in the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, filename, 
               length(raw_text) as text_length,
               substr(hash, 1, 12) as hash_prefix,
               created_at
        FROM documents
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    
    print("=" * 100)
    print(f"Documents (showing {limit} most recent)")
    print("=" * 100)
    print(f"{'ID':<5} {'Filename':<50} {'Size':<10} {'Hash':<15} {'Created':<20}")
    print("-" * 100)
    
    for row in cursor.fetchall():
        doc_id, filename, text_len, hash_prefix, created_at = row
        filename_short = Path(filename).name[:45] + "..." if len(Path(filename).name) > 45 else Path(filename).name
        print(f"{doc_id:<5} {filename_short:<50} {text_len:<10} {hash_prefix:<15} {created_at:<20}")
    
    cursor.execute("SELECT COUNT(*) FROM documents")
    total = cursor.fetchone()[0]
    print("-" * 100)
    print(f"Total documents: {total}")
    print()


def list_entities_by_type(conn: sqlite3.Connection, entity_type: str = None, limit: int = 20):
    """List entities by type."""
    cursor = conn.cursor()
    
    if entity_type:
        cursor.execute("""
            SELECT e.entity_type, e.value, COUNT(*) as count
            FROM entities e
            JOIN documents d ON e.doc_id = d.id
            WHERE e.entity_type = ?
            GROUP BY e.value
            ORDER BY count DESC
            LIMIT ?
        """, (entity_type, limit))
        print("=" * 100)
        print(f"Top {entity_type} Entities")
        print("=" * 100)
    else:
        cursor.execute("""
            SELECT e.entity_type, e.value, COUNT(*) as count
            FROM entities e
            GROUP BY e.entity_type, e.value
            ORDER BY e.entity_type, count DESC
            LIMIT ?
        """, (limit,))
        print("=" * 100)
        print(f"Top Entities (showing {limit})")
        print("=" * 100)
    
    print(f"{'Type':<10} {'Value':<40} {'Count':<10}")
    print("-" * 100)
    
    for row in cursor.fetchall():
        entity_type_val, value, count = row[:3]
        value_short = value[:37] + "..." if len(value) > 40 else value
        print(f"{entity_type_val:<10} {value_short:<40} {count:<10}")
    
    print()


def search_entities(conn: sqlite3.Connection, search_term: str):
    """Search for entities matching a term."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.entity_type, e.value, e.context_snippet, d.filename
        FROM entities e
        JOIN documents d ON e.doc_id = d.id
        WHERE e.value LIKE ?
        ORDER BY e.entity_type
        LIMIT 50
    """, (f"%{search_term}%",))
    
    results = cursor.fetchall()
    
    print("=" * 100)
    print(f"Search Results for: '{search_term}' ({len(results)} matches)")
    print("=" * 100)
    
    if not results:
        print("No matches found.")
        print()
        return
    
    for entity_type, value, context, filename in results:
        print(f"\n{entity_type}: {value}")
        print(f"  Document: {Path(filename).name}")
        if context:
            context_clean = context.replace('\n', ' ')[:100]
            print(f"  Context: ...{context_clean}...")
    
    print()


def show_statistics(conn: sqlite3.Connection):
    """Display database statistics."""
    cursor = conn.cursor()
    
    # Document count
    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]
    
    # Entity count
    cursor.execute("SELECT COUNT(*) FROM entities")
    entity_count = cursor.fetchone()[0]
    
    # Entities by type
    cursor.execute("""
        SELECT entity_type, COUNT(*) 
        FROM entities 
        GROUP BY entity_type
        ORDER BY COUNT(*) DESC
    """)
    entity_types = cursor.fetchall()
    
    # Most common entities
    cursor.execute("""
        SELECT entity_type, value, COUNT(*) as count
        FROM entities
        GROUP BY entity_type, value
        ORDER BY count DESC
        LIMIT 10
    """)
    top_entities = cursor.fetchall()
    
    print("=" * 100)
    print("Database Statistics")
    print("=" * 100)
    print(f"Total Documents: {doc_count}")
    print(f"Total Entities: {entity_count}")
    print()
    
    print("Entities by Type:")
    for entity_type, count in entity_types:
        percentage = (count / entity_count * 100) if entity_count > 0 else 0
        print(f"  {entity_type:<15} {count:>6} ({percentage:>5.1f}%)")
    print()
    
    print("Top 10 Most Common Entities:")
    for entity_type, value, count in top_entities:
        value_short = value[:30] + "..." if len(value) > 30 else value
        print(f"  {entity_type:<10} {value_short:<35} {count:>4}x")
    print()


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Query and explore the investigation database',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--db',
        default='investigation.db',
        help='Path to SQLite database (default: investigation.db)'
    )
    
    parser.add_argument(
        '--docs',
        action='store_true',
        help='List documents in the database'
    )
    
    parser.add_argument(
        '--entities',
        choices=['PERSON', 'MONEY', 'DATE', 'all'],
        help='List entities by type'
    )
    
    parser.add_argument(
        '--search',
        metavar='TERM',
        help='Search for entities containing the given term'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics (default if no other options)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Limit number of results (default: 20)'
    )
    
    args = parser.parse_args()
    
    # If no specific action, show stats
    if not any([args.docs, args.entities, args.search]):
        args.stats = True
    
    # Connect to database
    conn = connect_db(args.db)
    
    try:
        if args.stats:
            show_statistics(conn)
        
        if args.docs:
            list_documents(conn, args.limit)
        
        if args.entities:
            if args.entities == 'all':
                list_entities_by_type(conn, None, args.limit)
            else:
                list_entities_by_type(conn, args.entities, args.limit)
        
        if args.search:
            search_entities(conn, args.search)
        
    finally:
        conn.close()


if __name__ == '__main__':
    main()
