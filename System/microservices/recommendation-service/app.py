"""
Recommendation Service API - Flask application
"""
from flask import Flask, jsonify, request
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.config import get_config
from recommendation_service import RecommendationService

app = Flask(__name__)
config = get_config()

# Initialize recommendation service
rec_service = RecommendationService(
    config.MOVIE_SERVICE_URL,
    config.VECTOR_SERVICE_URL
)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'recommendation-service'}), 200

@app.route('/api/recommendations/similar', methods=['GET'])
def get_similar_recommendations():
    """Get similar movies for a given movie"""
    try:
        movie_id = request.args.get('movie_id', '').strip()
        method = request.args.get('method', 'vector')  # vector, genre, hybrid
        top_k = request.args.get('top_k', 10, type=int)
        
        if not movie_id:
            return jsonify({'error': 'movie_id is required'}), 400
        
        recommendations = rec_service.get_personalized_recommendations(
            movie_id, method, top_k
        )
        
        return jsonify({
            'movie_id': movie_id,
            'method': method,
            'recommendations': recommendations
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_similar_recommendations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/trending', methods=['GET'])
def get_trending():
    """Get trending movies"""
    try:
        top_k = request.args.get('top_k', 20, type=int)
        
        trending = rec_service.get_trending_recommendations(top_k)
        
        return jsonify({
            'type': 'trending',
            'recommendations': trending
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_trending: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/personalized', methods=['POST'])
def get_personalized():
    """Get personalized recommendations based on user preferences"""
    try:
        data = request.get_json()
        liked_movies = data.get('liked_movies', [])
        top_k = data.get('top_k', 10)
        
        if not liked_movies:
            return jsonify({'error': 'liked_movies list is required'}), 400
        
        recommendations = rec_service.get_recommendations_by_user_preference(
            liked_movies, top_k
        )
        
        return jsonify({
            'type': 'personalized',
            'liked_movies': liked_movies,
            'recommendations': recommendations
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_personalized: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config.RECOMMENDATION_SERVICE_PORT, debug=config.DEBUG)
