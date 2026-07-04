"""
Migrate movie data from a CSV file into the movie-db PostgreSQL database.

Default connection values match System/microservices/docker-compose.yml when
the script is run from the host machine.
"""
import argparse
import csv
import os
import sys
import time
from pathlib import Path


DEFAULT_CSV_PATH = Path(__file__).resolve().parents[3] / "web" / "imdb_movies_3000.csv"


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


UPSERT_MOVIE_SQL = """
INSERT INTO movies (
    movie_id,
    movie_name,
    year,
    certificate,
    runtime,
    genre,
    rating,
    description,
    director,
    director_id,
    star,
    star_id,
    votes,
    gross,
    poster,
    source_id
)
VALUES %s
ON CONFLICT (movie_id) DO UPDATE SET
    movie_name = EXCLUDED.movie_name,
    year = EXCLUDED.year,
    certificate = EXCLUDED.certificate,
    runtime = EXCLUDED.runtime,
    genre = EXCLUDED.genre,
    rating = EXCLUDED.rating,
    description = EXCLUDED.description,
    director = EXCLUDED.director,
    director_id = EXCLUDED.director_id,
    star = EXCLUDED.star,
    star_id = EXCLUDED.star_id,
    votes = EXCLUDED.votes,
    gross = EXCLUDED.gross,
    poster = EXCLUDED.poster,
    source_id = EXCLUDED.source_id,
    updated_at = NOW();
"""


def clean_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def parse_int(value):
    value = clean_text(value)
    if value is None:
        return None
    digits = "".join(char for char in value if char.isdigit())
    if not digits:
        return None
    return int(digits)


def parse_year(value):
    value = clean_text(value)
    if value is None:
        return None
    try:
        year = int(float(value))
    except ValueError:
        return None
    return year if 1800 <= year <= 2200 else None


def parse_decimal(value):
    value = clean_text(value)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def movie_from_row(row):
    movie_id = clean_text(row.get("movie_id"))
    movie_name = clean_text(row.get("movie_name"))
    if not movie_id or not movie_name:
        return None

    return (
        movie_id,
        movie_name,
        parse_year(row.get("year")),
        clean_text(row.get("certificate")),
        clean_text(row.get("runtime")),
        clean_text(row.get("genre")),
        parse_decimal(row.get("rating")),
        clean_text(row.get("description")),
        clean_text(row.get("director")),
        clean_text(row.get("director_id")),
        clean_text(row.get("star")),
        clean_text(row.get("star_id")),
        parse_int(row.get("votes")),
        parse_int(row.get("gross(in $)") or row.get("gross")),
        clean_text(row.get("poster")),
        parse_int(row.get("id")),
    )


def iter_movie_rows(csv_path):
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            yield movie_from_row(row)


def connect_with_retry(psycopg2, db_config, attempts=30, delay_seconds=1):
    last_error = None
    for _ in range(attempts):
        try:
            return psycopg2.connect(**db_config)
        except psycopg2.OperationalError as exc:
            last_error = exc
            time.sleep(delay_seconds)
    raise last_error


def migrate(args):
    try:
        import psycopg2
        from psycopg2.extras import execute_values
    except ImportError:
        print("Missing dependency: psycopg2-binary", file=sys.stderr)
        print("Install it with: pip install psycopg2-binary", file=sys.stderr)
        return 1

    csv_path = Path(args.csv).resolve()
    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}", file=sys.stderr)
        return 1

    db_config = {
        "host": args.db_host,
        "port": args.db_port,
        "dbname": args.db_name,
        "user": args.db_user,
        "password": args.db_password,
    }

    imported_count = 0
    skipped_count = 0
    batch = []

    with connect_with_retry(psycopg2, db_config) as conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_MOVIES_TABLE_SQL)
            cursor.execute(CREATE_INDEXES_SQL)
            if args.truncate:
                cursor.execute("TRUNCATE TABLE movies;")
            conn.commit()

        with conn.cursor() as cursor:
            for movie in iter_movie_rows(csv_path):
                if not movie:
                    skipped_count += 1
                    continue
                batch.append(movie)
                if len(batch) >= args.batch_size:
                    execute_values(cursor, UPSERT_MOVIE_SQL, batch)
                    imported_count += len(batch)
                    batch.clear()

            if batch:
                execute_values(cursor, UPSERT_MOVIE_SQL, batch)
                imported_count += len(batch)

        conn.commit()

        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM movies;")
            total_movies = cursor.fetchone()[0]

    print(f"CSV: {csv_path}")
    print(f"Imported or updated: {imported_count}")
    print(f"Skipped invalid rows: {skipped_count}")
    print(f"Total movies in database: {total_movies}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Migrate movie CSV data into PostgreSQL movie-db.")
    parser.add_argument("--csv", default=str(DEFAULT_CSV_PATH), help="Path to the movie CSV file.")
    parser.add_argument("--db-host", default=os.getenv("DB_HOST", "localhost"))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", "5433")))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", "movie_db"))
    parser.add_argument("--db-user", default=os.getenv("DB_USER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("DB_PASSWORD", "postgres"))
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--truncate", action="store_true", help="Delete existing rows before importing.")
    return parser


if __name__ == "__main__":
    raise SystemExit(migrate(build_parser().parse_args()))
