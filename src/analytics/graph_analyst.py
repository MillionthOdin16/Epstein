"""
Graph Analyst Module - Network Topology Analysis

This module identifies "Bridge Nodes" - entities that connect disconnected groups.
Uses NetworkX to build a co-occurrence graph and calculate betweenness centrality.
"""

import re
import sqlite3
import csv
from typing import List, Dict, Tuple, Set
from collections import defaultdict
import networkx as nx
from pathlib import Path

from .database import get_db_connection


class GraphAnalyst:
    """
    Analyzes network topology to find bridge nodes.
    """
    
    def __init__(self, db_path: str = "data/epstein_analysis.db"):
        """
        Initialize the Graph Analyst.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self.graph = nx.Graph()
        self.entity_documents = defaultdict(set)  # entity -> set of (doc_id, doc_hash, page)
        
    def extract_entities(self, text: str) -> Set[str]:
        """
        Extract entity names from text.
        Uses simple heuristics to find capitalized names (2-3 words).
        
        Args:
            text: Document text
            
        Returns:
            Set of entity names
        """
        # Pattern for capitalized names (2-3 words)
        # This is a simple pattern; in production you'd use spaCy NER
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b'
        
        entities = set()
        matches = re.findall(pattern, text)
        
        for match in matches:
            # Filter out common words and short names
            if len(match) > 5 and match not in ['The', 'This', 'That', 'There', 'These', 'Those']:
                entities.add(match)
        
        return entities
    
    def build_graph(self, limit: int = None) -> None:
        """
        Build the co-occurrence graph from documents.
        
        Args:
            limit: Optional limit on number of documents to process
        """
        print("Building co-occurrence graph...")
        
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # Get all documents
        if limit:
            cursor.execute("SELECT id, filename, source_document_hash, text, page_number FROM documents LIMIT ?", (limit,))
        else:
            cursor.execute("SELECT id, filename, source_document_hash, text, page_number FROM documents")
        
        doc_count = 0
        edge_count = 0
        
        for row in cursor.fetchall():
            doc_id = row[0]
            filename = row[1]
            doc_hash = row[2]
            text = row[3]
            page_number = row[4]
            
            # Extract entities from this document
            entities = self.extract_entities(text)
            
            # Add entities as nodes
            for entity in entities:
                if entity not in self.graph:
                    self.graph.add_node(entity)
                self.entity_documents[entity].add((doc_id, doc_hash, page_number, filename))
            
            # Create edges for co-occurring entities
            entity_list = list(entities)
            for i in range(len(entity_list)):
                for j in range(i + 1, len(entity_list)):
                    entity1, entity2 = entity_list[i], entity_list[j]
                    
                    if self.graph.has_edge(entity1, entity2):
                        # Increment weight
                        self.graph[entity1][entity2]['weight'] += 1
                        self.graph[entity1][entity2]['documents'].append((doc_id, doc_hash, page_number, filename))
                    else:
                        # Create new edge
                        self.graph.add_edge(entity1, entity2, weight=1, 
                                          documents=[(doc_id, doc_hash, page_number, filename)])
                        edge_count += 1
            
            doc_count += 1
            if doc_count % 100 == 0:
                print(f"Processed {doc_count} documents, {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        
        conn.close()
        
        print(f"\nGraph built:")
        print(f"  Documents processed: {doc_count}")
        print(f"  Nodes (entities): {self.graph.number_of_nodes()}")
        print(f"  Edges (co-occurrences): {self.graph.number_of_edges()}")
    
    def calculate_bridge_nodes(self, top_n: int = 50) -> List[Tuple[str, float, List]]:
        """
        Calculate betweenness centrality and identify bridge nodes.
        
        Args:
            top_n: Number of top bridge nodes to return
            
        Returns:
            List of tuples (entity_name, centrality_score, source_documents)
        """
        print("\nCalculating betweenness centrality...")
        
        if self.graph.number_of_nodes() == 0:
            print("Warning: Graph is empty. No nodes to analyze.")
            return []
        
        # Calculate betweenness centrality
        centrality = nx.betweenness_centrality(self.graph, weight='weight')
        
        # Sort by centrality score
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        
        # Get top N bridge nodes with their source documents
        bridge_nodes = []
        for entity, score in sorted_nodes[:top_n]:
            # Get source documents for this entity
            docs = list(self.entity_documents[entity])
            bridge_nodes.append((entity, score, docs))
        
        print(f"Identified top {min(top_n, len(bridge_nodes))} bridge nodes")
        return bridge_nodes
    
    def export_bridge_report(self, bridge_nodes: List[Tuple[str, float, List]], 
                            output_path: str = "bridge_report.csv") -> None:
        """
        Export bridge nodes to CSV with source citations.
        
        Args:
            bridge_nodes: List of (entity, centrality, documents) tuples
            output_path: Path to output CSV file
        """
        print(f"\nExporting bridge report to: {output_path}")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Rank', 'Entity Name', 'Betweenness Centrality', 
                'Document Count', 'Source Document Hash', 'Page Number', 'Filename'
            ])
            
            for rank, (entity, score, docs) in enumerate(bridge_nodes, 1):
                # Get first document as primary source
                if docs:
                    doc_id, doc_hash, page_number, filename = list(docs)[0]
                    writer.writerow([
                        rank, entity, f"{score:.6f}", len(docs), 
                        doc_hash, page_number, filename
                    ])
                else:
                    writer.writerow([rank, entity, f"{score:.6f}", 0, '', '', ''])
        
        print(f"Exported {len(bridge_nodes)} bridge nodes")
    
    def export_graph(self, output_path: str = "network.gexf") -> None:
        """
        Export the full graph to GEXF format for Gephi visualization.
        
        Args:
            output_path: Path to output GEXF file
        """
        print(f"\nExporting graph to: {output_path}")
        
        # Create a copy of the graph for export
        export_graph = self.graph.copy()
        
        # Add node attributes (document count)
        for node in export_graph.nodes():
            export_graph.nodes[node]['doc_count'] = len(self.entity_documents[node])
        
        # Convert edge document lists to counts (GEXF can't serialize lists)
        for u, v, data in export_graph.edges(data=True):
            if 'documents' in data:
                data['doc_count'] = len(data['documents'])
                del data['documents']
        
        # Write graph to GEXF
        nx.write_gexf(export_graph, output_path)
        
        print(f"Exported graph with {export_graph.number_of_nodes()} nodes and {export_graph.number_of_edges()} edges")
    
    def run_analysis(self, limit: int = None, output_dir: str = ".") -> None:
        """
        Run complete graph analysis pipeline.
        
        Args:
            limit: Optional limit on documents to process
            output_dir: Directory for output files
        """
        print("="*60)
        print("GRAPH ANALYST - Network Topology Analysis")
        print("="*60)
        
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Build graph
        self.build_graph(limit=limit)
        
        if self.graph.number_of_nodes() == 0:
            print("\nERROR: No entities found. Cannot perform analysis.")
            return
        
        # Calculate bridge nodes
        bridge_nodes = self.calculate_bridge_nodes(top_n=50)
        
        # Export results
        bridge_report_path = Path(output_dir) / "bridge_report.csv"
        network_graph_path = Path(output_dir) / "network.gexf"
        
        self.export_bridge_report(bridge_nodes, str(bridge_report_path))
        self.export_graph(str(network_graph_path))
        
        print("\n" + "="*60)
        print("Graph analysis complete!")
        print("="*60)


def main():
    """Main function for running graph analysis."""
    analyst = GraphAnalyst()
    analyst.run_analysis(output_dir="data/analysis_output")


if __name__ == "__main__":
    main()
