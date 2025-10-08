"""
NER Model Management

This module handles loading and caching of NER models with lazy initialization.
"""

import spacy
from typing import Dict, Any
from .ner_config import NER_MODELS
from flair.models import SequenceTagger



class ModelManager:
    """
    Singleton class to manage NER model loading and caching.
    
    This class ensures models are loaded only once and cached for reuse,
    improving performance and memory usage.
    """
    
    _instance = None
    _models: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_spacy_model(self, language: str):
        """
        Load and cache a spaCy model for the specified language.
        
        Args:
            language: Language code ('dutch', 'german', 'english')
            
        Returns:
            Loaded spaCy model
            
        Raises:
            ValueError: If language is not supported
            Exception: If model cannot be loaded
        """
        if language not in NER_MODELS['spacy']:
            raise ValueError(f"Unsupported language: {language}")
        
        model_key = f"spacy_{language}"
        
        if model_key not in self._models:
            model_name = NER_MODELS['spacy'][language]
            try:
                self._models[model_key] = spacy.load(model_name)
            except OSError:
                raise Exception(
                    f"spaCy model '{model_name}' not found. "
                    f"Please install with: python -m spacy download {model_name}"
                )
        
        return self._models[model_key]
    
    def get_flair_model(self, model_name: str):
        """
        Load and cache a Flair model.
        
        Args:
            model_name: Flair model name (e.g., 'flair/ner-german-legal')
            
        Returns:
            Loaded Flair SequenceTagger model
            
        Raises:
            Exception: If model cannot be loaded
        """
        model_key = f"flair_{model_name.replace('/', '_')}"
        
        if model_key not in self._models:
            try:
                self._models[model_key] = SequenceTagger.load(model_name)
            except Exception as e:
                raise Exception(
                    f"Flair model '{model_name}' not found. "
                    f"Please install with: pip install flair. "
                    f"Error: {str(e)}"
                )
        
        return self._models[model_key]
    
    
    def clear_cache(self):
        """Clear all cached models to free memory."""
        self._models.clear()


# Global model manager instance
model_manager = ModelManager()
