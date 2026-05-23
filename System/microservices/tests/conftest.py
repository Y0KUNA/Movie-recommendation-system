"""
Test configuration
"""
import pytest
import sys
import os
from pathlib import Path

# Add microservices to path
sys.path.insert(0, str(Path(__file__).parent.parent))
