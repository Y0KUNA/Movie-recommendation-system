"""
Vector Service - Xử lý embeddings và vector hóa
Service này chịu trách nhiệm:
- Load vector của phim đã được tính toán từ movie_vectors.npz
- Tính toán độ tương tự giữa các phim
- Trả về các phim tương tự dựa trên vector
"""
import numpy as np
from scipy.sparse import load_npz, issparse
from sklearn.metrics.pairwise import cosine_similarity
import os
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class VectorRepository:
    """Repository for vector operations"""
    
    def __init__(self, vectors_npz_path: str, movie_ids: List[str]):
        """
        Initialize vector repository
        
        Args:
            vectors_npz_path: Path to movie_vectors.npz file
            movie_ids: List of movie IDs in order
        """
        self.vectors_npz_path = vectors_npz_path
        self.movie_ids = movie_ids
        self._vectors_cache: Optional[np.ndarray] = None
        self._id_to_index: Dict[str, int] = {mid: idx for idx, mid in enumerate(movie_ids)}
    
    def load_vectors(self) -> Optional[np.ndarray]:
        """Load vectors from NPZ file"""
        if self._vectors_cache is not None:
            return self._vectors_cache
        
        if not os.path.exists(self.vectors_npz_path):
            logger.error(f"Vector file not found: {self.vectors_npz_path}")
            return None
        
        try:
            vectors = load_npz(self.vectors_npz_path)
            
            # Convert sparse to dense if needed
            if issparse(vectors):
                logger.info("Converting sparse matrix to dense...")
                self._vectors_cache = vectors.toarray()
            else:
                self._vectors_cache = vectors
            
            row_count = int(self._vectors_cache.shape[0])
            if len(self.movie_ids) != row_count:
                logger.warning(
                    "Vector row count (%s) does not match movie ID count (%s). "
                    "Truncating to aligned minimum length.",
                    row_count,
                    len(self.movie_ids)
                )
                aligned_len = min(row_count, len(self.movie_ids))
                self._vectors_cache = self._vectors_cache[:aligned_len]
                self.movie_ids = self.movie_ids[:aligned_len]
                self._id_to_index = {mid: idx for idx, mid in enumerate(self.movie_ids)}

            logger.info(f"Loaded vectors with shape: {self._vectors_cache.shape}")
            return self._vectors_cache
            
        except Exception as e:
            logger.error(f"Error loading vectors: {e}")
            return None
    
    def get_movie_vector(self, movie_id: str) -> Optional[np.ndarray]:
        """Get vector for a movie"""
        vectors = self.load_vectors()
        if vectors is None:
            return None
        
        idx = self._id_to_index.get(movie_id)
        if idx is None:
            logger.warning(f"Movie ID not found: {movie_id}")
            return None
        
        return vectors[idx]
    
    def get_vectors(self) -> Optional[np.ndarray]:
        """Get all vectors"""
        return self.load_vectors()

class VectorService:
    """Vector similarity and embedding service"""
    
    def __init__(self, repository: VectorRepository):
        self.repository = repository
    
    def compute_similarity(self, movie_id1: str, movie_id2: str) -> Optional[float]:
        """Compute similarity between two movies"""
        vec1 = self.repository.get_movie_vector(movie_id1)
        vec2 = self.repository.get_movie_vector(movie_id2)
        
        if vec1 is None or vec2 is None:
            return None
        
        # Reshape for 1D vectors
        if len(vec1.shape) == 1:
            vec1 = vec1.reshape(1, -1)
        if len(vec2.shape) == 1:
            vec2 = vec2.reshape(1, -1)
        
        similarity = cosine_similarity(vec1, vec2)[0][0]
        return float(similarity)
    
    def find_similar_movies(self, movie_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Find top-k similar movies using cosine similarity
        
        Returns:
            List of tuples (movie_id, similarity_score)
        """
        vectors = self.repository.load_vectors()
        if vectors is None:
            return []
        
        movie_vec = self.repository.get_movie_vector(movie_id)
        if movie_vec is None:
            return []
        
        # Reshape for 1D vectors
        if len(movie_vec.shape) == 1:
            movie_vec = movie_vec.reshape(1, -1)
        
        # Compute similarity with all movies
        similarities = cosine_similarity(movie_vec, vectors)[0]
        
        # Get top-k (excluding the movie itself)
        similar_indices = np.argsort(-similarities)[:top_k + 1]  # +1 to exclude itself
        
        results = []
        for idx in similar_indices:
            movie_id_result = self.repository.movie_ids[idx]
            if movie_id_result != movie_id:
                results.append((movie_id_result, float(similarities[idx])))
                if len(results) >= top_k:
                    break
        
        return results
    
    def batch_find_similar(self, movie_ids: List[str], top_k: int = 5) -> Dict[str, List[Tuple[str, float]]]:
        """Find similar movies for multiple movie IDs"""
        result = {}
        for movie_id in movie_ids:
            similar = self.find_similar_movies(movie_id, top_k)
            result[movie_id] = similar
        return result
