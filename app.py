from flask import Flask, render_template, jsonify, request
import csv
import json
import os

app = Flask(__name__)

# Đọc dữ liệu từ CSV
def load_movies():
    movies = []
    csv_file = 'compilation_movies_cleaned.csv'
    
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
    
    all_movies = get_movies()
    
    # Lọc theo tìm kiếm
    if search:
        filtered_movies = [
            m for m in all_movies 
            if search in m.get('movie_name', '').lower() or 
               search in m.get('genre', '').lower() or
               search in m.get('director', '').lower()
        ]
    else:
        filtered_movies = all_movies
    
    # Phân trang
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)

