"""
Movie Service - Quản lý dữ liệu phim từ PostgreSQL
"""
import csv
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.models import Movie
from common.utils import clean_field, parse_rating, calculate_total_pages

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

SEARCH_FIELD_COLUMNS = {
    'movie_name': 'movie_name',
    'genre': 'genre',
    'director': 'director',
    'star': 'star',
    'description': 'description',
}


def _format_db_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float):
        text = f'{value:.1f}'.rstrip('0').rstrip('.')
        return text or '0'
    return str(value)


def _row_to_movie(row: dict) -> Movie:
    return Movie(
        movie_id=row['movie_id'],
        movie_name=row['movie_name'],
        year=_format_db_value(row.get('year')),
        certificate=row.get('certificate'),
        runtime=row.get('runtime'),
        genre=row.get('genre'),
        rating=_format_db_value(row.get('rating')),
        description=row.get('description'),
        director=row.get('director'),
        director_id=row.get('director_id'),
        star=row.get('star'),
        star_id=row.get('star_id'),
        votes=_format_db_value(row.get('votes')),
        gross=_format_db_value(row.get('gross')),
        poster=row.get('poster'),
    )


def _parse_year(value) -> Optional[int]:
    if value is None or value == '':
        return None
    try:
        year = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    return year if 1800 <= year <= 2200 else None


def _parse_int(value) -> Optional[int]:
    if value is None or value == '':
        return None
    if isinstance(value, int):
        return value
    digits = ''.join(char for char in str(value) if char.isdigit())
    return int(digits) if digits else None


def _parse_decimal(value) -> Optional[float]:
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _movie_payload_to_db_values(data: dict) -> dict:
    return {
        'movie_id': clean_field(data.get('movie_id', '')),
        'movie_name': clean_field(data.get('movie_name', '')),
        'year': _parse_year(data.get('year')),
        'certificate': clean_field(data.get('certificate')),
        'runtime': clean_field(data.get('runtime')),
        'genre': clean_field(data.get('genre')),
        'rating': _parse_decimal(data.get('rating')),
        'description': clean_field(data.get('description')),
        'director': clean_field(data.get('director')),
        'director_id': clean_field(data.get('director_id')),
        'star': clean_field(data.get('star')),
        'star_id': clean_field(data.get('star_id')),
        'votes': _parse_int(data.get('votes')),
        'gross': _parse_int(data.get('gross')),
        'poster': clean_field(data.get('poster')),
        'source_id': _parse_int(data.get('source_id') or data.get('id')),
    }


