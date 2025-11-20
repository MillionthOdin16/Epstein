#!/usr/bin/env python3
"""
Example script demonstrating the forensic analysis modules.

This script shows how to use each module programmatically.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.database import init_database, load_documents_from_csv
from analytics.graph_analyst import GraphAnalyst
from analytics.forensic_accountant import ForensicAccountant
from analytics.cartographer import Cartographer
from analytics.timeline_auditor import TimelineAuditor


def example_graph_analysis():
    """Example: Run graph analysis to find bridge nodes."""
    print("\n" + "="*60)
    print("EXAMPLE: Graph Analysis")
    print("="*60)
    
    # Initialize analyst
    analyst = GraphAnalyst(db_path="data/epstein_analysis.db")
    
    # Build the co-occurrence graph
    analyst.build_graph(limit=100)  # Limit to first 100 docs for demo
    
    # Calculate bridge nodes (top connectors)
    bridge_nodes = analyst.calculate_bridge_nodes(top_n=10)
    
    # Print results
    print("\nTop 10 Bridge Nodes:")
    for i, (entity, score, docs) in enumerate(bridge_nodes, 1):
        print(f"{i}. {entity} (centrality: {score:.4f}, docs: {len(docs)})")
    
    # Export results
    analyst.export_bridge_report(bridge_nodes, "example_bridges.csv")
    analyst.export_graph("example_network.gexf")


def example_financial_analysis():
    """Example: Detect financial anomalies."""
    print("\n" + "="*60)
    print("EXAMPLE: Financial Analysis")
    print("="*60)
    
    # Initialize accountant
    accountant = ForensicAccountant(db_path="data/epstein_analysis.db")
    
    # Load financial data
    accountant.load_financial_data(limit=100)
    
    # Perform Benford's Law test
    benford = accountant.benford_test()
    print(f"\nBenford's Law p-value: {benford.get('p_value', 'N/A')}")
    print(f"Suspicious: {benford.get('is_suspicious', False)}")
    
    # Check round numbers
    rounds = accountant.round_number_analysis()
    print(f"\nRound numbers: {rounds.get('round_percentage', 0):.1f}%")
    print(f"Very round: {rounds.get('very_round_percentage', 0):.1f}%")


def example_geospatial_analysis():
    """Example: Map locations and dates."""
    print("\n" + "="*60)
    print("EXAMPLE: Geospatial Analysis")
    print("="*60)
    
    # Initialize cartographer
    cartographer = Cartographer(db_path="data/epstein_analysis.db")
    
    # Extract location data
    cartographer.extract_location_data(limit=50)
    
    print(f"\nFound {len(cartographer.locations)} location mentions")
    
    # Generate map
    cartographer.generate_map("example_map.html")
    print("Map saved to example_map.html")


def example_timeline_analysis():
    """Example: Find silence intervals."""
    print("\n" + "="*60)
    print("EXAMPLE: Timeline Analysis")
    print("="*60)
    
    # Initialize auditor
    auditor = TimelineAuditor(db_path="data/epstein_analysis.db")
    
    # Extract dates
    auditor.extract_timeline_data(limit=100)
    
    print(f"\nExtracted {len(auditor.dates)} date mentions")
    print(f"Successfully parsed {len(auditor.parsed_dates)} dates")
    
    # Find gaps
    gaps = auditor.identify_silence_intervals(gap_days=20)
    
    print(f"\nFound {len(gaps)} silence intervals (>20 days)")
    if gaps:
        largest_gap = max(gaps, key=lambda x: x[2])
        print(f"Largest gap: {largest_gap[2]} days ({largest_gap[0]} to {largest_gap[1]})")


def main():
    """Run all examples."""
    print("="*60)
    print("Forensic Analysis Examples")
    print("="*60)
    print("\nThese examples demonstrate programmatic use of the modules.")
    print("Make sure you've run: python src/run_analysis.py --setup")
    print()
    
    try:
        # Check if database exists
        db_path = Path("data/epstein_analysis.db")
        if not db_path.exists():
            print("ERROR: Database not found!")
            print("Please run: python src/run_analysis.py --setup")
            return
        
        # Run examples
        example_graph_analysis()
        example_financial_analysis()
        example_geospatial_analysis()
        example_timeline_analysis()
        
        print("\n" + "="*60)
        print("Examples complete!")
        print("="*60)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
