import pandas as pd

# Bước 1: Đọc dữ liệu
action_df = pd.read_csv("action_trimmed.csv")           # chứa: id, name (title), year, director...
movies_df = pd.read_csv("movies.csv")                  # chứa: movieId, title, genres
ratings_df = pd.read_csv("ratings.csv")                # chứa: userId, movieId, rating, timestamp

# Bước 2: Chuẩn hóa tên phim (hạ chữ + bỏ khoảng trắng thừa)
def normalize_title(t):
    if isinstance(t, str):
        return t.lower().strip()
    return ""

action_titles = action_df["movie_name"].apply(normalize_title)
movies_df["norm_title"] = movies_df["title"].apply(normalize_title)

# Bước 3: Tìm các phim trong movies.csv xuất hiện trong action_trimmed.csv
matched_movies = movies_df[movies_df["norm_title"].isin(action_titles)]

# Bước 4: Lọc ratings tương ứng
filtered_ratings = ratings_df[ratings_df["movieId"].isin(matched_movies["movieId"])]

# Bước 5: Đếm số phim được giữ lại
num_movies = matched_movies.shape[0]

print("Số phim được giữ lại:", num_movies)

# (Không bắt buộc) — Lưu file mới nếu bạn muốn
matched_movies.to_csv("movies_filtered.csv", index=False)
filtered_ratings.to_csv("ratings_filtered.csv", index=False)
