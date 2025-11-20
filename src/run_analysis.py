#!/usr/bin/env python3
"""
Main runner for Epstein Files Forensic Analysis

This script runs all four forensic analysis modules:
1. Graph Analyst - Network topology
2. Forensic Accountant - Financial pattern recognition
3. Cartographer - Geospatial correlation
4. Timeline Auditor - Gap analysis
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.database import init_database, load_documents_from_csv, get_db_connection
from analytics.graph_analyst import GraphAnalyst
from analytics.forensic_accountant import ForensicAccountant
from analytics.cartographer import Cartographer
from analytics.timeline_auditor import TimelineAuditor


def setup_database(csv_path: str, db_path: str, limit: int = None) -> None:
    """
    Initialize database and load documents.
    
    Args:
        csv_path: Path to CSV file
        db_path: Path to database file
        limit: Optional limit on documents to load
    """
    print("="*60)
    print("DATABASE SETUP")
    print("="*60)
    
    # Check if database already exists and has data
    db_file = Path(db_path)
    if db_file.exists():
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            print(f"Database already contains {count} documents.")
            response = input("Reload data? (y/n): ")
            if response.lower() != 'y':
                print("Using existing database.")
                return
            else:
                # Delete and recreate
                db_file.unlink()
    
    # Initialize database schema
    init_database(db_path)
    
    # Load documents from CSV
    if Path(csv_path).exists():
        print(f"\nLoading documents from: {csv_path}")
        count = load_documents_from_csv(csv_path, db_path, limit=limit)
        print(f"Loaded {count} documents into database")
    else:
        print(f"\nERROR: CSV file not found: {csv_path}")
        print("Please run: python3 scripts/download_data.py")
        sys.exit(1)
    
    print("\nDatabase setup complete!\n")


def run_all_analyses(db_path: str, output_dir: str, limit: int = None) -> None:
    """
    Run all forensic analysis modules.
    
    Args:
        db_path: Path to database
        output_dir: Directory for output files
        limit: Optional limit on documents to process
    """
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("RUNNING FORENSIC ANALYSIS SUITE")
    print("="*60)
    print(f"Output directory: {output_dir}")
    if limit:
        print(f"Document limit: {limit}")
    print()
    
    # 1. Graph Analyst
    print("\n[1/4] Running Graph Analyst...")
    try:
        graph_analyst = GraphAnalyst(db_path)
        graph_analyst.run_analysis(limit=limit, output_dir=output_dir)
    except Exception as e:
        print(f"ERROR in Graph Analyst: {e}")
    
    # 2. Forensic Accountant
    print("\n[2/4] Running Forensic Accountant...")
    try:
        accountant = ForensicAccountant(db_path)
        accountant.run_analysis(limit=limit, output_dir=output_dir)
    except Exception as e:
        print(f"ERROR in Forensic Accountant: {e}")
    
    # 3. Cartographer
    print("\n[3/4] Running Cartographer...")
    try:
        cartographer = Cartographer(db_path)
        cartographer.run_analysis(limit=limit, output_dir=output_dir)
    except Exception as e:
        print(f"ERROR in Cartographer: {e}")
    
    # 4. Timeline Auditor
    print("\n[4/4] Running Timeline Auditor...")
    try:
        auditor = TimelineAuditor(db_path)
        auditor.run_analysis(limit=limit, output_dir=output_dir)
    except Exception as e:
        print(f"ERROR in Timeline Auditor: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE!")
    print("="*60)
    print(f"\nOutput files in: {output_dir}/")
    print("  - bridge_report.csv (Top 50 bridge nodes)")
    print("  - network.gexf (Full graph for Gephi)")
    print("  - financial_analysis_report.csv (Benford's Law & round numbers)")
    print("  - flight_map.html (Interactive geospatial map)")
    print("  - location_report.csv (All location mentions)")
    print("  - silence_report.md (Timeline gaps)")
    print("  - timeline_data.csv (All extracted dates)")
    print("\nAll outputs include source_document_hash and page_number citations.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Epstein Files Forensic Analysis Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup database and run all analyses
  python src/run_analysis.py --setup --all
  
  # Run specific analysis
  python src/run_analysis.py --graph
  python src/run_analysis.py --financial
  python src/run_analysis.py --geo
  python src/run_analysis.py --timeline
  
  # Limit documents for testing
  python src/run_analysis.py --setup --all --limit 100
        """
    )
    
    parser.add_argument('--setup', action='store_true',
                       help='Initialize database and load documents')
    parser.add_argument('--all', action='store_true',
                       help='Run all analysis modules')
    parser.add_argument('--graph', action='store_true',
                       help='Run graph analyst only')
    parser.add_argument('--financial', action='store_true',
                       help='Run forensic accountant only')
    parser.add_argument('--geo', action='store_true',
                       help='Run cartographer only')
    parser.add_argument('--timeline', action='store_true',
                       help='Run timeline auditor only')
    
    parser.add_argument('--csv', type=str, default='data/raw/EPS_FILES_20K_NOV2025.csv',
                       help='Path to CSV file (default: data/raw/EPS_FILES_20K_NOV2025.csv)')
    parser.add_argument('--db', type=str, default='data/epstein_analysis.db',
                       help='Path to SQLite database (default: data/epstein_analysis.db)')
    parser.add_argument('--output', type=str, default='data/analysis_output',
                       help='Output directory (default: data/analysis_output)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of documents to process (for testing)')
    
    args = parser.parse_args()
    
    # If no action specified, show help
    if not (args.setup or args.all or args.graph or args.financial or args.geo or args.timeline):
        parser.print_help()
        sys.exit(0)
    
    # Setup database if requested
    if args.setup:
        setup_database(args.csv, args.db, limit=args.limit)
    
    # Run analyses
    if args.all:
        run_all_analyses(args.db, args.output, limit=args.limit)
    else:
        # Run individual modules
        Path(args.output).mkdir(parents=True, exist_ok=True)
        
        if args.graph:
            print("Running Graph Analyst...")
            analyst = GraphAnalyst(args.db)
            analyst.run_analysis(limit=args.limit, output_dir=args.output)
        
        if args.financial:
            print("Running Forensic Accountant...")
            accountant = ForensicAccountant(args.db)
            accountant.run_analysis(limit=args.limit, output_dir=args.output)
        
        if args.geo:
            print("Running Cartographer...")
            cartographer = Cartographer(args.db)
            cartographer.run_analysis(limit=args.limit, output_dir=args.output)
        
        if args.timeline:
            print("Running Timeline Auditor...")
            auditor = TimelineAuditor(args.db)
            auditor.run_analysis(limit=args.limit, output_dir=args.output)


if __name__ == "__main__":
    main()
