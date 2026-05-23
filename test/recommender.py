import os
import json
import time
import math
import threading
import re
from collections import Counter, defaultdict

class Recommender:
    def __init__(self, get_movies_func, interactions_file=None, persist=True):
        self.get_movies = get_movies_func
        self.persist = persist
        self.interactions = []
        base = os.path.dirname(os.path.abspath(__file__))
        self.interactions_file = interactions_file or os.path.join(base, 'interactions.json')
        self._lock = threading.Lock()
        self.user_item_scores = defaultdict(dict)
        self.content_sim_cache = None
        self.collab_sim_cache = None
        self._collab_dirty = True

        self.load_interactions()
        self._compute_content_sim_cache()

    # ----- persistence -----
    def load_interactions(self):
        if os.path.exists(self.interactions_file):
            try:
                with open(self.interactions_file, 'r', encoding='utf-8') as f:
                    self.interactions = json.load(f)
            except Exception:
                self.interactions = []
        else:
            self.interactions = []
        self.user_item_scores.clear()
        for ev in self.interactions:
            uid = ev.get('user_id'); mid = ev.get('movie_id')
            action = ev.get('action'); rating = ev.get('rating')
            score = self._action_score(action, rating)
            if uid and mid:
                self.user_item_scores[uid][mid] = max(self.user_item_scores[uid].get(mid, 0), score)
        self._collab_dirty = True

    def save_interactions(self):
        with self._lock:
            try:
                with open(self.interactions_file, 'w', encoding='utf-8') as f:
                    json.dump(self.interactions, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print("Error saving interactions:", e)
       

    def _action_score(self, action, rating=None):
        if action == 'view':
            return 1.0
        if action == 'like':
            return 3.0
        if action == 'rate':
            try: return float(rating)
            except: return 0.0
        return 0.5

    # ----- content helpers -----
    def _tokens_for_movie(self, m):
        parts = []
        for k in ('movie_name','genre','director','star','description'):
            v = (m.get(k) or '')
            parts.append(v.lower())
        text = ' '.join(parts)
        toks = re.findall(r'\b[a-z0-9]{3,}\b', text)
        return toks

    def _build_content_vectors(self, movies):
        vectors = {}
        for m in movies:
            mid = m.get('movie_id')
            if not mid: continue
            toks = self._tokens_for_movie(m)
            vectors[mid] = Counter(toks)
        return vectors

    def _cosine_sim_counts(self, c1, c2):
        if not c1 or not c2: return 0.0
        dot = 0.0
        for t, v in c1.items():
            if t in c2: dot += v * c2[t]
        norm1 = math.sqrt(sum(v*v for v in c1.values()))
        norm2 = math.sqrt(sum(v*v for v in c2.values()))
        if norm1 == 0 or norm2 == 0: return 0.0
        return dot / (norm1 * norm2)

    def _compute_content_sim_cache(self):
        movies = self.get_movies()
        vectors = self._build_content_vectors(movies)
        self.content_sim_cache = {}
        ids = list(vectors.keys())
        for mid in ids:
            vi = vectors[mid]
            sims = []
            for other in ids:
                if mid == other: continue
                s = self._cosine_sim_counts(vi, vectors[other])
                if s > 0: sims.append((other, s))
            sims.sort(key=lambda x: x[1], reverse=True)
            self.content_sim_cache[mid] = sims
        for m in movies:
            if m.get('movie_id') not in self.content_sim_cache:
                self.content_sim_cache[m.get('movie_id')] = []
        return self.content_sim_cache

    def _compute_collab_sim_cache(self):
        print(">>> Computing content similarity cache...")
        item_user = defaultdict(dict)
        for uid, items in self.user_item_scores.items():
            for mid, score in items.items():
                item_user[mid][uid] = score
        self.collab_sim_cache = {}
        mids = list(item_user.keys())
        for mid in mids:
            vi = item_user[mid]
            norm_i = math.sqrt(sum(v*v for v in vi.values()))
            sims = []
            for other in mids:
                if other == mid: continue
                vj = item_user[other]
                dot = 0.0
                for u, s in vi.items():
                    if u in vj: dot += s * vj[u]
                norm_j = math.sqrt(sum(v*v for v in vj.values()))
                sim = 0.0 if (norm_i == 0 or norm_j == 0) else (dot / (norm_i * norm_j))
                if sim > 0: sims.append((other, sim))
            sims.sort(key=lambda x: x[1], reverse=True)
            self.collab_sim_cache[mid] = sims
        self._collab_dirty = False
        return self.collab_sim_cache

    def _ensure_collab_cache(self):
        if self._collab_dirty or self.collab_sim_cache is None:
            self._compute_collab_sim_cache()

    # ----- interactions -----
    def record_interaction(self, user_id, movie_id, action, rating=None):
        ts = int(time.time())
        ev = {
            'user_id': user_id,
            'movie_id': movie_id,
            'action': action,
            'rating': rating,
            'ts': ts
        }

        self.interactions.append(ev)

        score = self._action_score(action, rating)
        self.user_item_scores[user_id][movie_id] = max(
            self.user_item_scores[user_id].get(movie_id, 0),
            score
        )

        self._collab_dirty = True

        if self.persist:
            self.save_interactions()


    # ----- scoring / recommendations -----
    def _score_candidates_by_content_for_user(self, user_id, exclude_set, top_n):
        if self.content_sim_cache is None: self._compute_content_sim_cache()
        scores = defaultdict(float)
        user_items = self.user_item_scores.get(user_id, {})
        if not user_items: return []
        for mid, uscore in user_items.items():
            for other, sim in self.content_sim_cache.get(mid, []):
                if other in exclude_set: continue
                scores[other] += sim * uscore
        recs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        id_to_movie = {m.get('movie_id'): m for m in self.get_movies()}
        return [{'movie': id_to_movie.get(mid), 'score': score} for mid, score in recs if id_to_movie.get(mid)]

    def _score_candidates_by_collab_for_user(self, user_id, exclude_set, top_n):
        self._ensure_collab_cache()
        scores = defaultdict(float)
        user_items = self.user_item_scores.get(user_id, {})
        if not user_items: return []
        for mid, uscore in user_items.items():
            for other, sim in self.collab_sim_cache.get(mid, []):
                if other in exclude_set: continue
                scores[other] += sim * uscore
        recs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        id_to_movie = {m.get('movie_id'): m for m in self.get_movies()}
        return [{'movie': id_to_movie.get(mid), 'score': score} for mid, score in recs if id_to_movie.get(mid)]

    def get_recommendations_for_user(self, user_id, method='hybrid', top_n=20, seed_movie=None):
        movies = self.get_movies()
        seen = set(self.user_item_scores.get(user_id, {}).keys())
        if seed_movie: seen.add(seed_movie)
        content_recs = self._score_candidates_by_content_for_user(user_id, seen, top_n*2)
        collab_recs = self._score_candidates_by_collab_for_user(user_id, seen, top_n*2)
        final_scores = defaultdict(float)
        for r in content_recs:
            mid = r['movie'].get('movie_id')
            if method in ('content','hybrid'):
                final_scores[mid] += r['score'] * (0.6 if method=='hybrid' else 1.0)
        for r in collab_recs:
            mid = r['movie'].get('movie_id')
            if method in ('collab','hybrid'):
                final_scores[mid] += r['score'] * (0.4 if method=='hybrid' else 1.0)
        if not final_scores:
            def pr(r): 
                try: return float(r) if r else 0
                except: return 0
            sorted_movies = sorted(movies, key=lambda m: pr(m.get('rating')), reverse=True)
            return [{'movie': m, 'score': pr(m.get('rating'))} for m in sorted_movies if m.get('movie_id') not in seen][:top_n]
        id_to_movie = {m.get('movie_id'): m for m in movies}
        sorted_final = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return [{'movie': id_to_movie.get(mid), 'score': score} for mid, score in sorted_final if id_to_movie.get(mid)]

    def get_similar_movies_for(self, movie_id, method='content', top_n=10):
        movies = self.get_movies()
        id_to_movie = {m.get('movie_id'): m for m in movies}
        if method in ('content','hybrid'):
            if self.content_sim_cache is None: self._compute_content_sim_cache()
            content_sims = dict(self.content_sim_cache.get(movie_id, []))
        else:
            content_sims = {}
        if method in ('collab','hybrid'):
            self._ensure_collab_cache()
            collab_sims = dict(self.collab_sim_cache.get(movie_id, []))
        else:
            collab_sims = {}
        combined = defaultdict(float)
        w_content = 0.6 if method == 'hybrid' else (1.0 if method == 'content' else 0.0)
        w_collab = 0.4 if method == 'hybrid' else (1.0 if method == 'collab' else 0.0)
        for mid, s in content_sims.items(): combined[mid] += s * w_content
        for mid, s in collab_sims.items(): combined[mid] += s * w_collab
        items = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_n]
        res = []
        for mid, score in items:
            m = id_to_movie.get(mid)
            if not m: continue
            res.append({'movie_id': m.get('movie_id'), 'movie_name': m.get('movie_name'), 'year': m.get('year'), 'rating': m.get('rating'), 'score': round(float(score),6)})
        return res
