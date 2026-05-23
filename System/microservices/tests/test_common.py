"""
Test suite for microservices
Run with: pytest tests/ -v
"""
import pytest
import json
import sys
import os
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import Movie
from common.utils import parse_rating, calculate_total_pages, clean_field

class TestCommonUtils:
    """Test common utility functions"""
    
    def test_parse_rating_valid(self):
        """Test parsing valid rating"""
        assert parse_rating("8.5") == 8.5
        assert parse_rating("9.0") == 9.0
    
    def test_parse_rating_invalid(self):
        """Test parsing invalid rating"""
        assert parse_rating(None) == -1.0
        assert parse_rating("") == -1.0
        assert parse_rating("invalid") == -1.0
    
    def test_clean_field(self):
        """Test field cleaning"""
        assert clean_field("  test  ") == "test"
        assert clean_field("") is None
        assert clean_field(None) is None
        assert clean_field("value") == "value"
    
    def test_calculate_total_pages(self):
        """Test page calculation"""
        assert calculate_total_pages(100, 10) == 10
        assert calculate_total_pages(105, 10) == 11
        assert calculate_total_pages(9, 10) == 1
        assert calculate_total_pages(0, 10) == 0

class TestMovieModel:
    """Test Movie data model"""
    
    def test_movie_creation(self):
        """Test creating a movie"""
        movie = Movie(
            movie_id="tt0068646",
            movie_name="The Godfather",
            year="1972",
            genre="Crime, Drama",
            rating="9.2"
        )
        
        assert movie.movie_id == "tt0068646"
        assert movie.movie_name == "The Godfather"
        assert movie.year == "1972"
    
    def test_movie_to_dict(self):
        """Test converting movie to dict"""
        movie = Movie(
            movie_id="tt0068646",
            movie_name="The Godfather",
            rating="9.2"
        )
        
        movie_dict = movie.to_dict()
        assert isinstance(movie_dict, dict)
        assert movie_dict['movie_id'] == "tt0068646"
        assert movie_dict['movie_name'] == "The Godfather"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
