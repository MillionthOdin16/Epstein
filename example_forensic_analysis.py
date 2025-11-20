#!/usr/bin/env python3
"""
Example script demonstrating the forensic analysis capabilities.

This script shows how to:
1. Initialize the investigation database
2. Load sample data
3. Run all forensic analysis engines
4. View results
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import InvestigationDB
from src.analytics import ForensicAnalytics


def load_sample_data(db):
    """Load sample data into the database for demonstration."""
    print("\nLoading sample data...")
    
    # Sample documents with various patterns
    sample_docs = [
        {
            'filename': 'doc001.txt',
            'content': '''
                Meeting on January 15, 2005 regarding financial matters.
                Transaction amounts: $1,234.56, $2,345.67, $3,456.78
                Participants: John Doe, Jane Smith, ACME Corp
            ''',
            'category': 'TEXT',
            'source': '001'
        },
        {
            'filename': 'doc002.txt',
            'content': '''
                Communication dated February 20, 2005.
                Payments: $1,111.11, $1,222.22, $1,333.33, $1,444.44, $1,555.55
                Mentioned: Jane Smith, Bob Johnson, XYZ Inc
            ''',
            'category': 'TEXT',
            'source': '001'
        },
        {
            'filename': 'doc003.txt',
            'content': '''
                Report from March 10, 2005.
                Transfers: USD 2,000.00, USD 3,000.00, USD 4,000.00
                Entities: John Doe, Bob Johnson, Alice Brown
            ''',
            'category': 'TEXT',
            'source': '002'
        },
        {
            'filename': 'doc004.txt',
            'content': '''
                Document dated April 25, 2005 (45-day gap after March 10).
                Amounts: $5,678.90, $6,789.01, $7,890.12
                Parties: Alice Brown, ACME Corp
            ''',
            'category': 'TEXT',
            'source': '002'
        },
        {
            'filename': 'doc005.txt',
            'content': '''
                Memo from July 15, 2005 (significant gap after April 25).
                Values: $8,901.23, $9,012.34, $1,123.45
                People: John Doe, Charlie Davis
            ''',
            'category': 'TEXT',
            'source': '003'
        },
        {
            'filename': 'doc006_suspicious.txt',
            'content': '''
                Financial statement dated November 15, 2005.
                Suspicious amounts (potentially fabricated - all starting with 9):
                $9,100.00, $9,200.00, $9,300.00, $9,400.00, $9,500.00, 
                $9,600.00, $9,700.00, $9,800.00, $9,900.00, $9,150.00,
                $9,250.00, $9,350.00, $9,450.00, $9,550.00, $9,650.00,
                $9,750.00, $9,850.00, $9,950.00, $9,175.00, $9,275.00,
                $9,375.00, $9,475.00, $9,575.00, $9,675.00, $9,775.00,
                $9,875.00, $9,975.00, $9,125.00, $9,225.00, $9,325.00,
                $9,425.00, $9,525.00, $9,625.00, $9,725.00, $9,825.00
                Related parties: Charlie Davis, XYZ Inc
            ''',
            'category': 'TEXT',
            'source': '003'
        }
    ]
    
    # Add documents and extract entities
    entity_names = set()
    doc_entities = []
    
    for doc_data in sample_docs:
        # Add document
        doc_id = db.add_document(
            filename=doc_data['filename'],
            content=doc_data['content'],
            category=doc_data['category'],
            source=doc_data['source']
        )
        
        # Extract entity names (simple extraction for demo)
        potential_entities = [
            'John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown', 
            'Charlie Davis', 'ACME Corp', 'XYZ Inc'
        ]
        
        for entity_name in potential_entities:
            if entity_name in doc_data['content']:
                entity_names.add(entity_name)
                
                # Determine entity type
                entity_type = 'organization' if any(x in entity_name for x in ['Corp', 'Inc']) else 'person'
                
                # Add entity if not exists
                entity_id = db.add_entity(entity_name, entity_type)
                
                # Link document and entity
                if entity_id and doc_id:
                    db.add_document_entity(doc_id, entity_id)
    
    print(f"  Loaded {len(sample_docs)} documents")
    print(f"  Extracted {len(entity_names)} entities")


def main():
    """Main demonstration function."""
    print("="*70)
    print("Forensic Analysis Demonstration")
    print("="*70)
    
    # Initialize database
    db_path = "investigation.db"
    print(f"\nInitializing database: {db_path}")
    
    with InvestigationDB(db_path) as db:
        # Load sample data
        load_sample_data(db)
        
        # Initialize forensic analytics
        print("\n" + "="*70)
        print("Running Forensic Analytics")
        print("="*70)
        
        analytics = ForensicAnalytics(db)
        results = analytics.run_all_analyses()
        
        # Display results
        print("\n" + "="*70)
        print("Results Summary")
        print("="*70)
        
        # Bridge entities
        print(f"\n1. CONNECTOR ENGINE - Bridge Entities (Hidden Handlers):")
        print(f"   Found {len(results['bridge_entities'])} entities")
        if results['bridge_entities']:
            for i, bridge in enumerate(results['bridge_entities'][:5], 1):
                print(f"\n   {i}. {bridge['name']}")
                print(f"      Type: {bridge.get('entity_type', 'unknown')}")
                print(f"      Betweenness Centrality: {bridge['betweenness_centrality']:.3f}")
                print(f"      Degree (connections): {bridge['degree']}")
        else:
            print("   (Sample data may not have enough entities for bridge detection)")
        
        # Benford's Law violations
        print(f"\n2. ANOMALY ENGINE - Benford's Law Violations:")
        print(f"   Found {len(results['benfords_violations'])} violations")
        if results['benfords_violations']:
            for i, violation in enumerate(results['benfords_violations'][:5], 1):
                print(f"\n   {i}. {violation['filename']}")
                print(f"      Chi-square: {violation['chi_square']:.2f}")
                print(f"      Sample size: {violation['sample_size']}")
        else:
            print("   (Sample data may not have enough amounts for Benford's analysis)")
            print("   (Minimum 30 amounts per document required)")
        
        # Silence intervals
        print(f"\n3. TIMELINE ENGINE - Silence Intervals:")
        print(f"   Found {len(results['silence_intervals'])} gaps")
        if results['silence_intervals']:
            for i, interval in enumerate(results['silence_intervals'][:5], 1):
                print(f"\n   {i}. Gap of {interval['gap_days']} days")
                print(f"      From: {interval['start_date']}")
                print(f"      To: {interval['end_date']}")
        else:
            print("   (No significant gaps detected in sample data)")
        
        # Show all findings in database
        print("\n" + "="*70)
        print("All Findings Stored in Database")
        print("="*70)
        
        findings = db.get_findings()
        print(f"\nTotal findings: {len(findings)}")
        
        for finding in findings:
            print(f"\n- [{finding['severity'].upper()}] {finding['finding_type']}")
            print(f"  {finding['description']}")
            print(f"  Detected: {finding['detected_at']}")
    
    print("\n" + "="*70)
    print("Demonstration Complete!")
    print("="*70)
    print(f"\nDatabase saved to: {db_path}")
    print("You can now use the database for further analysis.")


if __name__ == "__main__":
    main()
