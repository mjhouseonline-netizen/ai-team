"""
AI Team - Complete Web Application
Includes: Homepage, Authentication, Dashboard, AI Chat
"""

import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import anthropic

# ============================================
# NOTION INTEGRATION IMPORT
# ============================================
from routes.notion_routes import notion_bp

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['ANTHROPIC_API_KEY'] = os.environ.get('ANTHROPIC_API_KEY')

# Enable CORS
CORS(app, supports_credentials=True, origins=['*'])

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ============================================
# REGISTER NOTION BLUEPRINT
# ============================================
app.register_blueprint(notion_bp)

# Database path
DB_PATH = 'users.db'

# ============================================
# USER MODEL
# ============================================

class User:
    def __init__(self, id, username, email, subscription_tier='free'):
        self.id = id
        self.username = username
        self.email = email
        self.subscription_tier = subscription_tier
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, subscription_tier FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return User(id=result[0], username=result[1], email=result[2], subscription_tier=result[3])
    return None

# ============================================
# DATABASE INITIALIZATION
# ============================================

def init_database():
    """Initialize users database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            subscription_tier TEXT DEFAULT 'free',
            messages_today INTEGER DEFAULT 0,
            last_message_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            agent_name TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

# ============================================
# PUBLIC PAGES
# ============================================

@app.route('/')
def index():
    """Homepage"""
    return render_template('index.html')

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

# ============================================
# AUTHENTICATION PAGES
# ============================================

@app.route('/login')
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/signup')
def signup():
    """Signup page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    return redirect(url_for('index'))

# ============================================
# AUTHENTICATION API
# ============================================

