import pandas as pd

# Đọc file
df = pd.read_csv("imdb_movies_3000.csv")

# ===== 1. Đếm thống kê =====
total_movies = len(df)
missing_rating = df['rating'].isna().sum()
missing_votes = df['votes'].isna().sum()
missing_poster = df['poster'].isna().sum() + (df['poster'].astype(str).str.strip() == "").sum()

print("Tổng số phim:", total_movies)
print("Thiếu rating:", missing_rating)
print("Thiếu votes:", missing_votes)
print("Thiếu poster:", missing_poster)

# ===== 2. Xóa phim không có rating hoặc votes =====
df_cleaned = df.dropna(subset=['rating', 'votes', 'poster'])

print("\nSố phim sau khi xóa:", len(df_cleaned))
print("Đã xóa:", total_movies - len(df_cleaned), "phim không có rating hoặc votes")

# ===== 3. Lưu file mới =====
#df_cleaned.to_csv("imdb_movies_3000.csv", index=False)
print("\nĐã lưu file cleaned: compilation_movies_cleaned.csv")
