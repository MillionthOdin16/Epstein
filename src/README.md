# Automated Investigation System

This directory contains the automated investigation orchestration system that runs daily to analyze documents, detect anomalies, and identify entities of interest.

## Overview

The system performs the following tasks automatically:

1. **File Ingestion** - Scans for new files in data directories
2. **Entity Extraction** - Identifies people, organizations from documents
3. **Network Analysis** - Builds graphs of entity relationships
4. **Bridge Detection** - Finds key entities connecting different clusters
5. **Anomaly Detection** - Uses Benford's Law to flag suspicious numerical data
6. **Lead Management** - Automatically adds high-priority entities as leads
7. **Report Generation** - Creates daily briefing summaries

## Components

### `database.py`
Manages the SQLite database (`investigation.db`) with the following schema:

- **files**: Tracks all ingested files with metadata
- **leads**: Entities of interest to investigate
- **documents**: Document analysis results and flags
- **entities**: Extracted entity names from documents
- **connections**: Relationships between entities

### `ingest.py`
Handles file scanning and ingestion:

- Scans `data/processed/files/` and `data/raw/` for new files
- Calculates checksums to prevent duplicate ingestion
- Extracts text content from files
- Identifies entity names using pattern matching
- Extracts numerical values for Benford's Law analysis

### `analytics.py`
Performs advanced analytics:

- **Network Analysis**: Builds entity relationship graphs
- **Bridge Detection**: Identifies entities connecting disparate clusters (high betweenness centrality)
- **Benford's Law Analysis**: Detects anomalous numerical patterns using chi-squared test

**Benford's Law Details:**
- Requires minimum 30 numbers for statistical significance
- Uses chi-squared threshold of 15.507 (p=0.05, df=8)
- Flags documents where first digit distribution deviates from expected

### `orchestrator.py`
Main entry point that coordinates the entire process:

1. Connects to database
2. Runs file ingestion
3. Performs network analytics
4. Applies decision logic:
   - Adds bridge entities as NEW leads
   - Marks documents as SUSPICIOUS based on Benford's Law
5. Generates `DAILY_BRIEFING.md`

## Usage

### Manual Execution
```bash
python src/orchestrator.py
```

### Automated Execution
The system runs automatically via GitHub Actions at 3 AM UTC daily.

See `.github/workflows/daily_investigation.yml` for the workflow configuration.

## Output

### `investigation.db`
SQLite database containing all investigation data. Can be queried directly:

```bash
sqlite3 investigation.db
```

Example queries:
```sql
-- View all leads
SELECT * FROM leads ORDER BY discovered_at DESC;

-- View suspicious documents
SELECT f.filename, d.benford_score 
FROM documents d 
JOIN files f ON d.file_id = f.id 
WHERE d.status = 'SUSPICIOUS';

-- View entity network
SELECT entity1, entity2, strength 
FROM connections 
ORDER BY strength DESC;
```

### `DAILY_BRIEFING.md`
Markdown report with:
- Executive summary of all statistics
- New leads discovered
- Suspicious documents flagged
- Complete lead list with status

## Algorithm Details

### Bridge Detection
Entities are considered bridges if they:
1. Have 3+ connections to other entities
2. Connect entities that aren't well-connected to each other
3. Have interconnectedness ratio < 0.5 among their neighbors

This identifies entities that act as key connectors in the network.

### Entity Extraction
Uses regex patterns to identify:
- Titles + names (Mr. John Smith, Dr. Jane Doe, etc.)
- Capitalized multi-word names (2-4 words)
- Filters common false positives

### Benford's Law Violation Detection
1. Extract all numbers from document (minimum 10, must be multi-digit)
2. Count first digit frequencies
3. Compare to expected Benford distribution: P(d) = log₁₀(1 + 1/d)
4. Calculate chi-squared statistic
5. Flag if χ² > 15.507 (p < 0.05)

High chi-squared values indicate the numbers may be fabricated rather than naturally occurring.

## Configuration

All configuration is in the source files:

- **Data directories**: `ingest.py` line 26-29
- **Benford threshold**: `analytics.py` line 169
- **Minimum numbers**: `orchestrator.py` line 206
- **Bridge threshold**: `analytics.py` line 62

## Dependencies

The system uses only Python standard library:
- `sqlite3` - Database
- `pathlib` - File handling
- `hashlib` - Checksums
- `re` - Pattern matching
- `datetime` - Timestamps
- `collections` - Data structures
- `math` - Statistical calculations

No external packages required.

## Troubleshooting

### No files ingested
- Check that data directories exist: `data/processed/files/` or `data/raw/`
- Verify files are `.txt` or `.csv` format
- Ensure files haven't been ingested before (check database)

### No bridge entities found
- Requires entities appearing in multiple documents
- Need distinct clusters of entities
- System needs enough data to build meaningful network

### No suspicious documents
- Requires documents with 30+ numerical values
- Numbers must deviate significantly from Benford's distribution
- Natural data often follows Benford's Law

### Database locked
- Close any SQLite browser connections
- Ensure only one orchestrator instance running
- Check file permissions on `investigation.db`

## Future Enhancements

Potential improvements:
- NLP-based entity recognition (spaCy, NLTK)
- Time-series analysis of entity appearances
- Document similarity clustering
- Automated email/Slack notifications
- Web dashboard for visualization
- Advanced graph metrics (PageRank, community detection)
- Machine learning for entity classification
