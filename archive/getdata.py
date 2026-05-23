import os
# This file is now a small orchestrator that builds a sampled compilation CSV and then fetches posters.

from compilation_movies import compile_movies
from poster import fetch_posters

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # sample ~200 movies from each genre/movies CSV and combine
    out_csv = compile_movies(base_dir=base_dir, per_file=200, out_name="compilation_movies.csv")
    if out_csv:
        fetch_posters(out_csv)
        print(f"Done. Compiled and fetched posters for: {out_csv}")
    else:
        print("No compilation CSV produced.")

if __name__ == "__main__":
    main()