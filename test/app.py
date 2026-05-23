from flask import Flask, render_template, jsonify, request
from markupsafe import escape
import csv
import json
import os
from collections import Counter, defaultdict
import re
import time
import math
from datetime import datetime
import threading
from recommender import Recommender

app = Flask(__name__)

# Đọc dữ liệu từ CSV
def load_movies():
    movies = []
    # Resolve CSV path robustly:
    # - primary: ../web/imdb_movies_3000.csv relative to this test/ folder (common development layout)
    # - fallback: ./web/imdb_movies_3000.csv from cwd
    base_dir = os.path.dirname(os.path.abspath(__file__))  # this file's folder (test/)
    csv_file = os.path.normpath(os.path.join(base_dir, '..', 'web', 'imdb_movies_3000.csv'))
    if not os.path.exists(csv_file):
        csv_file_alt = os.path.normpath(os.path.join(os.getcwd(), 'web', 'imdb_movies_3000.csv'))
        if os.path.exists(csv_file_alt):
            csv_file = csv_file_alt
    if not os.path.exists(csv_file):
        # nothing to load
        return movies

    try:
        # Open with UTF-8 with replacement to avoid crash on weird chars
        with open(csv_file, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Làm sạch dữ liệu
                def clean_field(value):
                    if not value or value.strip() == '':
                        return None
                    return value.strip()
                
                movie = {
                    'movie_id': clean_field(row.get('movie_id', '')),
                    'movie_name': clean_field(row.get('movie_name', '')),
                    'year': clean_field(row.get('year', '')),
                    'certificate': clean_field(row.get('certificate', '')),
                    'runtime': clean_field(row.get('runtime', '')),
                    'genre': clean_field(row.get('genre', '')),
                    'rating': clean_field(row.get('rating', '')),
                    'description': clean_field(row.get('description', '')),
                    'director': clean_field(row.get('director', '')),
                    'director_id': clean_field(row.get('director_id', '')),
                    'star': clean_field(row.get('star', '')),
                    'star_id': clean_field(row.get('star_id', '')),
                    'votes': clean_field(row.get('votes', '')),
                    # dataset doesn't always include gross; try common keys
                    'gross': clean_field(row.get('gross(in $)', row.get('gross', ''))),
                    'poster': clean_field(row.get('poster', ''))
                }
                # Chỉ thêm phim nếu có movie_id
                if movie['movie_id']:
                    movies.append(movie)
        print("Loaded movies:", len(movies))

    except Exception as e:
        print(f"Error reading CSV: {e}")
        import traceback
        traceback.print_exc()
    
    return movies

# Cache dữ liệu
movies_data = None

def get_movies():
    global movies_data
    if movies_data is None:
        movies_data = load_movies()
    return movies_data

# ------------------ Recommender/tracking additions ------------------
# File to persist interactions
interactions = []  # list of {user_id, movie_id, action, rating, ts}
# ensure interactions file lives next to this app.py (avoid cwd issues)
INTERACTIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'interactions.json')
_interaction_lock = threading.Lock()
user_item_scores = defaultdict(dict)  # user_id -> {movie_id: score}
content_sim_cache = None  # movie_id -> list of (other_movie_id, sim)
collab_sim_cache = None   # movie_id -> list of (other_movie_id, sim)
_collab_dirty = True      # mark to recompute collab sims when interactions change

def load_interactions():
    global interactions, user_item_scores, _collab_dirty
    # Read interactions from the interactions file placed next to this app.py
    if os.path.exists(INTERACTIONS_FILE):
        try:
            with open(INTERACTIONS_FILE, 'r', encoding='utf-8') as f:
                interactions = json.load(f)
        except Exception:
            interactions = []
    else:
        interactions = []
    # Build user_item_scores from interactions
    user_item_scores.clear()
    for ev in interactions:
        uid = ev.get('user_id')
        mid = ev.get('movie_id')
        action = ev.get('action')
        rating = ev.get('rating')
        score = _action_score(action, rating)
        if uid and mid:
            user_item_scores[uid][mid] = max(user_item_scores[uid].get(mid, 0), score)
    _collab_dirty = True

