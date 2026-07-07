"""
Vector Service API - Flask application backed by ChromaDB.
"""
from flask import Flask, jsonify, request
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.config import get_config
from vector_service import ChromaVectorRepository, VectorService

app = Flask(__name__)
config = get_config()

CHROMA_PERSIST_DIR = os.getenv(
    'CHROMA_PERSIST_DIR',
    str(Path(__file__).parent / 'chroma_data'),
)
MOVIE_SERVICE_URL = os.getenv('MOVIE_SERVICE_URL', config.MOVIE_SERVICE_URL)

repo = None
service = None


def initialize_service(force: bool = False):
    global repo, service
    if repo is not None and service is not None and not force:
        return

    repo = ChromaVectorRepository(CHROMA_PERSIST_DIR)
    service = VectorService(repo, MOVIE_SERVICE_URL)

    if repo.count() == 0:
        logger.info('ChromaDB is empty, syncing vectors from movie service...')
        sync_result = None
        for attempt in range(6):
            sync_result = service.sync_missing_movies()
            if sync_result['indexed'] > 0 or sync_result['total_movies'] > 0:
                break
            logger.info('Waiting for movie service data before vector sync (attempt %s)', attempt + 1)
            time.sleep(3)
        logger.info('Initial vector sync completed: %s', sync_result)


@app.route('/health', methods=['GET'])
def health_check():
    try:
        initialize_service()
        return jsonify({
            'status': 'healthy',
            'service': 'vector-service',
            'vector_store': 'chromadb',
            'collection_size': repo.count(),
        }), 200
    except Exception as exc:
        logger.error('Health check failed: %s', exc)
        return jsonify({'status': 'degraded', 'service': 'vector-service', 'error': str(exc)}), 503


@app.route('/api/vectors/similar', methods=['GET'])
def get_similar_vectors():
    try:
        initialize_service()
        movie_id = request.args.get('movie_id', '').strip()
        top_k = request.args.get('top_k', 10, type=int)
        if not movie_id:
            return jsonify({'error': 'movie_id is required'}), 400

        if not repo.has_movie(movie_id):
            service.reindex_movie(movie_id)

        similar = service.find_similar_movies(movie_id, top_k)
        return jsonify({
            'movie_id': movie_id,
            'similar_movies': [
                {'movie_id': mid, 'similarity_score': score}
                for mid, score in similar
            ],
        }), 200
    except Exception as exc:
        logger.error('Error in get_similar_vectors: %s', exc)
        return jsonify({'error': str(exc)}), 500


@app.route('/api/vectors/similarity', methods=['GET'])
def compute_similarity():
    try:
        initialize_service()
        movie_id1 = request.args.get('movie_id1', '').strip()
        movie_id2 = request.args.get('movie_id2', '').strip()
        if not movie_id1 or not movie_id2:
            return jsonify({'error': 'movie_id1 and movie_id2 are required'}), 400

        similarity = service.compute_similarity(movie_id1, movie_id2)
        if similarity is None:
            return jsonify({'error': 'One or both movies not found'}), 404

        return jsonify({
            'movie_id1': movie_id1,
            'movie_id2': movie_id2,
            'similarity_score': similarity,
        }), 200
    except Exception as exc:
        logger.error('Error in compute_similarity: %s', exc)
        return jsonify({'error': str(exc)}), 500


@app.route('/api/vectors/batch-similar', methods=['POST'])
def batch_similar():
    try:
        initialize_service()
        data = request.get_json(silent=True) or {}
        movie_ids_list = data.get('movie_ids', [])
        top_k = data.get('top_k', 5)
        if not movie_ids_list:
            return jsonify({'error': 'movie_ids is required'}), 400

        similar_dict = service.batch_find_similar(movie_ids_list, top_k)
        return jsonify({
            'results': {
                mid: [{'movie_id': movie_id, 'similarity_score': score} for movie_id, score in similar]
                for mid, similar in similar_dict.items()
            }
        }), 200
    except Exception as exc:
        logger.error('Error in batch_similar: %s', exc)
        return jsonify({'error': str(exc)}), 500


@app.route('/api/vectors/movies/<movie_id>/index', methods=['POST'])
def index_movie(movie_id):
    try:
        initialize_service()
        movie = request.get_json(silent=True) or service.fetch_movie(movie_id)
        if not movie:
            return jsonify({'error': 'Movie not found'}), 404

        movie['movie_id'] = movie_id
        indexed = service.index_movie(movie)
        if not indexed:
            return jsonify({'error': 'Unable to build embedding for movie'}), 400

        return jsonify({
            'message': 'Movie vector indexed',
            'movie_id': movie_id,
            'collection_size': repo.count(),
        }), 200
    except Exception as exc:
        logger.error('Error indexing movie %s: %s', movie_id, exc)
        return jsonify({'error': str(exc)}), 500


@app.route('/api/vectors/movies/<movie_id>', methods=['DELETE'])
def delete_movie_vector(movie_id):
    try:
        initialize_service()
        deleted = service.remove_movie(movie_id)
        if not deleted:
            return jsonify({'error': 'Vector not found'}), 404
        return jsonify({'message': 'Movie vector deleted', 'movie_id': movie_id}), 200
    except Exception as exc:
        logger.error('Error deleting vector for %s: %s', movie_id, exc)
        return jsonify({'error': str(exc)}), 500


@app.route('/api/vectors/sync', methods=['POST'])
def sync_vectors():
    try:
        initialize_service()
        result = service.sync_missing_movies()
        return jsonify({'message': 'Vector sync completed', **result}), 200
    except Exception as exc:
        logger.error('Error syncing vectors: %s', exc)
        return jsonify({'error': str(exc)}), 500


if __name__ == '__main__':
    initialize_service()
    app.run(host='0.0.0.0', port=config.VECTOR_SERVICE_PORT, debug=config.DEBUG)
