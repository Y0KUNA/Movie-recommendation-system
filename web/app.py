from flask import Flask, render_template, jsonify, request
import json
import os
import sys
import math
from collections import Counter, defaultdict
import re
import jwt

sys.path.insert(0, os.path.dirname(__file__))
from movie_db import MovieDatabase

app = Flask(__name__)

JWT_SECRET = os.getenv('JWT_SECRET', 'dev-user-service-secret')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')

movie_db = MovieDatabase()
movies_data = None
content_vectors_cache = None


def invalidate_movie_cache():
    global movies_data, content_vectors_cache
    movies_data = None
    content_vectors_cache = None


def get_movies():
    global movies_data
    if movies_data is None:
        movies_data = movie_db.get_all_movies()
        print('Loaded movies:', len(movies_data))
    return movies_data


def get_bearer_token():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.lower().startswith('bearer '):
        return auth_header.split(' ', 1)[1].strip()
    return None


def require_admin():
    token = get_bearer_token()
    if not token:
        return jsonify({'error': 'Authorization Bearer token is required'}), 401
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'token invalid'}), 401
    if payload.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    return None

def _tokens_for_movie(m):
    parts = []
    for k in ('movie_name', 'genre', 'director', 'star', 'description'):
        parts.append((m.get(k) or '').lower())
    text = ' '.join(parts)
    return re.findall(r'\b[a-z0-9]{3,}\b', text)

def _build_content_vectors(movies):
    vectors = {}
    for m in movies:
        mid = m.get('movie_id')
        if mid:
            vectors[mid] = Counter(_tokens_for_movie(m))
    return vectors

def _get_content_vectors():
    global content_vectors_cache
    if content_vectors_cache is None:
        content_vectors_cache = _build_content_vectors(get_movies())
    return content_vectors_cache

