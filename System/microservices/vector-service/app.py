"""
Vector Service API - Flask application
"""
from flask import Flask, jsonify, request
import os
import sys
import logging
import csv
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.config import get_config
from vector_service import VectorRepository, VectorService

app = Flask(__name__)
config = get_config()

# Determine data path
vectors_path = os.getenv(
    'MOVIE_VECTORS_NPZ',
    str(Path(__file__).parent.parent.parent / 'web' / 'movie_vectors.npz')
)

logger.info(f"Looking for vectors at: {vectors_path}")
logger.info(f"Vectors exist: {os.path.exists(vectors_path)}")

def resolve_metadata_csv_path() -> str:
    """
    Resolve metadata CSV path robustly across local/dev and docker layouts.
    Priority:
    1) MOVIE_VECTORS_METADATA_CSV
    2) MOVIES_CSV
    3) Same directory as vectors npz (e.g. /app/data)
    4) Common repository locations
    """
    env_explicit = os.getenv('MOVIE_VECTORS_METADATA_CSV')
    if env_explicit:
        return env_explicit

    env_movies_csv = os.getenv('MOVIES_CSV')
    if env_movies_csv:
        return env_movies_csv

    vectors_dir = str(Path(vectors_path).resolve().parent)
    candidates = [
        os.path.join(vectors_dir, 'imdb_movies_3000.csv'),
        os.path.join(vectors_dir, 'compilation_movies_cleaned.csv'),
        '/app/data/imdb_movies_3000.csv',
        '/app/data/compilation_movies_cleaned.csv',
        str(Path(__file__).resolve().parents[3] / 'web' / 'imdb_movies_3000.csv'),
        str(Path(__file__).resolve().parents[3] / 'web' / 'compilation_movies_cleaned.csv'),
    ]

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    # Last-resort fallback for clearer logs.
    return candidates[0]

metadata_csv_path = resolve_metadata_csv_path()
logger.info(f"Resolved vector metadata CSV path: {metadata_csv_path}")
logger.info(f"Metadata CSV exists: {os.path.exists(metadata_csv_path)}")

def get_movie_ids_from_metadata():
    """Load movie IDs aligned to rows in movie_vectors.npz."""
    if not os.path.exists(metadata_csv_path):
        logger.error(f"Metadata CSV not found: {metadata_csv_path}")
        return []

    movie_ids = []
    try:
        with open(metadata_csv_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                movie_id = (row.get('movie_id') or '').strip()
                if movie_id:
                    movie_ids.append(movie_id)
    except Exception as e:
        logger.error(f"Failed to load movie IDs from metadata CSV: {e}")
        return []

    return movie_ids

# Initialize with empty movie IDs (will be populated on first request)
movie_ids = []
repo = None
service = None

def initialize_service():
    """Initialize vector service with IDs aligned to vector rows."""
    global repo, service, movie_ids
    
    if repo is None:
        movie_ids = get_movie_ids_from_metadata()
        logger.info(f"Loaded {len(movie_ids)} movie IDs from metadata CSV")
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
