import os
import time
import requests
import pandas as pd

# prefer environment variable but fall back to provided API key
TMDB_API_KEY = os.environ.get(
    "TMDB_API_KEY",
    "7d24efcd020c10bd5add2a36168b2340"
)
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"

def build_poster_url(poster_path):
    if not poster_path:
        return ""
    return TMDB_IMAGE_BASE + poster_path

def get_movie_details(tmdb_id):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    params = {"api_key": TMDB_API_KEY}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def find_by_external(external_id):
    print("fetching by external id:", external_id)
    url = f"https://api.themoviedb.org/3/find/{external_id}"
    params = {"api_key": TMDB_API_KEY, "external_source": "imdb_id"}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def detect_id_column(df):
    # explicit imdb-like column names
    for col in ("imdb_id", "imdb", "external_id", "externalId"):
        if col in df.columns:
            return col, "imdb"
    # common id columns: try to infer type by sampling values
    for col in ("tmdb_id", "movie_id", "id"):
        if col in df.columns:
            sample = df[col].dropna().astype(str).head(50).tolist()
            # if any sample starts with 'tt' -> imdb ids
            for v in sample:
                if v.strip().lower().startswith("tt"):
                    return col, "imdb"
            # if most values are numeric -> tmdb ids
            numeric_count = sum(1 for v in sample if v.strip().lstrip('-').isdigit())
            if sample and numeric_count >= max(1, len(sample) // 2):
                return col, "tmdb"
            # fallback: treat as imdb if values are non-numeric (common in your dataset)
            return col, "imdb"
    return None, None

def try_call(func, *args, retries=2, delay=0.25, **kwargs):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            time.sleep(delay * (attempt + 1))
    raise last_exc

def fetch_posters(csv_path, save=True):
    """
    Read csv_path, populate a 'poster' column by querying TMDB, and optionally save.
    Returns the DataFrame.
    """
    if not os.path.isfile(csv_path):
        print(f"File not found: {csv_path}")
        return None

    df = pd.read_csv(csv_path, dtype=object)
    id_col, id_type = detect_id_column(df)
    if id_col is None:
        id_col, id_type = "id", "tmdb"
        df["id"] = df.get("id", "")
    else:
        # If detected id column exists but contains mostly empty strings,
        # still proceed — detection already sampled values.
        pass

    # ensure poster column exists
    if "poster" not in df.columns:
        df["poster"] = ""

    for idx, row in df.iterrows():
        existing = row.get("poster", "")
        if pd.notna(existing) and str(existing).strip() != "":
            continue  # keep existing poster

        poster_url = ""
        poster_path = None

        # try TMDB detail if there's a tmdb id
        tmdb_id = None
        if id_type == "tmdb":
            tmdb_id = row.get(id_col, "")
        else:
            # maybe a tmdb id is present in another column
            for c in ("tmdb_id", "id", "movie_id"):
                if c in df.columns and pd.notna(row.get(c, "")) and str(row.get(c, "")).strip() != "":
                    tmdb_id = row.get(c)
                    break

        if tmdb_id and str(tmdb_id).strip() != "":
            # if tmdb_id is numeric, call tmdb /movie/{id}
            tmdb_id_str = str(tmdb_id).strip()
            if tmdb_id_str.lstrip('-').isdigit():
                try:
                    details = try_call(get_movie_details, int(tmdb_id_str))
                    poster_path = details.get("poster_path")
                except Exception:
                    poster_path = None
            else:
                # non-numeric id in a tmdb column — likely an IMDb id; treat as external
                try:
                    ext = tmdb_id_str
                    if not ext.startswith("tt") and ext.isdigit():
                        ext = "tt" + ext
                    data = try_call(find_by_external, ext)
                    movie_results = data.get("movie_results", [])
                    if movie_results:
                        poster_path = movie_results[0].get("poster_path")
                except Exception:
                    poster_path = None

        # fallback to find by external id if imdb-style id available
        if not poster_path and id_type == "imdb":
            external_id_raw = str(row.get(id_col, "")).strip()
            if external_id_raw and external_id_raw.lower() != "nan":
                # prefer 'tt' prefix; try with and without if needed
                tries = []
                if external_id_raw.startswith("tt"):
                    tries = [external_id_raw]
                else:
                    # if purely digits, try prefixing 'tt'
                    if external_id_raw.isdigit():
                        tries = ["tt" + external_id_raw, external_id_raw]
                    else:
                        tries = [external_id_raw, "tt" + external_id_raw]

                for ext_try in tries:
                    try:
                        data = try_call(find_by_external, ext_try)
                        movie_results = data.get("movie_results", [])
                        if movie_results:
                            poster_path = movie_results[0].get("poster_path")
                            break
                    except Exception:
                        poster_path = None

        if poster_path:
            poster_url = build_poster_url(poster_path)
        else:
            poster_url = ""

        df.at[idx, "poster"] = poster_url
        # small delay to be polite to API
        time.sleep(0.08)

    if save:
        df.to_csv(csv_path, index=False)
        print(f"Saved posters to {csv_path}")

    return df

def enrich_from_tmdb(csv_path, save=True, fields_to_fill=None):
    """
    For each row in csv_path, if key fields are missing, call TMDB /find/{imdb_id}
    and fill: movie_name, year (from release_date), poster (full URL), rating (vote_average),
    votes (vote_count), description (overview).
    fields_to_fill: optional set/list of fields to consider filling.
    """
    if not os.path.isfile(csv_path):
        print(f"File not found: {csv_path}")
        return None

    df = pd.read_csv(csv_path, dtype=object)
    id_col, id_type = detect_id_column(df)
    if id_col is None:
        # fallback: look for movie_id column name present in your CSV
        id_col = "movie_id" if "movie_id" in df.columns else "id"
        id_type = "imdb"

    fields_to_fill = set(fields_to_fill or ["movie_name", "year", "poster", "rating", "votes", "description"])

    # ensure columns exist
    for col in ("movie_name", "year", "poster", "rating", "votes", "description"):
        if col not in df.columns:
            df[col] = ""

    updated = 0
    for idx, row in df.iterrows():
        # decide if we need to call API
        need = False
        for f in fields_to_fill:
            val = row.get(f, "")
            if pd.isna(val) or str(val).strip() == "":
                need = True
                break
        if not need:
            continue

        raw_id = str(row.get(id_col, "")).strip()
        if not raw_id or raw_id.lower() == "nan":
            continue

        # ensure imdb id format
        imdb_id = raw_id
        if not imdb_id.startswith("tt") and imdb_id.isdigit():
            imdb_id = "tt" + imdb_id

        try:
            data = try_call(find_by_external, imdb_id)
            movie_results = data.get("movie_results", []) if data else []
            if not movie_results:
                # sometimes TMDB requires the id without 'tt' — try without prefix
                if imdb_id.startswith("tt"):
                    try:
                        data = try_call(find_by_external, imdb_id[2:])
                        movie_results = data.get("movie_results", []) if data else []
                    except Exception:
                        movie_results = []
            if movie_results:
                m = movie_results[0]
                # fill fields if missing
                if "movie_name" in fields_to_fill and (pd.isna(row.get("movie_name", "")) or str(row.get("movie_name", "")).strip() == ""):
                    df.at[idx, "movie_name"] = m.get("title") or m.get("original_title") or df.at[idx, "movie_name"]
                if "year" in fields_to_fill:
                    rd = m.get("release_date") or ""
                    if rd:
                        df.at[idx, "year"] = rd.split("-")[0]
                if "poster" in fields_to_fill:
                    poster_path = m.get("poster_path")
                    if poster_path:
                        df.at[idx, "poster"] = build_poster_url(poster_path)
                if "rating" in fields_to_fill:
                    va = m.get("vote_average")
                    if va is not None:
                        df.at[idx, "rating"] = va
                if "votes" in fields_to_fill:
                    vc = m.get("vote_count")
                    if vc is not None:
                        df.at[idx, "votes"] = vc
                if "description" in fields_to_fill:
                    ov = m.get("overview")
                    if ov:
                        df.at[idx, "description"] = ov
                updated += 1
                print(f"Enriched row {idx} ({imdb_id})")
            else:
                print(f"No TMDB movie_results for {imdb_id}")
        except Exception as e:
            print(f"Error enriching {imdb_id}: {e}")
        time.sleep(0.12)  # polite delay

    if save and updated > 0:
        df.to_csv(csv_path, index=False)
        print(f"Saved enriched data to {csv_path} ({updated} rows updated)")
    else:
        print(f"No rows updated (checked {len(df)} rows).")
    return df

if __name__ == "__main__":
    # default: operate on compilation_movies.csv in same directory
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, "compilation_movies.csv")
    # first ensure posters (existing behavior)
    fetch_posters(target)
    # then enrich missing metadata from TMDB using IMDb ids
    enrich_from_tmdb(target)
