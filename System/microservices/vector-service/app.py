"""
Vector Service API - Flask application
"""
from flask import Flask, jsonify, request
import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.config import get_config
from common.utils import ServiceClient
from vector_service import VectorRepository, VectorService

app = Flask(__name__)
config = get_config()

# Determine data path
data_dir = Path(__file__).parent.parent.parent / 'web'
vectors_path = str(data_dir / 'movie_vectors.npz')

logger.info(f"Looking for vectors at: {vectors_path}")
logger.info(f"Vectors exist: {os.path.exists(vectors_path)}")

# Initialize services
# We need to get movie IDs from Movie Service
service_client = ServiceClient()

def get_movie_ids():
    """Get movie IDs from Movie Service"""
    try:
        response = service_client.get(f"{config.MOVIE_SERVICE_URL}/api/movies?per_page=10000")
        if response and 'data' in response:
            return [m['movie_id'] for m in response['data']]
    except Exception as e:
        logger.error(f"Failed to get movie IDs: {e}")
    return []

# Initialize with empty movie IDs (will be populated on first request)
movie_ids = []
repo = None
service = None

def initialize_service():
    """Initialize vector service with movie IDs"""
    global repo, service, movie_ids
    
    if repo is None:
        movie_ids = get_movie_ids()
        logger.info(f"Loaded {len(movie_ids)} movie IDs")
        repo = VectorRepository(vectors_path, movie_ids)
        service = VectorService(repo)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'vector-service'}), 200

@app.route('/api/vectors/similar', methods=['GET'])
def get_similar_vectors():
    """Get similar movies by vector similarity"""
    try:
        initialize_service()
        
        movie_id = request.args.get('movie_id', '').strip()
        top_k = request.args.get('top_k', 10, type=int)
        
        if not movie_id:
            return jsonify({'error': 'movie_id is required'}), 400
        
        similar = service.find_similar_movies(movie_id, top_k)
        
        return jsonify({
            'movie_id': movie_id,
            'similar_movies': [
                {'movie_id': mid, 'similarity_score': score}
                for mid, score in similar
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_similar_vectors: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vectors/similarity', methods=['GET'])
def compute_similarity():
    """Compute similarity between two movies"""
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
            'similarity_score': similarity
        }), 200
        
    except Exception as e:
        logger.error(f"Error in compute_similarity: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vectors/batch-similar', methods=['POST'])
def batch_similar():
    """Get similar movies for multiple movie IDs"""
    try:
        initialize_service()
        
        data = request.get_json()
        movie_ids_list = data.get('movie_ids', [])
        top_k = data.get('top_k', 5)
        
        if not movie_ids_list:
            return jsonify({'error': 'movie_ids is required'}), 400
        
        similar_dict = service.batch_find_similar(movie_ids_list, top_k)
        
        result = {
            'results': {
                mid: [{'movie_id': m, 'similarity_score': s} for m, s in similar]
                for mid, similar in similar_dict.items()
            }
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in batch_similar: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    initialize_service()
    app.run(host='0.0.0.0', port=config.VECTOR_SERVICE_PORT, debug=config.DEBUG)
