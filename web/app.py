from flask import Flask, render_template, jsonify, request
import csv
import json
import os
from collections import Counter, defaultdict
import re

app = Flask(__name__)

# Đọc dữ liệu từ CSV
def load_movies():
    movies = []
    csv_file = 'web\imdb_movies_3000.csv'
    
    if not os.path.exists(csv_file):
        return movies
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
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
                    'gross': clean_field(row.get('gross(in $)', '')),
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


@app.route('/api/movies/<movie_id>')
def get_movie_detail(movie_id):
    all_movies = get_movies()
    movie = next((m for m in all_movies if m.get('movie_id') == movie_id), None)
    
    if movie:
        return jsonify(movie)
    else:
        return jsonify({'error': 'Movie not found'}), 404

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
    app.run(debug=True, port=5000)

