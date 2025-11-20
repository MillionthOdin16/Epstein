# Epstein Files Dataset

This repository contains the Epstein Files dataset from multiple sources, organized for easy access and analysis.

## 🔍 Forensic Analysis Suite

**NEW:** This repository now includes a complete forensic analysis suite with four specialized modules:

### Quick Start - Run Forensic Analysis

```bash
# Install dependencies
pip install -r requirements.txt

# Setup database and run all analyses
python src/run_analysis.py --setup --all

# Results will be in data/analysis_output/
```

### Analysis Modules

1. **Graph Analyst** - Network topology and bridge node detection
2. **Forensic Accountant** - Benford's Law & round number anomaly detection
3. **Cartographer** - Geospatial correlation of locations and dates
4. **Timeline Auditor** - Gap analysis to find "silence intervals"

See [`src/analytics/README.md`](src/analytics/README.md) for detailed documentation.

## Dataset Overview

### Text Data (Hugging Face)
- **Total Files**: 25,800 text documents
- **Source**: [tensonaut/EPSTEIN_FILES_20K](https://huggingface.co/datasets/tensonaut/EPSTEIN_FILES_20K)
- **File Format**: Plain text (.txt) - OCR'd text extracted from scanned documents
- **Total Size**: ~101 MB (raw CSV)

### Image Data (Google Drive)
- **Source**: [Google Drive Archive](https://drive.google.com/drive/folders/1hTNH5woIRio578onLGElkTWofUSWRoH_?usp=sharing)
- **File Format**: JPEG images - Original scanned documents
- **Content**: High-resolution scans (300 DPI) of source documents
- **Note**: Due to Google Drive API rate limits, only partial downloads may be possible in a single session

## Quick Start

### 1. Download the text data from Hugging Face
```bash
python3 scripts/download_data.py
```

### 2. Organize the text files into directories
```bash
python3 scripts/organize_data.py
```

### 3. (Optional) Download original images from Google Drive
```bash
pip install gdown
python3 scripts/download_images.py
```

### 4. Analyze the dataset
```bash
python3 scripts/analyze_data.py
```

## Directory Structure

```
data/
├── raw/
│   └── EPS_FILES_20K_NOV2025.csv          # Original CSV file from Hugging Face
├── processed/
│   └── files/                              # Organized text files (OCR'd)
│       ├── IMAGES/                         # 22,903 files
│       │   ├── 001/                        # Source 001 (4,000 files)
│       │   ├── 002/                        # Source 002 (2,885 files)
│       │   ├── 003/                        # Source 003 (2,000 files)
│       │   ├── 004/                        # Source 004 (1,987 files)
│       │   ├── 005/                        # Source 005 (2,000 files)
│       │   ├── 006/                        # Source 006 (1,992 files)
│       │   ├── 007/                        # Source 007 (1,934 files)
│       │   ├── 008/                        # Source 008 (1,973 files)
│       │   ├── 009/                        # Source 009 (1,998 files)
│       │   ├── 010/                        # Source 010 (1,946 files)
│       │   ├── 011/                        # Source 011 (1,961 files)
│       │   └── 012/                        # Source 012 (1,127 files)
│       └── TEXT/                           # 2,897 files
│           ├── 001/                        # Source 001 (2,000 files)
│           └── 002/                        # Source 002 (897 files)
└── images/
    ├── gdrive_images/                      # Original JPG scans from Google Drive
    │   ├── 001/                            # Scanned images
    │   ├── 002/
    │   ├── 003/
    │   ├── 004/
    │   └── 005/
    └── gdrive_data/                        # Additional data files from Google Drive
        └── HOUSE_OVERSIGHT_009.dat/.opt    # Data and options files
```

## File Naming Convention

Files follow the pattern: `CATEGORY-SOURCE-IDENTIFIER.txt`

- **CATEGORY**: Type of document (IMAGES, TEXT)
- **SOURCE**: Source identifier (001-012)
- **IDENTIFIER**: Unique document identifier (e.g., HOUSE_OVERSIGHT_020367)

Example: `IMAGES-005-HOUSE_OVERSIGHT_020367.txt`

## Usage

### Accessing the Text Data (OCR'd)

The original CSV file is available at:
```
data/raw/EPS_FILES_20K_NOV2025.csv
```

This CSV contains two columns:
- `filename`: Original filename
- `text`: Full text content of the document (OCR'd from images)

### Accessing Organized Text Files

Individual text files are organized in:
```
data/processed/files/
```

You can navigate by category (IMAGES or TEXT) and source (001-012) to find specific documents.

### Accessing Original Image Scans

Original high-resolution scanned images (when available) are in:
```
data/images/gdrive_images/
```

These are the source JPG files from which the text was extracted. The images are organized by source number (001-012).

### Relationship Between Text and Images

The text files in `data/processed/files/` contain OCR'd text extracted from the corresponding JPG images in `data/images/gdrive_images/`.

For example:
- **Image**: `data/images/gdrive_images/001/HOUSE_OVERSIGHT_010477.jpg`
- **Text**: `data/processed/files/IMAGES/001/IMAGES-001-HOUSE_OVERSIGHT_010477.txt`

### Processing the Data

To re-process or customize the organization, use the provided script:

```bash
python3 scripts/organize_data.py
```

This script:
1. Reads the CSV file from `data/raw/`
2. Extracts each document into individual text files
3. Organizes files by category and source
4. Outputs to `data/processed/files/`

## Statistics

### By Category
- **IMAGES**: 22,903 files (88.8%)
- **TEXT**: 2,897 files (11.2%)

### By Source
| Source | File Count |
|--------|-----------|
| 001    | 4,000     |
| 002    | 2,885     |
| 003    | 2,000     |
| 004    | 1,987     |
| 005    | 2,000     |
| 006    | 1,992     |
| 007    | 1,934     |
| 008    | 1,973     |
| 009    | 1,998     |
| 010    | 1,946     |
| 011    | 1,961     |
| 012    | 1,124     |

## Data Sources

### 1. Hugging Face Dataset (Primary Source)
This dataset was obtained from the Hugging Face dataset repository:
- **Repository**: [tensonaut/EPSTEIN_FILES_20K](https://huggingface.co/datasets/tensonaut/EPSTEIN_FILES_20K)
- **File**: EPS_FILES_20K_NOV2025.csv
- **Content**: OCR'd text extracted from 25,800 scanned documents
- **Coverage**: Complete dataset with all text content

### 2. Google Drive Archive (Supplementary Source)
This archive provides the original scanned images:
- **Archive**: [Google Drive Folder](https://drive.google.com/drive/folders/1hTNH5woIRio578onLGElkTWofUSWRoH_?usp=sharing)
- **Content**: High-resolution JPG scans of original documents (300 DPI)
- **Coverage**: Partial - contains source images for a subset of the documents
- **Note**: The Hugging Face dataset text was extracted from these images via OCR

### Data Relationship
The CSV file from Hugging Face contains the OCR'd text from the Google Drive images. All Google Drive images have corresponding text entries in the Hugging Face dataset, but the Hugging Face dataset contains many more documents (25,800 total) than available in the partial Google Drive archive.

## Scripts

### download_data.py

Located in `scripts/download_data.py`, this script downloads the CSV file from Hugging Face.

**Usage:**
```bash
python3 scripts/download_data.py
```

**Features:**
- Downloads EPS_FILES_20K_NOV2025.csv from Hugging Face
- Shows progress during download
- Verifies file size after download

### organize_data.py

Located in `scripts/organize_data.py`, this script processes the raw CSV file and organizes it into a structured directory hierarchy.

**Usage:**
```bash
python3 scripts/organize_data.py
```

**Features:**
- Parses CSV with large text fields
- Creates organized directory structure
- Tracks statistics during processing
- Progress reporting every 1,000 files

### download_images.py

Located in `scripts/download_images.py`, this script downloads the original scanned images from Google Drive.

**Usage:**
```bash
pip install gdown  # Install dependency first
python3 scripts/download_images.py
```

**Features:**
- Downloads JPG images from Google Drive
- Handles rate limiting gracefully
- Can be run multiple times to resume downloads
- Organizes files by source

**Note:** Due to Google Drive API rate limits, downloads may be interrupted. Simply run the script again to continue.

### analyze_data.py

Located in `scripts/analyze_data.py`, this script analyzes and compares data from both sources.

**Usage:**
```bash
python3 scripts/analyze_data.py
```

**Features:**
- Shows statistics for text files (Hugging Face)
- Shows statistics for image files (Google Drive)
- Analyzes correspondence between text and images
- Reports files with both text and images

## Forensic Analysis Tools

### run_analysis.py

Located in `src/run_analysis.py`, this is the main entry point for forensic analysis.

**Quick Start:**
```bash
# Install dependencies first
pip install -r requirements.txt

# Setup database and run all analyses
python src/run_analysis.py --setup --all
```

**Individual Modules:**
```bash
# Run specific analyses
python src/run_analysis.py --graph        # Network topology
python src/run_analysis.py --financial    # Financial patterns
python src/run_analysis.py --geo          # Geospatial analysis
python src/run_analysis.py --timeline     # Timeline gaps
```

**Testing with Limited Data:**
```bash
# Process only 100 documents (for testing)
python src/run_analysis.py --setup --all --limit 100
```

### Output Files

All analyses generate reports in `data/analysis_output/`:

- `bridge_report.csv` - Top 50 bridge nodes (network connectors)
- `network.gexf` - Full network graph (open with Gephi)
- `financial_analysis_report.csv` - Benford's Law & round number analysis
- `flight_map.html` - Interactive map of locations and dates
- `location_report.csv` - All location mentions
- `silence_report.md` - Timeline gap analysis
- `timeline_data.csv` - All extracted dates

**All outputs include source_document_hash and page_number for verification.**

### Module Details

#### 1. Graph Analyst (Network Topology)
- Extracts entity names from documents
- Builds co-occurrence graph using NetworkX
- Calculates betweenness centrality to find "bridge nodes"
- Bridge nodes are people who connect otherwise disconnected groups

#### 2. Forensic Accountant (Financial Pattern Recognition)
- Extracts currency amounts from documents
- **Benford's Law Test**: Detects fabricated financial data by analyzing leading digit distribution
- **Round Number Anomaly**: Flags suspicious patterns (e.g., too many $10,000 payments vs $9,842)
- High frequency of round numbers often indicates laundering or bribes

#### 3. Cartographer (Geospatial Correlation)
- Extracts airport codes (KTEB, TJSJ, JFK, etc.) and city names
- Cross-references locations with dates from the same documents
- Generates interactive HTML map with pins for each location
- Links flight logs to meetings and events

#### 4. Timeline Auditor (Gap Analysis)
- Extracts all dates from documents
- Identifies "silence intervals" (>20 days with no communications)
- Criminal activity often occurs during communication gaps
- Reports include documents immediately before and after each gap

### Example Usage (Programmatic)

See `examples/forensic_analysis_demo.py` for programmatic usage examples.

```python
from analytics.graph_analyst import GraphAnalyst

# Initialize and run analysis
analyst = GraphAnalyst(db_path="data/epstein_analysis.db")
analyst.build_graph(limit=100)
bridge_nodes = analyst.calculate_bridge_nodes(top_n=10)
```
- Reports files with both text and images

## Requirements

### For Text Data Processing
Python 3.6+ with standard library modules (no external dependencies):
- `csv`
- `os`
- `sys`
- `pathlib`
- `urllib`

### For Image Downloads
Additional requirement:
- `gdown` - For downloading from Google Drive

Install with:
```bash
pip install gdown
```

## License

Please refer to the original dataset repository for licensing information.
