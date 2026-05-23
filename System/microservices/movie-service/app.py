"""
Movie Service API - Flask application
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
from movie_service import MovieRepository, MovieService

app = Flask(__name__)
config = get_config()

# Determine data path
data_dir = Path(__file__).parent.parent.parent / 'web'
csv_path = str(data_dir / 'imdb_movies_3000.csv')

logger.info(f"Looking for CSV at: {csv_path}")
logger.info(f"CSV exists: {os.path.exists(csv_path)}")

# Initialize services
repo = MovieRepository(csv_path)
service = MovieService(repo)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'movie-service'}), 200

@app.route('/api/movies', methods=['GET'])
def get_movies():
    """Get paginated movies"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        field = request.args.get('field', 'movie_name').lower()
        
        if search:
            result = service.search_movies_paginated(search, field, page, per_page)
        else:
            result = service.get_all_movies_paginated(page, per_page)
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in get_movies: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/movies/<movie_id>', methods=['GET'])
def get_movie_detail(movie_id):
    """Get movie detail by ID"""
    try:
        movie = service.get_movie_detail(movie_id)
        if movie:
            return jsonify(movie), 200
        else:
            return jsonify({'error': 'Movie not found'}), 404
    except Exception as e:
        logger.error(f"Error in get_movie_detail: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/movies/<movie_id>/similar', methods=['GET'])
def get_similar_movies(movie_id):
    """Get similar movies"""
    try:
        top_k = request.args.get('top_k', 10, type=int)
        similar = service.get_recommendations_based_on_similarity(movie_id, top_k)
        return jsonify({'data': similar}), 200
    except Exception as e:
        logger.error(f"Error in get_similar_movies: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/movies/search/by-genre', methods=['GET'])
def search_by_genre():
    """Search movies by genre"""
    try:
        genre = request.args.get('genre', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = service.search_movies_paginated(genre, 'genre', page, per_page)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in search_by_genre: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config.MOVIE_SERVICE_PORT, debug=config.DEBUG)
