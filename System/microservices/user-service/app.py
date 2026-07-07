"""
User Service API - registration, login, token verification, and profile lookup.
"""
from datetime import timedelta
import logging
import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
except ImportError:
    pass

from flask import Flask, jsonify, request
import jwt
from pymongo.errors import PyMongoError

from user_service import (
    DuplicateUserError,
    InvalidCredentialsError,
    PREFERENCE_FIELDS,
    UserPreferenceRepository,
    UserRepository,
    UserService,
    utc_now,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

JWT_SECRET = os.getenv('JWT_SECRET', 'dev-user-service-secret')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_EXPIRES_HOURS = int(os.getenv('JWT_EXPIRES_HOURS', 24))
USER_SERVICE_PORT = int(os.getenv('USER_SERVICE_PORT', 5004))

repo = UserRepository()
service = UserService(repo)
preference_repo = UserPreferenceRepository()


def make_token(user):
    now = utc_now()
    payload = {
        'sub': str(user.id),
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'iat': now,
        'exp': now + timedelta(hours=JWT_EXPIRES_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_bearer_token():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.lower().startswith('bearer '):
        return auth_header.split(' ', 1)[1].strip()
    data = request.get_json(silent=True) or {}
    return data.get('token')


def validate_registration(data):
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    full_name = (data.get('full_name') or '').strip() or None

    if not username or not email or not password:
        return None, 'username, email, and password are required'
    if len(username) < 3:
        return None, 'username must be at least 3 characters'
    if len(password) < 6:
        return None, 'password must be at least 6 characters'
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return None, 'email is invalid'

    return {
        'username': username,
        'email': email,
        'password': password,
        'full_name': full_name,
    }, None


def validate_profile_update(data):
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    full_name = (data.get('full_name') or '').strip() or None

    if not username or not email:
        return None, 'username and email are required'
    if len(username) < 3:
        return None, 'username must be at least 3 characters'
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return None, 'email is invalid'

    return {
        'username': username,
        'email': email,
        'full_name': full_name,
    }, None


def get_authenticated_user_id():
    token = get_bearer_token()
    if not token:
        return None, (jsonify({'error': 'Authorization Bearer token is required'}), 401)

    try:
        payload = decode_token(token)
        user_id = int(payload['sub'])
        if not service.get_user(user_id):
            return None, (jsonify({'error': 'user not found'}), 404)
        return user_id, None
    except jwt.ExpiredSignatureError:
        return None, (jsonify({'error': 'token expired'}), 401)
    except jwt.InvalidTokenError:
        return None, (jsonify({'error': 'token invalid'}), 401)


def validate_preference_payload(data):
    if not isinstance(data, dict):
        return None, 'JSON object is required'

    allowed_fields = PREFERENCE_FIELDS | {'name'}
    unknown_fields = sorted(set(data.keys()) - allowed_fields)
    if unknown_fields:
        return None, f"Unknown preference fields: {', '.join(unknown_fields)}"

    payload = {}
    name = data.get('name')
    if 'name' in data:
        if name is not None and not isinstance(name, str):
            return None, 'name must be a string'
        payload['name'] = name.strip() if isinstance(name, str) else None

    list_fields = PREFERENCE_FIELDS - {'watchHistory'}
    for field in list_fields:
        if field in data:
            if not isinstance(data[field], list):
                return None, f'{field} must be a list'
            payload[field] = data[field]

    if 'watchHistory' in data:
        if not isinstance(data['watchHistory'], list):
            return None, 'watchHistory must be a list'
        for item in data['watchHistory']:
            if not isinstance(item, dict):
                return None, 'watchHistory items must be objects'
            if 'movieId' not in item:
                return None, 'watchHistory items must include movieId'
        payload['watchHistory'] = data['watchHistory']

    return payload, None


def parse_movie_id(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return value
    return None


def normalize_string_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(',') if item.strip()]
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return []


def validate_movie_view_payload(data):
    if not isinstance(data, dict):
        return None, 'JSON object is required'

    movie_id = parse_movie_id(data.get('movieId') or data.get('movie_id'))
    if movie_id is None:
        return None, 'movieId is required'

    rating = data.get('rating')
    if rating is not None:
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return None, 'rating must be an integer from 1 to 5'
        if rating < 1 or rating > 5:
            return None, 'rating must be an integer from 1 to 5'

    return {
        'movieId': movie_id,
        'movieName': data.get('movieName') or data.get('movie_name'),
        'watchedAt': data.get('watchedAt'),
        'rating': rating,
        'genres': normalize_string_list(data.get('genres') or data.get('genre')),
        'actors': normalize_string_list(data.get('actors') or data.get('star')),
        'directors': normalize_string_list(data.get('directors') or data.get('director')),
    }, None


def validate_rating_payload(data):
    if not isinstance(data, dict):
        return None, 'JSON object is required'

    movie_id = parse_movie_id(data.get('movieId') or data.get('movie_id'))
    if movie_id is None:
        return None, 'movieId is required'

    try:
        rating = int(data.get('rating'))
    except (TypeError, ValueError):
        return None, 'rating must be an integer from 1 to 5'

    if rating < 1 or rating > 5:
        return None, 'rating must be an integer from 1 to 5'

    return {
        'movieId': movie_id,
        'rating': rating,
        'watchedAt': data.get('watchedAt'),
    }, None


@app.route('/health', methods=['GET'])
def health_check():
    try:
        db_ok = repo.health_check()
        mongo_ok = preference_repo.health_check()
        return jsonify({
            'status': 'healthy' if db_ok and mongo_ok else 'degraded',
            'service': 'user-service',
            'database': 'ok' if db_ok else 'down',
            'preference_database': 'ok' if mongo_ok else 'down',
        }), 200 if db_ok and mongo_ok else 503
    except Exception as exc:
        logger.error(f'Health check failed: {exc}')
        return jsonify({
            'status': 'degraded',
            'service': 'user-service',
            'database': 'down',
            'preference_database': 'down',
        }), 503


@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    payload, error = validate_registration(data)
    if error:
        return jsonify({'error': error}), 400

    try:
        user = service.register(**payload)
        token = make_token(user)
        return jsonify({'user': user.to_dict(), 'token': token, 'token_type': 'Bearer'}), 201
    except DuplicateUserError as exc:
        return jsonify({'error': str(exc)}), 409
    except Exception as exc:
        logger.error(f'Registration failed: {exc}')
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get('identifier') or data.get('email') or data.get('username') or '').strip()
    password = data.get('password') or ''

    if not identifier or not password:
        return jsonify({'error': 'identifier/email/username and password are required'}), 400

    try:
        user = service.login(identifier, password)
        token = make_token(user)
        return jsonify({'user': user.to_dict(), 'token': token, 'token_type': 'Bearer'}), 200
    except InvalidCredentialsError as exc:
        return jsonify({'error': str(exc)}), 401
    except Exception as exc:
        logger.error(f'Login failed: {exc}')
        return jsonify({'error': 'Login failed'}), 500


@app.route('/api/auth/verify', methods=['GET', 'POST'])
def verify_token():
    token = get_bearer_token()
    if not token:
        return jsonify({'valid': False, 'error': 'token is required'}), 400

    try:
        payload = decode_token(token)
        user = service.get_user(int(payload['sub']))
        if not user:
            return jsonify({'valid': False, 'error': 'user not found'}), 404
        return jsonify({'valid': True, 'user': user.to_dict()}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'valid': False, 'error': 'token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'valid': False, 'error': 'token invalid'}), 401


@app.route('/api/users/me', methods=['GET'])
def current_user():
    token = get_bearer_token()
    if not token:
        return jsonify({'error': 'Authorization Bearer token is required'}), 401

    try:
        payload = decode_token(token)
        user = service.get_user(int(payload['sub']))
        if not user:
            return jsonify({'error': 'user not found'}), 404
        return jsonify({'user': user.to_dict()}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'token invalid'}), 401


@app.route('/api/users/me', methods=['PUT'])
def update_current_user():
    token = get_bearer_token()
    if not token:
        return jsonify({'error': 'Authorization Bearer token is required'}), 401

    data = request.get_json(silent=True) or {}
    payload, error = validate_profile_update(data)
    if error:
        return jsonify({'error': error}), 400

    try:
        token_payload = decode_token(token)
        user = service.update_profile(int(token_payload['sub']), **payload)
        if not user:
            return jsonify({'error': 'user not found'}), 404
        return jsonify({'user': user.to_dict()}), 200
    except DuplicateUserError as exc:
        return jsonify({'error': str(exc)}), 409
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'token invalid'}), 401


