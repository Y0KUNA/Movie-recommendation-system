"""
Recommendation Service - Gợi ý phim cho người dùng
Service này chịu trách nhiệm:
- Gợi ý phim dựa trên vector similarity (gọi Vector Service)
- Gợi ý phim dựa trên collaborative filtering
- Gợi ý phim dựa trên content (genre, director, etc)
"""
import os
import sys
import logging
from typing import List, Dict, Optional
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.utils import ServiceClient

logger = logging.getLogger(__name__)

class RecommendationService:
    """Main recommendation service"""
    
    def __init__(self, movie_service_url: str, vector_service_url: str):
        """
        Initialize recommendation service
        
        Args:
            movie_service_url: URL of Movie Service
            vector_service_url: URL of Vector Service
        """
        self.movie_client = ServiceClient()
        self.movie_service_url = movie_service_url
        self.vector_service_url = vector_service_url
    
    def get_movie(self, movie_id: str) -> Optional[Dict]:
        """Get movie detail from Movie Service"""
        try:
            url = f"{self.movie_service_url}/api/movies/{movie_id}"
            return self.movie_client.get(url)
        except Exception as e:
            logger.error(f"Error getting movie {movie_id}: {e}")
            return None
    
    def get_similar_by_vector(self, movie_id: str, top_k: int = 10) -> List[Dict]:
        """Get similar movies using vector similarity (Vector Service)"""
        try:
            url = f"{self.vector_service_url}/api/vectors/similar?movie_id={movie_id}&top_k={top_k}"
            response = self.movie_client.get(url)
            
            if response and 'similar_movies' in response:
                similar_movies = []
                for item in response['similar_movies']:
                    movie = self.get_movie(item['movie_id'])
                    if movie:
                        movie['similarity_score'] = item['similarity_score']
                        similar_movies.append(movie)
                
                return similar_movies
        except Exception as e:
            logger.error(f"Error getting vector similar movies: {e}")
        
        return []
    
    def get_similar_by_genre(self, movie_id: str, top_k: int = 10) -> List[Dict]:
        """Get similar movies by genre"""
        try:
            # Get target movie
            movie = self.get_movie(movie_id)
            if not movie or not movie.get('genre'):
                return []
            
            # Search by genre
            genre = movie['genre'].split(',')[0].strip()
            url = f"{self.movie_service_url}/api/movies/search/by-genre?genre={genre}&per_page={top_k+10}"
            response = self.movie_client.get(url)
            
            if response and 'data' in response:
                similar_movies = [m for m in response['data'] if m['movie_id'] != movie_id]
                return similar_movies[:top_k]
        except Exception as e:
            logger.error(f"Error getting genre similar movies: {e}")
        
        return []
    
    def get_personalized_recommendations(self, movie_id: str, 
                                         method: str = 'vector',
                                         top_k: int = 10) -> List[Dict]:
        """
        Get personalized recommendations
        
        Args:
            movie_id: Reference movie ID
            method: 'vector', 'genre', or 'hybrid'
            top_k: Number of recommendations
        
        Returns:
            List of recommended movies
        """
        if method == 'vector':
            return self.get_similar_by_vector(movie_id, top_k)
        elif method == 'genre':
            return self.get_similar_by_genre(movie_id, top_k)
        elif method == 'hybrid':
            # Combine both methods
            vector_recs = self.get_similar_by_vector(movie_id, top_k // 2)
            genre_recs = self.get_similar_by_genre(movie_id, top_k - len(vector_recs))
            
            # Remove duplicates and combine
            combined = vector_recs + genre_recs
            seen = set()
            unique = []
            for movie in combined:
                if movie['movie_id'] not in seen:
                    seen.add(movie['movie_id'])
                    unique.append(movie)
            
            return unique[:top_k]
        else:
            return []
    
    def get_trending_recommendations(self, top_k: int = 20) -> List[Dict]:
        """Get trending movies (highest rated)"""
        try:
            url = f"{self.movie_service_url}/api/movies?per_page={top_k}"
            response = self.movie_client.get(url)
            
            if response and 'data' in response:
                return response['data']
        except Exception as e:
            logger.error(f"Error getting trending movies: {e}")
        
        return []
    
    def get_recommendations_by_user_preference(self, liked_movie_ids: List[str], 
                                               top_k: int = 10) -> List[Dict]:
        """
        Get recommendations based on multiple liked movies
        
        Args:
            liked_movie_ids: List of movie IDs user liked
            top_k: Number of recommendations
        
        Returns:
            List of recommended movies
        """
        if not liked_movie_ids:
            return self.get_trending_recommendations(top_k)
        
        # Collect all recommendations from liked movies
        all_recommendations = defaultdict(lambda: {'movie': None, 'score': 0})
        
        for movie_id in liked_movie_ids:
            similar = self.get_similar_by_vector(movie_id, top_k * 2)
            
            for movie in similar:
                mid = movie['movie_id']
                if mid not in liked_movie_ids:
                    score = movie.get('similarity_score', 0)
                    if all_recommendations[mid]['movie'] is None:
                        all_recommendations[mid]['movie'] = movie
                    all_recommendations[mid]['score'] += score
        
        # Sort by cumulative score
        sorted_recs = sorted(
            all_recommendations.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )
        
        return [movie_info['movie'] for _, movie_info in sorted_recs[:top_k]]
