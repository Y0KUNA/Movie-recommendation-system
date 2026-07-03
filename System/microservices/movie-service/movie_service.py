"""
Movie Service - Quản lý dữ liệu phim
Service này chịu trách nhiệm:
- Đọc và cache dữ liệu phim từ CSV
- Tìm kiếm phim
- Lấy thông tin chi tiết phim
- Lọc phim theo criteria
"""
import csv
import os
from typing import List, Dict, Optional
import logging
from pathlib import Path

# Thêm common vào path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.models import Movie
from common.utils import clean_field, parse_rating, calculate_total_pages
from common.config import get_config

logger = logging.getLogger(__name__)
config = get_config()

class MovieRepository:
    """Repository pattern for movie data access"""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._movies_cache: Optional[List[Movie]] = None
        self._movies_dict: Dict[str, Movie] = {}
    
    def load_movies(self) -> List[Movie]:
        """Load movies from CSV file"""
        if self._movies_cache is not None:
            return self._movies_cache
        
        movies = []
        
        if not os.path.exists(self.csv_path):
            logger.error(f"CSV file not found: {self.csv_path}")
            return movies
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    movie = Movie(
                        movie_id=clean_field(row.get('movie_id', '')),
                        movie_name=clean_field(row.get('movie_name', '')),
                        year=clean_field(row.get('year', '')),
                        certificate=clean_field(row.get('certificate', '')),
                        runtime=clean_field(row.get('runtime', '')),
                        genre=clean_field(row.get('genre', '')),
                        rating=clean_field(row.get('rating', '')),
                        description=clean_field(row.get('description', '')),
                        director=clean_field(row.get('director', '')),
                        director_id=clean_field(row.get('director_id', '')),
                        star=clean_field(row.get('star', '')),
                        star_id=clean_field(row.get('star_id', '')),
                        votes=clean_field(row.get('votes', '')),
                        gross=clean_field(row.get('gross(in $)', '')),
                        poster=clean_field(row.get('poster', ''))
                    )
                    
                    if movie.movie_id:
                        movies.append(movie)
                        self._movies_dict[movie.movie_id] = movie
            
            self._movies_cache = movies
            logger.info(f"Loaded {len(movies)} movies from {self.csv_path}")
            
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            import traceback
            traceback.print_exc()
        
        return movies
    
    def get_all_movies(self) -> List[Movie]:
        """Get all movies"""
        if self._movies_cache is None:
            self.load_movies()
        return self._movies_cache or []
    
    def get_movie_by_id(self, movie_id: str) -> Optional[Movie]:
        """Get movie by ID"""
        if not self._movies_cache:
            self.load_movies()
        return self._movies_dict.get(movie_id)
    
    def search_movies(self, query: str, field: str = 'movie_name') -> List[Movie]:
        """Search movies by field"""
        movies = self.get_all_movies()
        query = query.lower()
        
        field_map = {
            'movie_name': lambda m: (m.movie_name or '').lower(),
            'genre': lambda m: (m.genre or '').lower(),
            'director': lambda m: (m.director or '').lower(),
            'star': lambda m: (m.star or '').lower(),
            'description': lambda m: (m.description or '').lower(),
            'all': lambda m: ' '.join([
                m.movie_name or '',
                m.genre or '',
                m.director or '',
                m.star or '',
                m.description or '',
            ]).lower(),
        }
        
        get_field_value = field_map.get(field, field_map['movie_name'])
        
        return [m for m in movies if query in get_field_value(m)]
    
    def filter_by_genre(self, genre: str) -> List[Movie]:
        """Filter movies by genre"""
        return self.search_movies(genre, 'genre')
    
    def filter_by_director(self, director: str) -> List[Movie]:
        """Filter movies by director"""
        return self.search_movies(director, 'director')
    
    def sort_by_rating(self, movies: List[Movie], reverse: bool = True) -> List[Movie]:
        """Sort movies by rating"""
        return sorted(movies, key=lambda m: parse_rating(m.rating), reverse=reverse)

class MovieService:
    """Movie business logic service"""
    
    def __init__(self, repository: MovieRepository):
        self.repository = repository
    
    def get_all_movies_paginated(self, page: int = 1, per_page: int = 20) -> Dict:
        """Get paginated movies sorted by rating"""
        movies = self.repository.get_all_movies()
        movies = self.repository.sort_by_rating(movies)
        
        total = len(movies)
        start = (page - 1) * per_page
        end = start + per_page
        
        paginated_movies = [m.to_dict() for m in movies[start:end]]
        
        return {
            'data': paginated_movies,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': calculate_total_pages(total, per_page)
        }
    
    def search_movies_paginated(self, query: str, field: str = 'movie_name', 
                               page: int = 1, per_page: int = 20) -> Dict:
        """Search movies with pagination"""
        movies = self.repository.search_movies(query, field)
        movies = self.repository.sort_by_rating(movies)
        
        total = len(movies)
        start = (page - 1) * per_page
        end = start + per_page
        
        paginated_movies = [m.to_dict() for m in movies[start:end]]
        
        return {
            'data': paginated_movies,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': calculate_total_pages(total, per_page)
        }
    
    def get_movie_detail(self, movie_id: str) -> Optional[Dict]:
        """Get movie detail by ID"""
        movie = self.repository.get_movie_by_id(movie_id)
        return movie.to_dict() if movie else None
    
    def get_recommendations_based_on_similarity(self, movie_id: str, 
                                               top_k: int = 10) -> List[Dict]:
        """Get similar movies (placeholder for vector service integration)"""
        # This will be called by Recommendation Service
        movies = self.repository.get_all_movies()
        # Basic filtering: same genre, similar rating
        target_movie = self.repository.get_movie_by_id(movie_id)
        
        if not target_movie:
            return []
        
        similar_movies = [
            m for m in movies 
            if m.movie_id != movie_id 
            and (target_movie.genre and m.genre and target_movie.genre.lower() in m.genre.lower())
        ]
        
        similar_movies = self.repository.sort_by_rating(similar_movies)
        return [m.to_dict() for m in similar_movies[:top_k]]
