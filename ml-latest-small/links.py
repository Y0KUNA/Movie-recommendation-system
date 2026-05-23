import time
import requests
import pandas as pd
from tqdm import tqdm

INPUT_FILE = "ml-latest-small\links.csv"
OUTPUT_FILE = "imdb_movies_3000.csv"
API_BASE = "https://api.imdbapi.dev/titles/"
DELAY = 0.5
MAX_MOVIES = 3000

links = pd.read_csv(INPUT_FILE)
links = links[links["imdbId"].notna()].head(MAX_MOVIES)

results = []
def safe_list(obj):
    return obj if isinstance(obj, list) else []

for _, row in tqdm(links.iterrows(), total=len(links)):
    movie_id = row["movieId"]
    imdb_id = f"tt{int(row['imdbId']):07d}"
    url = API_BASE + imdb_id
    print(f"Fetching {imdb_id}...")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            time.sleep(DELAY)
            continue

        data = r.json()

        # ===== BASIC INFO =====
        title = data.get("primaryTitle")
        year = data.get("startYear")

        runtime_sec = data.get("runtimeSeconds")
        runtime = runtime_sec // 60 if isinstance(runtime_sec, int) else None

        genres = safe_list(data.get("genres"))
        genre = ", ".join(genres) if genres else None

        description = data.get("plot")

        poster = (
            data.get("primaryImage", {}).get("url")
            if isinstance(data.get("primaryImage"), dict)
            else None
        )

        # ===== RATING =====
        rating_data = data.get("rating", {})
        rating = rating_data.get("aggregateRating")
        votes = rating_data.get("voteCount")

        # ===== DIRECTOR =====
        director = director_id = None
        directors = safe_list(data.get("directors"))
        if directors:
            director = directors[0].get("displayName")
            director_id = directors[0].get("id")

        # ===== STAR =====
        star = star_id = None
        stars = safe_list(data.get("stars"))
        if stars:
            star = stars[0].get("displayName")
            star_id = stars[0].get("id")

        results.append({
            "movie_id": imdb_id,
            "movie_name": title,
            "year": year,
            "certificate": None,   # API không có
            "runtime": runtime,
            "genre": genre,
            "rating": rating,
            "description": description,
            "director": director,
            "director_id": director_id,
            "star": star,
            "star_id": star_id,
            "votes": votes,
            "poster": poster
        })

    except Exception as e:
        print(f"❌ Error with {imdb_id}: {e}")

    time.sleep(DELAY)

df = pd.DataFrame(results)
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print(f"✅ Saved {len(df)} movies to {OUTPUT_FILE}")
