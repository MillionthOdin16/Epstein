#!/usr/bin/env python3
"""
Orchestrator for the automated investigation system.

This module coordinates the entire investigation pipeline:
1. Load the investigation database
2. Run ingestion to scan for new files
3. Run analytics to update graphs and stats
4. Apply decision logic for leads and suspicious documents
5. Generate daily briefing report
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
from database import InvestigationDB
from ingest import ingest_new_files
from analytics import analyze_documents, find_bridges, generate_entity_graph_data


def generate_daily_briefing(db: InvestigationDB, stats: Dict, 
                            new_files: int, analysis_stats: Dict) -> str:
    """Generate a daily briefing markdown report.
    
    Args:
        db: InvestigationDB instance
        stats: Database statistics
        new_files: Number of new files ingested
        analysis_stats: Analysis statistics
        
    Returns:
        Markdown content for the briefing
    """
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get new leads
    new_leads = db.get_leads_by_status('NEW')
    
    # Get suspicious documents from today
    suspicious_docs = db.get_suspicious_documents(since_date=today)
    
    # Get bridge entities
    bridges = find_bridges(db, min_connections=3)
    
    briefing = f"""# Daily Investigation Briefing
**Date:** {today}

## Executive Summary
- **New Files Processed:** {new_files}
- **Total Documents in Database:** {stats['total_documents']}
- **New Leads Generated:** {len(new_leads)}
- **Suspicious Documents Flagged:** {len(suspicious_docs)}
- **Total Entities Tracked:** {stats['total_entities']}
- **Entity Connections Mapped:** {stats['total_connections']}

## New Leads

