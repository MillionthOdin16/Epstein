#!/usr/bin/env python3
"""
Analytics module for the investigation system.

This module provides:
- Benford's Law violation detection
- Bridge/connection detection between entities
- Statistical analysis of documents and entities
"""

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
import math
from database import InvestigationDB
from ingest import extract_entities_from_file


# Expected Benford's Law distribution for first digits
BENFORDS_LAW = {
    '1': 0.301,
    '2': 0.176,
    '3': 0.125,
    '4': 0.097,
    '5': 0.079,
    '6': 0.067,
    '7': 0.058,
    '8': 0.051,
    '9': 0.046
}


def extract_numbers_from_text(text: str) -> List[str]:
    """Extract numbers from text content.
    
    Args:
        text: Text content to analyze
        
    Returns:
        List of number strings
    """
    # Find all numbers (integers and decimals)
    # Exclude years (4-digit numbers 1900-2099) and single digits
    numbers = []
    
    # Pattern for numbers: integers or decimals with at least 2 digits
    pattern = r'\b\d{2,}(?:\.\d+)?\b'
    matches = re.findall(pattern, text)
    
    for num in matches:
        # Skip years
        if len(num) == 4 and num.startswith(('19', '20')):
            continue
        numbers.append(num)
    
    return numbers


def calculate_benfords_law_chi_squared(numbers: List[str]) -> Tuple[float, bool]:
    """Calculate chi-squared statistic for Benford's Law compliance.
    
    Args:
        numbers: List of number strings
        
    Returns:
        Tuple of (chi_squared_value, is_violation)
        is_violation is True if chi-squared > 15.507 (critical value at 95% confidence)
    """
    if len(numbers) < 30:
        # Not enough data for reliable analysis
        return 0.0, False
    
    # Get first digits
    first_digits = []
    for num in numbers:
        # Get first non-zero digit
        for char in num:
            if char.isdigit() and char != '0':
                first_digits.append(char)
                break
    
    if len(first_digits) < 30:
        return 0.0, False
    
    # Count frequency of each digit
    digit_counts = Counter(first_digits)
    total_count = len(first_digits)
    
    # Calculate chi-squared statistic
    chi_squared = 0.0
    for digit in '123456789':
        observed = digit_counts.get(digit, 0)
        expected = BENFORDS_LAW[digit] * total_count
        
        if expected > 0:
            chi_squared += ((observed - expected) ** 2) / expected
    
    # Critical value at 95% confidence with 8 degrees of freedom
    critical_value = 15.507
    is_violation = chi_squared > critical_value
    
    return chi_squared, is_violation


