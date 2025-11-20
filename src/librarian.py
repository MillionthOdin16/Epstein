"""
Librarian module for document ingestion and OCR.

This module handles document discovery, OCR processing, and deduplication.
"""

import hashlib
import logging
import os
from pathlib import Path
from typing import List, Tuple, Optional
import mimetypes

logger = logging.getLogger(__name__)

# Configuration constants
MIN_TEXT_LENGTH_FOR_DIRECT_EXTRACTION = 100  # Minimum text length to consider direct PDF extraction successful

# Try to import OCR dependencies
try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    logger.warning("pytesseract or PIL not available. OCR functionality will be limited.")

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available. PDF OCR functionality will be limited.")

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 not available. PDF text extraction will be limited.")


def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA256 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Hexadecimal hash string
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error computing hash for {file_path}: {e}")
        return ""


def ingest_documents(directory: str, extensions: Optional[List[str]] = None) -> List[Tuple[str, str, str]]:
    """
    Recursively scan directory for documents and extract text.
    
    Scans for .pdf, .jpg, .jpeg, .png, .txt files by default.
    
    Args:
        directory: Root directory to scan
        extensions: List of file extensions to process (default: ['.pdf', '.jpg', '.jpeg', '.png', '.txt'])
        
    Returns:
        List of tuples: (filename, extracted_text, file_hash)
    """
    if extensions is None:
        extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.txt']
    
    # Normalize extensions to lowercase
    extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]
    
    documents = []
    directory_path = Path(directory)
    
    if not directory_path.exists():
        logger.error(f"Directory does not exist: {directory}")
        return documents
    
    logger.info(f"Scanning directory: {directory}")
    
    # Recursively find all files with specified extensions
    for file_path in directory_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            try:
                logger.debug(f"Processing file: {file_path}")
                
                # Compute file hash
                file_hash = compute_file_hash(str(file_path))
                if not file_hash:
                    logger.warning(f"Skipping file with empty hash: {file_path}")
                    continue
                
                # Extract text based on file type
                extracted_text = extract_text_from_file(str(file_path))
                
                if extracted_text:
                    documents.append((str(file_path), extracted_text, file_hash))
                    logger.info(f"Successfully processed: {file_path.name}")
                else:
                    logger.warning(f"No text extracted from: {file_path.name}")
                    
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue
    
    logger.info(f"Completed scanning. Found {len(documents)} documents.")
    return documents


def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from a file based on its type.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Extracted text content
    """
    file_path_obj = Path(file_path)
    extension = file_path_obj.suffix.lower()
    
    try:
        if extension == '.txt':
            return extract_text_from_txt(file_path)
        elif extension == '.pdf':
            return extract_text_from_pdf(file_path)
        elif extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            return extract_text_from_image(file_path)
        else:
            logger.warning(f"Unsupported file type: {extension}")
            return ""
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""


def extract_text_from_txt(file_path: str) -> str:
    """
    Extract text from a plain text file.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        Text content
    """
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        logger.warning(f"Could not decode text file with common encodings: {file_path}")
        return ""
        
    except Exception as e:
        logger.error(f"Error reading text file {file_path}: {e}")
        return ""


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file.
    
    First attempts to extract text directly, then falls back to OCR if needed.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text content
    """
    text = ""
    
    # Try to extract text directly from PDF first
    if PYPDF2_AVAILABLE:
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # If we got substantial text, return it
            if len(text.strip()) > MIN_TEXT_LENGTH_FOR_DIRECT_EXTRACTION:
                logger.debug(f"Extracted text directly from PDF: {file_path}")
                return text
        except Exception as e:
            logger.debug(f"Direct PDF text extraction failed: {e}")
    
    # Fall back to OCR if direct extraction didn't work
    if PDF2IMAGE_AVAILABLE and PYTESSERACT_AVAILABLE:
        try:
            logger.debug(f"Attempting OCR on PDF: {file_path}")
            images = convert_from_path(file_path)
            
            ocr_text = ""
            for i, image in enumerate(images):
                logger.debug(f"Processing page {i+1}/{len(images)}")
                page_text = pytesseract.image_to_string(image)
                ocr_text += page_text + "\n"
            
            if ocr_text.strip():
                return ocr_text
                
        except Exception as e:
            logger.error(f"OCR failed for PDF {file_path}: {e}")
    
    return text


def extract_text_from_image(file_path: str) -> str:
    """
    Extract text from an image using OCR.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Extracted text content
    """
    if not PYTESSERACT_AVAILABLE:
        logger.warning("pytesseract not available. Cannot perform OCR.")
        return ""
    
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logger.error(f"OCR failed for image {file_path}: {e}")
        return ""


def detect_duplicates(documents: List[Tuple[str, str, str]]) -> Tuple[List[Tuple[str, str, str]], List[str]]:
    """
    Detect and remove duplicate documents based on hash.
    
    Args:
        documents: List of (filename, text, hash) tuples
        
    Returns:
        Tuple of (unique_documents, duplicate_filenames)
    """
    seen_hashes = set()
    unique_documents = []
    duplicates = []
    
    for filename, text, file_hash in documents:
        if file_hash in seen_hashes:
            duplicates.append(filename)
            logger.debug(f"Duplicate detected: {filename}")
        else:
            seen_hashes.add(file_hash)
            unique_documents.append((filename, text, file_hash))
    
    if duplicates:
        logger.info(f"Found {len(duplicates)} duplicate documents")
    
    return unique_documents, duplicates
