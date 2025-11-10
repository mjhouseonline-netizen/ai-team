"""
Gunicorn WSGI Auth Application
Handles authentication, user management, and third-party integrations
"""

import os
import sys
from datetime import datetime, timedelta
import secrets
import hashlib
from functools import wraps

from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from flask_cors import CORS
import requests

# Add project root to path
sys.path.insert(0, '/opt/render/project/src')

# Import database models and utilities
from gunicorn.app.base import BaseApplication
from database import (
    db, User, Integration, RefreshToken, 
    init_db, create_tables
)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configure database URL for psycopg3
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
elif database_url and database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enable CORS
CORS(app, supports_credentials=True, origins=['*'])

# Initialize database
db.init_app(app)

# OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
SLACK_CLIENT_ID = os.environ.get('SLACK_CLIENT_ID')
SLACK_CLIENT_SECRET = os.environ.get('SLACK_CLIENT_SECRET')

# OAuth URLs
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'

SLACK_AUTH_URL = 'https://slack.com/oauth/v2/authorize'
SLACK_TOKEN_URL = 'https://slack.com/api/oauth.v2.access'

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def require_auth(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get current authenticated user"""
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])


def hash_token(token):
    """Hash a token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'auth'
    }), 200


# ============================================================================
# HOMEPAGE & PUBLIC PAGES
# ============================================================================

@app.route('/')
def index():
    """Serve the homepage"""
    return render_template('index.html')


@app.route('/about')
def about():
    """Serve the about page"""
    return render_template('about.html')


# ============================================================================
# USER AUTHENTICATION ROUTES
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        # Check if user exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'User already exists'}), 400

        # Create new user
        user = User(email=email, name=name)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()

        # Create session
        session['user_id'] = user.id
        
        return jsonify({
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Create session
        session['user_id'] = user.id
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_me():
    """Get current user info"""
    user = get_current_user()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'created_at': user.created_at.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
    }), 200


# ============================================================================
# GOOGLE OAUTH ROUTES
# ============================================================================