def detect_benfords_law_violation(filepath: Path) -> Tuple[bool, float, int]:
    """Detect if a document violates Benford's Law.
    
    Args:
        filepath: Path to the document
        
    Returns:
        Tuple of (is_violation, chi_squared, number_count)
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        numbers = extract_numbers_from_text(content)
        chi_squared, is_violation = calculate_benfords_law_chi_squared(numbers)
        
        return is_violation, chi_squared, len(numbers)
    
    except Exception as e:
        print(f"Warning: Could not analyze {filepath}: {e}")
        return False, 0.0, 0


def find_bridges(db: InvestigationDB, min_connections: int = 2) -> List[Dict]:
    """Find bridge entities that connect multiple other entities.
    
    A bridge is an entity that appears with many other entities across documents,
    potentially indicating a central figure or important connection.
    
    Args:
        db: InvestigationDB instance
        min_connections: Minimum number of connections to be considered a bridge
        
    Returns:
        List of bridge entity dictionaries with connection information
    """
    cursor = db.conn.cursor()
    
    # Find entities with multiple connections
    cursor.execute("""
        SELECT e.id, e.name, e.entity_type, e.occurrence_count,
               COUNT(DISTINCT CASE 
                   WHEN e.id = ec.entity1_id THEN ec.entity2_id 
                   ELSE ec.entity1_id 
               END) as unique_connections
        FROM entities e
        JOIN entity_connections ec ON (e.id = ec.entity1_id OR e.id = ec.entity2_id)
        GROUP BY e.id
        HAVING unique_connections >= ?
        ORDER BY unique_connections DESC, e.occurrence_count DESC
        LIMIT 50
    """, (min_connections,))
    
    bridges = []
    for row in cursor.fetchall():
        bridge = dict(row)
        
        # Get connected entities
        cursor.execute("""
            SELECT DISTINCT e2.name, e2.entity_type
            FROM entity_connections ec
            JOIN entities e2 ON (
                (ec.entity1_id = ? AND ec.entity2_id = e2.id) OR
                (ec.entity2_id = ? AND ec.entity1_id = e2.id)
            )
            WHERE e2.id != ?
            LIMIT 10
        """, (bridge['id'], bridge['id'], bridge['id']))
        
        bridge['connected_to'] = [dict(r) for r in cursor.fetchall()]
        bridges.append(bridge)
    
    return bridges


def analyze_documents(db: InvestigationDB, process_entities: bool = True, 
                     check_benfords: bool = True) -> Dict[str, int]:
    """Analyze all documents in the database.
    
    Args:
        db: InvestigationDB instance
        process_entities: Whether to extract and link entities
        check_benfords: Whether to check for Benford's Law violations
        
    Returns:
        Dictionary with analysis statistics
    """
    cursor = db.conn.cursor()
    
    # Get documents that haven't been analyzed or need re-analysis
    cursor.execute("""
        SELECT id, filename, filepath 
        FROM documents 
        WHERE last_analyzed IS NULL
        ORDER BY id
    """)
    
    documents = [dict(row) for row in cursor.fetchall()]
    
    print(f"Analyzing {len(documents)} documents...")
    
    stats = {
        'analyzed': 0,
        'entities_found': 0,
        'connections_created': 0,
        'benfords_violations': 0
    }
    
    for i, doc in enumerate(documents):
        filepath = Path(doc['filepath'])
        
        if not filepath.exists():
            print(f"Warning: File not found: {filepath}")
            continue
        
        # Extract entities if enabled
        if process_entities:
            entities = extract_entities_from_file(filepath)
            
            entity_ids = []
            for entity_name, entity_type in entities:
                entity_id = db.add_entity(entity_name, entity_type, doc['id'])
                entity_ids.append(entity_id)
            
            stats['entities_found'] += len(entities)
            
            # Create connections between entities in the same document
            for j in range(len(entity_ids)):
                for k in range(j + 1, len(entity_ids)):
                    connection_id = db.add_entity_connection(
                        entity_ids[j], entity_ids[k], doc['id']
                    )
                    if connection_id:
                        stats['connections_created'] += 1
        
        # Check Benford's Law if enabled
        if check_benfords:
            is_violation, chi_squared, num_count = detect_benfords_law_violation(filepath)
            
            if is_violation and num_count >= 50:
                # Only flag if we have enough numbers for reliable analysis
                db.mark_document_suspicious(
                    doc['id'],
                    f"Benford's Law violation (χ²={chi_squared:.2f}, n={num_count})",
                    severity='MEDIUM'
                )
                stats['benfords_violations'] += 1
        
        # Mark as analyzed
        db.update_document_analyzed(doc['id'])
        stats['analyzed'] += 1
        
        if (i + 1) % 100 == 0:
            print(f"  Analyzed {i + 1}/{len(documents)} documents...")
    
    print(f"Analysis complete!")
    return stats


def generate_entity_graph_data(db: InvestigationDB) -> Dict:
    """Generate data for entity relationship graph visualization.
    
    Args:
        db: InvestigationDB instance
        
    Returns:
        Dictionary with nodes and edges for graph visualization
    """
    cursor = db.conn.cursor()
    
    # Get top entities by occurrence
    cursor.execute("""
        SELECT id, name, entity_type, occurrence_count
        FROM entities
        ORDER BY occurrence_count DESC
        LIMIT 100
    """)
    
    nodes = [dict(row) for row in cursor.fetchall()]
    node_ids = {node['id'] for node in nodes}
    
    # Get connections between these top entities
    cursor.execute("""
        SELECT entity1_id, entity2_id, COUNT(*) as weight
        FROM entity_connections
        WHERE entity1_id IN ({}) AND entity2_id IN ({})
        GROUP BY entity1_id, entity2_id
    """.format(','.join('?' * len(node_ids)), ','.join('?' * len(node_ids))),
    list(node_ids) + list(node_ids))
    
    edges = [dict(row) for row in cursor.fetchall()]
    
    return {
        'nodes': nodes,
        'edges': edges
    }


if __name__ == '__main__':
    # Test analytics
    print("Testing analytics module...")
    
    with InvestigationDB() as db:
        # Run analysis
        stats = analyze_documents(db, process_entities=True, check_benfords=True)
        
        print(f"\nAnalysis statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Find bridges
        print(f"\nFinding bridge entities...")
        bridges = find_bridges(db, min_connections=2)
        print(f"Found {len(bridges)} bridge entities")
        
        if bridges:
            print(f"\nTop 5 bridge entities:")
            for i, bridge in enumerate(bridges[:5], 1):
                print(f"  {i}. {bridge['name']} ({bridge['entity_type']})")
                print(f"     Connections: {bridge['unique_connections']}, "
                      f"Occurrences: {bridge['occurrence_count']}")
