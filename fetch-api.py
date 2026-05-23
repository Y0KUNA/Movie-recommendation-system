import requests
import json
import time

API_KEY = "6b8fd6d8"
OUTPUT_FILE = "movies_500.json"

# ================================
# 1. Danh sách 500 IMDb ID
# ================================
# 👉 Bạn thay bằng list 500 ID thật của bạn
imdb_ids = [
    "tt0111161", "tt0068646", "tt0468569", "tt0071562", "tt0167260",
    # ...
    # Thêm đủ 500 ID vào đây
]

# Kiểm tra đủ 500 ID
if len(imdb_ids) < 500:
    print("⚠️ Bạn chưa có đủ 500 IMDb ID!")
    print(f"Hiện có {len(imdb_ids)} ID.")
    exit()

# ================================
# 2. Gọi API và gom dữ liệu
# ================================
all_movies = []

for idx, imdb_id in enumerate(imdb_ids):
    url = f"http://www.omdbapi.com/?apikey={API_KEY}&i={imdb_id}"
    print(f"[{idx+1}/500] Fetching {imdb_id} ...")

    try:
        res = requests.get(url)
        data = res.json()
        all_movies.append(data)
    except Exception as e:
        print(f"❌ Error with {imdb_id}: {e}")

    time.sleep(0.2)   # tránh giới hạn rate limit OMDb (5 requests / sec)

# ================================
# 3. Ghi vào file JSON
# ================================
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_movies, f, indent=4, ensure_ascii=False)

print(f"\n🎉 DONE! Đã lưu 500 phim vào {OUTPUT_FILE}\n")
