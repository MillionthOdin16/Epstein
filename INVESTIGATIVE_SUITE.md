# Investigative Suite

A Python-based investigative framework for analyzing documents with OCR and entity extraction capabilities.

## Features

- **Document Ingestion**: Recursively scans directories for documents (.pdf, .jpg, .png, .txt)
- **OCR Processing**: Converts image-based PDFs and images to text using Tesseract
- **Deduplication**: Detects and skips duplicate files using SHA-256 hashing
- **Entity Extraction**: Identifies people, money amounts, and dates using spaCy or regex
- **Relationship Detection**: Finds co-occurrences of names within documents
- **SQLite Storage**: Stores documents and entities in a structured database

## Installation

### Prerequisites

1. Python 3.7 or higher
2. Tesseract OCR engine (for OCR functionality)

#### Install Tesseract

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Install spaCy Language Model (Optional but Recommended)

For better entity extraction:
```bash
python -m spacy download en_core_web_sm
```

If spaCy model is not installed, the system will automatically fall back to regex-based extraction.

## Usage

### Basic Usage

Process documents in the default directory:
```bash
python main.py
```

### Specify Directory

Process documents in a specific directory:
```bash
python main.py data/processed/files
```

### Specify File Extensions

Process only specific file types:
```bash
python main.py data/images --extensions .jpg .pdf
```

### Verbose Mode

Enable detailed debug logging:
```bash
python main.py data/ --verbose
```

### View Statistics Only

Display database statistics without processing new documents:
```bash
python main.py --stats-only
```

### Custom Database and Log Files

```bash
python main.py data/ --db my_investigation.db --log my_investigation.log
```

### Query and Explore the Database

After processing documents, use the query script to explore results:

```bash
# Show statistics
python query.py --stats

# List documents
python query.py --docs

# List entities by type
python query.py --entities PERSON
python query.py --entities MONEY --limit 50

# Search for specific entities
python query.py --search "John Smith"
python query.py --search "$1000"
```

### Run the Example

See a demonstration of programmatic API usage:
```bash
python example.py
```

## Module Overview

### src/librarian.py - Document Ingestion

- `ingest_documents(directory)`: Recursively scans for documents
- `extract_text_from_file()`: Extracts text based on file type
- `extract_text_from_pdf()`: PDF text extraction with OCR fallback
- `extract_text_from_image()`: OCR for images
- `compute_file_hash()`: SHA-256 hashing for deduplication
- `detect_duplicates()`: Identifies duplicate documents

### src/detective.py - Entity Extraction

- `extract_entities(text)`: Identifies PERSON, MONEY, and DATE entities
- `find_relationships(text, entities)`: Discovers name co-occurrences
- Uses spaCy for NLP when available, falls back to regex patterns

### src/db.py - Database Management

- `InvestigationDB`: SQLite database wrapper
- Tables:
  - `documents`: Stores document metadata and text
  - `entities`: Stores extracted entities with context
- Methods for insertion, retrieval, and statistics

### main.py - Orchestration

Entry point that coordinates:
1. Document ingestion
2. OCR processing
3. Entity extraction
4. Database storage
5. Error handling and logging

### query.py - Database Explorer

Interactive query tool for exploring investigation results:
- `--stats`: Display database statistics (default)
- `--docs`: List processed documents
- `--entities TYPE`: List entities by type (PERSON, MONEY, DATE, all)
- `--search TERM`: Search for specific entities
- `--limit N`: Limit number of results

### example.py - Usage Example

Demonstrates programmatic API usage:
- Creates sample documents
- Shows complete workflow
- Extracts and displays entities
- Useful for integration reference

## Database Schema

### documents table
- `id`: Primary key
- `filename`: Document filename
- `raw_text`: Extracted text content
- `hash`: SHA-256 hash for deduplication
- `created_at`: Timestamp

### entities table
- `id`: Primary key
- `doc_id`: Foreign key to documents
- `entity_type`: Type (PERSON, MONEY, DATE)
- `value`: Entity value
- `context_snippet`: Surrounding text context
- `created_at`: Timestamp

## Example Workflow

```bash
# 1. Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 2. Process text files
python main.py data/processed/files --extensions .txt

# 3. View statistics
python main.py --stats-only

# 4. Check the logs
tail -f investigation.log
```

## Error Handling

The system handles errors gracefully:
- Corrupt PDFs are logged and skipped
- OCR failures are logged with detailed error messages
- All errors are written to `investigation.log`
- Processing continues even when individual files fail

## Logging

All activities are logged to `investigation.log` with:
- Timestamp
- Log level (INFO, WARNING, ERROR, DEBUG)
- Module name
- Detailed message

Use `--verbose` flag for debug-level logging.

## Performance Notes

- Large documents are processed in chunks to avoid memory issues
- Duplicate detection prevents reprocessing the same files
- Database uses indexes for efficient queries
- Text is limited to 1MB for spaCy processing to prevent memory issues

## Troubleshooting

### Tesseract Not Found
If you get "tesseract not found" errors:
1. Ensure Tesseract is installed
2. Add Tesseract to your system PATH
3. On Windows, you may need to set `pytesseract.pytesseract.tesseract_cmd`

### spaCy Model Not Found
```bash
python -m spacy download en_core_web_sm
```

### Database Locked
If you get database locked errors, ensure no other process is accessing the database file.

## License

Please refer to the main repository for licensing information.
