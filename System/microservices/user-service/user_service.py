"""
User domain logic, PostgreSQL auth repository, and MongoDB preference repository.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import os
import time
from typing import Optional

from pymongo import MongoClient
from pymongo.errors import PyMongoError
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import errors
from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)

PREFERENCE_COLLECTIONS = {
    'user': 'user',
    'favoriteGenres': 'favoriteGenres',
    'favoriteActors': 'favoriteActors',
    'favoriteDirectors': 'favoriteDirectors',
    'watchHistory': 'watchHistory',
    'favoriteMovies': 'favoriteMovies',
    'dislikedMovies': 'dislikedMovies',
}

PREFERENCE_FIELDS = {
    'favoriteGenres',
    'favoriteActors',
    'favoriteDirectors',
    'watchHistory',
    'favoriteMovies',
    'dislikedMovies',
}


@dataclass
class User:
    id: int
    username: str
    email: str
    full_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class DuplicateUserError(Exception):
    """Raised when username or email already exists."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""


class UserRepository:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5434)),
            'dbname': os.getenv('DB_NAME', 'user_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres'),
        }
        self._wait_for_db()
        self._ensure_schema()

    def _connect(self):
        return psycopg2.connect(**self.db_config)

    def _wait_for_db(self, attempts: int = 30, delay_seconds: float = 1.0):
        last_error = None
        for _ in range(attempts):
            try:
                with self._connect():
                    return
            except psycopg2.OperationalError as exc:
                last_error = exc
                time.sleep(delay_seconds)
        raise last_error

    def _ensure_schema(self):
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(80) NOT NULL UNIQUE,
                        email VARCHAR(255) NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        full_name VARCHAR(255),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_users_email
                    ON users (LOWER(email));
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_users_username
                    ON users (LOWER(username));
                    """
                )
            conn.commit()

    def create_user(self, username: str, email: str, password: str, full_name: Optional[str] = None) -> User:
        password_hash = generate_password_hash(password)
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        INSERT INTO users (username, email, password_hash, full_name)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id, username, email, full_name, created_at, updated_at;
                        """,
                        (username, email, password_hash, full_name),
                    )
                    row = cursor.fetchone()
                conn.commit()
        except errors.UniqueViolation as exc:
            raise DuplicateUserError('Username or email already exists') from exc
        return self._row_to_user(row)

    def find_by_id(self, user_id: int) -> Optional[User]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, username, email, full_name, created_at, updated_at
                    FROM users
                    WHERE id = %s;
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
        return self._row_to_user(row) if row else None

    def update_user(self, user_id: int, username: str, email: str, full_name: Optional[str] = None) -> User:
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        UPDATE users
                        SET username = %s,
                            email = %s,
                            full_name = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        RETURNING id, username, email, full_name, created_at, updated_at;
                        """,
                        (username, email, full_name, user_id),
                    )
                    row = cursor.fetchone()
                conn.commit()
        except errors.UniqueViolation as exc:
            raise DuplicateUserError('Username or email already exists') from exc

        return self._row_to_user(row) if row else None

    def find_with_password(self, identifier: str):
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, username, email, password_hash, full_name, created_at, updated_at
                    FROM users
                    WHERE LOWER(email) = LOWER(%s) OR LOWER(username) = LOWER(%s);
                    """,
                    (identifier, identifier),
                )
                return cursor.fetchone()

    def health_check(self) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1;')
                return cursor.fetchone()[0] == 1

    def _row_to_user(self, row) -> User:
        return User(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            full_name=row.get('full_name'),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )


