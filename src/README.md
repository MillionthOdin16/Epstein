# Forensic Analysis Package

This package provides forensic analysis capabilities for the Epstein Files dataset, implementing three specialized detection engines for pattern discovery and anomaly detection.

## Overview

The forensic analysis system consists of:
- **Database Layer** (`database.py`) - SQLite-based storage for documents, entities, and findings
- **Analytics Engines** (`analytics.py`) - Three detection engines for forensic analysis

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

Run the example demonstration:

```bash
python3 example_forensic_analysis.py
```

This will create an `investigation.db` database, load sample data, run all three engines, and display the results.

## Database Schema

The `InvestigationDB` class manages a SQLite database with the following tables:

### Documents Table
Stores document metadata and content:
- `id` - Primary key
- `filename` - Unique document filename
- `content` - Full text content
- `category` - Document category (e.g., 'IMAGES', 'TEXT')
- `source` - Source identifier (e.g., '001', '002')
- `created_at` - Timestamp

### Entities Table
Stores extracted entities (people, organizations, locations):
- `id` - Primary key
- `name` - Unique entity name
- `entity_type` - Type ('person', 'organization', 'location', etc.)
- `first_seen` - Timestamp

### Document_Entities Table
Tracks entity co-occurrences in documents:
- `id` - Primary key
- `document_id` - Foreign key to documents
- `entity_id` - Foreign key to entities
- `mention_count` - Number of mentions in the document

### Findings Table
Stores anomalies and patterns detected by analytics engines:
- `id` - Primary key
- `finding_type` - Type of finding ('bridge_entity', 'benfords_violation', 'silence_interval')
- `severity` - Severity level ('low', 'medium', 'high', 'critical')
- `entity_id` - Related entity (optional)
- `document_id` - Related document (optional)
- `description` - Human-readable description
- `metadata` - Additional data as JSON string
- `detected_at` - Timestamp

## Analytics Engines

### 1. Connector Engine (Graph Theory)

**Purpose**: Identify "bridge entities" or "hidden handlers" - entities that connect different parts of the network but have few direct connections themselves.

**Method**:
- Builds a NetworkX graph where nodes are entities and edges represent co-occurrence in documents
- Calculates betweenness centrality for each entity
- Identifies entities with high centrality (>0.1) but low degree (<5)

**Usage**:
```python
from src.database import InvestigationDB
from src.analytics import ConnectorEngine

with InvestigationDB('investigation.db') as db:
    engine = ConnectorEngine(db)
    bridges = engine.find_bridges(min_centrality=0.1, max_degree=5)
    
    for bridge in bridges:
        print(f"{bridge['name']}: centrality={bridge['betweenness_centrality']:.3f}, degree={bridge['degree']}")
```

**Output**: List of entities with their metrics, automatically stored in the findings table.

### 2. Anomaly Engine (Benford's Law)

**Purpose**: Detect potentially fabricated financial data by analyzing the distribution of first digits in numerical amounts.

**Method**:
- Extracts currency amounts from documents using regex patterns
- Calculates the distribution of first digits (1-9)
- Compares against Benford's Law expected distribution using chi-square test
- Flags documents with significant deviations (chi-square > 15.507)

**Benford's Law**: In naturally occurring datasets, the first digit follows a logarithmic distribution:
- 1: 30.1%
- 2: 17.6%
- 3: 12.5%
- 4: 9.7%
- 5: 7.9%
- 6: 6.7%
- 7: 5.8%
- 8: 5.1%
- 9: 4.6%

**Usage**:
```python
from src.database import InvestigationDB
from src.analytics import AnomalyEngine

with InvestigationDB('investigation.db') as db:
    engine = AnomalyEngine(db)
    violations = engine.detect_benfords_law_violation(
        min_sample_size=30,
        chi_square_threshold=15.507
    )
    
    for violation in violations:
        print(f"{violation['filename']}: chi-square={violation['chi_square']:.2f}")
```

**Output**: List of documents with suspicious numerical patterns, stored in the findings table.

### 3. Timeline Engine (Chronology)

**Purpose**: Identify suspicious gaps in document activity that may indicate missing documents or periods of concealment.

**Method**:
- Extracts dates from documents using multiple pattern matching (Month DD YYYY, MM/DD/YYYY, etc.)
- Sorts all dates chronologically
- Identifies gaps larger than a threshold (default: 20 days)

**Usage**:
```python
from src.database import InvestigationDB
from src.analytics import TimelineEngine

with InvestigationDB('investigation.db') as db:
    engine = TimelineEngine(db)
    gaps = engine.find_silence_intervals(min_gap_days=20)
    
    for gap in gaps:
        print(f"Gap of {gap['gap_days']} days: {gap['start_date']} to {gap['end_date']}")
```

**Output**: List of silence intervals sorted by duration, stored in the findings table.

## Complete Analysis

Run all three engines together:

```python
from src.database import InvestigationDB
from src.analytics import ForensicAnalytics

with InvestigationDB('investigation.db') as db:
    analytics = ForensicAnalytics(db)
    results = analytics.run_all_analyses()
    
    print(f"Bridge entities: {len(results['bridge_entities'])}")
    print(f"Benford violations: {len(results['benfords_violations'])}")
    print(f"Silence intervals: {len(results['silence_intervals'])}")
```

## Database API Examples

### Adding Documents and Entities

```python
from src.database import InvestigationDB

with InvestigationDB('investigation.db') as db:
    # Add a document
    doc_id = db.add_document(
        filename='example.txt',
        content='Meeting with John Doe regarding transaction of $10,000 on January 15, 2005',
        category='TEXT',
        source='001'
    )
    
    # Add entities
    person_id = db.add_entity('John Doe', 'person')
    
    # Link document and entity
    db.add_document_entity(doc_id, person_id, mention_count=1)
```

### Querying Findings

```python
with InvestigationDB('investigation.db') as db:
    # Get all findings
    all_findings = db.get_findings()
    
    # Get findings by type
    bridge_findings = db.get_findings(finding_type='bridge_entity')
    
    # Get findings by severity
    high_severity = db.get_findings(severity='high')
```

### Analyzing Entity Relationships

```python
with InvestigationDB('investigation.db') as db:
    # Get all documents mentioning an entity
    entity_id = 1
    docs = db.get_entity_documents(entity_id)
    
    # Get all entities mentioned in a document
    document_id = 1
    entities = db.get_document_entities(document_id)
    
    # Get entity co-occurrences for graph analysis
    cooccurrences = db.get_entity_cooccurrences()
```

## Configuration

### Connector Engine Parameters

- `min_centrality` (default: 0.1) - Minimum betweenness centrality threshold
- `max_degree` (default: 5) - Maximum degree (connections) threshold

### Anomaly Engine Parameters

- `min_sample_size` (default: 30) - Minimum number of amounts required per document
- `chi_square_threshold` (default: 15.507) - Chi-square critical value (p<0.05, df=8)

### Timeline Engine Parameters

- `min_gap_days` (default: 20) - Minimum gap in days to be considered significant

## Requirements

- Python 3.6+
- NetworkX 3.0+
- Standard library: sqlite3, re, json, datetime, collections, math

## License

Please refer to the main repository for licensing information.

## Notes

- All findings are automatically stored in the database for later retrieval and analysis
- The database uses proper indexing for efficient queries
- Entity co-occurrence tracking enables graph-based analysis
- Multiple date formats are supported for timeline analysis
- Currency patterns support various formats: $1,234.56, USD 1234, etc.
