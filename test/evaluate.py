# evaluate.py
# Đánh giá recommender.py bằng RMSE, MAE, Precision@K, Recall@K

import pandas as pd
import logging
import sys
import numpy as np
from collections import defaultdict
from sklearn.model_selection import train_test_split
from recommender import Recommender

# =========================
# Logging setup
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# =========================
# 1. Load ratings & split
# =========================
log.info('Loading ratings.csv')
ratings = pd.read_csv("test/ratings.csv")
log.info(f"Total ratings loaded: {len(ratings)}")
RATING_THRESHOLD = 3.5

train_rows = []
test_rows = []

for uid, g in ratings.groupby("userId"):
    if len(g) < 5:
        continue
    train, test = train_test_split(g, test_size=0.2, random_state=42)
    train_rows.append(train)
    test_rows.append(test)

train_df = pd.concat(train_rows)
test_df = pd.concat(test_rows)
log.info(f"Train size: {len(train_df)}, Test size: {len(test_df)}")
test_df = pd.concat(test_rows)

# =====================================
# 2. Fake get_movies() cho recommender
# =====================================
def get_movies_from_ratings(df):
    movies = {}
    for _, r in df.iterrows():
        mid = str(r.movieId)
        if mid not in movies:
            movies[mid] = {
                "movie_id": mid,
                "movie_name": f"Movie {mid}",
                "genre": "",
                "director": "",
                "star": "",
                "description": "",
                "rating": r.rating
            }
    return list(movies.values())

movies = get_movies_from_ratings(ratings)
log.info(f"Movies generated: {len(movies)}")

# =========================
# 3. Khởi tạo recommender
# =========================
log.info('Initializing recommender')
rec = Recommender(
    get_movies_func=lambda: movies,
    interactions_file=None  , # hoặc persist=False
    persist=False
)


# feed train interactions
log.info('Feeding training interactions into recommender')
for i, (_, r) in enumerate(train_df.iterrows(), start=1):
    if i % 1000 == 0:
        log.info(f"Processed {i}/{len(train_df)} interactions")

    rec.record_interaction(
        user_id=str(r.userId),
        movie_id=str(r.movieId),
        action="rate",
        rating=float(r.rating)
    )


# =========================
# 4. RMSE & MAE
# =========================
log.info('Evaluating RMSE & MAE')

def evaluate_rmse_mae(rec, test_df):
    y_true = []
    y_pred = []

    for _, r in test_df.iterrows():
        uid = str(r.userId)
        mid = str(r.movieId)
        true_rating = r.rating

        user_scores = rec.user_item_scores.get(uid, {})
        if mid not in user_scores:
            continue

        pred_rating = user_scores[mid]
        y_true.append(true_rating)
        y_pred.append(pred_rating)

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    mae = np.mean(np.abs(y_true - y_pred))
    return rmse, mae

# =========================
# 5. Precision@K, Recall@K
# =========================
log.info('Evaluating Precision@K & Recall@K')

def evaluate_precision_recall(rec, test_df, k=10, threshold=4.0):
    relevant = defaultdict(set)

    for _, r in test_df.iterrows():
        if r.rating >= threshold:
            relevant[str(r.userId)].add(str(r.movieId))

    precisions = []
    recalls = []

    for user_id, rel_items in relevant.items():
        if not rel_items:
            continue

        recs = rec.get_recommendations_for_user(
            user_id=user_id,
            method="hybrid",
            top_n=k
        )

        rec_items = {
            r["movie"]["movie_id"]
            for r in recs
            if r.get("movie")
        }

        tp = len(rec_items & rel_items)
        precisions.append(tp / k)
        recalls.append(tp / len(rel_items))

    return float(np.mean(precisions)), float(np.mean(recalls))

# =========================
# 6. Run evaluation
# =========================
log.info('Running evaluation')
rmse, mae = evaluate_rmse_mae(rec, test_df)
p, r = evaluate_precision_recall(rec, test_df, k=20)

print("RMSE:", round(rmse, 4))
print("MAE:", round(mae, 4))
print("Precision@20:", round(p, 4))
print("Recall@20:", round(r, 4))
