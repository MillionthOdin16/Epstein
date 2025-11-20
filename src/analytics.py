#!/usr/bin/env python3
"""
Analytics module for the investigation system.

This module performs advanced analytics including:
- Network graph analysis to find bridge entities
- Benford's Law analysis to detect anomalies in numerical data
"""

import math
from collections import defaultdict, Counter
from typing import List, Set, Dict, Tuple
from database import InvestigationDB


class NetworkAnalyzer:
    """Analyzes entity networks and connections."""
    
    def __init__(self, db: InvestigationDB):
        """
        Initialize the network analyzer.
        
        Args:
            db: InvestigationDB instance
        """
        self.db = db
        self.graph = defaultdict(set)
        
    def build_graph(self):
        """Build a graph of entity connections from the database."""
        cursor = self.db.conn.cursor()
        
        # Get all connections
        cursor.execute('SELECT entity1, entity2 FROM connections')
        for row in cursor.fetchall():
            entity1 = row['entity1']
            entity2 = row['entity2']
            self.graph[entity1].add(entity2)
            self.graph[entity2].add(entity1)
            
        # Also create implicit connections from entities appearing in the same document
        cursor.execute('''
            SELECT e1.entity_name as entity1, e2.entity_name as entity2
            FROM entities e1
            JOIN entities e2 ON e1.file_id = e2.file_id
            WHERE e1.entity_name < e2.entity_name
        ''')
        
        for row in cursor.fetchall():
            entity1 = row['entity1']
            entity2 = row['entity2']
            self.graph[entity1].add(entity2)
            self.graph[entity2].add(entity1)
            
    def find_bridges(self) -> List[str]:
        """
        Find bridge entities in the network.
        
        A bridge entity is one that connects different clusters of entities.
        These are entities that, if removed, would disconnect parts of the network.
        
        Returns:
            List of entity names that are bridges
        """
        if not self.graph:
            self.build_graph()
            
        bridges = []
        
        # Use a simple approach: entities with high betweenness centrality
        # For each entity, count how many paths it's on
        for entity in self.graph:
            # Count connections
            connections = len(self.graph[entity])
            
            # An entity is a potential bridge if it has multiple connections
            # and connects to otherwise disconnected clusters
            if connections >= 3:
                # Check if removing this entity would disconnect the graph
                neighbors = list(self.graph[entity])
                
                # Check if neighbors are connected to each other
                interconnected = 0
                for i in range(len(neighbors)):
                    for j in range(i + 1, len(neighbors)):
                        if neighbors[j] in self.graph.get(neighbors[i], set()):
                            interconnected += 1
                
                # If neighbors aren't well connected to each other,
                # this entity is a bridge
                max_connections = len(neighbors) * (len(neighbors) - 1) / 2
                if max_connections > 0:
                    interconnectedness = interconnected / max_connections
                    if interconnectedness < 0.5:  # Less than 50% interconnected
                        bridges.append(entity)
        
        return bridges
        
    def get_entity_stats(self) -> Dict[str, Dict]:
        """
        Get statistics for each entity.
        
        Returns:
            Dictionary mapping entity names to their statistics
        """
        if not self.graph:
            self.build_graph()
            
        stats = {}
        
        for entity in self.graph:
            stats[entity] = {
                'connections': len(self.graph[entity]),
                'connected_to': list(self.graph[entity])
            }
        
        return stats


