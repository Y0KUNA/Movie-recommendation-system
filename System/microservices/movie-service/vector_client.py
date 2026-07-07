"""Notify vector-service when movie data changes."""
import logging
import os

import requests

logger = logging.getLogger(__name__)

VECTOR_SERVICE_URL = os.getenv('VECTOR_SERVICE_URL', 'http://localhost:5003').rstrip('/')
VECTOR_SYNC_TIMEOUT = int(os.getenv('VECTOR_SYNC_TIMEOUT', 60))


def index_movie_vector(movie: dict) -> None:
    movie_id = (movie.get('movie_id') or '').strip()
    if not movie_id:
        return
    try:
        response = requests.post(
            f'{VECTOR_SERVICE_URL}/api/vectors/movies/{movie_id}/index',
            json=movie,
            timeout=VECTOR_SYNC_TIMEOUT,
        )
        response.raise_for_status()
        logger.info('Indexed vector for movie %s', movie_id)
    except requests.RequestException as exc:
        logger.warning('Failed to index vector for movie %s: %s', movie_id, exc)


def delete_movie_vector(movie_id: str) -> None:
    try:
        response = requests.delete(
            f'{VECTOR_SERVICE_URL}/api/vectors/movies/{movie_id}',
            timeout=15,
        )
        if response.status_code not in {200, 404}:
            response.raise_for_status()
        logger.info('Removed vector for movie %s', movie_id)
    except requests.RequestException as exc:
        logger.warning('Failed to delete vector for movie %s: %s', movie_id, exc)
