#!/usr/bin/env python3
"""
Validation script to demonstrate the automated investigation system.

This script tests all components of the investigation system to ensure they work correctly.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database import InvestigationDB
from ingest import ingest_new_files, extract_entities_from_file
from analytics import detect_benfords_law_violation, find_bridges, analyze_documents


def test_database():
    """Test database initialization and basic operations."""
    print("Testing Database...")
    
    # Use a test database
    db = InvestigationDB("test_investigation.db")
    
    # Test adding a document
    doc_id = db.add_document(
        filename="TEST-001-DOC.txt",
        filepath="/tmp/test.txt",
        category="TEST",
        source="001",
        content_hash="abc123"
    )
    assert doc_id is not None, "Failed to add document"
    
    # Test adding an entity
    entity_id = db.add_entity("Test Person", "PERSON", doc_id)
    assert entity_id is not None, "Failed to add entity"
    
    # Test adding a lead
    lead_id = db.add_lead("Test lead", entity_id=entity_id, priority="HIGH")
    assert lead_id is not None, "Failed to add lead"
    
    # Test marking document suspicious
    susp_id = db.mark_document_suspicious(doc_id, "Test reason", "MEDIUM")
    assert susp_id is not None, "Failed to mark document suspicious"
    
    # Test getting statistics
    stats = db.get_statistics()
    assert stats['total_documents'] == 1, "Statistics not working"
    assert stats['total_entities'] == 1, "Statistics not working"
    assert stats['total_leads'] == 1, "Statistics not working"
    
    db.close()
    
    # Clean up
    os.remove("test_investigation.db")
    
    print("✓ Database tests passed!\n")


def test_benfords_law():
    """Test Benford's Law violation detection."""
    print("Testing Benford's Law Detection...")
    
    # Create a test file with sequential numbers (should violate Benford's Law)
    test_file = Path("/tmp/test_benfords.txt")
    with open(test_file, 'w') as f:
        # Write sequential numbers starting with 1 (violates Benford's Law)
        numbers = [str(100 + i) for i in range(60)]
        f.write("Test document with numbers: " + ", ".join(numbers))
    
    is_violation, chi_squared, num_count = detect_benfords_law_violation(test_file)
    
    assert num_count >= 50, "Should have detected enough numbers"
    assert is_violation, "Should detect Benford's Law violation"
    assert chi_squared > 15.507, "Chi-squared should exceed threshold"
    
    # Clean up
    test_file.unlink()
    
    print(f"✓ Benford's Law tests passed! (χ²={chi_squared:.2f}, n={num_count})\n")


def test_entity_extraction():
    """Test entity extraction from documents."""
    print("Testing Entity Extraction...")
    
    # Create a test file with entities
    test_file = Path("/tmp/test_entities.txt")
    with open(test_file, 'w') as f:
        f.write("""
        Meeting between John Smith and Jane Doe.
        John Smith discussed the proposal with Robert Johnson.
        Jane Doe agreed to coordinate with Robert Johnson.
        """)
    
    entities = extract_entities_from_file(test_file)
    
    assert len(entities) > 0, "Should extract entities"
    entity_names = [name for name, _ in entities]
    assert any("John Smith" in name for name in entity_names), "Should find John Smith"
    
    # Clean up
    test_file.unlink()
    
    print(f"✓ Entity extraction tests passed! (found {len(entities)} entities)\n")


def test_bridge_finding():
    """Test bridge entity detection."""
    print("Testing Bridge Finding...")
    
    # Create test database with entities and connections
    db = InvestigationDB("test_investigation.db")
    
    # Create documents
    doc1_id = db.add_document("DOC1.txt", "/tmp/doc1.txt", "TEST", "001")
    doc2_id = db.add_document("DOC2.txt", "/tmp/doc2.txt", "TEST", "001")
    
    # Create entities - Person A is a bridge connecting B and C
    person_a_id = db.add_entity("Person A", "PERSON", doc1_id)
    person_b_id = db.add_entity("Person B", "PERSON", doc1_id)
    person_c_id = db.add_entity("Person C", "PERSON", doc2_id)
    person_d_id = db.add_entity("Person D", "PERSON", doc2_id)
    
    # Create connections
    db.add_entity_connection(person_a_id, person_b_id, doc1_id)
    db.add_entity_connection(person_a_id, person_c_id, doc2_id)
    db.add_entity_connection(person_a_id, person_d_id, doc2_id)
    
    # Find bridges
    bridges = find_bridges(db, min_connections=2)
    
    assert len(bridges) > 0, "Should find bridge entities"
    bridge_names = [b['name'] for b in bridges]
    assert "Person A" in bridge_names, "Person A should be identified as a bridge"
    
    person_a_bridge = next(b for b in bridges if b['name'] == "Person A")
    assert person_a_bridge['unique_connections'] >= 3, "Person A should have 3 connections"
    
    db.close()
    
    # Clean up
    os.remove("test_investigation.db")
    
    print(f"✓ Bridge finding tests passed! (found {len(bridges)} bridges)\n")


def main():
    """Run all validation tests."""
    print("="*60)
    print("AUTOMATED INVESTIGATION SYSTEM - VALIDATION TESTS")
    print("="*60)
    print()
    
    try:
        test_database()
        test_benfords_law()
        test_entity_extraction()
        test_bridge_finding()
        
        print("="*60)
        print("✓ ALL VALIDATION TESTS PASSED!")
        print("="*60)
        print()
        print("The automated investigation system is working correctly.")
        print("It will run daily at 3 AM UTC via GitHub Actions.")
        print()
        return 0
    
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
