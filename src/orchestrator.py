#!/usr/bin/env python3
"""
Orchestrator for the automated investigation system.

This is the main entry point that coordinates:
1. File ingestion (scanning for new files)
2. Analytics (graph analysis and Benford's Law detection)
3. Decision logic (adding leads and marking suspicious documents)
4. Report generation (DAILY_BRIEFING.md)
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import InvestigationDB
from ingest import FileIngestor
from analytics import NetworkAnalyzer, BenfordsLawAnalyzer


class InvestigationOrchestrator:
    """Orchestrates the automated investigation process."""
    
    def __init__(self, db_path: str = "investigation.db"):
        """
        Initialize the orchestrator.
        
        Args:
            db_path: Path to the investigation database
        """
        self.db_path = db_path
        self.db = InvestigationDB(db_path)
        self.report_lines = []
        
    def log(self, message: str):
        """
        Log a message to both console and report.
        
        Args:
            message: Message to log
        """
        print(message)
        self.report_lines.append(message)
        
    def run(self):
        """Execute the full investigation loop."""
        self.log("=" * 60)
        self.log("🔎 AUTOMATED INVESTIGATION ORCHESTRATOR")
        self.log(f"📅 Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("=" * 60)
        self.log("")
        
        # Connect to database
        self.db.connect()
        
        try:
            # Step 1: Ingest new files
            self.log("## Step 1: File Ingestion")
            self.log("-" * 60)
            new_files, entities, all_numbers = self.ingest_files()
            self.log("")
            
            # Step 2: Run analytics
            self.log("## Step 2: Analytics")
            self.log("-" * 60)
            bridges = self.run_analytics()
            self.log("")
            
            # Step 3: Decision logic
            self.log("## Step 3: Decision Logic")
            self.log("-" * 60)
            new_leads = self.apply_decision_logic(bridges, entities)
            suspicious_docs = self.detect_suspicious_documents(all_numbers)
            self.log("")
            
            # Step 4: Generate report
            self.log("## Step 4: Report Generation")
            self.log("-" * 60)
            self.generate_daily_briefing(new_files, new_leads, suspicious_docs)
            self.log("")
            
            # Final statistics
            stats = self.db.get_statistics()
            self.log("## Final Statistics")
            self.log("-" * 60)
            self.log(f"📊 Total files in database: {stats['total_files']}")
            self.log(f"📊 Total leads: {stats['total_leads']} ({stats['new_leads']} new)")
            self.log(f"📊 Suspicious documents: {stats['suspicious_docs']}")
            self.log(f"📊 Total entities: {stats['total_entities']}")
            self.log(f"📊 Total connections: {stats['total_connections']}")
            
        finally:
            self.db.close()
            
        self.log("")
        self.log("=" * 60)
        self.log("✅ Investigation complete!")
        self.log("=" * 60)
        
    def ingest_files(self) -> tuple:
        """
        Run file ingestion to scan for new files.
        
        Returns:
            Tuple of (files_ingested, entities, all_numbers)
        """
        ingestor = FileIngestor(self.db)
        files_ingested, entities, all_numbers = ingestor.ingest_new_files()
        
        if files_ingested > 0:
            self.log(f"✓ Ingested {files_ingested} new files")
            self.log(f"✓ Extracted {len(entities)} unique entities")
        else:
            self.log("✓ No new files to ingest")
            
        return files_ingested, entities, all_numbers
        
    def run_analytics(self) -> List[str]:
        """
        Run analytics to find bridge entities.
        
        Returns:
            List of bridge entity names
        """
        analyzer = NetworkAnalyzer(self.db)
        bridges = analyzer.find_bridges()
        
        self.log(f"✓ Network analysis complete")
        self.log(f"✓ Found {len(bridges)} bridge entities")
        
        if bridges:
            self.log("   Top bridge entities:")
            for bridge in bridges[:5]:
                self.log(f"      - {bridge}")
        
        return bridges
        
    def apply_decision_logic(self, bridges: List[str], entities: set) -> List[str]:
        """
        Apply decision logic to add new leads.
        
        Bridge entities not already in the leads table are added as new leads.
        
        Args:
            bridges: List of bridge entity names
            entities: Set of all extracted entities
            
        Returns:
            List of newly added lead names
        """
        existing_leads = {lead['entity_name'] for lead in self.db.get_all_leads()}
        new_leads = []
        
        for bridge in bridges:
            if bridge not in existing_leads:
                self.db.add_lead(
                    entity_name=bridge,
                    status='NEW',
                    notes=f'Identified as bridge entity on {datetime.now().strftime("%Y-%m-%d")}'
                )
                new_leads.append(bridge)
        
        if new_leads:
            self.log(f"✓ Added {len(new_leads)} new leads:")
            for lead in new_leads[:10]:
                self.log(f"      - {lead}")
        else:
            self.log("✓ No new leads to add")
            
        return new_leads
        
    def detect_suspicious_documents(self, all_numbers: List[List[int]]) -> List[Dict]:
        """
        Detect suspicious documents using Benford's Law.
        
        Args:
            all_numbers: List of number lists (one per document)
            
        Returns:
            List of suspicious document records
        """
        analyzer = BenfordsLawAnalyzer()
        suspicious_count = 0
        
        # Get all files that were just ingested
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT f.id, f.filepath, f.filename 
            FROM files f
            LEFT JOIN documents d ON f.id = d.file_id
            WHERE d.id IS NULL
            ORDER BY f.id DESC
        ''')
        
        unanalyzed_files = cursor.fetchall()
        
        # Match files with their number lists (simplified approach)
        for i, file_row in enumerate(unanalyzed_files):
            if i < len(all_numbers):
                numbers = all_numbers[i]
                
                if len(numbers) >= 30:  # Only analyze if enough numbers
                    is_violation, chi_squared, distribution = analyzer.detect_benfords_law_violation(numbers)
                    
                    if is_violation:
                        self.db.mark_document_suspicious(
                            file_id=file_row['id'],
                            benford_score=chi_squared
                        )
                        suspicious_count += 1
        
        if suspicious_count > 0:
            self.log(f"⚠️  Marked {suspicious_count} documents as SUSPICIOUS")
        else:
            self.log("✓ No documents flagged as suspicious")
        
        return self.db.get_suspicious_documents()
        
    def generate_daily_briefing(self, files_ingested: int, new_leads: List[str], 
                               suspicious_docs: List[Dict]):
        """
        Generate the DAILY_BRIEFING.md file.
        
        Args:
            files_ingested: Number of files ingested
            new_leads: List of newly added lead names
            suspicious_docs: List of suspicious document records
        """
        briefing_path = Path("DAILY_BRIEFING.md")
        
        with open(briefing_path, 'w') as f:
            f.write("# Daily Investigation Briefing\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            # Summary
            f.write("## Executive Summary\n\n")
            stats = self.db.get_statistics()
            f.write(f"- **Files Processed:** {stats['total_files']} total ({files_ingested} new)\n")
            f.write(f"- **Active Leads:** {stats['total_leads']} total ({len(new_leads)} new)\n")
            f.write(f"- **Suspicious Documents:** {stats['suspicious_docs']}\n")
            f.write(f"- **Entities Tracked:** {stats['total_entities']}\n")
            f.write(f"- **Connections Mapped:** {stats['total_connections']}\n\n")
            
            # New Leads
            f.write("## 🔍 New Leads\n\n")
            if new_leads:
                f.write(f"Identified {len(new_leads)} new entities of interest:\n\n")
                for i, lead in enumerate(new_leads, 1):
                    f.write(f"{i}. **{lead}**\n")
                    f.write(f"   - Status: NEW\n")
                    f.write(f"   - Type: Bridge Entity (connects multiple clusters)\n")
                    f.write(f"   - Priority: High\n\n")
            else:
                f.write("No new leads identified in this cycle.\n\n")
            
            # Suspicious Documents
            f.write("## ⚠️ Suspicious Documents\n\n")
            if suspicious_docs:
                f.write(f"Flagged {len(suspicious_docs)} documents for review:\n\n")
                for i, doc in enumerate(suspicious_docs[:20], 1):  # Limit to 20
                    f.write(f"{i}. **{doc['filename']}**\n")
                    f.write(f"   - Path: `{doc['filepath']}`\n")
                    f.write(f"   - Benford Score: {doc['benford_score']:.2f}\n")
                    f.write(f"   - Analyzed: {doc['analyzed_at']}\n")
                    f.write(f"   - Reason: Numerical data shows anomalies (Benford's Law violation)\n\n")
                
                if len(suspicious_docs) > 20:
                    f.write(f"\n*...and {len(suspicious_docs) - 20} more*\n\n")
            else:
                f.write("No suspicious documents flagged in this cycle.\n\n")
            
            # All Active Leads
            f.write("## 📋 All Active Leads\n\n")
            all_leads = self.db.get_all_leads()
            if all_leads:
                f.write(f"Total active leads: {len(all_leads)}\n\n")
                
                # Group by status
                by_status = {}
                for lead in all_leads:
                    status = lead['status']
                    if status not in by_status:
                        by_status[status] = []
                    by_status[status].append(lead)
                
                for status, leads in by_status.items():
                    f.write(f"### {status} ({len(leads)})\n\n")
                    for lead in leads[:10]:  # Show top 10 per status
                        f.write(f"- **{lead['entity_name']}** (discovered: {lead['discovered_at'][:10]})\n")
                    
                    if len(leads) > 10:
                        f.write(f"\n*...and {len(leads) - 10} more*\n")
                    f.write("\n")
            else:
                f.write("No active leads yet.\n\n")
            
            # Footer
            f.write("---\n\n")
            f.write("*This briefing was automatically generated by the Auto-Investigator system.*\n")
            f.write("*Next scheduled run: Tomorrow at 03:00 UTC*\n")
        
        self.log(f"✓ Daily briefing generated: {briefing_path}")


def main():
    """Main entry point for the orchestrator."""
    orchestrator = InvestigationOrchestrator()
    orchestrator.run()


if __name__ == '__main__':
    main()
