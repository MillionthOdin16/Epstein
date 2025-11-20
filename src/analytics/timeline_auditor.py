"""
Timeline Auditor Module - Gap Analysis

This module identifies "Silence Intervals" - periods where no communications exist.
Criminal activity often happens in the silence.
"""

import re
import csv
import sqlite3
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

from .database import get_db_connection


class TimelineAuditor:
    """
    Analyzes temporal patterns and identifies gaps in communications.
    """
    
    def __init__(self, db_path: str = "data/epstein_analysis.db"):
        """
        Initialize the Timeline Auditor.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self.dates = []  # List of (date, doc_id, doc_hash, page_number, filename, context)
        self.parsed_dates = []  # List of (datetime, doc_id, doc_hash, page_number, filename)
    
    def extract_dates(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract dates from text with context.
        
        Args:
            text: Document text
            
        Returns:
            List of (date_string, context) tuples
        """
        dates = []
        
        # Various date patterns
        patterns = [
            (r'\b(\d{1,2}/\d{1,2}/\d{4})\b', '%m/%d/%Y'),  # MM/DD/YYYY
            (r'\b(\d{1,2}-\d{1,2}-\d{4})\b', '%m-%d-%Y'),  # MM-DD-YYYY
            (r'\b(\d{4}-\d{2}-\d{2})\b', '%Y-%m-%d'),  # YYYY-MM-DD
            (r'\b([A-Z][a-z]+\s+\d{1,2},\s+\d{4})\b', '%B %d, %Y'),  # Month DD, YYYY
            (r'\b([A-Z][a-z]+\s+\d{1,2}\s+\d{4})\b', '%B %d %Y'),  # Month DD YYYY
        ]
        
        for pattern, date_format in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                date_str = match.group(1)
                # Get context (30 chars before and after)
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].replace('\n', ' ')
                dates.append((date_str, context, date_format))
        
        return dates
    
    def parse_date(self, date_str: str, date_format: str) -> Optional[datetime]:
        """
        Parse a date string to datetime object.
        
        Args:
            date_str: Date string
            date_format: Format string for parsing
            
        Returns:
            datetime object or None if parsing fails
        """
        try:
            return datetime.strptime(date_str, date_format)
        except ValueError:
            return None
    
    def extract_timeline_data(self, limit: int = None) -> None:
        """
        Extract date data from documents.
        
        Args:
            limit: Optional limit on documents to process
        """
        print("Extracting dates from documents...")
        
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # Get all documents
        if limit:
            cursor.execute("SELECT id, filename, source_document_hash, text, page_number FROM documents LIMIT ?", (limit,))
        else:
            cursor.execute("SELECT id, filename, source_document_hash, text, page_number FROM documents")
        
        doc_count = 0
        date_count = 0
        
        for row in cursor.fetchall():
            doc_id = row[0]
            filename = row[1]
            doc_hash = row[2]
            text = row[3]
            page_number = row[4]
            
            # Extract dates
            dates = self.extract_dates(text)
            
            for date_str, context, date_format in dates:
                self.dates.append((date_str, doc_id, doc_hash, page_number, filename, context))
                date_count += 1
                
                # Try to parse date
                parsed = self.parse_date(date_str, date_format)
                if parsed:
                    self.parsed_dates.append((parsed, doc_id, doc_hash, page_number, filename))
            
            doc_count += 1
            if doc_count % 100 == 0:
                print(f"Processed {doc_count} documents, found {date_count} dates")
        
        conn.close()
        
        print(f"\nExtracted {date_count} dates from {doc_count} documents")
        print(f"Successfully parsed {len(self.parsed_dates)} dates")
    
    def identify_silence_intervals(self, gap_days: int = 20) -> List[Tuple[datetime, datetime, int, List]]:
        """
        Identify periods with no communications.
        
        Args:
            gap_days: Minimum gap in days to be considered suspicious
            
        Returns:
            List of (start_date, end_date, gap_days, surrounding_docs) tuples
        """
        print(f"\nIdentifying silence intervals (>{gap_days} days)...")
        
        if not self.parsed_dates:
            print("Warning: No parsed dates to analyze")
            return []
        
        # Sort dates chronologically
        sorted_dates = sorted(self.parsed_dates, key=lambda x: x[0])
        
        # Find gaps
        gaps = []
        for i in range(len(sorted_dates) - 1):
            curr_date, curr_doc_id, curr_doc_hash, curr_page, curr_filename = sorted_dates[i]
            next_date, next_doc_id, next_doc_hash, next_page, next_filename = sorted_dates[i + 1]
            
            gap = (next_date - curr_date).days
            
            if gap > gap_days:
                # Store gap with surrounding document info
                gaps.append((
                    curr_date, 
                    next_date, 
                    gap,
                    [
                        ('before', curr_doc_id, curr_doc_hash, curr_page, curr_filename),
                        ('after', next_doc_id, next_doc_hash, next_page, next_filename)
                    ]
                ))
        
        print(f"Found {len(gaps)} silence intervals")
        
        return gaps
    
    def analyze_temporal_patterns(self) -> Dict:
        """
        Analyze temporal patterns in the data.
        
        Returns:
            Dictionary with temporal statistics
        """
        print("\nAnalyzing temporal patterns...")
        
        if not self.parsed_dates:
            print("Warning: No parsed dates to analyze")
            return {}
        
        # Extract just the dates
        dates_only = [date for date, _, _, _, _ in self.parsed_dates]
        
        # Calculate statistics
        min_date = min(dates_only)
        max_date = max(dates_only)
        total_span = (max_date - min_date).days
        
        # Count by year
        by_year = defaultdict(int)
        for date in dates_only:
            by_year[date.year] += 1
        
        # Count by month
        by_month = defaultdict(int)
        for date in dates_only:
            by_month[date.month] += 1
        
        result = {
            'min_date': min_date,
            'max_date': max_date,
            'total_span_days': total_span,
            'total_dates': len(dates_only),
            'by_year': dict(by_year),
            'by_month': dict(by_month)
        }
        
        print(f"  Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
        print(f"  Total span: {total_span} days")
        print(f"  Total dates found: {len(dates_only)}")
        
        return result
    
    def export_silence_report(self, gaps: List[Tuple], temporal_stats: Dict,
                             output_path: str = "silence_report.md") -> None:
        """
        Export silence intervals report in Markdown format.
        
        Args:
            gaps: List of silence intervals
            temporal_stats: Temporal statistics
            output_path: Path to output Markdown file
        """
        print(f"\nExporting silence report to: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Timeline Audit Report: Silence Intervals\n\n")
            
            # Overview
            f.write("## Overview\n\n")
            f.write(f"- **Total dates analyzed:** {temporal_stats.get('total_dates', 0)}\n")
            f.write(f"- **Date range:** {temporal_stats.get('min_date', 'N/A')} to {temporal_stats.get('max_date', 'N/A')}\n")
            f.write(f"- **Total span:** {temporal_stats.get('total_span_days', 0)} days\n")
            f.write(f"- **Silence intervals found:** {len(gaps)}\n\n")
            
            # Temporal distribution
            f.write("## Temporal Distribution\n\n")
            f.write("### By Year\n\n")
            by_year = temporal_stats.get('by_year', {})
            for year in sorted(by_year.keys()):
                f.write(f"- **{year}:** {by_year[year]} dates\n")
            f.write("\n")
            
            # Silence intervals
            f.write("## Suspicious Silence Intervals\n\n")
            f.write("Periods of >20 days with ZERO communications in the dataset.\n\n")
            
            if not gaps:
                f.write("*No significant silence intervals found.*\n\n")
            else:
                for i, (start_date, end_date, gap_days, docs) in enumerate(sorted(gaps, key=lambda x: x[2], reverse=True), 1):
                    f.write(f"### {i}. Gap of {gap_days} days\n\n")
                    f.write(f"**Period:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n\n")
                    
                    f.write("**Last communication before gap:**\n")
                    before_doc = [d for d in docs if d[0] == 'before'][0]
                    f.write(f"- Document Hash: `{before_doc[2]}`\n")
                    f.write(f"- Page Number: {before_doc[3]}\n")
                    f.write(f"- Filename: `{before_doc[4]}`\n\n")
                    
                    f.write("**First communication after gap:**\n")
                    after_doc = [d for d in docs if d[0] == 'after'][0]
                    f.write(f"- Document Hash: `{after_doc[2]}`\n")
                    f.write(f"- Page Number: {after_doc[3]}\n")
                    f.write(f"- Filename: `{after_doc[4]}`\n\n")
            
            # Conclusions
            f.write("## Analysis Notes\n\n")
            f.write("Silence intervals may indicate:\n")
            f.write("- Missing documents or communications\n")
            f.write("- Periods of heightened operational security\n")
            f.write("- Document destruction or withholding\n")
            f.write("- Natural gaps in business/personal correspondence\n\n")
            f.write("**Note:** All dates cited above include source document hash and page number for verification.\n")
        
        print(f"Exported silence report with {len(gaps)} intervals")
    
    def export_timeline_csv(self, output_path: str = "timeline_data.csv") -> None:
        """
        Export all extracted dates to CSV.
        
        Args:
            output_path: Path to output CSV file
        """
        print(f"\nExporting timeline data to: {output_path}")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Source Document Hash', 'Page Number', 'Filename', 'Context'])
            
            for date_str, doc_id, doc_hash, page_number, filename, context in self.dates:
                writer.writerow([date_str, doc_hash, page_number, filename, context[:100]])
        
        print(f"Exported {len(self.dates)} date mentions")
    
    def run_analysis(self, limit: int = None, output_dir: str = ".", gap_days: int = 20) -> None:
        """
        Run complete timeline analysis.
        
        Args:
            limit: Optional limit on documents to process
            output_dir: Directory for output files
            gap_days: Minimum gap days for silence intervals
        """
        print("="*60)
        print("TIMELINE AUDITOR - Gap Analysis")
        print("="*60)
        
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Extract timeline data
        self.extract_timeline_data(limit=limit)
        
        if not self.dates:
            print("\nERROR: No dates found. Cannot perform analysis.")
            return
        
        # Analyze patterns
        temporal_stats = self.analyze_temporal_patterns()
        
        # Identify silence intervals
        gaps = self.identify_silence_intervals(gap_days=gap_days)
        
        # Export reports
        silence_report_path = Path(output_dir) / "silence_report.md"
        timeline_csv_path = Path(output_dir) / "timeline_data.csv"
        
        self.export_silence_report(gaps, temporal_stats, str(silence_report_path))
        self.export_timeline_csv(str(timeline_csv_path))
        
        print("\n" + "="*60)
        print("Timeline analysis complete!")
        print("="*60)


def main():
    """Main function for running timeline analysis."""
    auditor = TimelineAuditor()
    auditor.run_analysis(output_dir="data/analysis_output")


if __name__ == "__main__":
    main()
