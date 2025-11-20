"""
Detective module for entity extraction and relationship finding.

This module handles entity extraction (people, money, dates) and
relationship discovery from text documents.
"""

import logging
import re
from typing import List, Dict, Tuple, Set
from collections import defaultdict

logger = logging.getLogger(__name__)

# Configuration constants
MAX_TEXT_SIZE_FOR_SPACY = 1000000  # Maximum text size to process with spaCy (1MB)
ENTITY_CONTEXT_WINDOW = 50  # Characters to include before and after entity for context
RELATIONSHIP_PROXIMITY_THRESHOLD = 500  # Max character distance to consider entities related

# Try to import spaCy
try:
    import spacy
    SPACY_AVAILABLE = True
    # Global spaCy model - will be loaded on first use
    _nlp_model = None
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not available. Entity extraction will use regex fallback.")


def _load_spacy_model():
    """Load spaCy model lazily."""
    global _nlp_model
    if _nlp_model is None and SPACY_AVAILABLE:
        try:
            _nlp_model = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy model: en_core_web_sm")
        except OSError:
            logger.warning("spaCy model 'en_core_web_sm' not found. Using regex fallback.")
            logger.info("Run 'python -m spacy download en_core_web_sm' to enable spaCy.")
    return _nlp_model


def extract_entities(text: str, use_spacy: bool = True) -> Dict[str, List[Tuple[str, str]]]:
    """
    Extract entities from text using spaCy or regex fallback.
    
    Extracts:
    - PERSON: Names of people
    - MONEY: Currency amounts
    - DATE: Date references
    
    Args:
        text: Input text to analyze
        use_spacy: Whether to attempt using spaCy (falls back to regex if unavailable)
        
    Returns:
        Dictionary mapping entity types to list of (value, context) tuples
    """
    entities = {
        'PERSON': [],
        'MONEY': [],
        'DATE': []
    }
    
    if not text or not text.strip():
        return entities
    
    # Try spaCy first if available and requested
    if use_spacy and SPACY_AVAILABLE:
        nlp = _load_spacy_model()
        if nlp:
            try:
                entities = _extract_entities_spacy(text, nlp)
                logger.debug(f"Extracted entities using spaCy: {len(entities['PERSON'])} people, "
                           f"{len(entities['MONEY'])} money, {len(entities['DATE'])} dates")
                return entities
            except Exception as e:
                logger.warning(f"spaCy extraction failed, falling back to regex: {e}")
    
    # Fallback to regex-based extraction
    entities = _extract_entities_regex(text)
    logger.debug(f"Extracted entities using regex: {len(entities['PERSON'])} people, "
               f"{len(entities['MONEY'])} money, {len(entities['DATE'])} dates")
    return entities


def _extract_entities_spacy(text: str, nlp) -> Dict[str, List[Tuple[str, str]]]:
    """
    Extract entities using spaCy NLP.
    
    Args:
        text: Input text
        nlp: Loaded spaCy model
        
    Returns:
        Dictionary of entities with context
    """
    entities = {
        'PERSON': [],
        'MONEY': [],
        'DATE': []
    }
    
    # Process text with spaCy
    doc = nlp(text[:MAX_TEXT_SIZE_FOR_SPACY])  # Limit text size to avoid memory issues
    
    for ent in doc.ents:
        # Get context snippet (±ENTITY_CONTEXT_WINDOW characters around entity)
        start_idx = max(0, ent.start_char - ENTITY_CONTEXT_WINDOW)
        end_idx = min(len(text), ent.end_char + ENTITY_CONTEXT_WINDOW)
        context = text[start_idx:end_idx].replace('\n', ' ').strip()
        
        if ent.label_ == 'PERSON':
            entities['PERSON'].append((ent.text, context))
        elif ent.label_ == 'MONEY':
            entities['MONEY'].append((ent.text, context))
        elif ent.label_ == 'DATE':
            entities['DATE'].append((ent.text, context))
    
    return entities


