#!/usr/bin/env python3
"""
Investigative Suite - Main Entry Point

This script orchestrates the investigative framework to analyze documents
in the repository using OCR and entity extraction.

Usage:
    python main.py [directory] [--extensions ext1 ext2 ...]
    
Example:
    python main.py data/processed/files --extensions .txt
    python main.py data/images --extensions .jpg .pdf
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from src.librarian import ingest_documents, detect_duplicates
from src.detective import extract_entities, find_relationships
from src.db import InvestigationDB

# Configuration constants
DEFAULT_DATA_DIRECTORY = 'data/processed/files'
DEFAULT_DATABASE_PATH = 'investigation.db'
DEFAULT_LOG_PATH = 'investigation.log'
DEFAULT_FILE_EXTENSIONS = ['.txt', '.pdf', '.jpg', '.jpeg', '.png']


def setup_logging(log_file: str = DEFAULT_LOG_PATH, verbose: bool = False):
    """
    Configure logging for the investigation.
    
    Args:
        log_file: Path to log file
        verbose: Enable verbose debug logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.info("=" * 80)
    logging.info("Investigation started")
    logging.info("=" * 80)


def process_documents(directory: str, extensions: List[str], db: InvestigationDB):
    """
    Process documents from directory and store in database.
    
    Args:
        directory: Directory to scan
        extensions: File extensions to process
        db: Database connection
    """
    logger = logging.getLogger(__name__)
    
    logger.info(f"Scanning directory: {directory}")
    logger.info(f"Looking for extensions: {', '.join(extensions)}")
    
    # Ingest documents
    try:
        documents = ingest_documents(directory, extensions)
        
        if not documents:
            logger.warning("No documents found to process")
            return
        
        logger.info(f"Found {len(documents)} documents")
        
        # Detect duplicates
        unique_docs, duplicates = detect_duplicates(documents)
        logger.info(f"Unique documents: {len(unique_docs)}")
        if duplicates:
            logger.info(f"Duplicates found: {len(duplicates)}")
        
        # Process each unique document
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        for filename, text, file_hash in unique_docs:
            try:
                # Check if document already exists
                if db.document_exists(file_hash):
                    logger.debug(f"Document already in database: {filename}")
                    skipped_count += 1
                    continue
                
                # Insert document
                doc_id = db.insert_document(filename, text, file_hash)
                
                if doc_id is None:
                    logger.warning(f"Failed to insert document: {filename}")
                    error_count += 1
                    continue
                
                # Extract entities
                entities = extract_entities(text)
                
                # Store entities
                entity_count = 0
                for entity_type, entity_list in entities.items():
                    for value, context in entity_list:
                        entity_id = db.insert_entity(doc_id, entity_type, value, context)
                        if entity_id:
                            entity_count += 1
                
                logger.info(f"Processed: {Path(filename).name} ({entity_count} entities)")
                processed_count += 1
                
                # Find relationships (optional - can be slow for large texts)
                if entity_count > 1:
                    relationships = find_relationships(text, entities)
                    if relationships:
                        logger.debug(f"Found {len(relationships)} relationships in {Path(filename).name}")
                
            except Exception as e:
                logger.error(f"Error processing document {filename}: {e}", exc_info=True)
                error_count += 1
                continue
        
        # Summary
        logger.info("=" * 80)
        logger.info("Processing Summary:")
        logger.info(f"  Processed: {processed_count}")
        logger.info(f"  Skipped (already in DB): {skipped_count}")
        logger.info(f"  Errors: {error_count}")
        logger.info(f"  Total unique documents: {len(unique_docs)}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error during document processing: {e}", exc_info=True)
        raise


def print_statistics(db: InvestigationDB):
    """
    Print database statistics.
    
    Args:
        db: Database connection
    """
    logger = logging.getLogger(__name__)
    
    try:
        stats = db.get_statistics()
        
        logger.info("=" * 80)
        logger.info("Database Statistics:")
        logger.info(f"  Total documents: {stats.get('documents', 0)}")
        logger.info(f"  Total entities: {stats.get('entities', 0)}")
        
        entity_types = stats.get('entities_by_type', {})
        if entity_types:
            logger.info("  Entities by type:")
            for entity_type, count in sorted(entity_types.items()):
                logger.info(f"    {entity_type}: {count}")
        
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Investigative Suite - Analyze documents with OCR and entity extraction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py data/processed/files
  python main.py data/images --extensions .jpg .pdf
  python main.py data/ --verbose
        """
    )
    
    parser.add_argument(
        'directory',
        nargs='?',
        default=DEFAULT_DATA_DIRECTORY,
        help=f'Directory to scan for documents (default: {DEFAULT_DATA_DIRECTORY})'
    )
    
    parser.add_argument(
        '--extensions',
        nargs='+',
        default=DEFAULT_FILE_EXTENSIONS,
        help=f'File extensions to process (default: {" ".join(DEFAULT_FILE_EXTENSIONS)})'
    )
    
    parser.add_argument(
        '--db',
        default=DEFAULT_DATABASE_PATH,
        help=f'Path to SQLite database (default: {DEFAULT_DATABASE_PATH})'
    )
    
    parser.add_argument(
        '--log',
        default=DEFAULT_LOG_PATH,
        help=f'Path to log file (default: {DEFAULT_LOG_PATH})'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose debug logging'
    )
    
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Only print database statistics without processing new documents'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log, args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize database
        logger.info(f"Opening database: {args.db}")
        db = InvestigationDB(args.db)
        
        if args.stats_only:
            # Just print statistics
            print_statistics(db)
        else:
            # Check if directory exists
            if not Path(args.directory).exists():
                logger.error(f"Directory does not exist: {args.directory}")
                sys.exit(1)
            
            # Process documents
            process_documents(args.directory, args.extensions, db)
            
            # Print statistics
            print_statistics(db)
        
        # Close database
        db.close()
        
        logger.info("Investigation completed successfully")
        
    except KeyboardInterrupt:
        logger.warning("Investigation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error during investigation: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