@app.route('/api/auth/google/authorize', methods=['GET'])
@require_auth
def google_authorize():
    """Initiate Google OAuth flow"""
    try:
        # Build redirect URI
        redirect_uri = request.args.get('redirect_uri', request.url_root + 'api/auth/google/callback')
        
        # Scopes for Google Calendar and Drive
        scopes = [
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        
        # Build authorization URL
        params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(scopes),
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent',
            'state': secrets.token_urlsafe(32)
        }
        
        # Store state in session
        session['google_oauth_state'] = params['state']
        
        auth_url = f"{GOOGLE_AUTH_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        
        return jsonify({'authorization_url': auth_url}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/google/callback', methods=['GET'])
@require_auth
def google_callback():
    """Handle Google OAuth callback"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
        # Verify state
        if state != session.get('google_oauth_state'):
            return jsonify({'error': 'Invalid state'}), 400
        
        # Exchange code for tokens
        redirect_uri = request.url_root + 'api/auth/google/callback'
        
        token_response = requests.post(GOOGLE_TOKEN_URL, data={
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        })
        
        if token_response.status_code != 200:
            return jsonify({'error': 'Failed to exchange code'}), 400
        
        tokens = token_response.json()
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token')
        expires_in = tokens.get('expires_in', 3600)
        
        # Get user info
        user_response = requests.get(
            GOOGLE_USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if user_response.status_code != 200:
            return jsonify({'error': 'Failed to get user info'}), 400
        
        user_info = user_response.json()
        
        # Store integration
        user = get_current_user()
        
        # Check for existing integration
        integration = Integration.query.filter_by(
            user_id=user.id,
            provider='google'
        ).first()
        
        if integration:
            # Update existing
            integration.access_token = hash_token(access_token)
            integration.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            integration.provider_data = user_info
        else:
            # Create new
            integration = Integration(
                user_id=user.id,
                provider='google',
                access_token=hash_token(access_token),
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                provider_data=user_info
            )
            db.session.add(integration)
        
        # Store refresh token if available
        if refresh_token:
            refresh_token_obj = RefreshToken.query.filter_by(
                integration_id=integration.id
            ).first()
            
            if refresh_token_obj:
                refresh_token_obj.token = hash_token(refresh_token)
            else:
                refresh_token_obj = RefreshToken(
                    integration_id=integration.id,
                    token=hash_token(refresh_token)
                )
                db.session.add(refresh_token_obj)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Google integration successful',
            'integration': {
                'id': integration.id,
                'provider': integration.provider,
                'connected': True
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# SLACK OAUTH ROUTES
# ============================================================================

@app.route('/api/auth/slack/authorize', methods=['GET'])
@require_auth
def slack_authorize():
    """Initiate Slack OAuth flow"""
    try:
        redirect_uri = request.args.get('redirect_uri', request.url_root + 'api/auth/slack/callback')
        
        # Slack scopes
        scopes = [
            'channels:history',
            'channels:read',
            'groups:history',
            'groups:read',
            'im:history',
            'im:read',
            'mpim:history',
            'mpim:read',
            'users:read'
        ]
        
        params = {
            'client_id': SLACK_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'scope': ','.join(scopes),
            'state': secrets.token_urlsafe(32)
        }
        
        session['slack_oauth_state'] = params['state']
        
        auth_url = f"{SLACK_AUTH_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        
        return jsonify({'authorization_url': auth_url}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/slack/callback', methods=['GET'])
@require_auth
def slack_callback():
    """Handle Slack OAuth callback"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
        if state != session.get('slack_oauth_state'):
            return jsonify({'error': 'Invalid state'}), 400
        
        redirect_uri = request.url_root + 'api/auth/slack/callback'
        
        token_response = requests.post(SLACK_TOKEN_URL, data={
            'code': code,
            'client_id': SLACK_CLIENT_ID,
            'client_secret': SLACK_CLIENT_SECRET,
            'redirect_uri': redirect_uri
        })
        
        if token_response.status_code != 200:
            return jsonify({'error': 'Failed to exchange code'}), 400
        
        tokens = token_response.json()
        
        if not tokens.get('ok'):
            return jsonify({'error': tokens.get('error', 'Unknown error')}), 400
        
        access_token = tokens.get('access_token')
        team_info = tokens.get('team', {})
        
        user = get_current_user()
        
        integration = Integration.query.filter_by(
            user_id=user.id,
            provider='slack'
        ).first()
        
        if integration:
            integration.access_token = hash_token(access_token)
            integration.provider_data = team_info
        else:
            integration = Integration(
                user_id=user.id,
                provider='slack',
                access_token=hash_token(access_token),
                provider_data=team_info
            )
            db.session.add(integration)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Slack integration successful',
            'integration': {
                'id': integration.id,
                'provider': integration.provider,
                'connected': True
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# INTEGRATION MANAGEMENT ROUTES
# ============================================================================

@app.route('/api/integrations', methods=['GET'])
@require_auth
def get_integrations():
    """Get all user integrations"""
    try:
        user = get_current_user()
        integrations = Integration.query.filter_by(user_id=user.id).all()
        
        return jsonify({
            'integrations': [{
                'id': i.id,
                'provider': i.provider,
                'connected': i.is_active,
                'connected_at': i.created_at.isoformat(),
                'provider_data': i.provider_data
            } for i in integrations]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/integrations/<int:integration_id>', methods=['DELETE'])
@require_auth
def delete_integration(integration_id):
    """Delete an integration"""
    try:
        user = get_current_user()
        integration = Integration.query.filter_by(
            id=integration_id,
            user_id=user.id
        ).first()
        
        if not integration:
            return jsonify({'error': 'Integration not found'}), 404
        
        db.session.delete(integration)
        db.session.commit()
        
        return jsonify({'message': 'Integration deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# GUNICORN APPLICATION
# ============================================================================

class StandaloneApplication(BaseApplication):
    """Custom Gunicorn application"""

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        """Load Gunicorn configuration"""
        config = {
            key: value for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        """Load the Flask application"""
        return self.application


# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

def create_app():
    """Create and configure the Flask application"""
    with app.app_context():
        # Create tables if they don't exist
        create_tables()
    
    return app


if __name__ == '__main__':
    # Configuration options
    options = {
        'bind': f"0.0.0.0:{os.environ.get('PORT', '10000')}",
        'workers': int(os.environ.get('WEB_CONCURRENCY', '2')),
        'worker_class': 'sync',
        'timeout': 120,
        'keepalive': 5,
        'accesslog': '-',
        'errorlog': '-',
        'loglevel': 'info'
    }
    
    # Create and run application
    application = create_app()
    StandaloneApplication(application, options).run()
