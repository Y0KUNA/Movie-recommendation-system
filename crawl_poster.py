import pandas as pd
import requests
import time

# --- CONFIG ---
INPUT_FILE = "compilation_movies_cleaned.csv"
OUTPUT_FILE = "compilation_movies_cleaned.csv"
API_URL = "https://api.imdbapi.dev/titles/{movie_id}/images"
SLEEP_SECONDS = 0.3   # nghỉ 0.3s mỗi lần gọi API

# --- LOAD CSV ---
df = pd.read_csv(INPUT_FILE)

# Đảm bảo cột poster tồn tại
if "poster" not in df.columns:
    df["poster"] = ""

# --- FUNCTION: GET POSTER ---
def get_poster_from_api(movie_id):
    try:
        url = API_URL.format(movie_id=movie_id)
        res = requests.get(url, timeout=10)

        if res.status_code != 200:
            print(f"❌ API lỗi {res.status_code} cho ID {movie_id}")
            return None
        
        data = res.json()

        if "images" not in data or len(data["images"]) == 0:
            print(f"⚠ Không có ảnh cho {movie_id}")
            return None

        posters = [img for img in data["images"] if img.get("type") == "poster"]

        if not posters:
            print(f"⚠ Không tìm thấy poster cho {movie_id}")
            return None

        # Chọn poster có độ phân giải lớn nhất
        posters.sort(key=lambda x: (x.get("width", 0) * x.get("height", 0)), reverse=True)

        best_poster = posters[0]["url"]

        print(f"✔ Lấy poster cho {movie_id}: {best_poster}")

        return best_poster

    except Exception as e:
        print(f"❌ Lỗi khi gọi API cho {movie_id}: {e}")
        return None


# --- MAIN LOOP ---
for i, row in df.iterrows():

    if pd.isna(row["poster"]) or row["poster"] == "":
        movie_id = row["movie_id"]

        print(f"Đang xử lý {i+1}/{len(df)} : {movie_id}")

        poster_url = get_poster_from_api(movie_id)

        if poster_url:
            df.at[i, "poster"] = poster_url

        time.sleep(SLEEP_SECONDS)  # tránh spam API

# --- SAVE ---
df.to_csv(OUTPUT_FILE, index=False)
print("🎉 DONE! Đã lưu vào:", OUTPUT_FILE)