def _extract_entities_regex(text: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    Extract entities using regex patterns as fallback.
    
    Args:
        text: Input text
        
    Returns:
        Dictionary of entities with context
    """
    entities = {
        'PERSON': [],
        'MONEY': [],
        'DATE': []
    }
    
    # Extract money patterns
    money_patterns = [
        r'\$\s*[\d,]+(?:\.\d{2})?',  # $1,234.56
        r'USD\s*[\d,]+(?:\.\d{2})?',  # USD 1234.56
        r'[\d,]+(?:\.\d{2})?\s*(?:dollars|USD)',  # 1234.56 dollars
    ]
    
    for pattern in money_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(0)
            context = _get_context(text, match.start(), match.end())
            entities['MONEY'].append((value, context))
    
    # Extract date patterns
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY or M/D/YY
        r'\d{1,2}-\d{1,2}-\d{2,4}',  # MM-DD-YYYY
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}',  # Month DD, YYYY
        r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}',  # DD Month YYYY
    ]
    
    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(0)
            context = _get_context(text, match.start(), match.end())
            entities['DATE'].append((value, context))
    
    # Extract person names (proper nouns - basic pattern)
    # Look for capitalized words that appear to be names
    name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'
    
    for match in re.finditer(name_pattern, text):
        value = match.group(0)
        # Filter out common false positives
        if not _is_likely_name(value):
            continue
        context = _get_context(text, match.start(), match.end())
        entities['PERSON'].append((value, context))
    
    return entities


def _get_context(text: str, start: int, end: int, window: int = ENTITY_CONTEXT_WINDOW) -> str:
    """
    Get context snippet around a match.
    
    Args:
        text: Full text
        start: Start index of match
        end: End index of match
        window: Number of characters to include before and after
        
    Returns:
        Context snippet
    """
    context_start = max(0, start - window)
    context_end = min(len(text), end + window)
    context = text[context_start:context_end].replace('\n', ' ').strip()
    return context


def _is_likely_name(text: str) -> bool:
    """
    Check if text is likely a person's name.
    
    Filters out common false positives like organization names, titles, etc.
    
    Args:
        text: Potential name text
        
    Returns:
        True if likely a name, False otherwise
    """
    # Filter out common false positives
    false_positives = {
        'United States', 'New York', 'Los Angeles', 'San Francisco',
        'United Kingdom', 'Supreme Court', 'District Court', 'Federal Bureau',
        'Department Of', 'State Of', 'City Of', 'County Of'
    }
    
    for fp in false_positives:
        if fp.lower() in text.lower():
            return False
    
    # Names should have 2-4 words
    words = text.split()
    if len(words) < 2 or len(words) > 4:
        return False
    
    # Each word should be reasonably short (2-15 characters)
    for word in words:
        if len(word) < 2 or len(word) > 15:
            return False
    
    return True


def find_relationships(text: str, entities: Dict[str, List[Tuple[str, str]]]) -> List[Dict]:
    """
    Find relationships between entities based on co-occurrence.
    
    Identifies when multiple people are mentioned in the same document
    or in close proximity.
    
    Args:
        text: Document text
        entities: Dictionary of extracted entities
        
    Returns:
        List of relationship dictionaries with entity pairs and context
    """
    relationships = []
    
    people = entities.get('PERSON', [])
    
    if len(people) < 2:
        return relationships
    
    # Extract unique person names
    person_names = list(set(name for name, _ in people))
    
    # Find co-occurrences within the same document
    for i, person1 in enumerate(person_names):
        for person2 in person_names[i+1:]:
            # Find all positions of both names in text
            positions1 = [m.start() for m in re.finditer(re.escape(person1), text, re.IGNORECASE)]
            positions2 = [m.start() for m in re.finditer(re.escape(person2), text, re.IGNORECASE)]
            
            if not positions1 or not positions2:
                continue
            
            # Find closest co-occurrences
            close_occurrences = []
            
            for pos1 in positions1:
                for pos2 in positions2:
                    distance = abs(pos1 - pos2)
                    if distance <= RELATIONSHIP_PROXIMITY_THRESHOLD:
                        # Get context around both mentions
                        start = min(pos1, pos2) - ENTITY_CONTEXT_WINDOW
                        end = max(pos1, pos2) + max(len(person1), len(person2)) + ENTITY_CONTEXT_WINDOW
                        start = max(0, start)
                        end = min(len(text), end)
                        context = text[start:end].replace('\n', ' ').strip()
                        close_occurrences.append({
                            'person1': person1,
                            'person2': person2,
                            'distance': distance,
                            'context': context
                        })
            
            if close_occurrences:
                # Keep the closest occurrence
                closest = min(close_occurrences, key=lambda x: x['distance'])
                relationships.append(closest)
    
    logger.debug(f"Found {len(relationships)} relationships")
    return relationships


def find_entity_cooccurrences(entities: Dict[str, List[Tuple[str, str]]], 
                              window_size: int = 100) -> Dict[Tuple[str, str], int]:
    """
    Find how often entities co-occur in similar contexts.
    
    Args:
        entities: Dictionary of extracted entities
        window_size: Character window to consider for co-occurrence
        
    Returns:
        Dictionary mapping entity pairs to co-occurrence count
    """
    cooccurrences = defaultdict(int)
    
    people = entities.get('PERSON', [])
    
    # Create a list of (name, position_estimate) based on context
    # This is simplified - in reality we'd need exact positions
    person_names = [name for name, _ in people]
    
    # Count unique co-occurrences
    unique_people = list(set(person_names))
    
    for i, person1 in enumerate(unique_people):
        for person2 in unique_people[i+1:]:
            # Count how many times they appear together in contexts
            count = sum(1 for name in person_names if name == person1) * \
                   sum(1 for name in person_names if name == person2)
            if count > 0:
                pair = tuple(sorted([person1, person2]))
                cooccurrences[pair] += 1
    
    return dict(cooccurrences)