class UserPreferenceRepository:
    def __init__(self):
        self.mongo_uri = os.getenv('MONGO_URI')
        if not self.mongo_uri:
            raise ValueError(
                'MONGO_URI is required. Set it in System/microservices/.env '
                '(see .env.example).'
            )
        self.db_name = os.getenv('MONGO_DB_NAME', 'user-preference-db')
        self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[self.db_name]
        self.collections = {
            key: self.db[collection_name]
            for key, collection_name in PREFERENCE_COLLECTIONS.items()
        }
        self._ensure_indexes()

    def _ensure_indexes(self):
        try:
            for collection in self.collections.values():
                collection.create_index('userId', unique=True)
        except PyMongoError as exc:
            logger.warning(f'MongoDB preference indexes were not created: {exc}')

    def health_check(self) -> bool:
        self.client.admin.command('ping')
        return True

    def get_preferences(self, user_id: int) -> dict:
        preferences = {'userId': user_id}
        user_doc = self._find_one('user', user_id)
        if user_doc and user_doc.get('name') is not None:
            preferences['name'] = user_doc['name']

        for field in PREFERENCE_FIELDS:
            doc = self._find_one(field, user_id)
            preferences[field] = doc.get(field, []) if doc else []

        return preferences

    def upsert_preferences(self, user_id: int, payload: dict) -> dict:
        if 'name' in payload:
            self.collections['user'].update_one(
                {'userId': user_id},
                {'$set': {'userId': user_id, 'name': payload.get('name')}},
                upsert=True,
            )

        for field in PREFERENCE_FIELDS:
            if field in payload:
                self.collections[field].update_one(
                    {'userId': user_id},
                    {'$set': {'userId': user_id, field: payload[field]}},
                    upsert=True,
                )

        return self.get_preferences(user_id)

    def replace_collection_value(self, user_id: int, field: str, value: list) -> dict:
        if field not in PREFERENCE_FIELDS:
            raise ValueError(f'Unknown preference field: {field}')

        self.collections[field].update_one(
            {'userId': user_id},
            {'$set': {'userId': user_id, field: value}},
            upsert=True,
        )
        return self._find_one(field, user_id)

    def track_movie_view(self, user_id: int, movie: dict) -> dict:
        movie_id = movie['movieId']
        watched_at = movie.get('watchedAt') or utc_now().isoformat()
        entry = {
            'movieId': movie_id,
            'watchedAt': watched_at,
            'rating': movie.get('rating'),
        }

        self._upsert_watch_history_entry(user_id, entry)
        self._add_unique_values(user_id, 'favoriteGenres', movie.get('genres', []))
        self._add_unique_values(user_id, 'favoriteActors', movie.get('actors', []))
        self._add_unique_values(user_id, 'favoriteDirectors', movie.get('directors', []))
        return self.get_preferences(user_id)

    def rate_movie(self, user_id: int, movie_id, rating: int, watched_at: Optional[str] = None) -> dict:
        self._upsert_watch_history_entry(
            user_id,
            {
                'movieId': movie_id,
                'watchedAt': watched_at or utc_now().isoformat(),
                'rating': rating,
            },
        )

        if rating >= 4:
            self._add_unique_values(user_id, 'favoriteMovies', [movie_id])
            self._pull_value(user_id, 'dislikedMovies', movie_id)
        elif rating <= 2:
            self._add_unique_values(user_id, 'dislikedMovies', [movie_id])
            self._pull_value(user_id, 'favoriteMovies', movie_id)

        return self.get_preferences(user_id)

    def _upsert_watch_history_entry(self, user_id: int, entry: dict):
        doc = self._find_one('watchHistory', user_id) or {'userId': user_id, 'watchHistory': []}
        history = doc.get('watchHistory') or []
        updated = False

        for index, item in enumerate(history):
            if item.get('movieId') == entry['movieId']:
                merged = {**item, **entry}
                if entry.get('rating') is None and item.get('rating') is not None:
                    merged['rating'] = item['rating']
                history[index] = merged
                updated = True
                break

        if not updated:
            history.append(entry)

        self.collections['watchHistory'].update_one(
            {'userId': user_id},
            {'$set': {'userId': user_id, 'watchHistory': history}},
            upsert=True,
        )

    def _add_unique_values(self, user_id: int, field: str, values: list):
        cleaned_values = [
            value.strip() if isinstance(value, str) else value
            for value in values
            if value is not None and (not isinstance(value, str) or value.strip())
        ]
        if not cleaned_values:
            return

        self.collections[field].update_one(
            {'userId': user_id},
            {'$setOnInsert': {'userId': user_id}, '$addToSet': {field: {'$each': cleaned_values}}},
            upsert=True,
        )

    def _pull_value(self, user_id: int, field: str, value):
        self.collections[field].update_one(
            {'userId': user_id},
            {'$setOnInsert': {'userId': user_id}, '$pull': {field: value}},
            upsert=True,
        )

    def _find_one(self, collection_key: str, user_id: int) -> Optional[dict]:
        doc = self.collections[collection_key].find_one({'userId': user_id}, {'_id': 0})
        return doc


class UserService:
    def __init__(self, repository: UserRepository, preference_repository: Optional['UserPreferenceRepository'] = None):
        self.repository = repository
        self.preference_repository = preference_repository

    def register(self, username: str, email: str, password: str, full_name: Optional[str] = None) -> User:
        user = self.repository.create_user(username, email, password, full_name)

        if self.preference_repository is not None:
            try:
                self.preference_repository.upsert_preferences(
                    user.id,
                    {'name': full_name or username},
                )
            except PyMongoError as exc:
                logger.warning(
                    f'Failed to initialize preferences for user {user.id}: {exc}'
                )

        return user

    def login(self, identifier: str, password: str) -> User:
        row = self.repository.find_with_password(identifier)
        if not row or not check_password_hash(row['password_hash'], password):
            raise InvalidCredentialsError('Invalid username/email or password')
        return self.repository._row_to_user(row)

    def get_user(self, user_id: int) -> Optional[User]:
        return self.repository.find_by_id(user_id)

    def update_profile(self, user_id: int, username: str, email: str, full_name: Optional[str] = None) -> Optional[User]:
        return self.repository.update_user(user_id, username, email, full_name)

def utc_now() -> datetime:
    return datetime.now(timezone.utc)
