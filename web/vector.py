import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from scipy.sparse import hstack, csr_matrix
from sentence_transformers import SentenceTransformer
import numpy as np
from scipy.sparse import save_npz
# ============================
# 1. Load dataset
# ============================
df = pd.read_csv("compilation_movies_cleaned.csv")

# Fill NA
df['genre'] = df['genre'].fillna('')
df['description'] = df['description'].fillna('')
df['director'] = df['director'].fillna('')
df['star'] = df['star'].fillna('')

# ============================
# 2. Vectorize GENRE (TF-IDF)
# ============================
print("Vectorizing genre (TF-IDF)...")
tfidf_genre = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
genre_vec = tfidf_genre.fit_transform(df['genre'])

# ============================
# 3. Vectorize DIRECTOR (Count)
# ============================
print("Vectorizing director (CountVectorizer)...")
director_vec = CountVectorizer().fit_transform(df['director'])

# ============================
# 4. Vectorize STAR (Count)
# ============================
print("Vectorizing star (CountVectorizer)...")
star_vec = CountVectorizer().fit_transform(df['star'])

# ============================
# 5. Embeddings for DESCRIPTION
# ============================
print("Encoding description using Sentence-BERT...")
model = SentenceTransformer("all-MiniLM-L6-v2")
desc_embeddings = model.encode(df['description'], show_progress_bar=True)

# Convert dense embedding → sparse (để ghép vào sparse matrix)
desc_sparse = csr_matrix(desc_embeddings)

# ============================
# 6. Combine all vectors
# ============================
print("Combining all feature vectors...")

combined_features = hstack([
    genre_vec,
    director_vec,
    star_vec,
    desc_sparse
]).tocsr()
save_npz("movie_vectors.npz", combined_features)
print("Done!")
print("Final feature matrix shape:", combined_features.shape)