def save_interactions():
    # write interactions file in background to avoid blocking requests
    def _write():
        with _interaction_lock:
            try:
                with open(INTERACTIONS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(interactions, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print("Error saving interactions:", e)
    t = threading.Thread(target=_write, daemon=True)
    t.start()

def _action_score(action, rating=None):
    # Simple mapping: view=1, like=3, rating maps to rating (0-10)
    if action == 'view':
        return 1.0
    if action == 'like':
        return 3.0
    if action == 'rate':
        try:
            return float(rating)
        except:
            return 0.0
    return 0.5

# Tokenize / content feature helpers
def _tokens_for_movie(m):
    parts = []
    for k in ('movie_name','genre','director','star','description'):
        v = (m.get(k) or '')
        parts.append(v.lower())
    text = ' '.join(parts)
    # split on non-alphanum, keep tokens length >=3
    toks = re.findall(r'\b[a-z0-9]{3,}\b', text)
    return toks

def _build_content_vectors(movies):
    # returns dict movie_id -> Counter(token->count)
    vectors = {}
    for m in movies:
        mid = m.get('movie_id')
        if not mid:
            continue
        toks = _tokens_for_movie(m)
        cnt = Counter(toks)
        vectors[mid] = cnt
    return vectors

def _cosine_sim_counts(c1, c2):
    # c1, c2 are Counters/dicts token->count
    if not c1 or not c2:
        return 0.0
    dot = 0.0
    for t, v in c1.items():
        if t in c2:
            dot += v * c2[t]
    norm1 = math.sqrt(sum(v*v for v in c1.values()))
    norm2 = math.sqrt(sum(v*v for v in c2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def _compute_content_sim_cache():
    global content_sim_cache
    movies = get_movies()
    vectors = _build_content_vectors(movies)
    content_sim_cache = {}
    ids = list(vectors.keys())
    for i, mid in enumerate(ids):
        sims = []
        vi = vectors[mid]
        for j, other in enumerate(ids):
            if mid == other:
                continue
            s = _cosine_sim_counts(vi, vectors[other])
            if s > 0:
                sims.append((other, s))
        sims.sort(key=lambda x: x[1], reverse=True)
        content_sim_cache[mid] = sims
    # also build for movies without tokens as empty list
    for m in movies:
        if m.get('movie_id') not in content_sim_cache:
            content_sim_cache[m.get('movie_id')] = []
    return content_sim_cache

def _compute_collab_sim_cache():
    global collab_sim_cache, _collab_dirty
    # Build item -> user -> score
    item_user = defaultdict(dict)
    for uid, items in user_item_scores.items():
        for mid, score in items.items():
            item_user[mid][uid] = score
    # compute similarities
    collab_sim_cache = {}
    mids = list(item_user.keys())
    for i, mid in enumerate(mids):
        sims = []
        vi = item_user[mid]
        norm_i = math.sqrt(sum(v*v for v in vi.values()))
        for other in mids:
            if other == mid:
                continue
            vj = item_user[other]
            # dot product
            dot = 0.0
            for u, s in vi.items():
                if u in vj:
                    dot += s * vj[u]
            norm_j = math.sqrt(sum(v*v for v in vj.values()))
            if norm_i == 0 or norm_j == 0:
                sim = 0.0
            else:
                sim = dot / (norm_i * norm_j)
            if sim > 0:
                sims.append((other, sim))
        sims.sort(key=lambda x: x[1], reverse=True)
        collab_sim_cache[mid] = sims
    _collab_dirty = False
    return collab_sim_cache

# Initialize interactions and content cache on start
load_interactions()
_compute_content_sim_cache()

# instantiate recommender (loads interactions & builds content cache)
recommender = Recommender(get_movies)

def record_interaction(user_id, movie_id, action, rating=None):
    # Append event and update user_item_scores; mark collab dirty
    ts = int(time.time())
    ev = {'user_id': user_id, 'movie_id': movie_id, 'action': action, 'rating': rating, 'ts': ts}
    with _interaction_lock:
        interactions.append(ev)
        score = _action_score(action, rating)
        user_item_scores[user_id][movie_id] = max(user_item_scores[user_id].get(movie_id, 0), score)
        # schedule save in background
        save_interactions()
        global _collab_dirty
        _collab_dirty = True
    # start background collab recompute (non-blocking). If you prefer blocking for accuracy, call _ensure_collab_cache(sync=True)
    _ensure_collab_cache(sync=False)

def _score_candidates_by_content_for_user(user_id, exclude_set, top_n):
    # For user's watched movies, accumulate similarity scores to others
    movies = get_movies()
    if content_sim_cache is None:
        _compute_content_sim_cache()
    scores = defaultdict(float)
    user_items = user_item_scores.get(user_id, {})
    if not user_items:
        return []
    for mid, uscore in user_items.items():
        for other, sim in content_sim_cache.get(mid, []):
            if other in exclude_set:
                continue
            scores[other] += sim * uscore
    # map back to movie objects and sort
    recs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    id_to_movie = {m.get('movie_id'): m for m in movies}
    return [{'movie': id_to_movie.get(mid), 'score': score} for mid, score in recs if id_to_movie.get(mid)]

def _score_candidates_by_collab_for_user(user_id, exclude_set, top_n):
    _ensure_collab_cache()
    scores = defaultdict(float)
    user_items = user_item_scores.get(user_id, {})
    if not user_items:
        return []
    for mid, uscore in user_items.items():
        for other, sim in collab_sim_cache.get(mid, []):
            if other in exclude_set:
                continue
            scores[other] += sim * uscore
    recs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    movies = get_movies()
    id_to_movie = {m.get('movie_id'): m for m in movies}
    return [{'movie': id_to_movie.get(mid), 'score': score} for mid, score in recs if id_to_movie.get(mid)]

def get_recommendations_for_user(user_id, method='hybrid', top_n=10, seed_movie=None):
    # method: content, collab, hybrid
    movies = get_movies()
    seen = set(user_item_scores.get(user_id, {}).keys())
    if seed_movie:
        seen.add(seed_movie)
    # content-only
    content_recs = _score_candidates_by_content_for_user(user_id, seen, top_n*2)
    collab_recs = _score_candidates_by_collab_for_user(user_id, seen, top_n*2)
    # combine
    final_scores = defaultdict(float)
    for r in content_recs:
        mid = r['movie'].get('movie_id')
        if method in ('content','hybrid'):
            final_scores[mid] += r['score'] * (0.6 if method=='hybrid' else 1.0)
    for r in collab_recs:
        mid = r['movie'].get('movie_id')
        if method in ('collab','hybrid'):
            final_scores[mid] += r['score'] * (0.4 if method=='hybrid' else 1.0)
    # fallback: if no final_scores, try popular top by rating
    if not final_scores:
        # use top rated
        def parse_rating(r):
            try:
                return float(r) if r else 0
            except:
                return 0
        sorted_movies = sorted(movies, key=lambda m: parse_rating(m.get('rating')), reverse=True)
        results = [{'movie': m, 'score': parse_rating(m.get('rating'))} for m in sorted_movies if m.get('movie_id') not in seen][:top_n]
        return results
    # prepare return list
    id_to_movie = {m.get('movie_id'): m for m in movies}
    sorted_final = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [{'movie': id_to_movie.get(mid), 'score': score} for mid, score in sorted_final if id_to_movie.get(mid)]

def _get_similar_movies_for(movie_id, method='content', top_n=10):
    """
    Return list of {'movie': movie_obj, 'score': float} for given movie_id.
    method: 'content', 'collab', 'hybrid'
    """
    movies = get_movies()
    id_to_movie = {m.get('movie_id'): m for m in movies}
    if method in ('content','hybrid'):
        if content_sim_cache is None:
            _compute_content_sim_cache()
        content_sims = dict(content_sim_cache.get(movie_id, []))
    else:
        content_sims = {}
    if method in ('collab','hybrid'):
        _ensure_collab_cache()
        collab_sims = dict(collab_sim_cache.get(movie_id, []))
    else:
        collab_sims = {}

    combined = defaultdict(float)
    # weights for hybrid
    w_content = 0.6 if method == 'hybrid' else (1.0 if method == 'content' else 0.0)
    w_collab = 0.4 if method == 'hybrid' else (1.0 if method == 'collab' else 0.0)

    # accumulate
    for mid, s in content_sims.items():
        combined[mid] += s * w_content
    for mid, s in collab_sims.items():
        combined[mid] += s * w_collab

    # sort and map to movie objects
    items = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_n]
    result = []
    for mid, score in items:
        m = id_to_movie.get(mid)
        if not m:
            continue
        result.append({'movie_id': m.get('movie_id'),
                       'movie_name': m.get('movie_name'),
                       'genre': m.get('genre'),
                       'year': m.get('year'),
                       'rating': m.get('rating'),
                       'score': round(float(score), 6)})
    return result

# ------------------ API endpoints for tracking and recommendations ------------------
@app.route('/api/track', methods=['POST'])
def api_track():
    payload = request.get_json(force=True, silent=True) or {}
    user_id = str(payload.get('user_id') or payload.get('uid') or 'anonymous')
    movie_id = payload.get('movie_id')
    action = payload.get('action', 'view')
    rating = payload.get('rating')
    if not movie_id:
        return jsonify({'error': 'movie_id required'}), 400
    recommender.record_interaction(user_id, movie_id, action, rating)
    return jsonify({'status': 'ok'})

@app.route('/api/recommendations')
def api_recommendations():
    user_id = request.args.get('user_id') or request.args.get('uid')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    method = request.args.get('method', 'hybrid')  # content, collab, hybrid
    top_n = int(request.args.get('top_n', 10))
    seed_movie = request.args.get('seed_movie')  # optional seed movie to exclude
    recs = recommender.get_recommendations_for_user(user_id, method=method, top_n=top_n, seed_movie=seed_movie)
    # Return simplified movie objects + score
    out = []
    for r in recs:
        m = r['movie']
        out.append({
            'movie_id': m.get('movie_id'),
            'movie_name': m.get('movie_name'),
            'year': m.get('year'),
            'rating': m.get('rating'),
            'score': round(float(r['score']), 4),
            'poster': m.get('poster', '')  # include poster for frontend "For you" cards
        })
    return jsonify({'user_id': user_id, 'method': method, 'recommendations': out})

@app.route('/api/visualization/recommend-activity')
def api_recommend_activity():
    # Summarize interactions: counts, top movies, recent events
    # Load interactions in memory (already loaded)
    recent = sorted(recommender.interactions, key=lambda x: x.get('ts',0), reverse=True)[:50]
    total = len(recommender.interactions)
    action_counts = Counter(ev.get('action') for ev in recommender.interactions)
    movie_counts = Counter(ev.get('movie_id') for ev in recommender.interactions)
    top_movies = [{'movie_id': mid, 'count': cnt} for mid, cnt in movie_counts.most_common(20)]
    # interactions over days (last 30 days)
    day_counts = defaultdict(int)
    now = int(time.time())
    for ev in interactions:
        ts = ev.get('ts', 0)
        # ignore bizarre timestamps
        try:
            day = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
        except:
            continue
        day_counts[day] += 1
    day_series = sorted(day_counts.items())
    return jsonify({
        'total_interactions': total,
        'action_counts': dict(action_counts),
        'top_movies': top_movies,
        'recent_events': recent,
        'interactions_by_day': [{'day': d, 'count': c} for d, c in day_series]
    })

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/movies')
def get_movies_api():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').lower()
    field = request.args.get('field', 'movie_name').lower()  # new

    all_movies = get_movies()

    # --- Convert rating sang float ---
    def parse_rating(r):
        try:
            return float(r)
        except:
            return -1  # rating lỗi/None sẽ nằm cuối danh sách

    # --- Sắp xếp giảm dần theo rating ---
    all_movies_sorted = sorted(all_movies, key=lambda m: parse_rating(m.get('rating')), reverse=True)

    # --- Lọc theo từ khóa và trường được chọn ---
    if search:
        if field == 'movie_name':
            filtered_movies = [m for m in all_movies_sorted if search in (m.get('movie_name') or '').lower()]
        elif field == 'genre':
            filtered_movies = [m for m in all_movies_sorted if search in (m.get('genre') or '').lower()]
        elif field == 'director':
            filtered_movies = [m for m in all_movies_sorted if search in (m.get('director') or '').lower()]
        elif field == 'star':
            filtered_movies = [m for m in all_movies_sorted if search in (m.get('star') or '').lower()]
        else:
            # fallback: search across main fields (previous behavior)
            filtered_movies = [
                m for m in all_movies_sorted
                if search in (m.get('movie_name') or '').lower() or
                   search in (m.get('genre') or '').lower() or
                   search in (m.get('director') or '').lower()
            ]
    else:
        filtered_movies = all_movies_sorted

    # --- Phân trang ---
    total = len(filtered_movies)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_movies = filtered_movies[start:end]

    return jsonify({
        'movies': paginated_movies,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })
def build_movie_detail(movie_id, user_id=None, method='content', top_n=10):
    all_movies = get_movies()
    movie = next((m for m in all_movies if m.get('movie_id') == movie_id), None)
    if not movie:
        return None, None

    # tracking view
    if user_id:
        try:
            record_interaction(str(user_id), movie_id, 'view')
        except Exception:
            pass

    more_like = _get_similar_movies_for(movie_id, method=method, top_n=top_n)
    if not more_like and method != 'content':
        more_like = _get_similar_movies_for(movie_id, method='content', top_n=top_n)

    out = dict(movie)
    out['more_like_this'] = more_like

    return out, all_movies


@app.route('/api/movies/<movie_id>')
def get_movie_detail_api(movie_id):
    user_id = request.args.get('user_id') or request.args.get('uid')
    method = request.args.get('recommend_method', 'content')

    try:
        top_n = int(request.args.get('top_n', 5))
    except:
        top_n = 5

    data, all_movies = build_movie_detail(movie_id, user_id, method, top_n)

    if not data:
        return jsonify({'error': 'Movie not found'}), 404

    # 🔥 GẮN POSTER CHO RECOMMENDATIONS
    movie_index = {m['movie_id']: m for m in all_movies}

    enriched_more = []
    for r in data.get('more_like_this', []):
        m = movie_index.get(r.get('movie_id'), {})
        rr = dict(r)
        rr['poster'] = m.get('poster', '')
        enriched_more.append(rr)

    return jsonify({
        "movie": {
            k: v for k, v in data.items() if k != 'more_like_this'
        },
        "recommendations": enriched_more
    })



@app.route('/movies/<movie_id>')
def movie_spa(movie_id):
    return render_template('index.html')

# Visualization endpoints
@app.route('/api/visualization/rating-distribution')
def get_rating_distribution():
    all_movies = get_movies()
    ratings = []
    
    for movie in all_movies:
        rating = movie.get('rating')
        if rating:
            try:
                r = float(rating)
                if 0 <= r <= 10:  # Valid rating range
                    ratings.append(r)
            except:
                pass
    
    # Create bins for histogram (0-10, step 0.5)
    bins = [i * 0.5 for i in range(21)]  # 0, 0.5, 1.0, ..., 10.0
    distribution = [0] * 20
    
    for rating in ratings:
        bin_idx = min(int(rating * 2), 19)
        distribution[bin_idx] += 1
    
    labels = [f"{bins[i]:.1f}-{bins[i+1]:.1f}" for i in range(20)]
    
    return jsonify({
        'labels': labels,
        'data': distribution,
        'total': len(ratings)
    })

@app.route('/api/visualization/top-movies')
def get_top_movies():
    all_movies = get_movies()
    
    def parse_rating(r):
        try:
            return float(r) if r else 0
        except:
            return 0
    
    def parse_votes(v):
        try:
            return int(float(v)) if v else 0
        except:
            return 0
    
    # Sort by rating, then by votes
    sorted_movies = sorted(
        all_movies,
        key=lambda m: (parse_rating(m.get('rating')), parse_votes(m.get('votes'))),
        reverse=True
    )
    
    top_movies = []
    for movie in sorted_movies[:20]:  # Top 20
        rating = parse_rating(movie.get('rating'))
        if rating > 0:
            top_movies.append({
                'name': movie.get('movie_name', 'N/A'),
                'rating': rating,
                'votes': parse_votes(movie.get('votes')),
                'year': movie.get('year', 'N/A')
            })
    
    return jsonify(top_movies)

@app.route('/api/visualization/top-genres')
def get_top_genres():
    all_movies = get_movies()
    genre_counter = Counter()
    
    for movie in all_movies:
        genre_str = movie.get('genre', '')
        if genre_str:
            # Split genres by comma and clean
            genres = [g.strip() for g in genre_str.split(',')]
            for genre in genres:
                if genre:
                    genre_counter[genre] += 1
    
    top_genres = [{'genre': genre, 'count': count} 
                  for genre, count in genre_counter.most_common(15)]
    
    return jsonify(top_genres)

@app.route('/api/visualization/heatmap-data')
def get_heatmap_data():
    all_movies = get_movies()
    
    # Create year-rating heatmap data
    year_rating_data = defaultdict(list)
    
    for movie in all_movies:
        year = movie.get('year', '')
        rating = movie.get('rating', '')
        
        if year and rating:
            try:
                y = int(year)
                r = float(rating)
                if 1900 <= y <= 2024 and 0 <= r <= 10:
                    year_rating_data[y].append(r)
            except:
                pass
    
    # Calculate average rating per year
    heatmap_data = []
    for year in sorted(year_rating_data.keys()):
        avg_rating = sum(year_rating_data[year]) / len(year_rating_data[year])
        count = len(year_rating_data[year])
        heatmap_data.append({
            'year': year,
            'avg_rating': round(avg_rating, 2),
            'count': count
        })
    
    return jsonify(heatmap_data)

@app.route('/api/visualization/bar-chart-data')
def get_bar_chart_data():
    all_movies = get_movies()
    
    # Movies per year
    year_counter = Counter()
    
    for movie in all_movies:
        year = movie.get('year', '')
        if year:
            try:
                y = int(year)
                if 1900 <= y <= 2024:
                    year_counter[y] += 1
            except:
                pass
    
    # Get top 20 years by count
    top_years = year_counter.most_common(20)
    top_years.sort(key=lambda x: x[0])  # Sort by year
    
    return jsonify({
        'labels': [str(year) for year, _ in top_years],
        'data': [count for _, count in top_years]
    })

@app.route('/api/visualization/histogram-data')
def get_histogram_data():
    all_movies = get_movies()
    
    # Runtime histogram
    runtimes = []
    
    for movie in all_movies:
        runtime = movie.get('runtime', '')
        if runtime:
            # Extract number from "102 min" format
            match = re.search(r'(\d+)', runtime)
            if match:
                try:
                    minutes = int(match.group(1))
                    if 0 < minutes < 500:  # Reasonable range
                        runtimes.append(minutes)
                except:
                    pass
    
    # Create bins: 0-60, 60-90, 90-120, 120-150, 150-180, 180+
    bins = [0, 60, 90, 120, 150, 180, 500]
    bin_labels = ['0-60', '60-90', '90-120', '120-150', '150-180', '180+']
    distribution = [0] * 6
    
    for runtime in runtimes:
        for i in range(len(bins) - 1):
            if bins[i] <= runtime < bins[i+1]:
                distribution[i] += 1
                break
    
    return jsonify({
        'labels': bin_labels,
        'data': distribution,
        'total': len(runtimes)
    })

@app.route('/api/visualization/wordcloud-data')
def get_wordcloud_data():
    all_movies = get_movies()
    
    # Extract words from movie names and descriptions
    word_counter = Counter()
    
    # Common stop words to exclude
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'now'}
    
    for movie in all_movies:
        # From movie names
        name = movie.get('movie_name', '')
        if name:
            words = re.findall(r'\b[a-zA-Z]{3,}\b', name.lower())
            for word in words:
                if word not in stop_words:
                    word_counter[word] += 1
        
        # From descriptions
        desc = movie.get('description', '')
        if desc:
            words = re.findall(r'\b[a-zA-Z]{4,}\b', desc.lower())
            for word in words:
                if word not in stop_words and len(word) > 3:
                    word_counter[word] += 1
    
    # Get top 50 words
    top_words = [{'text': word, 'value': count} 
                 for word, count in word_counter.most_common(50)]
    
    return jsonify(top_words)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)