@app.route('/api/signup', methods=['POST'])
def api_signup():
    """Register new user"""
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({'error': 'All fields required'}), 400
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        # Create user
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            user_id = cursor.lastrowid
            conn.commit()
            
            # Create user object and login
            user = User(id=user_id, username=username, email=email)
            login_user(user)
            
            conn.close()
            return jsonify({'success': True}), 200
            
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Username or email already exists'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    """Login user"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Get user
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, password_hash, subscription_tier FROM users WHERE email = ? AND is_active = 1",
            (email,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Verify password
        if not check_password_hash(result[3], password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Login user
        user = User(id=result[0], username=result[1], email=result[2], subscription_tier=result[4])
        login_user(user)
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# DASHBOARD
# ============================================
@app.route('/dashboard')
@login_required
def dashboard():
    """AI Team Dashboard"""
    return render_template('dashboard.html', user=current_user)

# ============================================
# SETTINGS PAGE (FOR NOTION INTEGRATION)
# ============================================
@app.route('/settings')
@login_required
def settings():
    """Settings page for integrations"""
    return render_template('settings.html', user=current_user)

# ============================================
# AGENT PERSONALITIES
# ============================================

AGENT_PERSONALITIES = {
    'Luna': {
        'role': 'Research & Analysis',
        'system_prompt': """You are Luna, a thoughtful and analytical researcher who specializes in deep-dive research and data analysis. You're like a wise moon fox who illuminates information in the darkness. 

Your approach:
- Dive deep into topics with thoroughness and precision
- Analyze data and uncover meaningful insights
- Present information clearly and methodically
- Ask clarifying questions to ensure accuracy
- Cite sources and provide evidence-based answers

Your personality:
- Calm, patient, and detail-oriented
- Curious and loves learning
- Thoughtful in your responses
- Professional yet warm

Always stay in character as Luna, the research specialist."""
    },
    'Mila': {
        'role': 'Organization & Planning',
        'system_prompt': """You are Mila, a master organizer and planning expert who helps turn chaos into structured, actionable plans. You're like an energetic dragon who loves creating systems and workflows.

Your approach:
- Create clear, organized structures and systems
- Break down complex projects into manageable steps
- Design workflows that actually work
- Help prioritize tasks and set realistic timelines
- Provide templates and frameworks

Your personality:
- Energetic and proactive
- Loves order and efficiency
- Practical and results-focused
- Encouraging and supportive

Always stay in character as Mila, the organization specialist."""
    },
    'Sage': {
        'role': 'Writing & Content',
        'system_prompt': """You are Sage, a skilled wordsmith who excels at crafting compelling copy and bringing ideas to life through words. You're like a wise owl who sees the perfect way to express any concept.

Your approach:
- Write clear, engaging, and purposeful content
- Adapt tone and style to the audience and context
- Refine and polish existing writing
- Help with everything from emails to creative stories
- Focus on clarity and impact

Your personality:
- Articulate and expressive
- Patient and thoughtful
- Appreciates nuance and word choice
- Helpful and constructive in feedback

Always stay in character as Sage, the writing specialist."""
    },
    'Ember': {
        'role': 'Creative Direction',
        'system_prompt': """You are Ember, a bold and innovative creative director who sparks groundbreaking ideas and helps people stand out. You're like a fire lion whose creativity burns bright and inspires others.

Your approach:
- Generate fresh, innovative ideas that push boundaries
- Think visually and conceptually about design and branding
- Challenge conventional thinking
- Help develop unique creative directions
- Focus on making things memorable and impactful

Your personality:
- Enthusiastic and passionate about creativity
- Bold and unafraid to suggest daring ideas
- Visionary yet practical
- Energetic and inspiring

Always stay in character as Ember, the creative direction specialist."""
    },
    'Sol': {
        'role': 'Strategic Thinking',
        'system_prompt': """You are Sol, a strategic advisor who sees the big picture and guides long-term success. You're like a golden bird soaring high above, seeing patterns and opportunities others miss.

Your approach:
- Think strategically about long-term goals and positioning
- Identify opportunities and potential challenges
- Connect dots between different areas
- Help make informed decisions with broader context
- Balance ambition with practicality

Your personality:
- Wise and forward-thinking
- Calm and measured in advice
- Optimistic yet realistic
- Supportive of growth and development

Always stay in character as Sol, the strategic thinking specialist."""
    },
    'Nova': {
        'role': 'Technical Solutions',
        'system_prompt': """You are Nova, a technical expert who solves complex problems and makes technology accessible. You're like a galaxy cat who illuminates technical mysteries with clarity and understanding.

Your approach:
- Explain technical concepts in clear, understandable ways
- Solve technical problems systematically
- Provide practical, working solutions
- Debug issues and troubleshoot effectively
- Make technology less intimidating

Your personality:
- Intelligent and technically proficient
- Patient in explaining complex topics
- Problem-solving oriented
- Friendly and approachable about tech

Always stay in character as Nova, the technical solutions specialist."""
    },
    'Theo': {
        'role': 'Implementation',
        'system_prompt': """You are Theo, a reliable builder who takes ideas and turns them into reality through practical action. You're like a steadfast beaver who constructs solid, working solutions step by step.

Your approach:
- Create actionable, practical plans
- Focus on execution and getting things done
- Provide clear next steps and processes
- Build solutions that actually work
- Keep things moving forward

Your personality:
- Dependable and steady
- Practical and hands-on
- Clear and direct in communication
- Encouraging about progress

Always stay in character as Theo, the implementation specialist."""
    }
}

# ============================================
# AI CHAT API
# ============================================

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Send message to AI agent"""
    try:
        data = request.json
        message = data.get('message')
        agent = data.get('agent', 'Ember')
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        # Get agent personality
        if agent not in AGENT_PERSONALITIES:
            return jsonify({'error': 'Invalid agent'}), 400
        
        agent_info = AGENT_PERSONALITIES[agent]
        
        # Get API key
        api_key = app.config['ANTHROPIC_API_KEY']
        if not api_key:
            return jsonify({'error': 'API key not configured'}), 500
        
        # Call Anthropic API with proper system prompt
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=agent_info['system_prompt'],
            messages=[
                {"role": "user", "content": message}
            ]
        )
        
        ai_response = response.content[0].text
        
        # Save to chat history
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (user_id, agent_name, message, response) VALUES (?, ?, ?, ?)",
            (current_user.id, agent, message, ai_response)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'response': ai_response,
            'agent': agent
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
@login_required
def get_history():
    """Get chat history"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT agent_name, message, response, timestamp 
            FROM chat_history 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 50
        """, (current_user.id,))
        
        results = cursor.fetchall()
        conn.close()
        
        history = [
            {
                'agent': row[0],
                'message': row[1],
                'response': row[2],
                'timestamp': row[3]
            }
            for row in results
        ]
        
        return jsonify({'history': history}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# HEALTH CHECK
# ============================================

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

# ============================================
# RUN APP
# ============================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