@app.route('/api/users/me/preferences', methods=['GET'])
def get_current_user_preferences():
    user_id, error_response = get_authenticated_user_id()
    if error_response:
        return error_response

    try:
        return jsonify({'preferences': preference_repo.get_preferences(user_id)}), 200
    except PyMongoError as exc:
        logger.error(f'Failed to fetch preferences: {exc}')
        return jsonify({'error': 'Preference database unavailable'}), 503


@app.route('/api/users/me/preferences', methods=['PUT'])
def update_current_user_preferences():
    user_id, error_response = get_authenticated_user_id()
    if error_response:
        return error_response

    payload, error = validate_preference_payload(request.get_json(silent=True) or {})
    if error:
        return jsonify({'error': error}), 400

    try:
        preferences = preference_repo.upsert_preferences(user_id, payload)
        return jsonify({'preferences': preferences}), 200
    except PyMongoError as exc:
        logger.error(f'Failed to update preferences: {exc}')
        return jsonify({'error': 'Preference database unavailable'}), 503


@app.route('/api/users/me/interactions/watch', methods=['POST'])
def track_current_user_movie_view():
    user_id, error_response = get_authenticated_user_id()
    if error_response:
        return error_response

    payload, error = validate_movie_view_payload(request.get_json(silent=True) or {})
    if error:
        return jsonify({'error': error}), 400

    try:
        preferences = preference_repo.track_movie_view(user_id, payload)
        return jsonify({'message': 'Movie view tracked', 'preferences': preferences}), 200
    except PyMongoError as exc:
        logger.error(f'Failed to track movie view: {exc}')
        return jsonify({'error': 'Preference database unavailable'}), 503