"""
    
    if new_leads:
        briefing += f"**{len(new_leads)} new leads requiring investigation:**\n\n"
        for i, lead in enumerate(new_leads[:10], 1):  # Show top 10
            entity_info = f" ({lead['entity_name']} - {lead['entity_type']})" if lead['entity_name'] else ""
            briefing += f"{i}. **{lead['description']}**{entity_info}\n"
            briefing += f"   - Priority: {lead['priority']}\n"
            briefing += f"   - Created: {lead['created_at']}\n"
            if lead['notes']:
                briefing += f"   - Notes: {lead['notes']}\n"
            briefing += "\n"
        
        if len(new_leads) > 10:
            briefing += f"\n*...and {len(new_leads) - 10} more leads*\n"
    else:
        briefing += "No new leads generated today.\n"
    
    briefing += "\n## Suspicious Documents\n\n"
    
    if suspicious_docs:
        briefing += f"**{len(suspicious_docs)} documents flagged for review:**\n\n"
        for i, doc in enumerate(suspicious_docs[:10], 1):  # Show top 10
            briefing += f"{i}. **{doc['filename']}**\n"
            briefing += f"   - Reason: {doc['reason']}\n"
            briefing += f"   - Severity: {doc['severity']}\n"
            briefing += f"   - Category: {doc['category']}\n"
            briefing += f"   - Detected: {doc['detected_at']}\n\n"
        
        if len(suspicious_docs) > 10:
            briefing += f"\n*...and {len(suspicious_docs) - 10} more suspicious documents*\n"
    else:
        briefing += "No suspicious documents flagged today.\n"
    
    briefing += "\n## Key Entities (Bridges)\n\n"
    
    if bridges:
        briefing += f"**Top {min(len(bridges), 10)} entities with significant connections:**\n\n"
        for i, bridge in enumerate(bridges[:10], 1):
            briefing += f"{i}. **{bridge['name']}** ({bridge['entity_type']})\n"
            briefing += f"   - Unique Connections: {bridge['unique_connections']}\n"
            briefing += f"   - Total Occurrences: {bridge['occurrence_count']}\n"
            
            if bridge.get('connected_to'):
                connected_names = [f"{e['name']}" for e in bridge['connected_to'][:5]]
                briefing += f"   - Connected to: {', '.join(connected_names)}"
                if len(bridge['connected_to']) > 5:
                    briefing += f" and {len(bridge['connected_to']) - 5} more"
                briefing += "\n"
            briefing += "\n"
    else:
        briefing += "No significant entity bridges detected yet.\n"
    
    briefing += "\n## Analysis Statistics\n\n"
    briefing += f"- Documents Analyzed: {analysis_stats.get('analyzed', 0)}\n"
    briefing += f"- Entities Extracted: {analysis_stats.get('entities_found', 0)}\n"
    briefing += f"- Entity Connections Created: {analysis_stats.get('connections_created', 0)}\n"
    briefing += f"- Benford's Law Violations: {analysis_stats.get('benfords_violations', 0)}\n"
    
    briefing += "\n## Database Overview\n\n"
    briefing += f"- Total Documents: {stats['total_documents']}\n"
    briefing += f"- Total Entities: {stats['total_entities']}\n"
    briefing += f"- Total Leads: {stats['total_leads']} ({stats['new_leads']} new)\n"
    briefing += f"- Total Suspicious Documents: {stats['total_suspicious']}\n"
    briefing += f"- Entity Connections: {stats['total_connections']}\n"
    
    briefing += "\n---\n"
    briefing += f"*Report generated automatically by the Auto-Investigator on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    
    return briefing


def apply_decision_logic(db: InvestigationDB, bridges: List[Dict], 
                        suspicious_docs: List[Dict]) -> Dict[str, int]:
    """Apply decision logic to generate leads and flag suspicious documents.
    
    Args:
        db: InvestigationDB instance
        bridges: List of bridge entities
        suspicious_docs: List of suspicious documents
        
    Returns:
        Dictionary with counts of actions taken
    """
    actions = {
        'new_leads_created': 0,
        'documents_flagged': 0
    }
    
    # Get existing leads to avoid duplicates
    cursor = db.conn.cursor()
    cursor.execute("SELECT entity_id FROM leads WHERE entity_id IS NOT NULL")
    existing_lead_entities = {row[0] for row in cursor.fetchall()}
    
    # Generate leads for new bridge entities
    for bridge in bridges:
        entity_id = bridge['id']
        
        # Check if we already have a lead for this entity
        if entity_id in existing_lead_entities:
            continue
        
        # Create a new lead
        description = f"Investigate bridge entity: {bridge['name']}"
        notes = (f"Entity type: {bridge['entity_type']}, "
                f"Connections: {bridge['unique_connections']}, "
                f"Occurrences: {bridge['occurrence_count']}")
        
        priority = 'HIGH' if bridge['unique_connections'] >= 10 else 'MEDIUM'
        
        lead_id = db.add_lead(
            description=description,
            entity_id=entity_id,
            priority=priority,
            notes=notes
        )
        
        if lead_id:
            actions['new_leads_created'] += 1
            existing_lead_entities.add(entity_id)
    
    return actions


def run_investigation():
    """Main orchestration function."""
    print("=" * 60)
    print("AUTO-INVESTIGATOR - Daily Investigation Run")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Step 1: Load/Initialize Database
    print("Step 1: Loading investigation database...")
    db = InvestigationDB("investigation.db")
    print("✓ Database loaded\n")
    
    # Step 2: Run Ingestion
    print("Step 2: Scanning for new files...")
    new_files, total_files = ingest_new_files(db)
    print(f"✓ Ingestion complete: {new_files} new files, {total_files} total\n")
    
    # Step 3: Run Analytics
    print("Step 3: Running analytics...")
    analysis_stats = analyze_documents(db, process_entities=True, check_benfords=True)
    print(f"✓ Analytics complete\n")
    
    # Step 4: Find Bridges
    print("Step 4: Finding bridge entities...")
    bridges = find_bridges(db, min_connections=3)
    print(f"✓ Found {len(bridges)} bridge entities\n")
    
    # Step 5: Apply Decision Logic
    print("Step 5: Applying decision logic...")
    today = datetime.now().strftime('%Y-%m-%d')
    suspicious_docs = db.get_suspicious_documents(since_date=today)
    
    actions = apply_decision_logic(db, bridges, suspicious_docs)
    print(f"✓ Decision logic applied:")
    print(f"  - New leads created: {actions['new_leads_created']}")
    print(f"  - Suspicious documents: {len(suspicious_docs)}\n")
    
    # Step 6: Get Statistics
    print("Step 6: Gathering statistics...")
    stats = db.get_statistics()
    print(f"✓ Statistics gathered\n")
    
    # Step 7: Generate Briefing
    print("Step 7: Generating daily briefing...")
    briefing_content = generate_daily_briefing(db, stats, new_files, analysis_stats)
    
    briefing_path = Path("DAILY_BRIEFING.md")
    with open(briefing_path, 'w', encoding='utf-8') as f:
        f.write(briefing_content)
    
    print(f"✓ Briefing saved to {briefing_path}\n")
    
    # Close database
    db.close()
    
    print("=" * 60)
    print("Investigation run completed successfully!")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return {
        'new_files': new_files,
        'total_files': total_files,
        'new_leads': actions['new_leads_created'],
        'suspicious_docs': len(suspicious_docs),
        'bridges_found': len(bridges)
    }


if __name__ == '__main__':
    try:
        results = run_investigation()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR: Investigation run failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
