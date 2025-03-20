import pytest
import sys
import os

# Add the parent directory to the path so we can import the core modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def api_client():
    """Create a test client for the API"""
    from core.app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client