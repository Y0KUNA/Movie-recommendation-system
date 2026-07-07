"""
Configuration for microservices
"""
import os
from typing import Dict

class Config:
    """Base configuration"""
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Service ports
    MOVIE_SERVICE_PORT = int(os.getenv('MOVIE_SERVICE_PORT', 5001))
    RECOMMENDATION_SERVICE_PORT = int(os.getenv('RECOMMENDATION_SERVICE_PORT', 5002))
    VECTOR_SERVICE_PORT = int(os.getenv('VECTOR_SERVICE_PORT', 5003))
    GATEWAY_PORT = int(os.getenv('GATEWAY_PORT', 5000))
    USER_PORT = int(os.getenv('USER_PORT', 5004))
    # Service URLs
    MOVIE_SERVICE_URL = os.getenv('MOVIE_SERVICE_URL', 'http://localhost:5001')
    RECOMMENDATION_SERVICE_URL = os.getenv('RECOMMENDATION_SERVICE_URL', 'http://localhost:5002')
    VECTOR_SERVICE_URL = os.getenv('VECTOR_SERVICE_URL', 'http://localhost:5003')
    USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://localhost:5004')
    # Data paths
    MOVIES_CSV = os.getenv('MOVIES_CSV', '../data/imdb_movies_3000.csv')
    MOVIE_VECTORS_NPZ = os.getenv('MOVIE_VECTORS_NPZ', '../data/movie_vectors.npz')

    # Movie database
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5433))
    DB_NAME = os.getenv('DB_NAME', 'movie_db')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

    # Vector store
    CHROMA_PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', './chroma_data')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

def get_config(env: str = None) -> Config:
    """Get configuration based on environment"""
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    
    config_map: Dict[str, type] = {
        'development': DevelopmentConfig,
        'production': ProductionConfig
    }
    
    return config_map.get(env, DevelopmentConfig)()
