"""
Simplified NER Functions Interface

This module provides a clean, simple interface to the refactored NER system.
It maintains backward compatibility while using the improved architecture.
"""

from typing import List, Dict, Any
from .ner_extractors import (
    create_german_extractor, 
    create_dutch_extractor, 
    create_english_extractor,
    SpacyExtractor,
    LanguageRegexExtractor
)


# Cached extractors for performance
_extractors = {}


def get_extractor(language: str, extractor_type: str = 'composite'):
    """
    Get a cached extractor for the specified language and type.
    
    Args:
        language: Language code ('german', 'dutch', 'english')
        extractor_type: Type of extractor ('composite', 'spacy', 'flair', 'date')
        
    Returns:
        Configured extractor instance
    """
    key = f"{language}_{extractor_type}"
    
    if key not in _extractors:
        if extractor_type == 'composite':
            if language == 'german':
                _extractors[key] = create_german_extractor()
            elif language == 'dutch':
                _extractors[key] = create_dutch_extractor()
            elif language == 'english':
                _extractors[key] = create_english_extractor()
            else:
                raise ValueError(f"Unsupported language: {language}")
        
        elif extractor_type == 'spacy':
            _extractors[key] = SpacyExtractor(language)
        
        elif extractor_type == 'regex':
            _extractors[key] = LanguageRegexExtractor(language)
        
        else:
            raise ValueError(f"Unsupported combination: {language} + {extractor_type}")
    
    return _extractors[key]

# New simplified interface
def extract_entities(text: str, language: str = 'german', method: str = 'composite') -> List[Dict[str, Any]]:
    """
    Extract entities from text using the specified language and method.
    
    Args:
        text: Input text to process
        language: Language of the text ('german', 'dutch', 'english')
        method: Extraction method ('composite', 'spacy', 'regex')
        
    Returns:
        List of entity dictionaries with keys: text, label, start, end, confidence
        
    Example:
        entities = extract_entities("John Doe works at Microsoft in Berlin.", 'english')
    """
    if method == 'composite':
        extractor = get_extractor(language, 'composite')
    elif method == 'spacy':
        extractor = get_extractor(language, 'spacy')
    elif method == 'regex':
        extractor = get_extractor(language, 'regex')
    else:
        raise ValueError(f"Unsupported method '{method}' for language '{language}'")
    
    return extractor.extract(text)
