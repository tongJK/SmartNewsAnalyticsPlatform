"""
Embedding service with configurable model selection and caching
"""
from sentence_transformers import SentenceTransformer
from django.conf import settings
import logging
import os

logger = logging.getLogger('articles')


class EmbeddingModelConfig:
    """Configuration for embedding models"""
    
    # Available models with their specifications
    MODELS = {
        'fast': {
            'name': 'all-MiniLM-L6-v2',
            'dimensions': 384,
            'size_mb': 23,
            'description': 'Fastest, good quality, multilingual'
        },
        'balanced': {
            'name': 'all-MiniLM-L12-v2', 
            'dimensions': 384,
            'size_mb': 33,
            'description': 'Balanced speed/quality, multilingual'
        },
        'accurate': {
            'name': 'all-mpnet-base-v2',
            'dimensions': 768,
            'size_mb': 420,
            'description': 'Best quality, slower, English-focused'
        },
        'qa': {
            'name': 'multi-qa-MiniLM-L6-cos-v1',
            'dimensions': 384,
            'size_mb': 23,
            'description': 'Optimized for Q&A tasks'
        },
        'search': {
            'name': 'msmarco-MiniLM-L6-cos-v5',
            'dimensions': 384,
            'size_mb': 23,
            'description': 'Optimized for search/retrieval'
        },
        'multilingual': {
            'name': 'paraphrase-multilingual-MiniLM-L12-v2',
            'dimensions': 384,
            'size_mb': 470,
            'description': 'High-quality multilingual support'
        }
    }
    
    @classmethod
    def get_model_name(cls, model_key='fast'):
        """Get model name from configuration key"""
        model_key = os.getenv('EMBEDDING_MODEL', model_key)
        return cls.MODELS.get(model_key, cls.MODELS['fast'])['name']
    
    @classmethod
    def get_dimensions(cls, model_key='fast'):
        """Get embedding dimensions for the model"""
        model_key = os.getenv('EMBEDDING_MODEL', model_key)
        return cls.MODELS.get(model_key, cls.MODELS['fast'])['dimensions']


class EmbeddingModelManager:
    """Singleton manager for embedding models with caching"""
    
    _instance = None
    _model = None
    _current_model_name = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_model(self, model_key='fast'):
        """Get cached model instance"""
        model_name = EmbeddingModelConfig.get_model_name(model_key)
        
        # Load model if not cached or if model changed
        if self._model is None or self._current_model_name != model_name:
            logger.info(f"Loading embedding model: {model_name}")
            self._model = SentenceTransformer(model_name)
            self._current_model_name = model_name
            
            # Log model info
            config = next(
                (config for config in EmbeddingModelConfig.MODELS.values() 
                 if config['name'] == model_name), 
                {'description': 'Custom model'}
            )
            logger.info(f"Model loaded: {config['description']}")
        
        return self._model
    
    def encode(self, texts, model_key='fast', **kwargs):
        """Encode texts using the specified model"""
        model = self.get_model(model_key)
        
        # Default parameters for consistent results
        default_kwargs = {
            'normalize_embeddings': True,
            'batch_size': 32,
            'show_progress_bar': False
        }
        default_kwargs.update(kwargs)
        
        return model.encode(texts, **default_kwargs)
    
    def get_model_info(self, model_key='fast'):
        """Get information about the current model"""
        model_name = EmbeddingModelConfig.get_model_name(model_key)
        config = next(
            (config for config in EmbeddingModelConfig.MODELS.values() 
             if config['name'] == model_name), 
            None
        )
        
        return {
            'name': model_name,
            'key': model_key,
            'dimensions': config['dimensions'] if config else 'unknown',
            'size_mb': config['size_mb'] if config else 'unknown',
            'description': config['description'] if config else 'Custom model'
        }


# Global instance
embedding_manager = EmbeddingModelManager()


def get_embedding_model():
    """Get the global embedding model instance"""
    return embedding_manager.get_model()


def encode_text(texts, model_key='fast', **kwargs):
    """Convenience function to encode texts"""
    return embedding_manager.encode(texts, model_key=model_key, **kwargs)


def get_model_info():
    """Get information about the current embedding model"""
    return embedding_manager.get_model_info()