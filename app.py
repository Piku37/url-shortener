"""
URL Shortener Application
Main Flask application file
"""

from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import string
import random
import os

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///urls.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# ============================================
# DATABASE MODEL
# ============================================
class URL(db.Model):
    """Database model for storing URLs"""
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(2048), nullable=False)
    short_code = db.Column(db.String(10), unique=True, nullable=False)
    clicks = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    def __repr__(self):
        return f'<URL {self.short_code}>'

# ============================================
# HELPER FUNCTIONS
# ============================================
def generate_short_code(length=6):
    """Generate random short code"""
    characters = string.ascii_letters + string.digits
    while True:
        short_code = ''.join(random.choices(characters, k=length))
        # Check if code already exists
        if not URL.query.filter_by(short_code=short_code).first():
            return short_code

def is_valid_url(url):
    """Basic URL validation"""
    return url.startswith(('http://', 'https://'))

def get_base_url():
    """Get base URL for shortened links"""
    # For demo, use localhost or server IP
    return request.host_url.rstrip('/')

# ============================================
# ROUTES
# ============================================

@app.route('/')
def home():
    """Home page with URL shortener form"""
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten_url():
    """Create shortened URL"""
    try:
        # Get URL from request
        data = request.get_json() if request.is_json else request.form
        original_url = data.get('url', '').strip()
        
        # Validate URL
        if not original_url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not is_valid_url(original_url):
            return jsonify({'error': 'Invalid URL. Must start with http:// or https://'}), 400
        
        # Generate short code
        short_code = generate_short_code()
        
        # Save to database
        new_url = URL(original_url=original_url, short_code=short_code)
        db.session.add(new_url)
        db.session.commit()
        
        # Return shortened URL
        short_url = f"{get_base_url()}/{short_code}"
        
        return jsonify({
            'success': True,
            'short_url': short_url,
            'short_code': short_code,
            'original_url': original_url
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/<short_code>')
def redirect_to_url(short_code):
    """Redirect short URL to original URL"""
    # Find URL in database
    url_entry = URL.query.filter_by(short_code=short_code).first()
    
    if url_entry:
        # Increment click counter
        url_entry.clicks += 1
        db.session.commit()
        
        # Redirect to original URL
        return redirect(url_entry.original_url)
    else:
        return render_template('404.html', short_code=short_code), 404

@app.route('/stats/<short_code>')
def get_stats(short_code):
    """Get statistics for a short URL"""
    url_entry = URL.query.filter_by(short_code=short_code).first()
    
    if url_entry:
        return jsonify({
            'short_code': url_entry.short_code,
            'original_url': url_entry.original_url,
            'clicks': url_entry.clicks,
            'created_at': url_entry.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        return jsonify({'error': 'URL not found'}), 404

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({'status': 'healthy'}), 200

# ============================================
# APPLICATION INITIALIZATION
# ============================================
def init_db():
    """Initialize database"""
    with app.app_context():
        db.create_all()
        print("Database initialized!")

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run application
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
