# Autonomous Investigative Architecture

A production-grade Python package for autonomous document investigation with OCR, entity extraction, and lead management capabilities.

## Features

### 1. Document Ingestion (`src/ingest.py`)

- **Recursive File Scanner**: Scans directories for `.pdf`, `.jpg`, `.jpeg`, `.png`, and `.txt` files
- **OCR Processing**: Uses `pytesseract` for optical character recognition on images and PDFs
- **Deduplication**: SHA-256 hash checking to skip duplicate files
- **Text Cleaning**: Removes excess whitespace and normalizes unicode characters
- **Error Handling**: Comprehensive error logging to `error.log` without crashes

### 2. Database Management (`src/database.py`)

SQLite database (`investigation.db`) with three core tables:

#### `documents` Table
- `id`: Primary key (auto-increment)
- `hash`: SHA-256 hash (unique)
- `path`: File path
- `raw_text`: Extracted and cleaned text
- `ingested_at`: Timestamp of ingestion

#### `entities` Table
- `id`: Primary key (auto-increment)
- `doc_id`: Foreign key to documents
- `type`: Entity type (PERSON/ORG/LOC)
- `value`: Entity name/value
- `confidence`: Confidence score (0-1)

#### `leads` Table
- `id`: Primary key (auto-increment)
- `entity_value`: Entity associated with lead
- `suspicion_score`: Suspicion score
- `status`: Investigation status (NEW/INVESTIGATING/CLOSED)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## Installation

### System Dependencies

Before installing Python packages, ensure you have:

1. **Tesseract OCR** (required for OCR functionality):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr
   
   # macOS
   brew install tesseract
   
   # Windows
   # Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

2. **Poppler** (required for PDF processing):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install poppler-utils
   
   # macOS
   brew install poppler
   
   # Windows
   # Download from: https://blog.alivate.com.au/poppler-windows/
   ```

### Python Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Basic Example

```python
from src.database import DatabaseManager
from src.ingest import DocumentIngester

# Initialize components
db = DatabaseManager("investigation.db")
ingester = DocumentIngester()

# Scan and process documents
directory = "/path/to/documents"
results = ingester.ingest_directory(directory, recursive=True)

# Store results in database
for file_path, file_hash, cleaned_text in results:
    doc_id = db.insert_document(file_hash, file_path, cleaned_text)
    if doc_id:
        print(f"Ingested: {file_path}")

# View statistics
stats = db.get_statistics()
print(f"Total documents: {stats['total_documents']}")

# Close database connection
db.close()
```

### Command-Line Usage

#### Ingest Documents

```bash
python3 src/ingest.py /path/to/documents
```

### Advanced Usage

#### Using Context Manager

```python
with DatabaseManager("investigation.db") as db:
    # Your database operations
    doc_id = db.insert_document(hash_val, path, text)
    entities = db.get_entities_by_document(doc_id)
```

#### Entity Extraction

```python
# Insert entities found in a document
doc_id = 1
db.insert_entity(doc_id, 'PERSON', 'John Doe', confidence=0.95)
db.insert_entity(doc_id, 'ORG', 'ACME Corp', confidence=0.88)
db.insert_entity(doc_id, 'LOC', 'New York', confidence=0.92)
```

#### Lead Management

```python
# Create a new lead
lead_id = db.insert_lead('Suspicious Person', suspicion_score=0.85, status='NEW')

# Update lead status
db.update_lead_status(lead_id, 'INVESTIGATING')

# Retrieve leads by status
active_leads = db.get_leads_by_status('INVESTIGATING')
```

#### Custom Tesseract Path

```python
# If tesseract is not in PATH
ingester = DocumentIngester(tesseract_cmd='/usr/local/bin/tesseract')
```

## Error Handling

All errors are logged to `error.log` with timestamps and stack traces. The system is designed to continue operation even when individual files fail to process.

Example error log entry:
```
2025-11-20 23:30:00 - src.ingest - ERROR - Error extracting text from image /path/to/image.jpg: [Errno 2] No such file or directory
```

## Performance Considerations

- **Large Files**: Files are read in 4KB chunks for hash calculation
- **Memory**: PDF pages are processed individually to manage memory usage
- **Progress Logging**: Status logged every 10 files during ingestion
- **Indexing**: Database indexes on hash, doc_id, type, and status for fast queries

## Database Schema

```sql
-- Documents table
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT NOT NULL UNIQUE,
    path TEXT NOT NULL,
    raw_text TEXT,
    ingested_at TIMESTAMP NOT NULL
);

-- Entities table
CREATE TABLE entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('PERSON', 'ORG', 'LOC')),
    value TEXT NOT NULL,
    confidence REAL,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Leads table
CREATE TABLE leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_value TEXT NOT NULL,
    suspicion_score REAL,
    status TEXT NOT NULL DEFAULT 'NEW' CHECK(status IN ('NEW', 'INVESTIGATING', 'CLOSED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Reference

### DocumentIngester

- `__init__(tesseract_cmd=None)`: Initialize ingester
- `calculate_hash(file_path)`: Calculate SHA-256 hash
- `is_duplicate(file_hash)`: Check if hash already processed
- `scan_directory(directory, recursive=True)`: Scan for supported files
- `extract_text_from_image(image_path)`: OCR from image
- `extract_text_from_pdf(pdf_path)`: OCR from PDF
- `extract_text_from_txt(txt_path)`: Read text file
- `clean_text(text)`: Clean and normalize text
- `process_file(file_path)`: Process single file
- `ingest_directory(directory, recursive=True)`: Process all files in directory

### DatabaseManager

- `__init__(db_path)`: Initialize database
- `insert_document(hash_value, path, raw_text)`: Add document
- `document_exists(hash_value)`: Check if document exists
- `insert_entity(doc_id, entity_type, value, confidence)`: Add entity
- `insert_lead(entity_value, suspicion_score, status)`: Add lead
- `update_lead_status(lead_id, status)`: Update lead status
- `get_document_by_hash(hash_value)`: Retrieve document
- `get_entities_by_document(doc_id)`: Get entities for document
- `get_leads_by_status(status)`: Get leads by status
- `get_statistics()`: Get database statistics
- `close()`: Close database connection

## Security Considerations

- **SQL Injection**: All queries use parameterized statements
- **File Access**: Error handling for permission and access issues
- **Data Validation**: Type checking and constraints on all inputs
- **Logging**: Sensitive data not logged; only errors and metadata

## License

See repository license.

## Contributing

Contributions welcome! Please ensure:
- Comprehensive error handling
- Type hints for all functions
- Docstrings following Google style
- All errors logged, not raised unnecessarily
