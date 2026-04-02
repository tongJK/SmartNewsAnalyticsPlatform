"""
Multimodal embedding service for image and video search.
Handles CLIP embeddings for visual content.
"""

import logging
import numpy as np
from typing import Optional, List, Union
from PIL import Image
import requests
from io import BytesIO

logger = logging.getLogger('multimodal')

try:
    import torch
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logger.warning("CLIP not available. Install: pip install torch transformers")


class MultimodalService:
    """Service for generating embeddings from images and videos"""
    
    _instance = None
    _model = None
    _processor = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._load_model()
    
    def _load_model(self):
        """Load CLIP model for image embeddings"""
        if not CLIP_AVAILABLE:
            logger.error("CLIP not available")
            return
        
        try:
            model_name = "openai/clip-vit-base-patch32"
            self._model = CLIPModel.from_pretrained(model_name)
            self._processor = CLIPProcessor.from_pretrained(model_name)
            logger.info(f"Loaded CLIP model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
    
    def generate_image_embedding(self, image_input: Union[str, Image.Image]) -> Optional[List[float]]:
        """
        Generate embedding for an image
        
        Args:
            image_input: URL string or PIL Image
            
        Returns:
            512-dimensional embedding vector or None if failed
        """
        if not CLIP_AVAILABLE or self._model is None:
            return None
        
        try:
            # Load image
            if isinstance(image_input, str):
                if image_input.startswith(('http://', 'https://')):
                    response = requests.get(image_input, timeout=10)
                    image = Image.open(BytesIO(response.content))
                else:
                    image = Image.open(image_input)
            else:
                image = image_input
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Generate embedding
            inputs = self._processor(images=image, return_tensors="pt")
            
            with torch.no_grad():
                image_features = self._model.get_image_features(**inputs)
                # Normalize the embedding
                embedding = image_features / image_features.norm(dim=-1, keepdim=True)
                
            return embedding.squeeze().tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate image embedding: {e}")
            return None
    
    def generate_text_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate CLIP text embedding for text-to-image search
        
        Args:
            text: Text query
            
        Returns:
            512-dimensional embedding vector or None if failed
        """
        if not CLIP_AVAILABLE or self._model is None:
            return None
        
        try:
            inputs = self._processor(text=[text], return_tensors="pt", padding=True)
            
            with torch.no_grad():
                text_features = self._model.get_text_features(**inputs)
                # Normalize the embedding
                embedding = text_features / text_features.norm(dim=-1, keepdim=True)
                
            return embedding.squeeze().tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate text embedding: {e}")
            return None
    
    def generate_video_embedding(self, video_path: str, frame_count: int = 5) -> Optional[List[float]]:
        """
        Generate embedding for video by sampling frames
        
        Args:
            video_path: Path to video file
            frame_count: Number of frames to sample
            
        Returns:
            512-dimensional embedding vector (average of frame embeddings)
        """
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV not available for video processing")
            return None
        
        if not CLIP_AVAILABLE or self._model is None:
            return None
        
        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if total_frames == 0:
                return None
            
            # Sample frames evenly
            frame_indices = np.linspace(0, total_frames - 1, frame_count, dtype=int)
            embeddings = []
            
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = Image.fromarray(frame_rgb)
                    
                    embedding = self.generate_image_embedding(image)
                    if embedding:
                        embeddings.append(embedding)
            
            cap.release()
            
            if embeddings:
                # Average all frame embeddings
                avg_embedding = np.mean(embeddings, axis=0)
                return avg_embedding.tolist()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate video embedding: {e}")
            return None
    
    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0


# Singleton instance
multimodal_service = MultimodalService()