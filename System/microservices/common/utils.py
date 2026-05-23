"""
Utility functions for microservices
"""
import requests
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ServiceClient:
    """HTTP client for inter-service communication"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def get(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make GET request"""
        try:
            response = requests.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"GET request failed: {url} - {str(e)}")
            return None
    
    def post(self, url: str, json_data: Dict = None, **kwargs) -> Optional[Dict[str, Any]]:
        """Make POST request"""
        try:
            response = requests.post(url, json=json_data, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"POST request failed: {url} - {str(e)}")
            return None

def clean_field(value: str) -> Optional[str]:
    """Clean CSV field value"""
    if not value or value.strip() == '':
        return None
    return value.strip()

def parse_rating(rating: Optional[str]) -> float:
    """Parse rating to float"""
    try:
        return float(rating) if rating else -1.0
    except (ValueError, TypeError):
        return -1.0

def calculate_total_pages(total: int, per_page: int) -> int:
    """Calculate total pages"""
    return (total + per_page - 1) // per_page
