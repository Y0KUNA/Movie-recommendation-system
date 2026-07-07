"""Sentence-BERT embedding helpers for movie vectors."""
import logging
import os
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

_model = None


def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        logger.info('Loading embedding model: %s', model_name)
        _model = SentenceTransformer(model_name)
    return _model


def build_movie_text(movie: Dict) -> str:
    parts = [
        movie.get('movie_name') or '',
        movie.get('genre') or '',
        movie.get('director') or '',
        movie.get('star') or '',
        movie.get('description') or '',
    ]
    return ' '.join(part.strip() for part in parts if isinstance(part, str) and part.strip())


def encode_movie(movie: Dict) -> Optional[List[float]]:
    text = build_movie_text(movie)
    if not text:
        return None
    vector = get_embedding_model().encode(text, show_progress_bar=False)
    return vector.astype(np.float32).tolist()


def encode_movies(movies: List[Dict], batch_size: int = 32) -> Dict[str, List[float]]:
    valid_movies = []
    texts = []
    for movie in movies:
        movie_id = (movie.get('movie_id') or '').strip()
        text = build_movie_text(movie)
        if not movie_id or not text:
            continue
        valid_movies.append(movie_id)
        texts.append(text)

    if not texts:
        return {}

    model = get_embedding_model()
    vectors = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
    return {
        movie_id: vector.astype(np.float32).tolist()
        for movie_id, vector in zip(valid_movies, vectors)
    }
