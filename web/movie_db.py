"""PostgreSQL movie access for the Flask monolith."""
import csv
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

CREATE_MOVIES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS movies (
    movie_id TEXT PRIMARY KEY,
    movie_name TEXT NOT NULL,
    year INTEGER,
    certificate TEXT,
    runtime TEXT,
    genre TEXT,
    rating NUMERIC(3, 1),
    description TEXT,
    director TEXT,
    director_id TEXT,
    star TEXT,
    star_id TEXT,
    votes INTEGER,
    gross BIGINT,
    poster TEXT,
    source_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_movies_name ON movies (LOWER(movie_name));
CREATE INDEX IF NOT EXISTS idx_movies_genre ON movies (LOWER(genre));
CREATE INDEX IF NOT EXISTS idx_movies_director ON movies (LOWER(director));
CREATE INDEX IF NOT EXISTS idx_movies_star ON movies (LOWER(star));
CREATE INDEX IF NOT EXISTS idx_movies_rating ON movies (rating DESC);
"""


def clean_field(value):
    if value is None or str(value).strip() == '':
        return None
    return str(value).strip()


def _format_db_value(value):
    if value is None:
        return None
    if isinstance(value, float):
        text = f'{value:.1f}'.rstrip('0').rstrip('.')
        return text or '0'
    return str(value)


def _row_to_dict(row):
    return {
        'movie_id': row['movie_id'],
        'movie_name': row['movie_name'],
        'year': _format_db_value(row.get('year')),
        'certificate': row.get('certificate'),
        'runtime': row.get('runtime'),
        'genre': row.get('genre'),
        'rating': _format_db_value(row.get('rating')),
        'description': row.get('description'),
        'director': row.get('director'),
        'director_id': row.get('director_id'),
        'star': row.get('star'),
        'star_id': row.get('star_id'),
        'votes': _format_db_value(row.get('votes')),
        'gross': _format_db_value(row.get('gross')),
        'poster': row.get('poster'),
    }


class MovieDatabase:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5433)),
            'dbname': os.getenv('DB_NAME', 'movie_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres'),
        }
        self._wait_for_db()
        self._ensure_schema()
        self._seed_from_csv_if_empty()

    def _connect(self):
        return psycopg2.connect(**self.db_config)

    def _wait_for_db(self, attempts=30, delay_seconds=1.0):
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
                cursor.execute(CREATE_MOVIES_TABLE_SQL)
                cursor.execute(CREATE_INDEXES_SQL)
            conn.commit()

    def _seed_from_csv_if_empty(self):
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM movies;')
                if cursor.fetchone()[0] > 0:
                    return

        csv_file = os.path.join(os.path.dirname(__file__), 'imdb_movies_3000.csv')
        if not os.path.exists(csv_file):
            logger.warning('No movies in database and CSV seed file not found')
            return

        imported = 0
        with open(csv_file, 'r', encoding='utf-8-sig', newline='') as csv_file_handle:
            for row in csv.DictReader(csv_file_handle):
                payload = {
                    'movie_id': clean_field(row.get('movie_id')),
                    'movie_name': clean_field(row.get('movie_name')),
                    'year': clean_field(row.get('year')),
                    'certificate': clean_field(row.get('certificate')),
                    'runtime': clean_field(row.get('runtime')),
                    'genre': clean_field(row.get('genre')),
                    'rating': clean_field(row.get('rating')),
                    'description': clean_field(row.get('description')),
                    'director': clean_field(row.get('director')),
                    'director_id': clean_field(row.get('director_id')),
                    'star': clean_field(row.get('star')),
                    'star_id': clean_field(row.get('star_id')),
                    'votes': clean_field(row.get('votes')),
                    'gross': clean_field(row.get('gross(in $)')),
                    'poster': clean_field(row.get('poster')),
                }
                if not payload['movie_id'] or not payload['movie_name']:
                    continue
                try:
                    self.create_movie(payload)
                    imported += 1
                except ValueError:
                    continue
        logger.info('Seeded %s movies from CSV', imported)

    def _build_search_clause(self, search, field):
        if not search:
            return '', []
        if field == 'all':
            pattern = f'%{search.lower()}%'
            clause = """
                AND (
                    LOWER(movie_name) LIKE %s OR
                    LOWER(COALESCE(genre, '')) LIKE %s OR
                    LOWER(COALESCE(director, '')) LIKE %s OR
                    LOWER(COALESCE(star, '')) LIKE %s
                )
            """
            return clause, [pattern, pattern, pattern, pattern]
        column_map = {
            'movie_name': 'movie_name',
            'genre': 'genre',
            'director': 'director',
            'star': 'star',
        }
        column = column_map.get(field, 'movie_name')
        return f' AND LOWER(COALESCE({column}, \'\')) LIKE %s', [f'%{search.lower()}%']

    def get_all_movies(self, search='', field='movie_name'):
        where_clause, params = self._build_search_clause(search, field)
        sql = f"""
            SELECT * FROM movies
            WHERE 1=1{where_clause}
            ORDER BY rating DESC NULLS LAST, movie_name ASC;
        """
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                return [_row_to_dict(row) for row in cursor.fetchall()]

    def get_movie_by_id(self, movie_id):
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute('SELECT * FROM movies WHERE movie_id = %s;', (movie_id,))
                row = cursor.fetchone()
        return _row_to_dict(row) if row else None

    def create_movie(self, data):
        movie_id = clean_field(data.get('movie_id'))
        movie_name = clean_field(data.get('movie_name'))
        if not movie_id or not movie_name:
            raise ValueError('movie_id and movie_name are required')
        sql = """
            INSERT INTO movies (
                movie_id, movie_name, year, certificate, runtime, genre, rating,
                description, director, director_id, star, star_id, votes, gross, poster
            ) VALUES (
                %(movie_id)s, %(movie_name)s, %(year)s, %(certificate)s, %(runtime)s,
                %(genre)s, %(rating)s, %(description)s, %(director)s, %(director_id)s,
                %(star)s, %(star_id)s, %(votes)s, %(gross)s, %(poster)s
            ) RETURNING *;
        """
        values = {key: clean_field(data.get(key)) for key in [
            'movie_id', 'movie_name', 'year', 'certificate', 'runtime', 'genre', 'rating',
            'description', 'director', 'director_id', 'star', 'star_id', 'votes', 'gross', 'poster'
        ]}
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, values)
                row = cursor.fetchone()
            conn.commit()
        return _row_to_dict(row)

    def update_movie(self, movie_id, data):
        existing = self.get_movie_by_id(movie_id)
        if not existing:
            return None
        merged = existing.copy()
        merged.update({key: value for key, value in data.items() if value is not None})
        merged['movie_id'] = movie_id
        sql = """
            UPDATE movies SET
                movie_name = %(movie_name)s, year = %(year)s, certificate = %(certificate)s,
                runtime = %(runtime)s, genre = %(genre)s, rating = %(rating)s,
                description = %(description)s, director = %(director)s, director_id = %(director_id)s,
                star = %(star)s, star_id = %(star_id)s, votes = %(votes)s, gross = %(gross)s,
                poster = %(poster)s, updated_at = NOW()
            WHERE movie_id = %(movie_id)s
            RETURNING *;
        """
        values = {key: clean_field(merged.get(key)) for key in [
            'movie_id', 'movie_name', 'year', 'certificate', 'runtime', 'genre', 'rating',
            'description', 'director', 'director_id', 'star', 'star_id', 'votes', 'gross', 'poster'
        ]}
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, values)
                row = cursor.fetchone()
            conn.commit()
        return _row_to_dict(row) if row else None

    def delete_movie(self, movie_id):
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM movies WHERE movie_id = %s RETURNING movie_id;', (movie_id,))
                deleted = cursor.fetchone()
            conn.commit()
        return deleted is not None
