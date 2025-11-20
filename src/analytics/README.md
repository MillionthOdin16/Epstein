# Forensic Analysis Modules

This package provides four forensic analysis modules for investigating the Epstein Files dataset.

## Modules

### 1. Graph Analyst (Network Topology)
**File:** `graph_analyst.py`

Identifies "Bridge Nodes" - entities that connect disconnected groups.

**Features:**
- Builds co-occurrence graph using NetworkX
- Calculates betweenness centrality for all nodes
- Exports top 50 bridge nodes to `bridge_report.csv`
- Exports full graph to `network.gexf` (for Gephi visualization)

**Output:**
- `bridge_report.csv` - Top bridge nodes with centrality scores and source citations
- `network.gexf` - Full network graph for visualization in Gephi

### 2. Forensic Accountant (Pattern Recognition)
**File:** `forensic_accountant.py`

Identifies suspicious financial activity patterns.

**Features:**
- Extracts all currency amounts from documents
- **Benford's Law Test:** Analyzes leading digits of payments to detect fabricated numbers
- **Round Number Anomaly:** Flags high frequency of "clean" numbers (e.g., $10,000 vs $9,842)

**Output:**
- `financial_analysis_report.csv` - Complete financial analysis with Benford's Law results and round number anomalies

### 3. Cartographer (Geospatial Correlator)
**File:** `cartographer.py`

Links flight logs to meetings through geospatial analysis.

**Features:**
- Extracts airport codes (ICAO/IATA like "KTEB", "TJSJ") and city names
- Cross-references locations with dates from same documents
- Geocodes locations using geopy
- Generates interactive map with Folium

**Output:**
- `flight_map.html` - Interactive map showing entity locations on specific dates
- `location_report.csv` - All location mentions with source citations

### 4. Timeline Auditor (Gap Analysis)
**File:** `timeline_auditor.py`

Identifies what is *missing* - silence intervals in communications.

**Features:**
- Extracts and plots all dates from documents
- Identifies "Silence Intervals" - periods of >20 days with zero communications
- Criminal activity often happens in the silence

**Output:**
- `silence_report.md` - Markdown report listing suspicious date ranges
- `timeline_data.csv` - All extracted dates with source citations

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Download the dataset (if not already done):
```bash
python3 scripts/download_data.py
```

## Usage

### Quick Start - Run All Analyses

```bash
python src/run_analysis.py --setup --all
```

This will:
1. Initialize the SQLite database
2. Load all documents from CSV
3. Run all four analysis modules
4. Generate all reports in `data/analysis_output/`

### Run Individual Modules

```bash
# Graph analysis only
python src/run_analysis.py --graph

# Financial analysis only
python src/run_analysis.py --financial

# Geospatial analysis only
python src/run_analysis.py --geo

# Timeline analysis only
python src/run_analysis.py --timeline
```

### Testing with Limited Data

For testing or quick iterations, limit the number of documents:

```bash
python src/run_analysis.py --setup --all --limit 100
```

### Custom Paths

```bash
python src/run_analysis.py --setup --all \
  --csv data/raw/EPS_FILES_20K_NOV2025.csv \
  --db data/my_database.db \
  --output data/my_results
```

## Database Schema

The SQLite database (`data/epstein_analysis.db`) includes:

- **documents** - All document text with hash and metadata
- **entities** - Extracted entity names (for graph analysis)
- **entity_cooccurrences** - Co-occurrence edges (for graph)
- **financial_data** - Extracted currency amounts
- **locations** - Extracted locations and dates
- **dates_extracted** - All extracted dates

## Output Files

All analysis results are saved to `data/analysis_output/` (by default):

1. **bridge_report.csv** - Top 50 bridge nodes with source citations
2. **network.gexf** - Full network graph (open with Gephi)
3. **financial_analysis_report.csv** - Benford's Law and round number analysis
4. **flight_map.html** - Interactive geospatial map (open in browser)
5. **location_report.csv** - All location mentions with sources
6. **silence_report.md** - Timeline gaps analysis
7. **timeline_data.csv** - All extracted dates with sources

## Source Citations

**All outputs include proper source citations:**
- `source_document_hash` - Unique SHA256 hash of the document
- `page_number` - Page number within the document
- `filename` - Original filename

This ensures complete traceability and prevents hallucinations.

## Architecture

```
src/analytics/
├── __init__.py              # Package initialization
├── database.py              # Database operations and schema
├── graph_analyst.py         # Network topology analysis
├── forensic_accountant.py   # Financial pattern recognition
├── cartographer.py          # Geospatial correlation
└── timeline_auditor.py      # Gap analysis
```

## Dependencies

- **pandas** - Data manipulation
- **numpy** - Numerical operations
- **networkx** - Graph analysis
- **scikit-learn** - Machine learning utilities
- **scipy** - Statistical tests
- **folium** - Interactive maps
- **geopy** - Geocoding

## Examples

### Visualizing the Network Graph

1. Run graph analysis:
   ```bash
   python src/run_analysis.py --graph
   ```

2. Open `data/analysis_output/network.gexf` in [Gephi](https://gephi.org/)

3. Apply ForceAtlas2 layout to visualize the network

4. Color nodes by betweenness centrality to identify bridge nodes

### Investigating Financial Anomalies

1. Run financial analysis:
   ```bash
   python src/run_analysis.py --financial
   ```

2. Open `data/analysis_output/financial_analysis_report.csv`

3. Check the Benford's Law p-value:
   - p < 0.05 indicates suspicious deviation from natural distribution

4. Review round numbers section for patterns

### Exploring the Geospatial Map

1. Run geospatial analysis:
   ```bash
   python src/run_analysis.py --geo
   ```

2. Open `data/analysis_output/flight_map.html` in a web browser

3. Click on markers to see dates and source documents

### Analyzing Timeline Gaps

1. Run timeline analysis:
   ```bash
   python src/run_analysis.py --timeline
   ```

2. Open `data/analysis_output/silence_report.md`

3. Review suspicious intervals (>20 days with no communications)

4. Investigate the documents before and after each gap

## Notes

- Entity extraction uses simple regex patterns. For production use, consider spaCy NER.
- Geocoding has rate limits. The cartographer caches results to minimize API calls.
- Large datasets may take significant time to process. Use `--limit` for testing.
- All dates are parsed best-effort. Some formats may not be recognized.

## License

Please refer to the main repository for licensing information.