class MovieRepository:
    """PostgreSQL repository for movie data."""

    def __init__(self, db_config: Optional[dict] = None):
        self.db_config = db_config or {
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
                cursor.execute(CREATE_MOVIES_TABLE_SQL)
                cursor.execute(CREATE_INDEXES_SQL)
            conn.commit()

    def _seed_from_csv_if_empty(self):
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM movies;')
                if cursor.fetchone()[0] > 0:
                    return

        csv_path = os.getenv(
            'MOVIES_CSV',
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'web', 'imdb_movies_3000.csv'),
        )
        if not os.path.exists(csv_path):
            logger.warning(f'No movies in database and CSV seed file not found: {csv_path}')
            return

        imported = 0
        with open(csv_path, 'r', encoding='utf-8-sig', newline='') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                payload = _movie_payload_to_db_values(row)
                if not payload['movie_id'] or not payload['movie_name']:
                    continue
                try:
                    self.create_movie(payload)
                    imported += 1
                except DuplicateMovieError:
                    continue

        logger.info(f'Seeded {imported} movies from CSV into database')

    def health_check(self) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1;')
                return cursor.fetchone()[0] == 1

    def _build_search_clause(self, query: str, field: str) -> Tuple[str, List[Any]]:
        if not query:
            return '', []

        if field == 'all':
            pattern = f'%{query.lower()}%'
            clause = """
                AND (
                    LOWER(movie_name) LIKE %s OR
                    LOWER(COALESCE(genre, '')) LIKE %s OR
                    LOWER(COALESCE(director, '')) LIKE %s OR
                    LOWER(COALESCE(star, '')) LIKE %s OR
                    LOWER(COALESCE(description, '')) LIKE %s
                )
            """
            return clause, [pattern, pattern, pattern, pattern, pattern]

        column = SEARCH_FIELD_COLUMNS.get(field, 'movie_name')
        return f' AND LOWER(COALESCE({column}, \'\')) LIKE %s', [f'%{query.lower()}%']

    def count_movies(self, query: str = '', field: str = 'movie_name') -> int:
        where_clause, params = self._build_search_clause(query, field)
        sql = f'SELECT COUNT(*) FROM movies WHERE 1=1{where_clause};'
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()[0]

    def get_movies_page(
        self,
        page: int = 1,
        per_page: int = 20,
        query: str = '',
        field: str = 'movie_name',
    ) -> List[Movie]:
        where_clause, params = self._build_search_clause(query, field)
        offset = (page - 1) * per_page
        sql = f"""
            SELECT *
            FROM movies
            WHERE 1=1{where_clause}
            ORDER BY rating DESC NULLS LAST, movie_name ASC
            LIMIT %s OFFSET %s;
        """
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, [*params, per_page, offset])
                return [_row_to_movie(row) for row in cursor.fetchall()]

    def get_all_movies(self) -> List[Movie]:
        return self.get_movies_page(page=1, per_page=100000)

    def get_movie_by_id(self, movie_id: str) -> Optional[Movie]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute('SELECT * FROM movies WHERE movie_id = %s;', (movie_id,))
                row = cursor.fetchone()
        return _row_to_movie(row) if row else None

    def search_movies(self, query: str, field: str = 'movie_name') -> List[Movie]:
        return self.get_movies_page(page=1, per_page=100000, query=query, field=field)

    def filter_by_genre(self, genre: str) -> List[Movie]:
        return self.search_movies(genre, 'genre')

    def filter_by_director(self, director: str) -> List[Movie]:
        return self.search_movies(director, 'director')

    def sort_by_rating(self, movies: List[Movie], reverse: bool = True) -> List[Movie]:
        return sorted(movies, key=lambda movie: parse_rating(movie.rating), reverse=reverse)

    def create_movie(self, data: dict) -> Movie:
        values = _movie_payload_to_db_values(data)
        if not values['movie_id'] or not values['movie_name']:
            raise ValueError('movie_id and movie_name are required')

        sql = """
            INSERT INTO movies (
                movie_id, movie_name, year, certificate, runtime, genre, rating,
                description, director, director_id, star, star_id, votes, gross,
                poster, source_id
            )
            VALUES (
                %(movie_id)s, %(movie_name)s, %(year)s, %(certificate)s, %(runtime)s,
                %(genre)s, %(rating)s, %(description)s, %(director)s, %(director_id)s,
                %(star)s, %(star_id)s, %(votes)s, %(gross)s, %(poster)s, %(source_id)s
            )
            RETURNING *;
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(sql, values)
                    row = cursor.fetchone()
                conn.commit()
        except psycopg2.errors.UniqueViolation as exc:
            raise DuplicateMovieError(f'Movie ID already exists: {values["movie_id"]}') from exc

        return _row_to_movie(row)

    def update_movie(self, movie_id: str, data: dict) -> Optional[Movie]:
        existing = self.get_movie_by_id(movie_id)
        if not existing:
            return None

        merged = existing.to_dict()
        merged.update({key: value for key, value in data.items() if value is not None})
        merged['movie_id'] = movie_id
        values = _movie_payload_to_db_values(merged)
        values['movie_id'] = movie_id

        sql = """
            UPDATE movies SET
                movie_name = %(movie_name)s,
                year = %(year)s,
                certificate = %(certificate)s,
                runtime = %(runtime)s,
                genre = %(genre)s,
                rating = %(rating)s,
                description = %(description)s,
                director = %(director)s,
                director_id = %(director_id)s,
                star = %(star)s,
                star_id = %(star_id)s,
                votes = %(votes)s,
                gross = %(gross)s,
                poster = %(poster)s,
                source_id = %(source_id)s,
                updated_at = NOW()
            WHERE movie_id = %(movie_id)s
            RETURNING *;
        """
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, values)
                row = cursor.fetchone()
            conn.commit()
        return _row_to_movie(row) if row else None

    def delete_movie(self, movie_id: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM movies WHERE movie_id = %s RETURNING movie_id;', (movie_id,))
                deleted = cursor.fetchone()
            conn.commit()
        return deleted is not None


class DuplicateMovieError(Exception):
    """Raised when creating a movie with an existing ID."""


class MovieService:
    """Movie business logic service."""

    def __init__(self, repository: MovieRepository):
        self.repository = repository

    def get_all_movies_paginated(self, page: int = 1, per_page: int = 20) -> Dict:
        total = self.repository.count_movies()
        movies = self.repository.get_movies_page(page=page, per_page=per_page)
        return {
            'data': [movie.to_dict() for movie in movies],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': calculate_total_pages(total, per_page),
        }

    def search_movies_paginated(
        self,
        query: str,
        field: str = 'movie_name',
        page: int = 1,
        per_page: int = 20,
    ) -> Dict:
        total = self.repository.count_movies(query, field)
        movies = self.repository.get_movies_page(page=page, per_page=per_page, query=query, field=field)
        return {
            'data': [movie.to_dict() for movie in movies],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': calculate_total_pages(total, per_page),
        }

    def get_movie_detail(self, movie_id: str) -> Optional[Dict]:
        movie = self.repository.get_movie_by_id(movie_id)
        return movie.to_dict() if movie else None

    def create_movie(self, data: dict) -> Dict:
        return self.repository.create_movie(data).to_dict()

    def update_movie(self, movie_id: str, data: dict) -> Optional[Dict]:
        movie = self.repository.update_movie(movie_id, data)
        return movie.to_dict() if movie else None

    def delete_movie(self, movie_id: str) -> bool:
        return self.repository.delete_movie(movie_id)

    def get_recommendations_based_on_similarity(self, movie_id: str, top_k: int = 10) -> List[Dict]:
        movies = self.repository.get_all_movies()
        target_movie = self.repository.get_movie_by_id(movie_id)
        if not target_movie:
            return []

        similar_movies = [
            movie
            for movie in movies
            if movie.movie_id != movie_id
            and target_movie.genre
            and movie.genre
            and target_movie.genre.lower() in movie.genre.lower()
        ]
        similar_movies = self.repository.sort_by_rating(similar_movies)
        return [movie.to_dict() for movie in similar_movies[:top_k]]