@app.route('/api/users/me/interactions/rating', methods=['POST'])
def rate_current_user_movie():
    user_id, error_response = get_authenticated_user_id()
    if error_response:
        return error_response

    payload, error = validate_rating_payload(request.get_json(silent=True) or {})
    if error:
        return jsonify({'error': error}), 400

    try:
        preferences = preference_repo.rate_movie(
            user_id,
            payload['movieId'],
            payload['rating'],
            payload.get('watchedAt'),
        )
        return jsonify({'message': 'Movie rating saved', 'preferences': preferences}), 200
    except PyMongoError as exc:
        logger.error(f'Failed to save movie rating: {exc}')
        return jsonify({'error': 'Preference database unavailable'}), 503


@app.route('/api/users/<int:user_id>/preferences', methods=['GET'])
def get_user_preferences(user_id):
    try:
        return jsonify({'preferences': preference_repo.get_preferences(user_id)}), 200
    except PyMongoError as exc:
        logger.error(f'Failed to fetch preferences for user {user_id}: {exc}')
        return jsonify({'error': 'Preference database unavailable'}), 503


@app.route('/api/users/<int:user_id>/preferences', methods=['PUT'])
def update_user_preferences(user_id):
    payload, error = validate_preference_payload(request.get_json(silent=True) or {})
    if error:
        return jsonify({'error': error}), 400

    try:
        preferences = preference_repo.upsert_preferences(user_id, payload)
        return jsonify({'preferences': preferences}), 200
    except PyMongoError as exc:
        logger.error(f'Failed to update preferences for user {user_id}: {exc}')
        return jsonify({'error': 'Preference database unavailable'}), 503


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=USER_SERVICE_PORT, debug=os.getenv('DEBUG', 'False').lower() == 'true')
