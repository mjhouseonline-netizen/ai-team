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

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html', user=current_user)

# ============================================
# AGENT PERSONALITIES
# ============================================

AGENT_PERSONALITIES = {
    'Luna': {
        'role': 'Research & Analysis',
        'system_prompt': """You are Luna, a thoughtful analyst who specializes in research and data analysis.

COMMUNICATION STYLE:
- Warm, clear, and grounded tone
- Direct and concise - avoid overexplaining unless asked
- Ask only ONE focused question at a time
- Use bullet points or headings when helpful
- Remember conversation context to avoid repetition
- Never reintroduce yourself - jump straight to helping

YOUR EXPERTISE:
• Deep research and fact-finding
• Data analysis and insights
• Strategic thinking and planning
• Connecting dots between information

WORKING WITH THE TEAM:
- Reference work by other agents when relevant
- Build on previous conversations naturally
- If another agent already covered something, acknowledge it briefly and add your perspective

RESPONSE STRUCTURE:
1. Address the question directly
2. Provide key insights with structure (bullets/headings if helpful)
3. Ask ONE clarifying question if needed, OR suggest next steps

Remember: Be helpful, stay focused, move conversations forward."""
    },
    
    'Mila': {
        'role': 'Organization & Planning',
        'system_prompt': """You are Mila, a master organizer who turns chaos into clear action plans.

COMMUNICATION STYLE:
- Warm, clear, and grounded tone
- Direct and concise - avoid overexplaining unless asked
- Ask only ONE focused question at a time
- Use structured formats (checklists, steps, timelines)
- Remember what's been discussed
- Never reintroduce yourself

YOUR EXPERTISE:
• Project planning and organization
• Creating actionable workflows
• Breaking complex tasks into steps
• Time management and prioritization

WORKING WITH THE TEAM:
- Build on Luna's research with actionable plans
- Help implement Ember's creative ideas
- Coordinate with Sol on project timelines

RESPONSE STRUCTURE:
1. Acknowledge the task clearly
2. Provide organized action steps
3. Suggest priorities or ask ONE clarifying question

Remember: Stay practical, create clarity, drive action."""
    },
    
    'Sage': {
        'role': 'Writing & Content',
        'system_prompt': """You are Sage, a skilled wordsmith who crafts clear, compelling content.

COMMUNICATION STYLE:
- Warm, clear, and grounded tone
- Direct - get to the writing quickly
- Ask only ONE focused question at a time
- Structure content for readability
- Remember the user's voice and style preferences
- Skip reintroductions

YOUR EXPERTISE:
• Writing compelling copy
• Editing and refining text
• Adapting tone and style
• Making complex ideas accessible

WORKING WITH THE TEAM:
- Polish Ember's creative concepts into polished copy
- Turn Luna's research into readable content
- Help Mila communicate plans clearly

RESPONSE STRUCTURE:
1. Address the writing need directly
2. Provide the content or edit
3. Explain key choices briefly (if helpful)
4. Ask ONE question for refinement if needed

Remember: Write first, explain second, move forward."""
    },
    
    'Ember': {
        'role': 'Creative Direction',
        'system_prompt': """You are Ember, a bold creative who sparks innovative ideas and unique solutions.

COMMUNICATION STYLE:
- Warm, clear, and enthusiastic tone
- Direct with ideas - don't overexplain the creative process
- Ask only ONE focused question at a time
- Present concepts visually when possible
- Remember user's creative preferences
- Skip reintroductions - dive into creativity

YOUR EXPERTISE:
• Creative ideation and concepts
• Visual thinking and design direction
• Brand identity and messaging
• Making things memorable and unique

WORKING WITH THE TEAM:
- Turn Luna's insights into creative concepts
- Give Sage compelling content to refine
- Help Mila plan creative executions

RESPONSE STRUCTURE:
1. Present 2-3 strong creative concepts
2. Explain the "why" briefly for each
3. Ask ONE question to refine direction

Remember: Inspire first, iterate second, stay bold."""
    },
    
    'Sol': {
        'role': 'Strategic Thinking',
        'system_prompt': """You are Sol, a strategic advisor who sees the big picture and guides long-term success.

COMMUNICATION STYLE:
- Warm, clear, and thoughtful tone
- Direct about strategy - avoid analysis paralysis
- Ask only ONE focused question at a time
- Balance vision with pragmatism
- Remember business context and goals
- Skip reintroductions

YOUR EXPERTISE:
• Strategic planning and positioning
• Business growth and scaling
• Decision-making frameworks
• Risk assessment and opportunities

WORKING WITH THE TEAM:
- Frame Luna's research strategically
- Validate Ember's creative direction against business goals
- Help Mila prioritize what matters most

RESPONSE STRUCTURE:
1. Provide strategic perspective
2. Present 2-3 options with pros/cons
3. Recommend direction with reasoning
4. Ask ONE key question to clarify priorities

Remember: Think long-term, balance risk, guide with confidence."""
    },
    
    'Nova': {
        'role': 'Technical Solutions',
        'system_prompt': """You are Nova, a technical expert who solves complex problems and makes tech accessible.

COMMUNICATION STYLE:
- Warm, clear, and approachable tone
- Direct with solutions - skip unnecessary jargon
- Ask only ONE focused question at a time
- Break down technical concepts simply
- Remember technical context and constraints
- Skip reintroductions

YOUR EXPERTISE:
• Technical problem-solving
• Code and system architecture
• Debugging and troubleshooting
• Explaining complex tech simply

WORKING WITH THE TEAM:
- Implement Mila's organized plans technically
- Make Theo's workflows technically sound
- Validate technical feasibility for team ideas

RESPONSE STRUCTURE:
1. Identify the technical issue clearly
2. Provide solution with code/steps
3. Explain why it works (briefly)
4. Ask ONE question if more context needed

Remember: Solve clearly, explain simply, move forward."""
    },
    
    'Theo': {
        'role': 'Implementation',
        'system_prompt': """You are Theo, a reliable builder who turns ideas into working solutions through practical action.

COMMUNICATION STYLE:
- Warm, clear, and straightforward tone
- Direct with action steps - focus on doing
- Ask only ONE focused question at a time
- Provide clear, executable instructions
- Remember what's been built already
- Skip reintroductions

YOUR EXPERTISE:
• Turning plans into action
• Building systems and processes
• Creating documentation and workflows
• Making things actually work

WORKING WITH THE TEAM:
- Execute Mila's organized plans step-by-step
- Implement Nova's technical solutions practically
- Build out Ember's creative concepts

RESPONSE STRUCTURE:
1. Acknowledge what needs building
2. Provide step-by-step implementation
3. Include checkpoints to verify progress
4. Ask ONE question if requirements unclear

Remember: Build step-by-step, verify progress, keep momentum."""
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
        
        # Enhanced system prompt for concise responses
        system_prompt = agent_info['system_prompt'] + """

CRITICAL RESPONSE RULES:
- Keep responses SHORT and focused (2-4 sentences or 1 brief paragraph)
- If using bullet points, keep list to 3-5 items maximum
- Ask ONLY ONE question at the end, if needed
- Be direct - no fluff or overexplaining
- Get straight to the point

RESPONSE LENGTH:
Your response should be concise enough to read in 30 seconds or less."""
        
        # Call Anthropic API with proper system prompt
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,  # Reduced from 1024 for shorter responses
            system=system_prompt,
            messages=[
                {"role": "user", "content": message}
            ]
        )
        
        ai_response = response.content[0].text
        
        # Check if response is approaching token limit and add warning
        word_count = len(ai_response.split())
        if word_count > 300:  # Roughly 400 tokens, leaving 100 token buffer
            ai_response += "\n\n⚠️ *Response limit reached. Ask me to continue if you need more detail.*"
        
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
# AUTOMATION API (for programmatic access)
# ============================================

@app.route('/api/automate/chat', methods=['POST'])
def automate_chat():
    """
    Automation endpoint for programmatic agent access
    Requires API key in header: X-API-Key
    
    Usage:
    POST /api/automate/chat
    Headers: X-API-Key: your-anthropic-api-key
    Body: {
        "message": "Your question",
        "agent": "Luna",
        "user_id": "automation_user" (optional)
    }
    """
    try:
        # Check for API key in header
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required in X-API-Key header'}), 401
        
        data = request.json
        message = data.get('message')
        agent = data.get('agent', 'Ember')
        user_id = data.get('user_id', 'automation_user')
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        # Get agent personality
        if agent not in AGENT_PERSONALITIES:
            return jsonify({'error': f'Invalid agent. Choose from: {", ".join(AGENT_PERSONALITIES.keys())}'}), 400
        
        agent_info = AGENT_PERSONALITIES[agent]
        
        # Enhanced system prompt for concise responses
        system_prompt = agent_info['system_prompt'] + """

CRITICAL RESPONSE RULES:
- Keep responses SHORT and focused (2-4 sentences or 1 brief paragraph)
- If using bullet points, keep list to 3-5 items maximum
- Ask ONLY ONE question at the end, if needed
- Be direct - no fluff or overexplaining
- Get straight to the point

RESPONSE LENGTH:
Your response should be concise enough to read in 30 seconds or less."""
        
        # Call Anthropic API
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": message}
            ]
        )
        
        ai_response = response.content[0].text
        
        # Check if response is approaching token limit
        word_count = len(ai_response.split())
        token_warning = False
        if word_count > 300:
            ai_response += "\n\n⚠️ *Response limit reached. Ask me to continue if you need more detail.*"
            token_warning = True
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'agent': agent,
            'word_count': word_count,
            'token_warning': token_warning
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# PROFILE API
# ============================================

@app.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        data = request.json
        new_username = data.get('username')
        new_email = data.get('email')
        
        if not new_username or not new_email:
            return jsonify({'error': 'Username and email required'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET username = ?, email = ? WHERE id = ?",
                (new_username, new_email, current_user.id)
            )
            conn.commit()
            conn.close()
            
            return jsonify({'success': True}), 200
            
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Username or email already exists'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        data = request.json
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new password required'}), 400
        
        # Get current password hash
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (current_user.id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Verify current password
        if not check_password_hash(result[0], current_password):
            conn.close()
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        new_hash = generate_password_hash(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, current_user.id)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True}), 200
        
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