"""
AI Team Web Application with Authentication
Includes user signup, login, and session management
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import os
import secrets
from ai_team import AITeam
from auth import setup_login_manager, AuthManager

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Setup authentication
auth_manager = setup_login_manager(app)

# Global team instance
team = None

@app.route('/')
def index():
    """Home page - redirect based on auth status"""
    if current_user.is_authenticated:
        return render_template('dashboard.html', user=current_user)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        data = request.json
        email = data.get('email')
        password = data.get('password')
        remember = data.get('remember', False)
        
        if auth_manager.verify_password(email, password):
            user = auth_manager.get_user_by_email(email)
            if user:
                login_user(user, remember=remember)
                auth_manager.update_last_login(user.id)
                return jsonify({'success': True, 'redirect': url_for('index')})
        
        return jsonify({'success': False, 'error': 'Invalid email or password'}), 401
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        # Validation
        if not username or not email or not password:
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        
        if len(password) < 8:
            return jsonify({'success': False, 'error': 'Password must be at least 8 characters'}), 400
        
        # Create user
        user_id = auth_manager.create_user(username, email, password)
        
        if user_id:
            return jsonify({'success': True, 'redirect': url_for('login')})
        else:
            return jsonify({'success': False, 'error': 'Email already registered'}), 400
    
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    return render_template('dashboard.html', user=current_user)

@app.route('/api/init', methods=['POST'])
@login_required
def init_team():
    """Initialize the AI team with central API key"""
    global team
    
    # Use central API key from environment variable
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        return jsonify({'error': 'Service not configured. Please contact administrator.'}), 500
    
    try:
        team = AITeam(api_key=api_key)
        
        agents = team.list_agents()
        return jsonify({
            'success': True,
            'agents': agents
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Process a chat request"""
    global team
    
    if team is None:
        # Initialize with central API key
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            team = AITeam(api_key=api_key)
        else:
            return jsonify({'error': 'Service not configured. Please contact administrator.'}), 500
    
    data = request.json
    message = data.get('message')
    agent = data.get('agent')
    project_id = data.get('project_id')
    
    if not message:
        return jsonify({'error': 'Message required'}), 400
    
    try:
        result = team.process_request(
            message,
            specific_agent=agent if agent and agent != 'auto' else None,
            project_id=project_id
        )
        
        # Track usage
        for agent_name in result.keys():
            auth_manager.track_usage(current_user.id, agent_name)
        
        return jsonify({
            'success': True,
            'responses': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/context', methods=['POST'])
@login_required
def set_context():
    """Set context for the team"""
    global team
    
    if team is None:
        return jsonify({'error': 'Team not initialized'}), 400
    
    data = request.json
    key = data.get('key')
    value = data.get('value')
    
    if not key or not value:
        return jsonify({'error': 'Key and value required'}), 400
    
    try:
        team.set_context(key, value, current_user.username)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/context', methods=['GET'])
@login_required
def get_context():
    """Get all context"""
    global team
    
    if team is None:
        return jsonify({'error': 'Team not initialized'}), 400
    
    try:
        context = team.shared_memory.get_all_context()
        return jsonify({
            'success': True,
            'context': context
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    """Get recent work history"""
    global team
    
    if team is None:
        return jsonify({'error': 'Team not initialized'}), 400
    
    try:
        history = team.get_recent_work(limit=10)
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/usage', methods=['GET'])
@login_required
def get_usage():
    """Get user's usage statistics"""
    try:
        days = request.args.get('days', 30, type=int)
        usage = auth_manager.get_user_usage(current_user.id, days)
        return jsonify({
            'success': True,
            'usage': usage
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Get or update user profile"""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'user': {
                'username': current_user.username,
                'email': current_user.email,
                'has_api_key': bool(current_user.api_key)
            }
        })
    
    # POST - update profile
    data = request.json
    api_key = data.get('api_key')
    
    if api_key:
        auth_manager.save_api_key(current_user.id, api_key)
        return jsonify({'success': True, 'message': 'API key saved'})
    
    return jsonify({'success': True})

if __name__ == '__main__':
    print("\n🚀 Starting AI Team Web Interface...")
    print("📱 Opening in your browser...")
    print("\n⚠️  To stop: Press Ctrl+C in this window\n")
    
    # Get port from environment variable (for deployment) or use 5000 for local
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0' if os.environ.get('PORT') else '127.0.0.1'
    
    # Only open browser for local development
    if not os.environ.get('PORT'):
        import webbrowser
        import threading
        
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open('http://127.0.0.1:5000')
        
        threading.Thread(target=open_browser).start()
    
    app.run(debug=False, host=host, port=port)
