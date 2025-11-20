#!/usr/bin/env python3
"""
Forensic analytics module for detecting patterns and anomalies.

This module provides three detection engines:
1. Connector Engine - Graph analysis for finding bridge entities
2. Anomaly Engine - Statistical analysis using Benford's Law
3. Timeline Engine - Chronological gap analysis
"""

import re
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import math

try:
    import networkx as nx
except ImportError:
    nx = None
    print("Warning: NetworkX not installed. Install with: pip install networkx")


# Benford's Law expected distribution for first digits (1-9)
BENFORDS_DISTRIBUTION = {
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

# Currency pattern regexes
CURRENCY_PATTERNS = [
    r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
    r'USD\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # USD 1,234.56
    r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*USD',  # 1,234.56 USD
]


class ConnectorEngine:
    """
    Graph theory-based engine for finding bridge entities (hidden handlers).
    
    Analyzes entity co-occurrences to build a network graph and identifies
    entities with high betweenness centrality but low degree.
    """
    
    def __init__(self, db):
        """
        Initialize the Connector Engine.
        
        Args:
            db: InvestigationDB instance
        """
        self.db = db
        self.graph = None
    
    def build_graph(self):
        """
        Build a NetworkX graph from entity co-occurrences.
        
        Nodes represent entities, edges represent co-occurrence in documents.
        Edge weights represent the number of documents where entities co-occur.
        """
        if nx is None:
            raise ImportError("NetworkX is required. Install with: pip install networkx")
        
        self.graph = nx.Graph()
        
        # Add all entities as nodes
        entities = self.db.get_all_entities()
        for entity in entities:
            self.graph.add_node(entity['id'], name=entity['name'], 
                               entity_type=entity.get('entity_type'))
        
        # Add edges based on co-occurrences
        cooccurrences = self.db.get_entity_cooccurrences()
        for entity1_id, entity2_id, count in cooccurrences:
            self.graph.add_edge(entity1_id, entity2_id, weight=count)
        
        return self.graph
    
    def calculate_metrics(self) -> Dict[int, Dict[str, float]]:
        """
        Calculate graph metrics for all entities.
        
        Returns:
            Dictionary mapping entity_id to metrics (centrality, degree)
        """
        if self.graph is None:
            self.build_graph()
        
        metrics = {}
        
        # Calculate betweenness centrality
        betweenness = nx.betweenness_centrality(self.graph)
        
        # Calculate degree for each node
        degrees = dict(self.graph.degree())
        
        for node_id in self.graph.nodes():
            metrics[node_id] = {
                'betweenness_centrality': betweenness.get(node_id, 0),
                'degree': degrees.get(node_id, 0)
            }
        
        return metrics
    
    def find_bridges(self, min_centrality: float = 0.1, 
                     max_degree: int = 5) -> List[Dict[str, Any]]:
        """
        Find bridge entities (hidden handlers).
        
        Bridge entities have high betweenness centrality (>min_centrality) 
        but low degree (<max_degree), indicating they connect disparate parts 
        of the network without many direct connections.
        
        Args:
            min_centrality: Minimum betweenness centrality threshold (default: 0.1)
            max_degree: Maximum degree threshold (default: 5)
        
        Returns:
            List of bridge entities with their metrics
        """
        if self.graph is None:
            self.build_graph()
        
        metrics = self.calculate_metrics()
        bridges = []
        
        for entity_id, entity_metrics in metrics.items():
            centrality = entity_metrics['betweenness_centrality']
            degree = entity_metrics['degree']
            
            if centrality > min_centrality and degree < max_degree:
                # Get entity details
                entities = [e for e in self.db.get_all_entities() if e['id'] == entity_id]
                if entities:
                    entity = entities[0]
                    bridges.append({
                        'entity_id': entity_id,
                        'name': entity['name'],
                        'entity_type': entity.get('entity_type'),
                        'betweenness_centrality': centrality,
                        'degree': degree
                    })
        
        # Sort by centrality (descending)
        bridges.sort(key=lambda x: x['betweenness_centrality'], reverse=True)
        
        # Store findings in database
        for bridge in bridges:
            metadata = json.dumps({
                'betweenness_centrality': bridge['betweenness_centrality'],
                'degree': bridge['degree']
            })
            
            description = (
                f"Hidden handler detected: {bridge['name']} has high centrality "
                f"({bridge['betweenness_centrality']:.3f}) but low connections ({bridge['degree']})"
            )
            
            self.db.add_finding(
                finding_type='bridge_entity',
                description=description,
                severity='high',
                entity_id=bridge['entity_id'],
                metadata=metadata
            )
        
        return bridges


class AnomalyEngine:
    """
    Statistical anomaly detection engine using Benford's Law.
    
    Analyzes numerical patterns in documents to detect potential fabrication.
    """
    
    def __init__(self, db):
        """
        Initialize the Anomaly Engine.
        
        Args:
            db: InvestigationDB instance
        """
        self.db = db
        self.benfords_distribution = BENFORDS_DISTRIBUTION
    
    def extract_currency_amounts(self, text: str) -> List[float]:
        """
        Extract currency amounts from text using regex.
        
        Args:
            text: Document text content
        
        Returns:
            List of numerical amounts found
        """
        amounts = []
        
        for pattern in CURRENCY_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Remove commas and convert to float
                try:
                    amount = float(match.replace(',', ''))
                    if amount > 0:
                        amounts.append(amount)
                except ValueError:
                    continue
        
        return amounts
    
    def get_first_digit_distribution(self, numbers: List[float]) -> Dict[str, float]:
        """
        Calculate the distribution of first digits in a list of numbers.
        
        Args:
            numbers: List of numerical values
        
        Returns:
            Dictionary mapping first digit to its frequency
        """
        if not numbers:
            return {}
        
        first_digits = []
        for num in numbers:
            # Get the first significant digit
            first_digit = str(int(abs(num)))[0]
            if first_digit != '0':
                first_digits.append(first_digit)
        
        if not first_digits:
            return {}
        
        # Calculate frequencies
        total = len(first_digits)
        distribution = {}
        counter = Counter(first_digits)
        
        for digit in '123456789':
            distribution[digit] = counter.get(digit, 0) / total
        
        return distribution
    
    def chi_square_test(self, observed: Dict[str, float], 
                        expected: Dict[str, float],
                        sample_size: int) -> float:
        """
        Perform chi-square test to compare observed vs expected distributions.
        
        Args:
            observed: Observed distribution
            expected: Expected distribution (Benford's Law)
            sample_size: Number of observations
        
        Returns:
            Chi-square statistic
        """
        chi_square = 0.0
        
        for digit in '123456789':
            obs_freq = observed.get(digit, 0) * sample_size
            exp_freq = expected.get(digit, 0) * sample_size
            
            if exp_freq > 0:
                chi_square += ((obs_freq - exp_freq) ** 2) / exp_freq
        
        return chi_square
    
    def detect_benfords_law_violation(self, 
                                       min_sample_size: int = 30,
                                       chi_square_threshold: float = 15.507) -> List[Dict[str, Any]]:
        """
        Detect documents with significant deviations from Benford's Law.
        
        Benford's Law states that in many naturally occurring datasets,
        the first digit follows a specific logarithmic distribution.
        Significant deviations may indicate fabricated numbers.
        
        Args:
            min_sample_size: Minimum number of amounts needed for analysis
            chi_square_threshold: Chi-square critical value (default: 15.507 for p<0.05, df=8)
        
        Returns:
            List of documents with Benford's Law violations
        """
        violations = []
        documents = self.db.get_all_documents()
        
        for doc in documents:
            if not doc.get('content'):
                continue
            
            # Extract currency amounts
            amounts = self.extract_currency_amounts(doc['content'])
            
            if len(amounts) < min_sample_size:
                continue
            
            # Get first digit distribution
            observed_dist = self.get_first_digit_distribution(amounts)
            
            if not observed_dist:
                continue
            
            # Perform chi-square test
            chi_square = self.chi_square_test(
                observed_dist, 
                self.benfords_distribution,
                len(amounts)
            )
            
            # Check if violation is significant
            if chi_square > chi_square_threshold:
                violations.append({
                    'document_id': doc['id'],
                    'filename': doc['filename'],
                    'sample_size': len(amounts),
                    'chi_square': chi_square,
                    'observed_distribution': observed_dist
                })
                
                # Store finding in database
                metadata = json.dumps({
                    'sample_size': len(amounts),
                    'chi_square': chi_square,
                    'observed_distribution': observed_dist,
                    'expected_distribution': self.benfords_distribution
                })
                
                description = (
                    f"Benford's Law violation detected in {doc['filename']}: "
                    f"Chi-square={chi_square:.2f} (threshold={chi_square_threshold:.2f}), "
                    f"sample_size={len(amounts)}"
                )
                
                self.db.add_finding(
                    finding_type='benfords_violation',
                    description=description,
                    severity='high',
                    document_id=doc['id'],
                    metadata=metadata
                )
        
        # Sort by chi-square value (descending)
        violations.sort(key=lambda x: x['chi_square'], reverse=True)
        
        return violations


class TimelineEngine:
    """
    Chronological analysis engine for detecting activity patterns.
    
    Extracts dates from documents and identifies suspicious gaps in activity.
    """
    
    def __init__(self, db):
        """
        Initialize the Timeline Engine.
        
        Args:
            db: InvestigationDB instance
        """
        self.db = db
    
    def extract_dates(self, text: str) -> List[datetime]:
        """
        Extract dates from text using various patterns.
        
        Args:
            text: Document text content
        
        Returns:
            List of datetime objects found in text
        """
        dates = []
        
        # Common date patterns
        patterns = [
            # MM/DD/YYYY or MM-DD-YYYY
            (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', lambda m: (int(m[0]), int(m[1]), int(m[2]))),
            # Month DD, YYYY
            (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b',
             lambda m: (self._month_to_num(m[0]), int(m[1]), int(m[2]))),
            # DD Month YYYY
            (r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',
             lambda m: (self._month_to_num(m[1]), int(m[0]), int(m[2]))),
            # YYYY-MM-DD (ISO format)
            (r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', lambda m: (int(m[1]), int(m[2]), int(m[0]))),
        ]
        
        for pattern, parser in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    month, day, year = parser(match.groups())
                    date_obj = datetime(year, month, day)
                    # Only include reasonable dates (1900-2050)
                    if 1900 <= year <= 2050:
                        dates.append(date_obj)
                except (ValueError, IndexError):
                    continue
        
        return sorted(set(dates))
    
    def _month_to_num(self, month_name: str) -> int:
        """Convert month name to number."""
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        return months.get(month_name.lower(), 1)
    
    def extract_all_dates_from_documents(self) -> List[Tuple[int, str, datetime]]:
        """
        Extract all dates from all documents.
        
        Returns:
            List of tuples (document_id, filename, date)
        """
        all_dates = []
        documents = self.db.get_all_documents()
        
        for doc in documents:
            if not doc.get('content'):
                continue
            
            dates = self.extract_dates(doc['content'])
            for date in dates:
                all_dates.append((doc['id'], doc['filename'], date))
        
        return sorted(all_dates, key=lambda x: x[2])
    
    def find_silence_intervals(self, min_gap_days: int = 20) -> List[Dict[str, Any]]:
        """
        Identify gaps in document activity (silence intervals).
        
        Periods with no document dates may indicate:
        - Missing documents
        - Deliberate concealment
        - Periods of reduced activity
        
        Args:
            min_gap_days: Minimum gap in days to be considered significant (default: 20)
        
        Returns:
            List of silence intervals with start/end dates and duration
        """
        all_dates = self.extract_all_dates_from_documents()
        
        if len(all_dates) < 2:
            return []
        
        silence_intervals = []
        
        # Group by unique dates (ignore duplicate dates from different documents)
        unique_dates = sorted(set(date for _, _, date in all_dates))
        
        # Find gaps between consecutive dates
        for i in range(len(unique_dates) - 1):
            date1 = unique_dates[i]
            date2 = unique_dates[i + 1]
            gap_days = (date2 - date1).days
            
            if gap_days > min_gap_days:
                interval = {
                    'start_date': date1.strftime('%Y-%m-%d'),
                    'end_date': date2.strftime('%Y-%m-%d'),
                    'gap_days': gap_days
                }
                silence_intervals.append(interval)
                
                # Store finding in database
                metadata = json.dumps({
                    'start_date': interval['start_date'],
                    'end_date': interval['end_date'],
                    'gap_days': gap_days
                })
                
                description = (
                    f"Silence interval detected: {gap_days} days between "
                    f"{interval['start_date']} and {interval['end_date']}"
                )
                
                self.db.add_finding(
                    finding_type='silence_interval',
                    description=description,
                    severity='medium',
                    metadata=metadata
                )
        
        # Sort by gap duration (descending)
        silence_intervals.sort(key=lambda x: x['gap_days'], reverse=True)
        
        return silence_intervals


class ForensicAnalytics:
    """
    Main forensic analytics coordinator.
    
    Provides a unified interface to all detection engines.
    """
    
    def __init__(self, db):
        """
        Initialize forensic analytics with all engines.
        
        Args:
            db: InvestigationDB instance
        """
        self.db = db
        self.connector_engine = ConnectorEngine(db)
        self.anomaly_engine = AnomalyEngine(db)
        self.timeline_engine = TimelineEngine(db)
    
    def run_all_analyses(self) -> Dict[str, Any]:
        """
        Run all forensic analyses and return comprehensive results.
        
        Returns:
            Dictionary with results from all engines
        """
        results = {
            'bridge_entities': [],
            'benfords_violations': [],
            'silence_intervals': []
        }
        
        try:
            print("Running Connector Engine (Graph Analysis)...")
            results['bridge_entities'] = self.connector_engine.find_bridges()
            print(f"  Found {len(results['bridge_entities'])} bridge entities")
        except Exception as e:
            print(f"  Error in Connector Engine: {e}")
        
        try:
            print("Running Anomaly Engine (Benford's Law)...")
            results['benfords_violations'] = self.anomaly_engine.detect_benfords_law_violation()
            print(f"  Found {len(results['benfords_violations'])} Benford's Law violations")
        except Exception as e:
            print(f"  Error in Anomaly Engine: {e}")
        
        try:
            print("Running Timeline Engine (Chronological Analysis)...")
            results['silence_intervals'] = self.timeline_engine.find_silence_intervals()
            print(f"  Found {len(results['silence_intervals'])} silence intervals")
        except Exception as e:
            print(f"  Error in Timeline Engine: {e}")
        
        return results


if __name__ == "__main__":
    # Example usage
    from database import InvestigationDB
    
    print("Forensic Analytics Module")
    print("="*60)
    print("\nAvailable engines:")
    print("1. Connector Engine - Graph theory analysis")
    print("2. Anomaly Engine - Benford's Law detection")
    print("3. Timeline Engine - Chronological gap analysis")
    print("\nImport this module to use the analytics engines.")
