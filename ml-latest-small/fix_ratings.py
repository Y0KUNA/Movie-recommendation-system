import csv
import os
import pandas as pd
import tempfile

# =========================
# 1. Load dữ liệu
# =========================
ratings = pd.read_csv("ml-latest-small/ratings.csv")
links = pd.read_csv("ml-latest-small/links.csv")
imdb_movies = pd.read_csv("web/imdb_movies_3000.csv")

# File paths (adjust if needed)
BASE_DIR = r"d:\Huy\KHDL\Recommend-system"
LINKS = os.path.join(BASE_DIR, "ml-latest-small", "links.csv")
IMDB = os.path.join(BASE_DIR, "imdb_movies_3000.csv")
RATINGS = os.path.join(BASE_DIR, "ml-latest-small", "ratings.csv")


def norm_imdb_id(val):
    # Convert various imdb id representations to integer (e.g. "tt0123456" or "0123456" -> 123456)
    if not val:
        return None
    v = val.strip()
    if v.startswith("tt"):
        v = v[2:]
    v = v.lstrip("0")
    return int(v) if v != "" else 0


def build_links_map(path):
    mapping = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            imdb_raw = r.get("imdbId", "").strip()
            movieid_raw = r.get("movieId", "").strip()
            if imdb_raw == "" or movieid_raw == "":
                continue
            try:
                k = norm_imdb_id(imdb_raw)
                v = int(movieid_raw)
            except Exception:
                continue
            if k is not None:
                mapping[k] = v
    return mapping


def add_id_to_imdb(imdb_path, links_map):
    matched = 0
    total = 0

    # tạo temp file cùng thư mục với imdb_path
    tmp_path = imdb_path + ".tmp"

    with open(imdb_path, newline="", encoding="utf-8") as inp, open(
        tmp_path, "w", newline="", encoding="utf-8"
    ) as out:
        reader = csv.DictReader(inp)
        fieldnames = list(reader.fieldnames or [])
        if "id" not in fieldnames:
            fieldnames.append("id")

        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            total += 1
            imdb_raw = row.get("movie_id", "").strip()
            imdb_key = norm_imdb_id(imdb_raw)

            assigned = ""
            if imdb_key is not None and imdb_key in links_map:
                assigned = str(links_map[imdb_key])
                matched += 1

            row["id"] = assigned
            writer.writerow(row)

    # replace an toàn vì cùng ổ đĩa
    os.replace(tmp_path, imdb_path)

    return total, matched



def filter_ratings(ratings_path, valid_ids):
    kept = 0
    total = 0

    # file tạm cùng ổ đĩa
    tmp_path = ratings_path + ".tmp"

    with open(ratings_path, newline="", encoding="utf-8") as inp, open(
        tmp_path, "w", newline="", encoding="utf-8"
    ) as out:
        reader = csv.DictReader(inp)
        fieldnames = reader.fieldnames or ["userId", "movieId", "rating", "timestamp"]
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            total += 1
            try:
                mid = int(row.get("movieId", "").strip())
            except Exception:
                continue

            if mid in valid_ids:
                writer.writerow(row)
                kept += 1

    # replace an toàn (cùng ổ đĩa)
    os.replace(tmp_path, ratings_path)
    return total, kept



# =========================
# 2. Chuẩn hóa imdbId để join
# =========================
# imdbId trong links là số -> thêm 'tt' phía trước

links["imdbId_str"] = "tt" + links["imdbId"].astype(str)

# =========================
# 3. Thêm cột id (movieId) cho imdb_movies_3000
# =========================
imdb_movies = imdb_movies.merge(
    links[["movieId", "imdbId_str"]],
    left_on="movie_id",
    right_on="imdbId_str",
    how="left",
)

# Đổi tên cột movieId thành id theo yêu cầu
imdb_movies = imdb_movies.rename(columns={"movieId": "id"})

# Xóa cột phụ
imdb_movies = imdb_movies.drop(columns=["imdbId_str"])

# =========================
# 4. Xóa rating của phim không tồn tại trong imdb_movies_3000
# =========================
# Lấy danh sách movieId hợp lệ
valid_movie_ids = set(imdb_movies["id"].dropna().astype(int))

# Lọc ratings
ratings_filtered = ratings[ratings["movieId"].isin(valid_movie_ids)]

# =========================
# 5. (Tùy chọn) Lưu lại file mới
# =========================
imdb_movies.to_csv("imdb_movies_3000_with_id.csv", index=False)
ratings_filtered.to_csv("ratings_filtered.csv", index=False)

# =========================
# 6. Thống kê nhanh
# =========================
print("Số phim trong imdb_movies:", len(imdb_movies))
print("Số phim có map được movieId:", imdb_movies["id"].notna().sum())
print("Ratings ban đầu:", len(ratings))
print("Ratings sau khi lọc:", len(ratings_filtered))

def main():
    print("Loading links.csv ...")
    links_map = build_links_map(LINKS)
    print(f"Links entries mapped: {len(links_map)}")

    print("Updating imdb_movies_3000.csv with 'id' column ...")
    total_imdb, matched = add_id_to_imdb(IMDB, links_map)
    print(f"Processed {total_imdb} imdb rows, matched {matched} to links -> added ids.")

    # Build set of valid movieIds from imdb file (those with non-empty id)
    valid_ids = set()
    with open(IMDB, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            idv = r.get("id", "").strip()
            if idv != "":
                try:
                    valid_ids.add(int(idv))
                except Exception:
                    pass
    print(f"Valid movieIds found in imdb file: {len(valid_ids)}")

    print("Filtering ratings.csv to remove ratings for movies not in imdb list ...")
    total_ratings, kept = filter_ratings(RATINGS, valid_ids)
    removed = total_ratings - kept
    print(f"Ratings total: {total_ratings}, kept: {kept}, removed: {removed}")


if __name__ == "__main__":
    main()
