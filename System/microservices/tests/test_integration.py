"""
Integration tests for microservices
"""
import pytest
import json
import requests
from time import sleep

BASE_URL = "http://localhost:5000"
MOVIE_SERVICE_URL = "http://localhost:5001"
REC_SERVICE_URL = "http://localhost:5002"
VECTOR_SERVICE_URL = "http://localhost:5003"

class TestGatewayHealth:
    """Test API Gateway health endpoints"""
    
    def test_gateway_health(self):
        """Test gateway health check"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'api-gateway'
    
    def test_services_health(self):
        """Test all services health check"""
        response = requests.get(f"{BASE_URL}/health/services")
        assert response.status_code == 200
        data = response.json()
        # Each service should report status
        assert 'movie_service' in data
        assert 'recommendation_service' in data
        assert 'vector_service' in data

class TestMovieEndpoints:
    """Test movie service endpoints through gateway"""
    
    def test_get_movies(self):
        """Test getting movies list"""
        response = requests.get(f"{BASE_URL}/api/movies?page=1&per_page=10")
        assert response.status_code == 200
        data = response.json()
        assert 'data' in data
        assert 'total' in data
        assert 'page' in data
    
    def test_search_movies(self):
        """Test searching movies"""
        response = requests.get(f"{BASE_URL}/api/movies?search=avengers&field=movie_name")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data['data'], list)

class TestRecommendationEndpoints:
    """Test recommendation endpoints"""
    
    def test_trending_recommendations(self):
        """Test getting trending movies"""
        response = requests.get(f"{BASE_URL}/api/recommendations/trending?top_k=10")
        assert response.status_code in [200, 503]  # 503 if service not ready
        
        if response.status_code == 200:
            data = response.json()
            assert 'recommendations' in data

# Run with: pytest tests/test_integration.py -v
# Make sure all services are running first!
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
