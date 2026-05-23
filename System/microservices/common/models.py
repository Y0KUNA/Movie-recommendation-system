"""
Common data models for microservices
"""
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Movie:
    """Movie data model"""
    movie_id: str
    movie_name: str
    year: Optional[str] = None
    certificate: Optional[str] = None
    runtime: Optional[str] = None
    genre: Optional[str] = None
    rating: Optional[str] = None
    description: Optional[str] = None
    director: Optional[str] = None
    director_id: Optional[str] = None
    star: Optional[str] = None
    star_id: Optional[str] = None
    votes: Optional[str] = None
    gross: Optional[str] = None
    poster: Optional[str] = None

    def to_dict(self):
        return {
            'movie_id': self.movie_id,
            'movie_name': self.movie_name,
            'year': self.year,
            'certificate': self.certificate,
            'runtime': self.runtime,
            'genre': self.genre,
            'rating': self.rating,
            'description': self.description,
            'director': self.director,
            'director_id': self.director_id,
            'star': self.star,
            'star_id': self.star_id,
            'votes': self.votes,
            'gross': self.gross,
            'poster': self.poster
        }

@dataclass
class PaginatedResponse:
    """Paginated response model"""
    data: List[dict]
    total: int
    page: int
    per_page: int
    total_pages: int

    def to_dict(self):
        return {
            'data': self.data,
            'total': self.total,
            'page': self.page,
            'per_page': self.per_page,
            'total_pages': self.total_pages
        }
