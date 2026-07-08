"""
Movie Service API - Flask application
"""
from flask import Flask, jsonify, request
import jwt
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.config import get_config
from movie_service import DuplicateMovieError, MovieRepository, MovieService
from poster_service import fetch_imdb_posters, save_poster_upload
from vector_client import delete_movie_vector, index_movie_vector

app = Flask(__name__)
config = get_config()

JWT_SECRET = os.getenv('JWT_SECRET', 'dev-user-service-secret')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')

repo = MovieRepository()
service = MovieService(repo)


def get_bearer_token():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.lower().startswith('bearer '):
        return auth_header.split(' ', 1)[1].strip()
    return None


def require_admin():
    token = get_bearer_token()
    if not token:
        return None, (jsonify({'error': 'Authorization Bearer token is required'}), 401)

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None, (jsonify({'error': 'token expired'}), 401)
    except jwt.InvalidTokenError:
        return None, (jsonify({'error': 'token invalid'}), 401)

    if payload.get('role') != 'admin':
        return None, (jsonify({'error': 'Admin access required'}), 403)

    return payload, None


def validate_movie_payload(data, require_id: bool = False):
    if not isinstance(data, dict):
        return None, 'JSON object is required'

    movie_id = (data.get('movie_id') or '').strip()
    movie_name = (data.get('movie_name') or '').strip()
    if require_id and not movie_id:
        return None, 'movie_id is required'
    if not movie_name:
        return None, 'movie_name is required'

    payload = dict(data)
    payload['movie_name'] = movie_name
    if movie_id:
        payload['movie_id'] = movie_id
    return payload, None


@app.route('/health', methods=['GET'])
def health_check():
    try:
        db_ok = repo.health_check()
        return jsonify({
            'status': 'healthy' if db_ok else 'degraded',
            'service': 'movie-service',
            'database': 'ok' if db_ok else 'down',
        }), 200 if db_ok else 503
    except Exception as exc:
        logger.error(f'Health check failed: {exc}')
        return jsonify({'status': 'degraded', 'service': 'movie-service', 'database': 'down'}), 503


@app.route('/api/movies', methods=['GET'])
def get_movies():
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
    except Exception as exc:
        logger.error(f'Error in get_movies: {exc}')
        return jsonify({'error': str(exc)}), 500


@app.route('/api/movies', methods=['POST'])
def create_movie():
    _, error_response = require_admin()
    if error_response:
        return error_response

    payload, error = validate_movie_payload(request.get_json(silent=True) or {}, require_id=True)
    if error:
        return jsonify({'error': error}), 400

    try:
        movie = service.create_movie(payload)
        index_movie_vector(movie)
        return jsonify({'message': 'Movie created', 'movie': movie}), 201
    except DuplicateMovieError as exc:
        return jsonify({'error': str(exc)}), 409
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        logger.error(f'Error in create_movie: {exc}')
        return jsonify({'error': str(exc)}), 500


@app.route('/api/movies/<movie_id>', methods=['GET'])
def get_movie_detail(movie_id):
    try:
        movie = service.get_movie_detail(movie_id)
        if movie:
            return jsonify(movie), 200
        return jsonify({'error': 'Movie not found'}), 404
    except Exception as exc:
        logger.error(f'Error in get_movie_detail: {exc}')
        return jsonify({'error': str(exc)}), 500


@app.route('/api/movies/<movie_id>', methods=['PUT'])
def update_movie(movie_id):
    _, error_response = require_admin()
    if error_response:
        return error_response

    payload, error = validate_movie_payload(request.get_json(silent=True) or {}, require_id=False)
    if error:
        return jsonify({'error': error}), 400

    try:
        movie = service.update_movie(movie_id, payload)
        if not movie:
            return jsonify({'error': 'Movie not found'}), 404
        index_movie_vector(movie)
        return jsonify({'message': 'Movie updated', 'movie': movie}), 200
    except Exception as exc:
        logger.error(f'Error in update_movie: {exc}')
        return jsonify({'error': str(exc)}), 500


@app.route('/api/movies/<movie_id>', methods=['DELETE'])
def delete_movie(movie_id):
    _, error_response = require_admin()
    if error_response:
        return error_response

    try:
        deleted = service.delete_movie(movie_id)
        if not deleted:
            return jsonify({'error': 'Movie not found'}), 404
        delete_movie_vector(movie_id)
        return jsonify({'message': 'Movie deleted'}), 200
    except Exception as exc:
        logger.error(f'Error in delete_movie: {exc}')
        return jsonify({'error': str(exc)}), 500


@app.route('/api/movies/<movie_id>/similar', methods=['GET'])
def get_similar_movies(movie_id):
    try:
        top_k = request.args.get('top_k', 10, type=int)
        similar = service.get_recommendations_based_on_similarity(movie_id, top_k)
        return jsonify({'data': similar}), 200
    except Exception as exc:
        logger.error(f'Error in get_similar_movies: {exc}')
        return jsonify({'error': str(exc)}), 500


@app.route('/api/movies/search/by-genre', methods=['GET'])
def search_by_genre():
    try:
        genre = request.args.get('genre', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        result = service.search_movies_paginated(genre, 'genre', page, per_page)
        return jsonify(result), 200
    except Exception as exc:
        logger.error(f'Error in search_by_genre: {exc}')
        return jsonify({'error': str(exc)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config.MOVIE_SERVICE_PORT, debug=config.DEBUG)