class BenfordsLawAnalyzer:
    """Analyzes numerical data using Benford's Law."""
    
    @staticmethod
    def get_first_digit(number: int) -> int:
        """
        Get the first digit of a number.
        
        Args:
            number: Integer to analyze
            
        Returns:
            First digit (1-9)
        """
        # Handle negative numbers by taking absolute value
        number = abs(number)
        while number >= 10:
            number //= 10
        return number
        
    @staticmethod
    def expected_benford_distribution() -> Dict[int, float]:
        """
        Get the expected Benford's Law distribution.
        
        Returns:
            Dictionary mapping digits (1-9) to their expected probabilities
        """
        return {d: math.log10(1 + 1/d) for d in range(1, 10)}
        
    @staticmethod
    def calculate_chi_squared(observed: Dict[int, int], expected: Dict[int, float], 
                             total: int) -> float:
        """
        Calculate chi-squared statistic for goodness of fit.
        
        Args:
            observed: Observed frequencies of digits
            expected: Expected probabilities from Benford's Law
            total: Total number of observations
            
        Returns:
            Chi-squared statistic
        """
        chi_squared = 0.0
        
        for digit in range(1, 10):
            observed_count = observed.get(digit, 0)
            expected_count = expected[digit] * total
            
            if expected_count > 0:
                chi_squared += (observed_count - expected_count) ** 2 / expected_count
        
        return chi_squared
        
    def detect_benfords_law_violation(self, numbers: List[int], 
                                     threshold: float = 15.507) -> Tuple[bool, float, Dict]:
        """
        Detect if a set of numbers violates Benford's Law.
        
        Args:
            numbers: List of numbers to analyze
            threshold: Chi-squared threshold for violation (default: 15.507 for p=0.05, df=8)
            
        Returns:
            Tuple of (is_violation, chi_squared_score, digit_distribution)
        """
        if len(numbers) < 30:
            # Not enough data for reliable Benford's Law analysis
            return False, 0.0, {}
        
        # Count first digits
        first_digits = [self.get_first_digit(abs(n)) for n in numbers if n != 0]
        digit_counts = Counter(first_digits)
        
        # Calculate observed distribution
        total = len(first_digits)
        observed = {d: digit_counts.get(d, 0) for d in range(1, 10)}
        
        # Get expected distribution
        expected = self.expected_benford_distribution()
        
        # Calculate chi-squared statistic
        chi_squared = self.calculate_chi_squared(observed, expected, total)
        
        # Check if it violates Benford's Law
        is_violation = chi_squared > threshold
        
        # Calculate percentage distribution for reporting
        distribution = {
            d: {
                'observed': observed[d],
                'observed_pct': (observed[d] / total * 100) if total > 0 else 0,
                'expected_pct': expected[d] * 100
            }
            for d in range(1, 10)
        }
        
        return is_violation, chi_squared, distribution


def find_bridges(db_path: str = "investigation.db") -> List[str]:
    """
    Find bridge entities in the network.
    
    Args:
        db_path: Path to the investigation database
        
    Returns:
        List of entity names that are bridges
    """
    db = InvestigationDB(db_path)
    db.connect()
    
    try:
        analyzer = NetworkAnalyzer(db)
        bridges = analyzer.find_bridges()
        return bridges
    finally:
        db.close()


def detect_benfords_law_violation(numbers: List[int]) -> Tuple[bool, float, Dict]:
    """
    Detect if a set of numbers violates Benford's Law.
    
    Args:
        numbers: List of numbers to analyze
        
    Returns:
        Tuple of (is_violation, chi_squared_score, digit_distribution)
    """
    analyzer = BenfordsLawAnalyzer()
    return analyzer.detect_benfords_law_violation(numbers)


def run_analytics(db_path: str = "investigation.db"):
    """
    Main function to run analytics.
    
    Args:
        db_path: Path to the investigation database
    """
    db = InvestigationDB(db_path)
    db.connect()
    
    try:
        # Network analysis
        print("🔍 Running network analysis...")
        network_analyzer = NetworkAnalyzer(db)
        bridges = network_analyzer.find_bridges()
        
        print(f"✓ Found {len(bridges)} bridge entities")
        for bridge in bridges[:10]:  # Show top 10
            print(f"   - {bridge}")
        
        # Get statistics
        stats = db.get_statistics()
        print(f"\n📊 Database Statistics:")
        print(f"   Total files: {stats['total_files']}")
        print(f"   Total leads: {stats['total_leads']}")
        print(f"   New leads: {stats['new_leads']}")
        print(f"   Suspicious documents: {stats['suspicious_docs']}")
        print(f"   Total entities: {stats['total_entities']}")
        print(f"   Total connections: {stats['total_connections']}")
        
        return bridges, stats
        
    finally:
        db.close()


if __name__ == '__main__':
    run_analytics()
