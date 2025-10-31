"""
Unit tests for URL Shortener application
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, URL

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()
            # Clean up test DB file if exists
            try:
                os.remove('test.db')
            except OSError:
                pass

def test_home_page(client):
    """Test home page loads"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'URL Shortener' in response.data

def test_shorten_url(client):
    """Test URL shortening"""
    response = client.post('/shorten', 
                          json={'url': 'https://www.example.com'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert 'short_url' in data

def test_invalid_url(client):
    """Test invalid URL handling"""
    response = client.post('/shorten', 
                          json={'url': 'not-a-valid-url'})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_redirect(client):
    """Test URL redirection"""
    # First create a short URL
    response = client.post('/shorten', 
                          json={'url': 'https://www.example.com'})
    data = response.get_json()
    short_code = data['short_code']
    
    # Test redirect
    response = client.get(f'/{short_code}')
    assert response.status_code in (301, 302) or response.status_code == 200

def test_stats(client):
    """Test statistics endpoint"""
    # Create a short URL
    response = client.post('/shorten', 
                          json={'url': 'https://www.example.com'})
    data = response.get_json()
    short_code = data['short_code']
    
    # Get stats
    response = client.get(f'/stats/{short_code}')
    assert response.status_code == 200
    data = response.get_json()
    assert 'clicks' in data

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
