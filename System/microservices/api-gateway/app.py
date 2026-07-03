"""
API Gateway - Entry point cho toàn bộ microservices
Chịu trách nhiệm:
- Điều hướng request tới các service phù hợp
- Xử lý authentication/authorization
- Rate limiting
- Serve static files và templates
- CORS handling
"""
from flask import Flask, jsonify, request, render_template, send_from_directory
import os
import sys
import logging
import re
from collections import Counter, defaultdict
from functools import wraps
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.config import get_config
from common.utils import ServiceClient

app = Flask(__name__, 
    template_folder=os.getenv(
        'GATEWAY_TEMPLATE_DIR',
        str(Path(__file__).parent.parent.parent / 'web' / 'templates')
    ),
    static_folder=os.getenv(
        'GATEWAY_STATIC_DIR',
        str(Path(__file__).parent.parent.parent / 'web' / 'static')
    ))

config = get_config()

# Service clients
movie_client = ServiceClient()
rec_client = ServiceClient()
vector_client = ServiceClient()

# CORS headers middleware
@app.after_request
def add_cors_headers(response):
    """Add CORS headers to response"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.before_request
def handle_preflight():
    """Handle CORS preflight requests"""
    if request.method == 'OPTIONS':
        return '', 204

# ==================== Static & Templates ====================

@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')

@app.route('/movies/<movie_id>')
def movie_detail_page(movie_id):
    """Serve the single-page app for direct movie-detail URLs"""
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)

# ==================== Service Health ====================

@app.route('/health', methods=['GET'])
def gateway_health():
    """Check gateway health"""
    return jsonify({
        'status': 'healthy',
        'service': 'api-gateway',
        'version': '1.0.0'
    }), 200

@app.route('/health/services', methods=['GET'])
def check_all_services():
    """Check health of all microservices"""
    services = {
        'movie_service': f"{config.MOVIE_SERVICE_URL}/health",
        'recommendation_service': f"{config.RECOMMENDATION_SERVICE_URL}/health",
        'vector_service': f"{config.VECTOR_SERVICE_URL}/health"
    }
    
    results = {}
    for service_name, health_url in services.items():
        try:
            response = movie_client.get(health_url)
            results[service_name] = {
                'status': 'ok' if response else 'down',
                'url': health_url
            }
        except:
            results[service_name] = {
                'status': 'down',
                'url': health_url
            }
    
    return jsonify(results), 200

# ==================== Movie Service Proxy ====================

@app.route('/api/movies', methods=['GET'])
def get_movies():
    """Get movies (proxy to Movie Service)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        field = request.args.get('field', 'movie_name')
        
        params = {
            'page': page,
            'per_page': per_page
        }
        
        if search:
            params['search'] = search
        if field:
            params['field'] = field
        
        url = f"{config.MOVIE_SERVICE_URL}/api/movies"
        response = movie_client.get(url, params=params)
        
        if response:
            # The frontend expects the original monolith shape (`movies`), while
            # the movie service returns `data`. Keep both keys for compatibility.
            if 'data' in response and 'movies' not in response:
                response['movies'] = response['data']
            return jsonify(response), 200
        else:
            return jsonify({'error': 'Failed to fetch movies'}), 503
            
    except Exception as e:
        logger.error(f"Error in get_movies: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/movies/<movie_id>', methods=['GET'])
def get_movie_detail(movie_id):
    """Get movie detail (proxy to Movie Service)"""
    try:
        url = f"{config.MOVIE_SERVICE_URL}/api/movies/{movie_id}"
        response = movie_client.get(url)
        
        if response:
            return jsonify(response), 200
        else:
            return jsonify({'error': 'Movie not found'}), 404
            
    except Exception as e:
        logger.error(f"Error in get_movie_detail: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/movies/search/by-genre', methods=['GET'])
def search_by_genre():
    """Search by genre (proxy to Movie Service)"""
    try:
        genre = request.args.get('genre', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        url = f"{config.MOVIE_SERVICE_URL}/api/movies/search/by-genre"
        params = {'genre': genre, 'page': page, 'per_page': per_page}
        response = movie_client.get(url, params=params)
        
        if response:
            return jsonify(response), 200
        else:
            return jsonify({'error': 'No movies found'}), 404
            
    except Exception as e:
        logger.error(f"Error in search_by_genre: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== Visualization Data ====================

def get_all_movies_for_visualization():
    """Fetch movie data once per visualization request."""
    url = f"{config.MOVIE_SERVICE_URL}/api/movies"
    response = movie_client.get(url, params={'page': 1, 'per_page': 10000})
    if not response:
        return []
    return response.get('data') or response.get('movies') or []

def parse_float(value, default=0.0):
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default

def parse_int(value, default=0):
    try:
        return int(float(value)) if value is not None else default
    except (TypeError, ValueError):
        return default

@app.route('/api/visualization/rating-distribution', methods=['GET'])
def get_rating_distribution():
    ratings = [
        rating for rating in (
            parse_float(movie.get('rating'), None)
            for movie in get_all_movies_for_visualization()
        )
        if rating is not None and 0 <= rating <= 10
    ]

    distribution = [0] * 20
    for rating in ratings:
        distribution[min(int(rating * 2), 19)] += 1

    labels = [f"{i * 0.5:.1f}-{(i + 1) * 0.5:.1f}" for i in range(20)]
    return jsonify({'labels': labels, 'data': distribution, 'total': len(ratings)}), 200

@app.route('/api/visualization/top-movies', methods=['GET'])
def get_top_movies():
    movies = sorted(
        get_all_movies_for_visualization(),
        key=lambda movie: (
            parse_float(movie.get('rating')),
            parse_int(movie.get('votes'))
        ),
        reverse=True
    )

    top_movies = [
        {
            'name': movie.get('movie_name') or 'N/A',
            'rating': parse_float(movie.get('rating')),
            'votes': parse_int(movie.get('votes')),
            'year': movie.get('year') or 'N/A'
        }
        for movie in movies
        if parse_float(movie.get('rating')) > 0
    ][:20]

    return jsonify(top_movies), 200

@app.route('/api/visualization/top-genres', methods=['GET'])
def get_top_genres():
    genre_counter = Counter()

    for movie in get_all_movies_for_visualization():
        for genre in (movie.get('genre') or '').split(','):
            genre = genre.strip()
            if genre:
                genre_counter[genre] += 1

    return jsonify([
        {'genre': genre, 'count': count}
        for genre, count in genre_counter.most_common(15)
    ]), 200

@app.route('/api/visualization/heatmap-data', methods=['GET'])
def get_heatmap_data():
    year_rating_data = defaultdict(list)

    for movie in get_all_movies_for_visualization():
        try:
            year = int(movie.get('year'))
            rating = float(movie.get('rating'))
        except (TypeError, ValueError):
            continue

        if 1900 <= year <= 2026 and 0 <= rating <= 10:
            year_rating_data[year].append(rating)

    return jsonify([
        {
            'year': year,
            'avg_rating': round(sum(ratings) / len(ratings), 2),
            'count': len(ratings)
        }
        for year, ratings in sorted(year_rating_data.items())
    ]), 200

@app.route('/api/visualization/bar-chart-data', methods=['GET'])
def get_bar_chart_data():
    year_counter = Counter()

    for movie in get_all_movies_for_visualization():
        try:
            year = int(movie.get('year'))
        except (TypeError, ValueError):
            continue

        if 1900 <= year <= 2026:
            year_counter[year] += 1

    top_years = year_counter.most_common(20)
    top_years.sort(key=lambda item: item[0])

    return jsonify({
        'labels': [str(year) for year, _ in top_years],
        'data': [count for _, count in top_years]
    }), 200

@app.route('/api/visualization/histogram-data', methods=['GET'])
def get_histogram_data():
    runtimes = []

    for movie in get_all_movies_for_visualization():
        match = re.search(r'(\d+)', str(movie.get('runtime') or ''))
        if not match:
            continue

        minutes = int(match.group(1))
        if 0 < minutes < 500:
            runtimes.append(minutes)

    bins = [0, 60, 90, 120, 150, 180, 500]
    labels = ['0-60', '60-90', '90-120', '120-150', '150-180', '180+']
    distribution = [0] * 6

    for runtime in runtimes:
        for index in range(len(bins) - 1):
            if bins[index] <= runtime < bins[index + 1]:
                distribution[index] += 1
                break

    return jsonify({'labels': labels, 'data': distribution, 'total': len(runtimes)}), 200

@app.route('/api/visualization/wordcloud-data', methods=['GET'])
def get_wordcloud_data():
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
        'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are',
        'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can',
        'this', 'that', 'these', 'those', 'all', 'each', 'every', 'both',
        'few', 'more', 'most', 'other', 'some', 'such', 'only', 'same',
        'than', 'too', 'very', 'just', 'now'
    }
    word_counter = Counter()

    for movie in get_all_movies_for_visualization():
        text = f"{movie.get('movie_name') or ''} {movie.get('description') or ''}"
        for word in re.findall(r'\b[a-zA-Z]{4,}\b', text.lower()):
            if word not in stop_words:
                word_counter[word] += 1

    return jsonify([
        {'text': word, 'value': count}
        for word, count in word_counter.most_common(50)
    ]), 200

# ==================== Recommendation Service Proxy ====================

@app.route('/api/recommendations/similar', methods=['GET'])
def get_similar():
    """Get similar movies (proxy to Recommendation Service)"""
    try:
        movie_id = request.args.get('movie_id', '').strip()
        method = request.args.get('method', 'vector')
        top_k = request.args.get('top_k', 10, type=int)
        
        if not movie_id:
            return jsonify({'error': 'movie_id is required'}), 400
        
        url = f"{config.RECOMMENDATION_SERVICE_URL}/api/recommendations/similar"
        params = {'movie_id': movie_id, 'method': method, 'top_k': top_k}
        response = rec_client.get(url, params=params)
        
        if response:
            return jsonify(response), 200
        else:
            return jsonify({'error': 'Failed to get recommendations'}), 503
            
    except Exception as e:
        logger.error(f"Error in get_similar: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/trending', methods=['GET'])
def get_trending():
    """Get trending movies (proxy to Recommendation Service)"""
    try:
        top_k = request.args.get('top_k', 20, type=int)
        
        url = f"{config.RECOMMENDATION_SERVICE_URL}/api/recommendations/trending"
        params = {'top_k': top_k}
        response = rec_client.get(url, params=params)
        
        if response:
            return jsonify(response), 200
        else:
            return jsonify({'error': 'Failed to get trending'}), 503
            
    except Exception as e:
        logger.error(f"Error in get_trending: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/personalized', methods=['POST'])
def get_personalized():
    """Get personalized recommendations (proxy to Recommendation Service)"""
    try:
        data = request.get_json()
        
        url = f"{config.RECOMMENDATION_SERVICE_URL}/api/recommendations/personalized"
        response = rec_client.post(url, json_data=data)
        
        if response:
            return jsonify(response), 200
        else:
            return jsonify({'error': 'Failed to get recommendations'}), 503
            
    except Exception as e:
        logger.error(f"Error in get_personalized: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== Vector Service Proxy ====================

@app.route('/api/vectors/similar', methods=['GET'])
def get_vector_similar():
    """Get similar by vector (proxy to Vector Service)"""
    try:
        movie_id = request.args.get('movie_id', '').strip()
        top_k = request.args.get('top_k', 10, type=int)
        
        if not movie_id:
            return jsonify({'error': 'movie_id is required'}), 400
        
        url = f"{config.VECTOR_SERVICE_URL}/api/vectors/similar"
        params = {'movie_id': movie_id, 'top_k': top_k}
        response = vector_client.get(url, params=params)
        
        if response:
            return jsonify(response), 200
        else:
            return jsonify({'error': 'Failed to compute similarity'}), 503
            
    except Exception as e:
        logger.error(f"Error in get_vector_similar: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== Error Handling ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config.GATEWAY_PORT, debug=config.DEBUG)
