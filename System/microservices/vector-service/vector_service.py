"""
Vector Service - ChromaDB-backed movie embeddings and similarity search.
"""
import logging
import os
from typing import Dict, List, Optional, Tuple

import chromadb

from embedding_service import build_movie_text, encode_movie, encode_movies

logger = logging.getLogger(__name__)

COLLECTION_NAME = 'movie_vectors'


class ChromaVectorRepository:
    """Store and query movie vectors in ChromaDB."""

    def __init__(self, persist_dir: str):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={'hnsw:space': 'cosine'},
        )
        logger.info(
            'ChromaDB initialized at %s with %s vectors',
            persist_dir,
            self.collection.count(),
        )

    def count(self) -> int:
        return self.collection.count()

    def has_movie(self, movie_id: str) -> bool:
        result = self.collection.get(ids=[movie_id], include=[])
        return bool(result.get('ids'))

    def list_movie_ids(self) -> List[str]:
        result = self.collection.get(include=[])
        return result.get('ids') or []

    def upsert_movie(self, movie: Dict, embedding: Optional[List[float]] = None) -> bool:
        movie_id = (movie.get('movie_id') or '').strip()
        if not movie_id:
            return False

        vector = embedding or encode_movie(movie)
        if vector is None:
            logger.warning('Skipping vector index for movie %s: empty text', movie_id)
            return False

        self.collection.upsert(
            ids=[movie_id],
            embeddings=[vector],
            documents=[build_movie_text(movie)],
            metadatas=[{
                'movie_id': movie_id,
                'movie_name': movie.get('movie_name') or '',
                'year': str(movie.get('year') or ''),
                'genre': movie.get('genre') or '',
            }],
        )
        return True

    def upsert_movies(self, movies: List[Dict]) -> int:
        vectors = encode_movies(movies)
        indexed = 0
        for movie in movies:
            movie_id = (movie.get('movie_id') or '').strip()
            vector = vectors.get(movie_id)
            if vector and self.upsert_movie(movie, vector):
                indexed += 1
        return indexed

    def delete_movie(self, movie_id: str) -> bool:
        if not self.has_movie(movie_id):
            return False
        self.collection.delete(ids=[movie_id])
        return True

    def get_movie_vector(self, movie_id: str) -> Optional[List[float]]:
        result = self.collection.get(ids=[movie_id], include=['embeddings'])
        embeddings = result.get('embeddings') or []
        if not embeddings or embeddings[0] is None:
            return None
        return embeddings[0]

    def find_similar_movies(self, movie_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        vector = self.get_movie_vector(movie_id)
        if vector is None:
            return []

        result = self.collection.query(
            query_embeddings=[vector],
            n_results=min(top_k + 1, max(self.count(), 1)),
            include=['distances'],
        )

        ids = (result.get('ids') or [[]])[0]
        distances = (result.get('distances') or [[]])[0]
        similar = []
        for candidate_id, distance in zip(ids, distances):
            if candidate_id == movie_id:
                continue
            similarity = max(0.0, 1.0 - float(distance))
            similar.append((candidate_id, similarity))
            if len(similar) >= top_k:
                break
        return similar

    def compute_similarity(self, movie_id1: str, movie_id2: str) -> Optional[float]:
        vec1 = self.get_movie_vector(movie_id1)
        vec2 = self.get_movie_vector(movie_id2)
        if vec1 is None or vec2 is None:
            return None

        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        similarity = cosine_similarity(
            np.array(vec1).reshape(1, -1),
            np.array(vec2).reshape(1, -1),
        )[0][0]
        return float(similarity)


class VectorService:
    """Vector indexing and similarity service."""

    def __init__(self, repository: ChromaVectorRepository, movie_service_url: str):
        self.repository = repository
        self.movie_service_url = movie_service_url.rstrip('/')

    def index_movie(self, movie: Dict) -> bool:
        return self.repository.upsert_movie(movie)

    def remove_movie(self, movie_id: str) -> bool:
        return self.repository.delete_movie(movie_id)

    def find_similar_movies(self, movie_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        return self.repository.find_similar_movies(movie_id, top_k)

    def compute_similarity(self, movie_id1: str, movie_id2: str) -> Optional[float]:
        return self.repository.compute_similarity(movie_id1, movie_id2)

    def batch_find_similar(self, movie_ids: List[str], top_k: int = 5) -> Dict[str, List[Tuple[str, float]]]:
        return {
            movie_id: self.find_similar_movies(movie_id, top_k)
            for movie_id in movie_ids
        }

    def fetch_all_movies(self) -> List[Dict]:
        import requests

        movies = []
        page = 1
        per_page = 200
        while True:
            response = requests.get(
                f'{self.movie_service_url}/api/movies',
                params={'page': page, 'per_page': per_page},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            batch = payload.get('data') or payload.get('movies') or []
            movies.extend(batch)
            total_pages = payload.get('total_pages') or 1
            if page >= total_pages:
                break
            page += 1
        return movies

    def fetch_movie(self, movie_id: str) -> Optional[Dict]:
        import requests

        response = requests.get(
            f'{self.movie_service_url}/api/movies/{movie_id}',
            timeout=15,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def sync_missing_movies(self) -> Dict[str, int]:
        movies = self.fetch_all_movies()
        existing_ids = set(self.repository.list_movie_ids())
        missing_movies = [
            movie for movie in movies
            if (movie.get('movie_id') or '').strip() not in existing_ids
        ]
        indexed = self.repository.upsert_movies(missing_movies) if missing_movies else 0
        return {
            'total_movies': len(movies),
            'existing_vectors': len(existing_ids),
            'indexed': indexed,
            'collection_size': self.repository.count(),
        }

    def reindex_movie(self, movie_id: str, movie: Optional[Dict] = None) -> bool:
        payload = movie or self.fetch_movie(movie_id)
        if not payload:
            return False
        payload['movie_id'] = movie_id
        return self.index_movie(payload)
