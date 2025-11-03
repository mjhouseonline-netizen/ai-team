"""
User Authentication System
Handles user registration, login, and session management
"""

from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import secrets

class User(UserMixin):
    """User model for authentication"""
    def __init__(self, id, email, username, api_key=None):
        self.id = id
        self.email = email
        self.username = username
        self.api_key = api_key

class AuthManager:
    """Manages user authentication and database operations"""
    
    def __init__(self, db_path='users.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize users database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                api_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # User sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Usage tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                agent_name TEXT,
                request_count INTEGER DEFAULT 0,
                date DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_user(self, username, email, password):
        """Create a new user account"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Hash the password
            password_hash = generate_password_hash(password)
            
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return user_id
        except sqlite3.IntegrityError:
            return None  # User already exists
    
    def get_user_by_email(self, email):
        """Get user by email"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, email, api_key FROM users WHERE email = ? AND is_active = 1",
            (email,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return User(id=result[0], username=result[1], email=result[2], api_key=result[3])
        return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, email, api_key FROM users WHERE id = ? AND is_active = 1",
            (user_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return User(id=result[0], username=result[1], email=result[2], api_key=result[3])
        return None
    
    def verify_password(self, email, password):
        """Verify user password"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT password_hash FROM users WHERE email = ? AND is_active = 1",
            (email,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result and check_password_hash(result[0], password):
            return True
        return False
    
    def update_last_login(self, user_id):
        """Update user's last login timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now(), user_id)
        )
        
        conn.commit()
        conn.close()
    
    def save_api_key(self, user_id, api_key):
        """Save user's API key (encrypted in production!)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET api_key = ? WHERE id = ?",
            (api_key, user_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_user_api_key(self, user_id):
        """Get user's saved API key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT api_key FROM users WHERE id = ?",
            (user_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def track_usage(self, user_id, agent_name):
        """Track user's agent usage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().date()
        
        # Check if record exists for today
        cursor.execute(
            "SELECT id, request_count FROM usage_tracking WHERE user_id = ? AND agent_name = ? AND date = ?",
            (user_id, agent_name, today)
        )
        
        result = cursor.fetchone()
        
        if result:
            # Update existing record
            cursor.execute(
                "UPDATE usage_tracking SET request_count = request_count + 1 WHERE id = ?",
                (result[0],)
            )
        else:
            # Create new record
            cursor.execute(
                "INSERT INTO usage_tracking (user_id, agent_name, request_count, date) VALUES (?, ?, 1, ?)",
                (user_id, agent_name, today)
            )
        
        conn.commit()
        conn.close()
    
    def get_user_usage(self, user_id, days=30):
        """Get user's usage statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT agent_name, SUM(request_count) as total, date 
               FROM usage_tracking 
               WHERE user_id = ? AND date >= date('now', '-' || ? || ' days')
               GROUP BY agent_name
               ORDER BY total DESC""",
            (user_id, days)
        )
        
        results = cursor.fetchall()
        conn.close()
        
        return [{"agent": r[0], "count": r[1]} for r in results]

def setup_login_manager(app):
    """Configure Flask-Login"""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    auth_manager = AuthManager()
    
    @login_manager.user_loader
    def load_user(user_id):
        return auth_manager.get_user_by_id(int(user_id))
    
    return auth_manager