def _cosine_sim_counts(c1, c2):
    if not c1 or not c2:
        return 0.0
    dot = sum(v * c2[t] for t, v in c1.items() if t in c2)
    norm1 = math.sqrt(sum(v * v for v in c1.values()))
    norm2 = math.sqrt(sum(v * v for v in c2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def get_similar_movies(movie_id, top_n=10):
    movies = get_movies()
    id_to_movie = {m['movie_id']: m for m in movies}
    vectors = _get_content_vectors()
    vi = vectors.get(movie_id)
    if not vi:
        return []
    sims = []
    for other_id, vj in vectors.items():
        if other_id == movie_id:
            continue
        s = _cosine_sim_counts(vi, vj)
        if s > 0:
            sims.append((other_id, s))
    sims.sort(key=lambda x: x[1], reverse=True)
    results = []
    for other_id, score in sims[:top_n]:
        m = id_to_movie.get(other_id)
        if not m:
            continue
        results.append({
            'movie_id': m['movie_id'],
            'movie_name': m.get('movie_name'),
            'year': m.get('year'),
            'rating': m.get('rating'),
            'genre': m.get('genre'),
            'poster': m.get('poster'),
            'score': round(float(score), 4),
        })
    return results

def _parse_rating(r):
    try:
        return float(r) if r else 0
    except (TypeError, ValueError):
        return 0

def _enrich_similar(movie_id, top_n):
    all_movies = get_movies()
    source = next((m for m in all_movies if m.get('movie_id') == movie_id), None)
    if not source:
        return None, []
    return source, get_similar_movies(movie_id, top_n)

API_GATEWAY_URL = os.getenv('API_GATEWAY_URL', 'http://localhost:5000')

@app.route('/')
def index():
    return render_template('index.html', api_gateway_url=API_GATEWAY_URL)

@app.route('/movies/<movie_id>')
def movie_page(movie_id):
    return render_template('index.html', api_gateway_url=API_GATEWAY_URL)

@app.route('/api/movies')
def get_movies_api():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').lower()
    field = request.args.get('field', 'movie_name').lower()  # new

    all_movies = get_movies()

    # --- Convert rating sang float ---
    def parse_rating(r):
        try:
            return float(r)
        except:
            return -1  # rating lỗi/None sẽ nằm cuối danh sách

    # --- Sắp xếp giảm dần theo rating ---
    all_movies_sorted = sorted(all_movies, key=lambda m: parse_rating(m.get('rating')), reverse=True)

    # --- Lọc theo từ khóa và trường được chọn ---
    if search:
        if field == 'movie_name':
            filtered_movies = [m for m in all_movies_sorted if search in (m.get('movie_name') or '').lower()]
        elif field == 'genre':
            filtered_movies = [m for m in all_movies_sorted if search in (m.get('genre') or '').lower()]
        elif field == 'director':
            filtered_movies = [m for m in all_movies_sorted if search in (m.get('director') or '').lower()]
        elif field == 'star':
            filtered_movies = [m for m in all_movies_sorted if search in (m.get('star') or '').lower()]
        else:
            # fallback: search across main fields (previous behavior)
            filtered_movies = [
                m for m in all_movies_sorted
                if search in (m.get('movie_name') or '').lower() or
                   search in (m.get('genre') or '').lower() or
                   search in (m.get('director') or '').lower()
            ]
    else:
        filtered_movies = all_movies_sorted

    # --- Phân trang ---
    total = len(filtered_movies)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_movies = filtered_movies[start:end]

    return jsonify({
        'movies': paginated_movies,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })


@app.route('/api/movies', methods=['POST'])
def create_movie_api():
    error_response = require_admin()
    if error_response:
        return error_response

    data = request.get_json(silent=True) or {}
    try:
        movie = movie_db.create_movie(data)
        invalidate_movie_cache()
        return jsonify({'message': 'Movie created', 'movie': movie}), 201
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/api/movies/<movie_id>', methods=['PUT'])
def update_movie_api(movie_id):
    error_response = require_admin()
    if error_response:
        return error_response

    data = request.get_json(silent=True) or {}
    movie = movie_db.update_movie(movie_id, data)
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404
    invalidate_movie_cache()
    return jsonify({'message': 'Movie updated', 'movie': movie}), 200


@app.route('/api/movies/<movie_id>', methods=['DELETE'])
def delete_movie_api(movie_id):
    error_response = require_admin()
    if error_response:
        return error_response

    if not movie_db.delete_movie(movie_id):
        return jsonify({'error': 'Movie not found'}), 404
    invalidate_movie_cache()
    return jsonify({'message': 'Movie deleted'}), 200


@app.route('/api/movies/<movie_id>')
def get_movie_detail(movie_id):
    all_movies = get_movies()
    movie = next((m for m in all_movies if m.get('movie_id') == movie_id), None)
    
    if movie:
        return jsonify(movie)
    else:
        return jsonify({'error': 'Movie not found'}), 404

@app.route('/api/movies/<movie_id>/similar')
def get_similar_movies_api(movie_id):
    top_n = request.args.get('top_n', 10, type=int)
    source, recommendations = _enrich_similar(movie_id, top_n)
    if not source:
        return jsonify({'error': 'Movie not found'}), 404
    return jsonify({
        'movie_id': movie_id,
        'source_movie': {
            'movie_id': source.get('movie_id'),
            'movie_name': source.get('movie_name'),
        },
        'recommendations': recommendations,
    })

@app.route('/api/movies/similar/featured')
def get_featured_similar():
    top_n = request.args.get('top_n', 8, type=int)
    all_movies = get_movies()
    if not all_movies:
        return jsonify({'source_movie': None, 'recommendations': []})
    featured = max(all_movies, key=lambda m: _parse_rating(m.get('rating')))
    source, recommendations = _enrich_similar(featured['movie_id'], top_n)
    return jsonify({
        'source_movie': {
            'movie_id': source.get('movie_id'),
            'movie_name': source.get('movie_name'),
        },
        'recommendations': recommendations,
    })

# Visualization endpoints
@app.route('/api/visualization/rating-distribution')
def get_rating_distribution():
    all_movies = get_movies()
    ratings = []
    
    for movie in all_movies:
        rating = movie.get('rating')
        if rating:
            try:
                r = float(rating)
                if 0 <= r <= 10:  # Valid rating range
                    ratings.append(r)
            except:
                pass
    
    # Create bins for histogram (0-10, step 0.5)
    bins = [i * 0.5 for i in range(21)]  # 0, 0.5, 1.0, ..., 10.0
    distribution = [0] * 20
    
    for rating in ratings:
        bin_idx = min(int(rating * 2), 19)
        distribution[bin_idx] += 1
    
    labels = [f"{bins[i]:.1f}-{bins[i+1]:.1f}" for i in range(20)]
    
    return jsonify({
        'labels': labels,
        'data': distribution,
        'total': len(ratings)
    })

@app.route('/api/visualization/top-movies')
def get_top_movies():
    all_movies = get_movies()
    
    def parse_rating(r):
        try:
            return float(r) if r else 0
        except:
            return 0
    
    def parse_votes(v):
        try:
            return int(float(v)) if v else 0
        except:
            return 0
    
    # Sort by rating, then by votes
    sorted_movies = sorted(
        all_movies,
        key=lambda m: (parse_rating(m.get('rating')), parse_votes(m.get('votes'))),
        reverse=True
    )
    
    top_movies = []
    for movie in sorted_movies[:20]:  # Top 20
        rating = parse_rating(movie.get('rating'))
        if rating > 0:
            top_movies.append({
                'name': movie.get('movie_name', 'N/A'),
                'rating': rating,
                'votes': parse_votes(movie.get('votes')),
                'year': movie.get('year', 'N/A')
            })
    
    return jsonify(top_movies)

@app.route('/api/visualization/top-genres')
def get_top_genres():
    all_movies = get_movies()
    genre_counter = Counter()
    
    for movie in all_movies:
        genre_str = movie.get('genre', '')
        if genre_str:
            # Split genres by comma and clean
            genres = [g.strip() for g in genre_str.split(',')]
            for genre in genres:
                if genre:
                    genre_counter[genre] += 1
    
    top_genres = [{'genre': genre, 'count': count} 
                  for genre, count in genre_counter.most_common(15)]
    
    return jsonify(top_genres)

@app.route('/api/visualization/heatmap-data')
def get_heatmap_data():
    all_movies = get_movies()
    
    # Create year-rating heatmap data
    year_rating_data = defaultdict(list)
    
    for movie in all_movies:
        year = movie.get('year', '')
        rating = movie.get('rating', '')
        
        if year and rating:
            try:
                y = int(year)
                r = float(rating)
                if 1900 <= y <= 2024 and 0 <= r <= 10:
                    year_rating_data[y].append(r)
            except:
                pass
    
    # Calculate average rating per year
    heatmap_data = []
    for year in sorted(year_rating_data.keys()):
        avg_rating = sum(year_rating_data[year]) / len(year_rating_data[year])
        count = len(year_rating_data[year])
        heatmap_data.append({
            'year': year,
            'avg_rating': round(avg_rating, 2),
            'count': count
        })
    
    return jsonify(heatmap_data)

@app.route('/api/visualization/bar-chart-data')
def get_bar_chart_data():
    all_movies = get_movies()
    
    # Movies per year
    year_counter = Counter()
    
    for movie in all_movies:
        year = movie.get('year', '')
        if year:
            try:
                y = int(year)
                if 1900 <= y <= 2024:
                    year_counter[y] += 1
            except:
                pass
    
    # Get top 20 years by count
    top_years = year_counter.most_common(20)
    top_years.sort(key=lambda x: x[0])  # Sort by year
    
    return jsonify({
        'labels': [str(year) for year, _ in top_years],
        'data': [count for _, count in top_years]
    })

@app.route('/api/visualization/histogram-data')
def get_histogram_data():
    all_movies = get_movies()
    
    # Runtime histogram
    runtimes = []
    
    for movie in all_movies:
        runtime = movie.get('runtime', '')
        if runtime:
            # Extract number from "102 min" format
            match = re.search(r'(\d+)', runtime)
            if match:
                try:
                    minutes = int(match.group(1))
                    if 0 < minutes < 500:  # Reasonable range
                        runtimes.append(minutes)
                except:
                    pass
    
    # Create bins: 0-60, 60-90, 90-120, 120-150, 150-180, 180+
    bins = [0, 60, 90, 120, 150, 180, 500]
    bin_labels = ['0-60', '60-90', '90-120', '120-150', '150-180', '180+']
    distribution = [0] * 6
    
    for runtime in runtimes:
        for i in range(len(bins) - 1):
            if bins[i] <= runtime < bins[i+1]:
                distribution[i] += 1
                break
    
    return jsonify({
        'labels': bin_labels,
        'data': distribution,
        'total': len(runtimes)
    })

@app.route('/api/visualization/wordcloud-data')
def get_wordcloud_data():
    all_movies = get_movies()
    
    # Extract words from movie names and descriptions
    word_counter = Counter()
    
    # Common stop words to exclude
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'now'}
    
    for movie in all_movies:
        # From movie names
        name = movie.get('movie_name', '')
        if name:
            words = re.findall(r'\b[a-zA-Z]{3,}\b', name.lower())
            for word in words:
                if word not in stop_words:
                    word_counter[word] += 1
        
        # From descriptions
        desc = movie.get('description', '')
        if desc:
            words = re.findall(r'\b[a-zA-Z]{4,}\b', desc.lower())
            for word in words:
                if word not in stop_words and len(word) > 3:
                    word_counter[word] += 1
    
    # Get top 50 words
    top_words = [{'text': word, 'value': count} 
                 for word, count in word_counter.most_common(50)]
    
    return jsonify(top_words)

if __name__ == '__main__':
    app.run(debug=True, port=5005)

