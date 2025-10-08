"""
NER Entity Extractors

This module contains different NER extraction methods organized by approach.
"""
import re
from flair.data import Sentence
from typing import List, Dict, Any
from .ner_models import model_manager
from .ner_config import REGEX_PATTERNS, DEFAULT_SETTINGS


class BaseExtractor:
    """Base class for all NER extractors."""
    
    def __init__(self, language: str = 'english'):
        self.language = language
        self.settings = DEFAULT_SETTINGS.copy()
    
    def extract(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text. Must be implemented by subclasses.
        
        Args:
            text: Input text to process
            
        Returns:
            List of entity dictionaries with keys: text, label, start, end
        """
        raise NotImplementedError
    
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entities based on span and label."""
        if not self.settings['deduplicate']:
            return entities
        
        seen = set()
        deduped = []
        
        for entity in entities:
            key = (entity['start'], entity['end'], entity['label'])
            if key not in seen:
                seen.add(key)
                deduped.append(entity)
        
        return deduped
    
    def _filter_by_confidence(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter entities by minimum confidence score."""
        min_conf = self.settings['min_confidence']
        return [
            entity for entity in entities 
            if entity.get('confidence', 1.0) >= min_conf
        ]


class SpacyExtractor(BaseExtractor):
    """Extract entities using spaCy models."""
    
    def extract(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using spaCy NER."""
        try:
            nlp = model_manager.get_spacy_model(self.language)
            doc = nlp(text)
            
            entities = []
            for ent in doc.ents:
                entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'confidence': 1.0  # spaCy doesn't provide confidence scores by default
                })
            
            entities = self._filter_by_confidence(entities)
            return self._deduplicate_entities(entities)
            
        except Exception as e:
            print(f"Error in spaCy extraction ({self.language}): {e}")
            return []


class FlairExtractor(BaseExtractor):
    """Extract entities using Flair models."""
    
    def __init__(self, language: str = 'german', model_name: str = None):
        super().__init__(language)
        self.model_name = model_name or self._get_default_model()
    
    def _get_default_model(self) -> str:
        """Get default Flair model based on language."""
        model_mapping = {
            'german': 'flair/ner-german-legal',
            'english': 'flair/ner-english',
            'dutch': 'flair/ner-dutch'
        }
        return model_mapping.get(self.language, 'flair/ner-english')
    
    def extract(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using Flair NER."""
        try:
            # Load the Flair SequenceTagger model
            tagger = model_manager.get_flair_model(self.model_name)
            
            # Create sentence (don't use tokenizer for legal texts as recommended)
            sentence = Sentence(text, use_tokenizer=False)
            
            # Predict NER tags using the SequenceTagger
            tagger.predict(sentence)
            
            entities = []
            # Iterate over entities and extract information
            for entity in sentence.get_spans('ner'):
                entities.append({
                    'text': entity.text,
                    'label': entity.get_label('ner').value,
                    'start': entity.start_position,
                    'end': entity.end_position,
                    'confidence': entity.get_label('ner').score
                })
            
            entities = self._filter_by_confidence(entities)
            return self._deduplicate_entities(entities)
            
        except Exception as e:
            print(f"Error in Flair extraction ({self.model_name}): {e}")
            return []




class RegexExtractor(BaseExtractor):
    """Extract entities using regex patterns."""
    
    def __init__(self, language: str = 'english', patterns: Dict[str, List[str]] = None):
        super().__init__(language)
        self.patterns = patterns or {}
        self._compiled_patterns = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for better performance."""
        for label, pattern_list in self.patterns.items():
            self._compiled_patterns[label] = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in pattern_list
            ]
    
    def extract(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using regex patterns."""
        entities = []
        
        for label, compiled_patterns in self._compiled_patterns.items():
            for pattern in compiled_patterns:
                for match in pattern.finditer(text):
                    entities.append({
                        'text': match.group(0),
                        'label': label,
                        'start': match.start(),
                        'end': match.end(),
                        'confidence': 1.0
                    })
        
        return self._deduplicate_entities(entities)


class LanguageRegexExtractor(RegexExtractor):
    """Extract entities using all regex patterns for a specific language."""
    
    def __init__(self, language: str):
        # Get all regex patterns for this language and convert to uppercase labels
        language_patterns = REGEX_PATTERNS.get(language, {})
        patterns = {}
        
        for pattern_type, pattern_list in language_patterns.items():
            # Convert pattern type to uppercase for entity labels (date -> DATE)
            label = pattern_type.upper()
            patterns[label] = pattern_list
        
        super().__init__(language, patterns)


class CompositeExtractor(BaseExtractor):
    """Combine multiple extractors into one unified extractor."""
    
    def __init__(self, extractors: List[BaseExtractor]):
        super().__init__()
        self.extractors = extractors
    
    def extract(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using all configured extractors."""
        all_entities = []
        
        for extractor in self.extractors:
            try:
                entities = extractor.extract(text)
                all_entities.extend(entities)
            except Exception as e:
                print(f"Error in extractor {type(extractor).__name__}: {e}")
                continue
        
        return self._deduplicate_entities(all_entities)


# Pre-configured extractors for common use cases
def create_german_extractor() -> CompositeExtractor:
    """Create a comprehensive German NER extractor using Flair's legal model."""
    return CompositeExtractor([
        FlairExtractor('german', 'flair/ner-german-legal'),
        LanguageRegexExtractor('german')
    ])


def create_dutch_extractor() -> CompositeExtractor:
    """Create a comprehensive Dutch NER extractor."""
    return CompositeExtractor([
        SpacyExtractor('dutch'),
        LanguageRegexExtractor('dutch')
    ])


def create_english_extractor() -> CompositeExtractor:
    """Create a comprehensive English NER extractor."""
    return CompositeExtractor([
        SpacyExtractor('english'),
        LanguageRegexExtractor('english')  # Will be empty unless patterns are added
    ])
