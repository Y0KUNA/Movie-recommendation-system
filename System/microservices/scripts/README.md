# Migration Scripts

## Import movies CSV into movie-db

Start PostgreSQL:

```powershell
docker compose -f System\microservices\docker-compose.yml up -d movie-db
```

Install the PostgreSQL Python driver if it is not available:

```powershell
pip install psycopg2-binary
```

Run the migration from the repository root:

```powershell
python System\microservices\scripts\migrate_movies_csv_to_db.py
```

By default, the script reads `web\imdb_movies_3000.csv` and connects to
`localhost:5433/movie_db` with `postgres/postgres`, matching
`docker-compose.yml`.

Useful options:

```powershell
python System\microservices\scripts\migrate_movies_csv_to_db.py --truncate
python System\microservices\scripts\migrate_movies_csv_to_db.py --csv web\compilation_movies_cleaned.csv
```
