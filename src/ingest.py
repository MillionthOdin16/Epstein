"""
Ingestion module for the autonomous investigative architecture.

This module provides functionality to scan, process, and ingest documents
including PDFs, images, and text files with OCR capabilities.
"""

import hashlib
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Optional, List, Set, Tuple

# Third-party imports
try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
except ImportError as e:
    logging.error(f"Missing required dependency: {e}")
    raise

# Configure module-specific logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler('error.log')
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)


class DocumentIngester:
    """Handles document ingestion with OCR and deduplication."""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.txt'}
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
    
    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialize document ingester.
        
        Args:
            tesseract_cmd: Optional path to tesseract executable
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        self.processed_hashes: Set[str] = set()
        logger.info("DocumentIngester initialized")
    
    def calculate_hash(self, file_path: str) -> Optional[str]:
        """
        Calculate SHA-256 hash of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA-256 hash string, or None on error
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except (IOError, OSError) as e:
            logger.error(f"Error calculating hash for {file_path}: {e}", exc_info=True)
            return None
    
    def is_duplicate(self, file_hash: str) -> bool:
        """
        Check if a file hash has already been processed.
        
        Args:
            file_hash: SHA-256 hash to check
            
        Returns:
            True if duplicate, False otherwise
        """
        if file_hash in self.processed_hashes:
            logger.info(f"Duplicate file detected with hash: {file_hash}")
            return True
        return False
    
    def mark_as_processed(self, file_hash: str) -> None:
        """
        Mark a file hash as processed.
        
        Args:
            file_hash: SHA-256 hash to mark
        """
        self.processed_hashes.add(file_hash)
    
    def scan_directory(self, directory: str, recursive: bool = True) -> List[str]:
        """
        Scan directory for supported document files.
        
        Args:
            directory: Directory path to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            List of file paths
        """
        files = []
        try:
            path = Path(directory)
            if not path.exists():
                logger.error(f"Directory does not exist: {directory}")
                return files
            
            if not path.is_dir():
                logger.error(f"Path is not a directory: {directory}")
                return files
            
            # Use rglob for recursive, glob for non-recursive
            pattern = "**/*" if recursive else "*"
            
            for file_path in path.glob(pattern):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in self.SUPPORTED_EXTENSIONS:
                        files.append(str(file_path))
            
            logger.info(f"Found {len(files)} supported files in {directory}")
            return files
            
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}", exc_info=True)
            return files
    
    def extract_text_from_image(self, image_path: str) -> Optional[str]:
        """
        Extract text from image using OCR.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text, or None on error
        """
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            logger.info(f"Successfully extracted text from image: {image_path}")
            return text
        except pytesseract.TesseractNotFoundError:
            logger.error("Tesseract is not installed or not in PATH", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error extracting text from image {image_path}: {e}", exc_info=True)
            return None
    
    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extract text from PDF using OCR.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text, or None on error
        """
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path)
            
            # Extract text from each page
            text_parts = []
            for i, image in enumerate(images):
                try:
                    page_text = pytesseract.image_to_string(image)
                    text_parts.append(page_text)
                except Exception as e:
                    logger.error(f"Error processing page {i+1} of {pdf_path}: {e}")
                    continue
            
            full_text = "\n\n".join(text_parts)
            logger.info(f"Successfully extracted text from PDF: {pdf_path}")
            return full_text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}", exc_info=True)
            return None
    
    def extract_text_from_txt(self, txt_path: str) -> Optional[str]:
        """
        Read text from text file.
        
        Args:
            txt_path: Path to text file
            
        Returns:
            File contents, or None on error
        """
        try:
            with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            logger.info(f"Successfully read text file: {txt_path}")
            return text
        except Exception as e:
            logger.error(f"Error reading text file {txt_path}: {e}", exc_info=True)
            return None
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        try:
            # Normalize unicode characters
            text = unicodedata.normalize('NFKD', text)
            
            # Remove excessive whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove leading/trailing whitespace
            text = text.strip()
            
            # Remove null bytes and other control characters
            text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
            
            return text
            
        except Exception as e:
            logger.error(f"Error cleaning text: {e}", exc_info=True)
            return text
    
    def process_file(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Process a single file: calculate hash, extract text, clean text.
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (hash, cleaned_text), or (None, None) on error
        """
        try:
            # Calculate file hash
            file_hash = self.calculate_hash(file_path)
            if not file_hash:
                return None, None
            
            # Check for duplicates
            if self.is_duplicate(file_hash):
                logger.info(f"Skipping duplicate file: {file_path}")
                return file_hash, None
            
            # Extract text based on file type
            file_ext = Path(file_path).suffix.lower()
            raw_text = None
            
            if file_ext == '.pdf':
                raw_text = self.extract_text_from_pdf(file_path)
            elif file_ext in self.IMAGE_EXTENSIONS:
                raw_text = self.extract_text_from_image(file_path)
            elif file_ext == '.txt':
                raw_text = self.extract_text_from_txt(file_path)
            else:
                logger.warning(f"Unsupported file type: {file_ext} for {file_path}")
                return None, None
            
            if raw_text is None:
                logger.error(f"Failed to extract text from {file_path}")
                return file_hash, None
            
            # Clean the text
            cleaned_text = self.clean_text(raw_text)
            
            # Mark as processed
            self.mark_as_processed(file_hash)
            
            logger.info(f"Successfully processed file: {file_path}")
            return file_hash, cleaned_text
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
            return None, None
    
    def ingest_directory(self, directory: str, recursive: bool = True) -> List[Tuple[str, str, str]]:
        """
        Scan and process all files in a directory.
        
        Args:
            directory: Directory path to process
            recursive: Whether to process subdirectories
            
        Returns:
            List of tuples (file_path, hash, cleaned_text) for successfully processed files
        """
        results = []
        
        try:
            # Scan for files
            files = self.scan_directory(directory, recursive)
            logger.info(f"Starting ingestion of {len(files)} files from {directory}")
            
            # Process each file
            for i, file_path in enumerate(files, 1):
                try:
                    file_hash, cleaned_text = self.process_file(file_path)
                    
                    if file_hash and cleaned_text:
                        results.append((file_path, file_hash, cleaned_text))
                    
                    # Log progress every 10 files
                    if i % 10 == 0:
                        logger.info(f"Processed {i}/{len(files)} files")
                        
                except Exception as e:
                    logger.error(f"Error in ingestion loop for {file_path}: {e}", exc_info=True)
                    continue
            
            logger.info(f"Ingestion complete: {len(results)} files processed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error in ingest_directory: {e}", exc_info=True)
            return results
    
    def reset_duplicate_tracking(self) -> None:
        """Clear the set of processed hashes."""
        self.processed_hashes.clear()
        logger.info("Duplicate tracking reset")


def main():
    """Example usage of DocumentIngester."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <directory_path>")
        sys.exit(1)
    
    directory = sys.argv[1]
    
    try:
        ingester = DocumentIngester()
        results = ingester.ingest_directory(directory)
        
        print(f"\nIngestion Summary:")
        print(f"  Total files processed: {len(results)}")
        print(f"  Duplicates skipped: {len(ingester.processed_hashes) - len(results)}")
        
        # Display first few results
        if results:
            print(f"\nFirst {min(3, len(results))} processed files:")
            for file_path, file_hash, text in results[:3]:
                print(f"  - {file_path}")
                print(f"    Hash: {file_hash}")
                print(f"    Text length: {len(text)} characters")
                print()
    
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
