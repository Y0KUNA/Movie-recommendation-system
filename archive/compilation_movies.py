import os
import pandas as pd
from glob import glob

def detect_id_column(df):
    for col in ("imdb_id", "imdb", "external_id", "externalId"):
        if col in df.columns:
            return col
    for col in ("tmdb_id", "movie_id", "id"):
        if col in df.columns:
            return col
    return None

def load_csv_files(base_dir):
    pattern = os.path.join(base_dir, "*.csv")
    files = sorted(glob(pattern))
    # exclude previously generated compilation file
    files = [f for f in files if os.path.basename(f) not in ("compilation_movies.csv", "combined_movies.csv")]
    return files

def compile_movies(base_dir=None, target=3000, per_file=None, out_name="compilation_movies.csv"):
    """
    Two modes:
    - Sampling mode: if per_file is provided (int), take up to `per_file` rows from each CSV and combine them
      (preserves original columns). This is the '200 movies per genre file' behavior.
    - Original mode: if per_file is None, combine all CSVs, dedupe by id and pick top `target` by votes.
    Writes compilation_movies.csv (or custom out_name) into base_dir and returns its path.
    """
    base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
    files = load_csv_files(base_dir)
    if not files:
        print("No CSV files found to compile.")
        return None

    if per_file is not None:
        # Sampling mode: sample up to per_file rows from each file, keep original columns
        sampled_dfs = []
        for f in files:
            try:
                df = pd.read_csv(f, dtype=object)
            except Exception:
                continue
            if df.empty:
                continue
            n = min(per_file, len(df))
            # if file smaller than per_file, take all; else reproducible sample
            if n == len(df):
                sampled = df.copy()
            else:
                sampled = df.sample(n=n, random_state=42)
            sampled_dfs.append(sampled)
        if not sampled_dfs:
            print("No data sampled from CSVs.")
            return None
        combined = pd.concat(sampled_dfs, ignore_index=True, sort=False)
        # if an id column exists, dedupe by it to avoid exact duplicates across genre files
        id_col = detect_id_column(combined)
        if id_col:
            combined = combined.drop_duplicates(subset=[id_col])
        out_path = os.path.join(base_dir, out_name)
        combined.to_csv(out_path, index=False)
        print(f"Wrote {len(combined)} sampled movies to {out_path} (up to {per_file} per source file).")
        return out_path

    dfs = []
    for f in files:
        try:
            dfs.append(pd.read_csv(f, dtype=object))
        except Exception:
            continue
    if not dfs:
        print("No readable CSVs found.")
        return None

    combined = pd.concat(dfs, ignore_index=True, sort=False)
    id_col = detect_id_column(combined)
    if id_col is None:
        # ensure an 'id' column exists
        combined["id"] = combined.get("id", "")
        id_col = "id"

    # normalize id to string to avoid problems
    combined[id_col] = combined[id_col].astype(str).fillna("")

    # drop rows without id
    combined = combined[combined[id_col] != ""].copy()

    # dedupe by id, keep first occurrence
    combined = combined.drop_duplicates(subset=[id_col])

    # ensure numeric ranking fields exist as Series before coercion
    if "vote_count" in combined.columns:
        combined["vote_count"] = pd.to_numeric(combined["vote_count"], errors="coerce").fillna(0).astype(int)
    else:
        combined["vote_count"] = pd.Series(0, index=combined.index, dtype=int)

    if "vote_average" in combined.columns:
        combined["vote_average"] = pd.to_numeric(combined["vote_average"], errors="coerce").fillna(0.0).astype(float)
    else:
        combined["vote_average"] = pd.Series(0.0, index=combined.index, dtype=float)

    # sort by popularity (vote_count desc, vote_average desc) and pick top target
    combined = combined.sort_values(["vote_count", "vote_average"], ascending=[False, False])
    selected = combined.head(target).copy()

    out_path = os.path.join(base_dir, out_name)
    selected.to_csv(out_path, index=False)
    print(f"Wrote {len(selected)} movies to {out_path}")
    return out_path

# allow running standalone
if __name__ == "__main__":
    # default sampling behavior when run directly: ~200 per file
    compile_movies(per_file=200)
