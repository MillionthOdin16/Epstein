# Using the Automated Investigation System

## Quick Start

The system is fully automated and requires no manual intervention after setup. It will run every night at 3 AM UTC via GitHub Actions.

## Manual Testing

To test the system manually:

```bash
# Run the orchestrator
python src/orchestrator.py

# Check the generated briefing
cat DAILY_BRIEFING.md

# Query the database
sqlite3 investigation.db "SELECT * FROM leads;"
```

## GitHub Actions Workflow

The workflow is already configured in `.github/workflows/daily_investigation.yml`.

### Manual Trigger

You can manually trigger the workflow from GitHub:

1. Go to **Actions** tab
2. Select **Daily Investigation** workflow
3. Click **Run workflow**
4. Select branch and click **Run workflow**

### Viewing Results

After each run:
1. Check the **Actions** tab for workflow logs
2. View the updated `DAILY_BRIEFING.md` in the repository
3. The `investigation.db` will be updated with new data

## Understanding the Outputs

### DAILY_BRIEFING.md

Generated after each run with:
- **Executive Summary**: High-level statistics
- **New Leads**: Bridge entities discovered
- **Suspicious Documents**: Files flagged by Benford's Law
- **All Active Leads**: Complete list with status

### investigation.db

SQLite database containing:
- `files`: All ingested files
- `leads`: Entities to investigate
- `documents`: Analysis results
- `entities`: Extracted names
- `connections`: Entity relationships

## Adding Data

To have the system analyze new files:

1. Add files to `data/processed/files/` or `data/raw/`
2. Files should be `.txt` or `.csv` format
3. The system will automatically detect and ingest them on next run

## Checking System Health

```bash
# View last run date
head -n 3 DAILY_BRIEFING.md

# Count total files
sqlite3 investigation.db "SELECT COUNT(*) FROM files;"

# List all leads
sqlite3 investigation.db "SELECT entity_name, status FROM leads;"

# Check suspicious documents
sqlite3 investigation.db "SELECT f.filename, d.benford_score FROM documents d JOIN files f ON d.file_id = f.id WHERE d.status = 'SUSPICIOUS';"
```

## Troubleshooting

### Workflow fails
- Check Actions logs for error messages
- Verify Python syntax with `python -m py_compile src/*.py`
- Ensure database isn't corrupted: `sqlite3 investigation.db "PRAGMA integrity_check;"`

### No new files detected
- Verify files exist in data directories
- Check they haven't been ingested: `sqlite3 investigation.db "SELECT filepath FROM files;"`
- Ensure proper file extensions (.txt, .csv)

### No leads generated
- System needs documents with interconnected entities
- Bridge detection requires entity clusters
- Check entity extraction: `sqlite3 investigation.db "SELECT DISTINCT entity_name FROM entities;"`

## Advanced Usage

### Custom Queries

```sql
-- Find most connected entities
SELECT entity_name, COUNT(*) as connections 
FROM (
  SELECT entity1 as entity_name FROM connections
  UNION ALL
  SELECT entity2 FROM connections
) GROUP BY entity_name ORDER BY connections DESC LIMIT 10;

-- Files with most entities
SELECT f.filename, COUNT(e.id) as entity_count
FROM files f
JOIN entities e ON f.id = e.file_id
GROUP BY f.id
ORDER BY entity_count DESC
LIMIT 10;

-- Recent suspicious documents
SELECT f.filename, d.benford_score, d.analyzed_at
FROM documents d
JOIN files f ON d.file_id = f.id
WHERE d.status = 'SUSPICIOUS'
ORDER BY d.analyzed_at DESC;
```

### Manual Lead Management

```sql
-- Add a lead manually
INSERT INTO leads (entity_name, status, discovered_at, last_updated)
VALUES ('John Doe', 'INVESTIGATING', datetime('now'), datetime('now'));

-- Update lead status
UPDATE leads SET status = 'CLOSED', last_updated = datetime('now')
WHERE entity_name = 'John Doe';
```

## Monitoring

The system will automatically:
- ✅ Scan for new files daily
- ✅ Extract entities and relationships
- ✅ Identify bridge entities
- ✅ Flag suspicious documents
- ✅ Update the database
- ✅ Generate daily briefing
- ✅ Commit changes to repository

No manual intervention required! 🤖
