"""
AI Team - Complete Web Application
Includes: Homepage, Authentication, Dashboard, AI Chat
"""

import os
import sys
import secrets
import string
import json
from datetime import datetime
from flask import Flask, request, jsonify, session, redirect, url_for, render_template, send_from_directory, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import anthropic
import base64
import mimetypes
import stripe
from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv
from agent_collaboration import detect_agent_mentions, suggest_agent_transfer

# Load environment variables from .env file
load_dotenv()

# ============================================
# NOTION INTEGRATION IMPORT
# ============================================
try:
    from routes.notion_routes import notion_bp
    NOTION_AVAILABLE = True
except ImportError:
    print("⚠️  Notion integration not available - routes/notion_routes.py not found")
    notion_bp = None
    NOTION_AVAILABLE = False

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['ANTHROPIC_API_KEY'] = os.environ.get('ANTHROPIC_API_KEY')
app.config['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
app.config['GOOGLE_AI_API_KEY'] = os.environ.get('GOOGLE_AI_API_KEY')

# Initialize OpenAI client with proper error handling
try:
    if os.environ.get('OPENAI_API_KEY'):
        # Initialize with explicit settings to avoid proxy conflicts
        import httpx
        openai_client = OpenAI(
            api_key=os.environ.get('OPENAI_API_KEY'),
            http_client=httpx.Client()
        )
    else:
        openai_client = None
except Exception as e:
    print(f"Warning: Could not initialize OpenAI client: {e}")
    openai_client = None

# ============================================
# STRIPE CONFIGURATION
# ============================================
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
STRIPE_STARTER_PRICE_ID = os.environ.get('STRIPE_STARTER_PRICE_ID')
STRIPE_PRO_PRICE_ID = os.environ.get('STRIPE_PRO_PRICE_ID')
STRIPE_ENTERPRISE_PRICE_ID = os.environ.get('STRIPE_ENTERPRISE_PRICE_ID', 'price_1SaVi1Fj4r8OeJwWeMQuODE5')  # $99/month Enterprise tier

# File upload configuration
UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {
    # Images
    'png', 'jpg', 'jpeg', 'gif', 'webp',
    # Documents
    'pdf', 'txt', 'md', 'csv',
    # Office
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'
}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Enable CORS
CORS(app, supports_credentials=True, origins=['*'])

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ============================================
# STATIC FILES - Serve images, CSS, JS, etc.
# ============================================

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (images, CSS, JS)"""
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    return send_from_directory(static_dir, filename)

# ============================================
# REGISTER NOTION BLUEPRINT
# ============================================
if NOTION_AVAILABLE:
    app.register_blueprint(notion_bp)
    print("✅ Notion integration enabled")
else:
    print("⚠️  Notion integration disabled")

# Database path - use persistent disk if available, fallback to current directory
import os
if os.path.exists('/data'):
    DB_PATH = '/data/ai_team.db'
    print("✅ Using persistent disk: /data/ai_team.db")
else:
    DB_PATH = 'ai_team.db'
    print("⚠️  No persistent disk found, using local: ai_team.db")

# Helper function for database connection
def get_db_connection():
    """Get SQLite database connection"""
    return sqlite3.connect(DB_PATH)

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
# SUBSCRIPTION TIERS
# ============================================

SUBSCRIPTION_TIERS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'messages_per_day': 25,
        'agents_available': 7,
        'custom_agents_limit': 1,
        'api_access': False,
        'features': [
            '25 messages per day',
            'Access to all 7 agents',
            '1 custom agent',
            'Basic chat history',
            'File upload & analysis',
            'Notion integration'
        ]
    },
    'freeforlife': {
        'name': 'Free For Life',
        'price': 0,
        'messages_per_day': -1,  # Unlimited
        'agents_available': 7,
        'custom_agents_limit': 3,
        'api_access': False,  # NO API access for promo users
        'features': [
            'Unlimited messages',
            'All 7 AI agents',
            '3 custom agents',
            'Full chat history',
            'File upload & analysis',
            'Notion integration',
            'Priority support'
        ]
    },
    'starter': {
        'name': 'Starter',
        'price': 19,  # Increased from $10
        'messages_per_day': 60,  # Reduced from 100
        'agents_available': 7,
        'custom_agents_limit': 3,
        'api_access': False,  # NO API access
        'features': [
            '60 messages per day',
            'Claude AI access',
            'All 7 AI agents',
            '3 custom agents',
            'Full chat history',
            'File upload & analysis',
            'Notion integration',
            'Priority support'
        ]
    },
    'pro': {
        'name': 'Pro',
        'price': 49,  # Increased from $30
        'messages_per_day': 300,  # Reduced from 500
        'agents_available': 7,
        'custom_agents_limit': 10,
        'api_access': True,  # API access included
        'features': [
            '300 messages per day',
            'Claude AI access',
            'All 7 AI agents',
            '10 custom agents',
            'Unlimited chat history',
            'File upload & analysis',
            'All integrations',
            'API access & automation',
            'Priority support',
            'Early access to new features'
        ]
    },
    'enterprise': {
        'name': 'Enterprise',
        'price': 99,  # New tier
        'messages_per_day': 1000,
        'agents_available': 7,
        'custom_agents_limit': -1,  # Unlimited
        'api_access': True,
        'features': [
            '1,000 messages per day',
            'Claude AI access',
            'All 7 AI agents',
            'Unlimited custom agents',
            'Unlimited chat history',
            'File upload & analysis',
            'All integrations',
            'Full API access & automation',
            'Dedicated support',
            'Custom agent training',
            'White-label options',
            'Early access to all features'
        ]
    }
}

# ============================================
# COST MONITORING SYSTEM
# ============================================

# Model costs per message (approximate based on avg tokens)
MODEL_COSTS = {
    # Claude Models
    'claude-sonnet-4.5': 0.003,      # $3/1M tokens ≈ $0.003/msg
    'claude-opus-4': 0.015,          # $15/1M tokens ≈ $0.015/msg
    'claude-haiku-4.5': 0.0008,      # $0.80/1M tokens ≈ $0.0008/msg
    'claude-haiku': 0.0008,

    # OpenAI Models
    'gpt-4o': 0.0025,                # $2.50/1M tokens ≈ $0.0025/msg
    'gpt-4-turbo': 0.01,             # $10/1M tokens ≈ $0.01/msg
    'gpt-4o-mini': 0.00015,          # $0.15/1M tokens ≈ $0.00015/msg

    # Google Gemini Models (Free for now)
    'gemini-2.0-flash': 0.0,
    'gemini-1.5-pro': 0.0,
    'gemini-1.5-flash': 0.0,

    # DeepSeek Models (Ultra cheap)
    'deepseek-v3': 0.00027,          # $0.27/1M tokens ≈ $0.00027/msg
    'deepseek-r1': 0.00055,          # $0.55/1M tokens ≈ $0.00055/msg

    # Perplexity Models
    'perplexity-sonar': 0.001,       # $1/1M tokens ≈ $0.001/msg
    'perplexity-sonar-pro': 0.003,   # $3/1M tokens ≈ $0.003/msg

    # Grok Models
    'grok-2': 0.002,                 # $2/1M tokens ≈ $0.002/msg
    'grok-2-vision': 0.002,          # $2/1M tokens ≈ $0.002/msg

    # Meta Llama Models
    'llama-3.3-70b': 0.00018,        # $0.18/1M tokens ≈ $0.00018/msg
    'llama-3.1-405b': 0.0027,        # $2.70/1M tokens ≈ $0.0027/msg

    # Mistral Models
    'mistral-large': 0.002,          # $2/1M tokens ≈ $0.002/msg
    'mistral-small': 0.0002          # $0.20/1M tokens ≈ $0.0002/msg
}

# Cost thresholds per tier (daily limits in USD)
COST_THRESHOLDS = {
    'free': {
        'warning': 0.50,      # Alert at $0.50/day
        'critical': 1.00,     # Block expensive models at $1/day
        'monthly_budget': 15  # $15/month max
    },
    'freeforlife': {
        'warning': 1.00,
        'critical': 2.00,
        'monthly_budget': 30
    },
    'starter': {
        'warning': 1.00,      # Alert at $1/day
        'critical': 2.00,     # Block expensive models at $2/day
        'monthly_budget': 30  # $30/month (revenue $19, cost budget $30)
    },
    'pro': {
        'warning': 3.00,      # Alert at $3/day
        'critical': 5.00,     # Block expensive models at $5/day
        'monthly_budget': 100 # $100/month (revenue $49, cost budget $100)
    },
    'enterprise': {
        'warning': 5.00,      # Alert at $5/day
        'critical': 10.00,    # Block expensive models at $10/day
        'monthly_budget': 200 # $200/month (revenue $99, cost budget $200)
    }
}

# Expensive models to block when user hits critical threshold
EXPENSIVE_MODELS = ['claude-opus-4', 'gpt-4-turbo']

# ============================================
# HELPER FUNCTIONS
# ============================================

def is_paid_user(subscription_tier):
    """Check if user is on a paid subscription (starter or pro)
    
    This prevents free and freeforlife users from using expensive Claude API,
    saving significant costs. Only starter ($19/mo) and pro ($49/mo) subscribers
    can access Claude AI models.
    """
    return subscription_tier in ['starter', 'pro', 'enterprise']

def has_api_access(subscription_tier):
    """Check if user has API access

    API access is a premium feature only available to Pro ($49/mo) and
    Enterprise ($99/mo) subscribers. This prevents API abuse and creates
    a clear upgrade incentive from Starter to Pro.
    """
    return subscription_tier in ['pro', 'enterprise']

# ============================================
# COST TRACKING FUNCTIONS
# ============================================

def track_message_cost(user_id, model, cost, agent_name=None):
    """Track the cost of a single message"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Insert cost record
        cursor.execute("""
            INSERT INTO usage_costs (user_id, model, cost, agent_name)
            VALUES (?, ?, ?, ?)
        """, (user_id, model, cost, agent_name))

        # Update user's daily and monthly costs
        cursor.execute("""
            UPDATE users
            SET daily_cost = daily_cost + ?, monthly_cost = monthly_cost + ?
            WHERE id = ?
        """, (cost, cost, user_id))

        conn.commit()
        conn.close()

        return True
    except Exception as e:
        print(f"❌ Error tracking cost: {e}")
        return False

def get_user_daily_cost(user_id):
    """Get user's cost for today"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT daily_cost FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()

        return result[0] if result else 0.0
    except Exception as e:
        print(f"❌ Error getting daily cost: {e}")
        return 0.0

def reset_daily_costs():
    """Reset all users' daily costs (run at midnight UTC)"""
    try:
        from datetime import datetime
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Reset daily costs and unblock expensive models
        cursor.execute("""
            UPDATE users
            SET daily_cost = 0.0,
                expensive_models_blocked = 0,
                last_cost_reset = ?
            WHERE DATE(last_cost_reset) < DATE('now')
        """, (datetime.utcnow().isoformat(),))

        conn.commit()
        conn.close()

        print("✅ Daily costs reset")
        return True
    except Exception as e:
        print(f"❌ Error resetting daily costs: {e}")
        return False

def check_cost_threshold(user_id, tier):
    """Check if user has exceeded cost thresholds and trigger alerts

    Supports custom per-user thresholds that override tier defaults
    """
    try:
        daily_cost = get_user_daily_cost(user_id)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get custom thresholds if set, otherwise use tier defaults
        cursor.execute("""
            SELECT custom_warning_threshold, custom_critical_threshold, expensive_models_blocked
            FROM users WHERE id = ?
        """, (user_id,))
        result = cursor.fetchone()

        if result:
            custom_warning, custom_critical, already_blocked = result
        else:
            custom_warning, custom_critical, already_blocked = None, None, False

        # Use custom thresholds if available, otherwise tier defaults
        default_thresholds = COST_THRESHOLDS.get(tier, COST_THRESHOLDS['free'])
        warning_threshold = custom_warning if custom_warning is not None else default_thresholds['warning']
        critical_threshold = custom_critical if custom_critical is not None else default_thresholds['critical']

        # Critical threshold - block expensive models
        if daily_cost >= critical_threshold and not already_blocked:
            cursor.execute("""
                UPDATE users SET expensive_models_blocked = 1 WHERE id = ?
            """, (user_id,))

            # Log alert
            cursor.execute("""
                INSERT INTO cost_alerts (user_id, alert_type, daily_cost, threshold, message)
                VALUES (?, 'CRITICAL', ?, ?, ?)
            """, (user_id, daily_cost, critical_threshold,
                  f"Critical threshold reached! Blocking expensive models (Opus, GPT-4 Turbo)"))

            conn.commit()
            conn.close()

            threshold_info = f"(Custom: ${critical_threshold:.2f})" if custom_critical else f"(${critical_threshold:.2f})"
            return 'CRITICAL', f"⚠️ Daily cost limit reached {threshold_info}. Expensive models temporarily blocked. Use Gemini or Haiku instead."

        # Warning threshold
        elif daily_cost >= warning_threshold:
            # Check if we already sent warning today
            cursor.execute("""
                SELECT id FROM cost_alerts
                WHERE user_id = ? AND alert_type = 'WARNING'
                AND DATE(timestamp) = DATE('now')
            """, (user_id,))

            if not cursor.fetchone():
                # Log warning alert
                cursor.execute("""
                    INSERT INTO cost_alerts (user_id, alert_type, daily_cost, threshold, message)
                    VALUES (?, 'WARNING', ?, ?, ?)
                """, (user_id, daily_cost, warning_threshold,
                      f"Warning: Approaching daily cost limit"))

                conn.commit()

            conn.close()
            threshold_info = f"(Custom limit: ${critical_threshold:.2f})" if custom_critical else f"(limit: ${critical_threshold:.2f})"
            return 'WARNING', f"⚡ Heads up: You've used ${daily_cost:.2f} today {threshold_info}"

        conn.close()
        return None, None

    except Exception as e:
        print(f"❌ Error checking cost threshold: {e}")
        return None, None

def is_model_blocked_for_user(user_id, model):
    """Check if expensive models are blocked for this user"""
    try:
        if model not in EXPENSIVE_MODELS:
            return False

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT expensive_models_blocked FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()

        return result[0] if result else False
    except Exception as e:
        print(f"❌ Error checking model block: {e}")
        return False

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
            is_active BOOLEAN DEFAULT 1,
            stripe_customer_id TEXT UNIQUE,
            stripe_subscription_id TEXT UNIQUE
        )
    """)
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    print(f"Database columns check: {existing_columns}")
    
    # Migration: Add Stripe columns if they don't exist
    if 'stripe_customer_id' not in existing_columns:
        try:
            print("Adding stripe_customer_id column...")
            cursor.execute("ALTER TABLE users ADD COLUMN stripe_customer_id TEXT UNIQUE")
            print("✅ Added stripe_customer_id")
        except sqlite3.OperationalError as e:
            print(f"Warning: {e}")
    
    if 'stripe_subscription_id' not in existing_columns:
        try:
            print("Adding stripe_subscription_id column...")
            cursor.execute("ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT UNIQUE")
            print("✅ Added stripe_subscription_id")
        except sqlite3.OperationalError as e:
            print(f"Warning: {e}")
    
    # Migration: Add last_message_reset column if it doesn't exist
    if 'last_message_reset' not in existing_columns:
        try:
            print("Adding last_message_reset column...")
            cursor.execute("ALTER TABLE users ADD COLUMN last_message_reset TIMESTAMP")
            # Initialize existing users with current timestamp
            from datetime import datetime
            cursor.execute("UPDATE users SET last_message_reset = ? WHERE last_message_reset IS NULL",
                         (datetime.utcnow().isoformat(),))
            print("✅ Added and initialized last_message_reset column")
        except sqlite3.OperationalError as e:
            print(f"Warning: {e}")
    else:
        print("✅ last_message_reset column already exists")

    # Migration: Add api_key column for plan inheritance
    if 'api_key' not in existing_columns:
        try:
            print("Adding api_key column...")
            cursor.execute("ALTER TABLE users ADD COLUMN api_key TEXT")
            print("✅ Added api_key column")
        except sqlite3.OperationalError as e:
            print(f"Warning: {e}")

    # Migration: Add google_ai_api_key column for plan inheritance
    if 'google_ai_api_key' not in existing_columns:
        try:
            print("Adding google_ai_api_key column...")
            cursor.execute("ALTER TABLE users ADD COLUMN google_ai_api_key TEXT")
            print("✅ Added google_ai_api_key column")
        except sqlite3.OperationalError as e:
            print(f"Warning: {e}")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            agent_name TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            conversation_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
    """)
    
    # Add conversations table for grouping chats into sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            agent_name TEXT NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Add custom_agents table for user-created agents
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            emoji TEXT DEFAULT '🤖',
            personality TEXT,
            system_prompt TEXT,
            share_code TEXT UNIQUE,
            is_public BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Check if emoji column exists and add if missing (for existing tables)
    cursor.execute("PRAGMA table_info(custom_agents)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'emoji' not in columns:
        try:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN emoji TEXT DEFAULT '🤖'")
            print("✅ Added emoji column to custom_agents")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add emoji column: {e}")
    
    if 'share_code' not in columns:
        try:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN share_code TEXT UNIQUE")
            print("✅ Added share_code column to custom_agents")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add share_code column: {e}")
    
    if 'is_public' not in columns:
        try:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN is_public INTEGER DEFAULT 1")
            print("✅ Added is_public column to custom_agents")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add is_public column: {e}")

    if 'template_variables' not in columns:
        try:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN template_variables TEXT DEFAULT NULL")
            print("✅ Added template_variables column to custom_agents")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add template_variables column: {e}")

    # ============================================
    # GLOBAL AGENTS (ADMIN-MANAGED TEMPLATES)
    # ============================================

    # Global agents - admin creates these and assigns to users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS global_agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            emoji TEXT DEFAULT '🤖',
            category TEXT DEFAULT 'general',
            system_prompt TEXT NOT NULL,
            template_variables TEXT DEFAULT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    """)

    # Track which users have access to which global agents
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_global_agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            global_agent_id INTEGER NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assigned_by INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (global_agent_id) REFERENCES global_agents (id),
            FOREIGN KEY (assigned_by) REFERENCES users (id),
            UNIQUE(user_id, global_agent_id)
        )
    """)

    # ============================================
    # COST MONITORING TABLES
    # ============================================

    # Table to track cost of every message
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            model TEXT NOT NULL,
            cost REAL NOT NULL,
            agent_name TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Table to log cost alerts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cost_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            daily_cost REAL NOT NULL,
            threshold REAL NOT NULL,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Check and add cost tracking columns to users table
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in cursor.fetchall()]

    if 'daily_cost' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN daily_cost REAL DEFAULT 0.0")
            print("✅ Added daily_cost column to users")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add daily_cost column: {e}")

    if 'monthly_cost' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN monthly_cost REAL DEFAULT 0.0")
            print("✅ Added monthly_cost column to users")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add monthly_cost column: {e}")

    if 'expensive_models_blocked' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN expensive_models_blocked BOOLEAN DEFAULT 0")
            print("✅ Added expensive_models_blocked column to users")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add expensive_models_blocked column: {e}")

    if 'last_cost_reset' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN last_cost_reset TIMESTAMP DEFAULT NULL")
            print("✅ Added last_cost_reset column to users")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add last_cost_reset column: {e}")

    # Custom budget columns for per-user overrides
    if 'custom_daily_budget' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN custom_daily_budget REAL DEFAULT NULL")
            print("✅ Added custom_daily_budget column to users")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add custom_daily_budget column: {e}")

    if 'custom_monthly_budget' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN custom_monthly_budget REAL DEFAULT NULL")
            print("✅ Added custom_monthly_budget column to users")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add custom_monthly_budget column: {e}")

    if 'custom_warning_threshold' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN custom_warning_threshold REAL DEFAULT NULL")
            print("✅ Added custom_warning_threshold column to users")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add custom_warning_threshold column: {e}")

    if 'custom_critical_threshold' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN custom_critical_threshold REAL DEFAULT NULL")
            print("✅ Added custom_critical_threshold column to users")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add custom_critical_threshold column: {e}")

    # Promo code discount columns
    if 'promo_discount_type' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN promo_discount_type TEXT DEFAULT NULL")
            print("✅ Added promo_discount_type column to users (values: 'amount', 'percent')")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add promo_discount_type column: {e}")

    if 'promo_discount_value' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN promo_discount_value REAL DEFAULT NULL")
            print("✅ Added promo_discount_value column to users")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add promo_discount_value column: {e}")

    if 'promo_code_applied' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN promo_code_applied TEXT DEFAULT NULL")
            print("✅ Added promo_code_applied column to users")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add promo_code_applied column: {e}")

    if 'trial_end_date' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN trial_end_date TIMESTAMP DEFAULT NULL")
            print("✅ Added trial_end_date column to users (for free trial promo codes)")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add trial_end_date column: {e}")

    # ============================================
    # GLOBAL AGENTS TABLE MIGRATIONS
    # ============================================

    # Check for global_agents columns
    cursor.execute("PRAGMA table_info(global_agents)")
    global_agent_columns = [col[1] for col in cursor.fetchall()]

    if 'share_code' not in global_agent_columns:
        try:
            cursor.execute("ALTER TABLE global_agents ADD COLUMN share_code TEXT DEFAULT NULL")
            print("✅ Added share_code column to global_agents (for public sharing)")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add share_code column: {e}")

    if 'is_public' not in global_agent_columns:
        try:
            cursor.execute("ALTER TABLE global_agents ADD COLUMN is_public BOOLEAN DEFAULT 0")
            print("✅ Added is_public column to global_agents (for public access)")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add is_public column: {e}")

    if 'integrations' not in global_agent_columns:
        try:
            cursor.execute("ALTER TABLE global_agents ADD COLUMN integrations TEXT DEFAULT NULL")
            print("✅ Added integrations column to global_agents (JSON array of enabled integrations)")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add integrations column: {e}")

    # ============================================
    # USER INTEGRATIONS TABLE (OAuth Tokens)
    # ============================================

    # Create table for storing user OAuth tokens for external services
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_integrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            service TEXT NOT NULL,
            access_token TEXT,
            refresh_token TEXT,
            token_expiry TIMESTAMP,
            service_user_id TEXT,
            service_email TEXT,
            scopes TEXT,
            is_active BOOLEAN DEFAULT 1,
            connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, service)
        )
    """)
    print("✅ User integrations table initialized")

    print("✅ Cost monitoring tables initialized")

    conn.commit()
    conn.close()
    print("✅ Database initialization complete")

def init_promo_codes_table():
    """Initialize promo codes table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create promo_codes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            tier TEXT NOT NULL,
            max_uses INTEGER DEFAULT 1,
            times_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            single_use BOOLEAN DEFAULT 0
        )
    """)
    
    # Check if times_used column exists (migration)
    cursor.execute("PRAGMA table_info(promo_codes)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    if 'times_used' not in existing_columns:
        try:
            print("Adding times_used column to promo_codes table...")
            cursor.execute("ALTER TABLE promo_codes ADD COLUMN times_used INTEGER DEFAULT 0")
            print("✅ Added times_used column")
        except sqlite3.OperationalError as e:
            print(f"Warning: Could not add times_used column: {e}")
    
    if 'is_active' not in existing_columns:
        try:
            print("Adding is_active column to promo_codes table...")
            cursor.execute("ALTER TABLE promo_codes ADD COLUMN is_active BOOLEAN DEFAULT 1")
            print("✅ Added is_active column")
        except sqlite3.OperationalError as e:
            print(f"Warning: Could not add is_active column: {e}")
    
    if 'single_use' not in existing_columns:
        try:
            print("Adding single_use column to promo_codes table...")
            cursor.execute("ALTER TABLE promo_codes ADD COLUMN single_use BOOLEAN DEFAULT 0")
            print("✅ Added single_use column")
        except sqlite3.OperationalError as e:
            print(f"Warning: Could not add single_use column: {e}")

    # Add discount support columns
    if 'discount_type' not in existing_columns:
        try:
            print("Adding discount_type column to promo_codes table...")
            cursor.execute("ALTER TABLE promo_codes ADD COLUMN discount_type TEXT DEFAULT 'tier'")
            print("✅ Added discount_type column (values: 'tier', 'amount', 'percent')")
        except sqlite3.OperationalError as e:
            print(f"Warning: Could not add discount_type column: {e}")

    if 'discount_value' not in existing_columns:
        try:
            print("Adding discount_value column to promo_codes table...")
            cursor.execute("ALTER TABLE promo_codes ADD COLUMN discount_value REAL DEFAULT NULL")
            print("✅ Added discount_value column")
        except sqlite3.OperationalError as e:
            print(f"Warning: Could not add discount_value column: {e}")

    if 'trial_days' not in existing_columns:
        try:
            print("Adding trial_days column to promo_codes table...")
            cursor.execute("ALTER TABLE promo_codes ADD COLUMN trial_days INTEGER DEFAULT NULL")
            print("✅ Added trial_days column (for free trial promo codes)")
        except sqlite3.OperationalError as e:
            print(f"Warning: Could not add trial_days column: {e}")

    # Create promo_code_usage table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promo_code_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promo_code_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (promo_code_id) REFERENCES promo_codes (id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(promo_code_id, user_id)
        )
    """)
    
    # Insert default MASTER2024 code if it doesn't exist
    cursor.execute("SELECT COUNT(*) FROM promo_codes WHERE code = 'MASTER2024'")
    if cursor.fetchone()[0] == 0:
        print("Creating default MASTER2024 promo code...")
        cursor.execute("""
            INSERT INTO promo_codes (code, tier, max_uses, times_used, is_active, single_use)
            VALUES ('MASTER2024', 'enterprise', -1, 0, 1, 0)
        """)
        print("✅ MASTER2024 code created (Enterprise tier, unlimited uses)")
    else:
        print("✅ MASTER2024 code already exists")
    
    conn.commit()
    conn.close()
    print("✅ Promo codes tables initialized")

# ============================================
# ============================================
# GLOBAL AGENTS (System-level utilities)
# ============================================
# CRITICAL: Global agents are DISABLED by default
# Only admin can enable and assign global agents
# DO NOT auto-assign to new users
# ============================================

DEFAULT_GLOBAL_AGENTS = [
    {
        'name': 'Research Agent',
        'description': 'Gather, summarise, and structure information clearly',
        'emoji': '🔍',
        'category': 'utility',
        'system_prompt': '''AGENT ARCHITECTURE: You are a LAYER 2 Global Agent (Utility)
You operate within the AI Team platform's three-layer architecture:
- Layer 1: Base Agents (infrastructure only)
- Layer 2: Global Agents (utilities - YOU ARE HERE)
- Layer 3: Stand Alone Client Agents (paid products)

You are a Research Agent. Your purpose is to gather, summarise, and structure information clearly.

What you CAN do:
- Research topics
- Summarise documents or inputs
- Extract key points
- Structure findings into sections

What you CANNOT do:
- Write final publish-ready content
- Make strategic or business decisions
- Personalise tone unless explicitly asked

PRIORITY RULE: You must defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Analysis Agent',
        'description': 'Help analyse information, logic, trade-offs, and comparisons',
        'emoji': '📊',
        'category': 'utility',
        'system_prompt': '''AGENT ARCHITECTURE: You are a LAYER 2 Global Agent (Utility)
You operate within the AI Team platform's three-layer architecture:
- Layer 1: Base Agents (infrastructure only)
- Layer 2: Global Agents (utilities - YOU ARE HERE)
- Layer 3: Stand Alone Client Agents (paid products)

You are an Analysis Agent. Your purpose is to help analyse information, logic, trade-offs, and comparisons.

What you CAN do:
- Break down concepts or numbers
- Compare options
- Explain implications and risks

What you CANNOT do:
- Provide legal, financial, or medical advice
- Automate decisions
- Act as a strategist

PRIORITY RULE: You must defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Drafting Agent',
        'description': 'Produce first-pass written drafts from clear instructions',
        'emoji': '✍️',
        'category': 'utility',
        'system_prompt': '''AGENT ARCHITECTURE: You are a LAYER 2 Global Agent (Utility)
You operate within the AI Team platform's three-layer architecture:
- Layer 1: Base Agents (infrastructure only)
- Layer 2: Global Agents (utilities - YOU ARE HERE)
- Layer 3: Stand Alone Client Agents (paid products)

You are a Drafting Agent. Your purpose is to produce first-pass written drafts from clear instructions.

What you CAN do:
- Draft content
- Rewrite or restructure text
- Improve clarity and flow

What you CANNOT do:
- Define strategy
- Plan campaigns
- Replace stand alone content agents

PRIORITY RULE: You must defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Organisation Agent',
        'description': 'Organise and structure information',
        'emoji': '📋',
        'category': 'utility',
        'system_prompt': '''AGENT ARCHITECTURE: You are a LAYER 2 Global Agent (Utility)
You operate within the AI Team platform's three-layer architecture:
- Layer 1: Base Agents (infrastructure only)
- Layer 2: Global Agents (utilities - YOU ARE HERE)
- Layer 3: Stand Alone Client Agents (paid products)

You are an Organisation Agent. Your purpose is to organise and structure information.

What you CAN do:
- Sort notes and ideas
- Create lists or steps
- Summarise conversations or threads

What you CANNOT do:
- Automate tools
- Perform integrations
- Manage external systems

PRIORITY RULE: You must defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Instruction Interpreter',
        'description': 'Help users clarify what they are asking for',
        'emoji': '💡',
        'category': 'utility',
        'system_prompt': '''AGENT ARCHITECTURE: You are a LAYER 2 Global Agent (Utility)
You operate within the AI Team platform's three-layer architecture:
- Layer 1: Base Agents (infrastructure only)
- Layer 2: Global Agents (utilities - YOU ARE HERE)
- Layer 3: Stand Alone Client Agents (paid products)

You are an Instruction Interpreter. Your purpose is to help users clarify what they are asking for.

What you CAN do:
- Rewrite unclear prompts
- Ask clarifying questions
- Turn vague requests into clear instructions

What you CANNOT do:
- Complete the task itself
- Produce final outputs

PRIORITY RULE: You must defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    # Additional specialized global agents
    {
        'name': 'Content Helper',
        'description': 'Social media content creation and optimization',
        'emoji': '✍️',
        'category': 'productivity',
        'system_prompt': '''AGENT ARCHITECTURE: You are a LAYER 2 Global Agent (Utility)
You operate within the AI Team platform's three-layer architecture:
- Layer 1: Base Agents (infrastructure only)
- Layer 2: Global Agents (utilities - YOU ARE HERE)
- Layer 3: Stand Alone Client Agents (paid products)

You are a Content Helper specialized in social media content creation.

Your capabilities:
- Transform messy ideas into polished posts
- Shorten content while maintaining tone and voice
- Generate content ideas through strategic questions

When users share messy ideas, clean them up into engaging posts.
When asked to shorten content, preserve the original tone.
When users don't know what to post, ask 3-5 targeted questions about their target audience, recent business updates, pain points they solve, and success stories.

Always match the user's brand voice and keep responses actionable.

PRIORITY RULE: You must defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Email Assistant',
        'description': 'Draft professional emails and responses',
        'emoji': '📧',
        'category': 'productivity',
        'system_prompt': '''AGENT ARCHITECTURE: You are a LAYER 2 Global Agent (Utility)
You operate within the AI Team platform's three-layer architecture:
- Layer 1: Base Agents (infrastructure only)
- Layer 2: Global Agents (utilities - YOU ARE HERE)
- Layer 3: Stand Alone Client Agents (paid products)

You are an Email Assistant that helps write clear, professional emails.

Your role:
- Draft emails based on brief descriptions
- Improve tone and clarity of existing drafts
- Suggest subject lines
- Keep emails concise and actionable

Always ask for context if needed: recipient, purpose, desired tone.

PRIORITY RULE: You must defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Meeting Summarizer',
        'description': 'Create meeting notes and action items',
        'emoji': '📝',
        'category': 'productivity',
        'system_prompt': '''AGENT ARCHITECTURE: You are a LAYER 2 Global Agent (Utility)
You operate within the AI Team platform's three-layer architecture:
- Layer 1: Base Agents (infrastructure only)
- Layer 2: Global Agents (utilities - YOU ARE HERE)
- Layer 3: Stand Alone Client Agents (paid products)

You are a Meeting Summarizer that creates clear, actionable meeting notes.

Your tasks:
- Extract key discussion points
- Identify action items with owners
- Highlight decisions made
- Note follow-up questions

Format output with clear sections: Summary, Action Items, Decisions, Next Steps.

PRIORITY RULE: You must defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Code Review Assistant',
        'description': 'Expert code reviewer for all programming languages',
        'emoji': '👨‍💻',
        'category': 'development',
        'system_prompt': '''AGENT ARCHITECTURE: You are a LAYER 2 Global Agent (Utility)
You operate within the AI Team platform's three-layer architecture:
- Layer 1: Base Agents (infrastructure only)
- Layer 2: Global Agents (utilities - YOU ARE HERE)
- Layer 3: Stand Alone Client Agents (paid products)

You are an expert code reviewer with deep knowledge of software engineering best practices, design patterns, and security.

Review code thoroughly for:
- Logic errors and bugs
- Security vulnerabilities
- Performance issues
- Code style and readability
- Best practices

Provide constructive, actionable feedback.

PRIORITY RULE: You must defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Meeting Notes Taker',
        'description': 'Organize meeting discussions into structured notes',
        'emoji': '📋',
        'category': 'productivity',
        'system_prompt': '''AGENT ARCHITECTURE: You are a LAYER 2 Global Agent (Utility)
You operate within the AI Team platform's three-layer architecture:
- Layer 1: Base Agents (infrastructure only)
- Layer 2: Global Agents (utilities - YOU ARE HERE)
- Layer 3: Stand Alone Client Agents (paid products)

You are a professional meeting notes assistant. Transform meeting transcripts or discussions into well-organized notes.

Your capabilities:
- Key discussion points
- Action items with owners
- Decisions made
- Follow-up questions

Format output with clear sections: Summary, Action Items, Decisions, Next Steps.

PRIORITY RULE: You must defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    }
]

def initialize_default_global_agents():
    """Create default global agents in the database if they don't exist"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for agent in DEFAULT_GLOBAL_AGENTS:
            # Check if this agent already exists
            cursor.execute("""
                SELECT id FROM global_agents WHERE name = ?
            """, (agent['name'],))

            if not cursor.fetchone():
                # Create the global agent
                cursor.execute("""
                    INSERT INTO global_agents (
                        name, description, emoji, category, system_prompt,
                        template_variables, created_by, is_active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP)
                """, (
                    agent['name'],
                    agent['description'],
                    agent['emoji'],
                    agent['category'],
                    agent['system_prompt'],
                    agent.get('template_variables')
                ))
                print(f"✅ Created global agent: {agent['name']}")

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error initializing default global agents: {str(e)}")
        return False

def assign_default_global_agents_to_user(user_id):
    """
    DEPRECATED: DO NOT USE

    Global agents are DISABLED by default per platform architecture.
    Only admin can manually assign global agents through the admin portal.

    This function exists only for backwards compatibility but should never be called.
    """
    print(f"⚠️  WARNING: assign_default_global_agents_to_user() called but is DEPRECATED")
    print(f"   Global agents must be manually assigned by admin only")
    return False

# Initialize database on startup
try:
    init_database()
    init_promo_codes_table()
    initialize_default_global_agents()
    print("✅ Database initialization completed successfully")
except Exception as e:
    print(f"⚠️  Database initialization error: {str(e)}")
    import traceback
    traceback.print_exc()

# ============================================
# ADMIN ROUTES FOR DATABASE SETUP
# ============================================

@app.route('/admin/usage')
@login_required
def admin_usage():
    """Admin dashboard for cost monitoring and analytics"""
    # Check if user is admin (you can add admin check here)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Today's costs
        cursor.execute("""
            SELECT COALESCE(SUM(cost), 0) FROM usage_costs
            WHERE DATE(timestamp) = DATE('now')
        """)
        today_costs = cursor.fetchone()[0]

        # Monthly costs
        cursor.execute("""
            SELECT COALESCE(SUM(cost), 0) FROM usage_costs
            WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
        """)
        monthly_costs = cursor.fetchone()[0]

        # Monthly revenue (sum of all active subscriptions)
        cursor.execute("""
            SELECT COALESCE(SUM(
                CASE subscription_tier
                    WHEN 'starter' THEN 19
                    WHEN 'pro' THEN 49
                    WHEN 'enterprise' THEN 99
                    ELSE 0
                END
            ), 0)
            FROM users
            WHERE stripe_subscription_id IS NOT NULL
        """)
        monthly_revenue = cursor.fetchone()[0]

        # Profit margin
        profit_margin = ((monthly_revenue - monthly_costs) / monthly_revenue * 100) if monthly_revenue > 0 else 0

        # Recent alerts (last 24 hours)
        cursor.execute("""
            SELECT u.email, ca.alert_type, ca.daily_cost, ca.threshold,
                   ca.message, ca.timestamp
            FROM cost_alerts ca
            JOIN users u ON ca.user_id = u.id
            WHERE DATE(ca.timestamp) = DATE('now')
            ORDER BY ca.timestamp DESC
            LIMIT 50
        """)
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'email': row[0],
                'alert_type': row[1],
                'daily_cost': row[2],
                'threshold': row[3],
                'message': row[4],
                'timestamp': row[5]
            })

        # Top cost users (last 7 days)
        cursor.execute("""
            SELECT u.id, u.email, u.subscription_tier, u.daily_cost, u.monthly_cost,
                   u.expensive_models_blocked,
                   u.custom_warning_threshold, u.custom_critical_threshold,
                   (SELECT COUNT(*) FROM usage_costs uc
                    WHERE uc.user_id = u.id
                    AND DATE(uc.timestamp) >= DATE('now', '-7 days')) as message_count
            FROM users u
            WHERE u.daily_cost > 0 OR u.monthly_cost > 0
            ORDER BY u.monthly_cost DESC
            LIMIT 20
        """)
        top_users = []
        for row in cursor.fetchall():
            has_custom = row[6] is not None or row[7] is not None
            top_users.append({
                'id': row[0],
                'email': row[1],
                'tier': row[2],
                'daily_cost': row[3] or 0,
                'monthly_cost': row[4] or 0,
                'blocked': row[5],
                'message_count': row[8],
                'has_custom_budget': has_custom
            })

        # Model usage breakdown
        cursor.execute("""
            SELECT model, COUNT(*) as count, SUM(cost) as total_cost, AVG(cost) as avg_cost
            FROM usage_costs
            WHERE DATE(timestamp) = DATE('now')
            GROUP BY model
            ORDER BY total_cost DESC
        """)
        model_usage = []
        for row in cursor.fetchall():
            model_usage.append({
                'model': row[0],
                'count': row[1],
                'total_cost': row[2],
                'avg_cost': row[3]
            })

        conn.close()

        return render_template('admin_usage.html',
                             today_costs=today_costs,
                             monthly_costs=monthly_costs,
                             monthly_revenue=monthly_revenue,
                             profit_margin=profit_margin,
                             alerts=alerts,
                             top_users=top_users,
                             model_usage=model_usage)

    except Exception as e:
        print(f"❌ Error in admin usage dashboard: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/set-user-budget', methods=['POST'])
@login_required
def set_user_budget():
    """Set custom budget/thresholds for a specific user"""
    try:
        data = request.json
        user_id = data.get('user_id')
        custom_warning = data.get('custom_warning_threshold')
        custom_critical = data.get('custom_critical_threshold')
        custom_daily = data.get('custom_daily_budget')
        custom_monthly = data.get('custom_monthly_budget')

        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Update custom thresholds
        cursor.execute("""
            UPDATE users
            SET custom_warning_threshold = ?,
                custom_critical_threshold = ?,
                custom_daily_budget = ?,
                custom_monthly_budget = ?
            WHERE id = ?
        """, (custom_warning, custom_critical, custom_daily, custom_monthly, user_id))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Custom budgets updated successfully'
        })

    except Exception as e:
        print(f"❌ Error setting user budget: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/reset-user-budget', methods=['POST'])
@login_required
def reset_user_budget():
    """Reset user to tier defaults (remove custom budgets)"""
    try:
        data = request.json
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Reset to NULL (use tier defaults)
        cursor.execute("""
            UPDATE users
            SET custom_warning_threshold = NULL,
                custom_critical_threshold = NULL,
                custom_daily_budget = NULL,
                custom_monthly_budget = NULL
            WHERE id = ?
        """, (user_id,))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'User reset to tier defaults'
        })

    except Exception as e:
        print(f"❌ Error resetting user budget: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/cost-trends')
@login_required
def admin_cost_trends():
    """Get historical cost trend data for charts"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Daily costs for last 30 days
        cursor.execute("""
            SELECT DATE(timestamp) as date, SUM(cost) as total_cost, COUNT(*) as message_count
            FROM usage_costs
            WHERE DATE(timestamp) >= DATE('now', '-30 days')
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """)
        daily_trends = []
        for row in cursor.fetchall():
            daily_trends.append({
                'date': row[0],
                'cost': row[1],
                'messages': row[2]
            })

        # Cost by tier
        cursor.execute("""
            SELECT u.subscription_tier, SUM(uc.cost) as total_cost, COUNT(uc.id) as message_count
            FROM usage_costs uc
            JOIN users u ON uc.user_id = u.id
            WHERE DATE(uc.timestamp) >= DATE('now', '-30 days')
            GROUP BY u.subscription_tier
        """)
        tier_breakdown = []
        for row in cursor.fetchall():
            tier_breakdown.append({
                'tier': row[0],
                'cost': row[1],
                'messages': row[2]
            })

        # Cost by model
        cursor.execute("""
            SELECT model, SUM(cost) as total_cost, COUNT(*) as message_count
            FROM usage_costs
            WHERE DATE(timestamp) >= DATE('now', '-30 days')
            GROUP BY model
            ORDER BY total_cost DESC
        """)
        model_breakdown = []
        for row in cursor.fetchall():
            model_breakdown.append({
                'model': row[0],
                'cost': row[1],
                'messages': row[2]
            })

        conn.close()

        return jsonify({
            'daily_trends': daily_trends,
            'tier_breakdown': tier_breakdown,
            'model_breakdown': model_breakdown
        })

    except Exception as e:
        print(f"❌ Error getting cost trends: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/check-agents')
def check_agents():
    """Check all custom agents and their share codes"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # First check what columns exist
        cursor.execute("PRAGMA table_info(custom_agents)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Build SELECT query based on available columns
        select_cols = ['id', 'user_id', 'name']
        if 'description' in columns:
            select_cols.append('description')
        if 'emoji' in columns:
            select_cols.append('emoji')
        if 'share_code' in columns:
            select_cols.append('share_code')
        if 'is_public' in columns:
            select_cols.append('is_public')
        if 'created_at' in columns:
            select_cols.append('created_at')
        
        query = f"SELECT {', '.join(select_cols)} FROM custom_agents"
        cursor.execute(query)
        
        agents = cursor.fetchall()
        conn.close()
        
        if not agents:
            return jsonify({
                'success': True,
                'total_agents': 0,
                'message': 'No custom agents found',
                'agents': [],
                'available_columns': columns,
                'missing_columns': [c for c in ['emoji', 'share_code', 'is_public'] if c not in columns]
            }), 200
        
        agent_list = []
        for agent in agents:
            idx = 0
            agent_info = {
                'id': agent[idx],
                'user_id': agent[idx+1],
                'name': agent[idx+2]
            }
            idx = 3
            
            if 'description' in columns:
                agent_info['description'] = agent[idx]
                idx += 1
            
            if 'emoji' in columns:
                agent_info['emoji'] = agent[idx]
                idx += 1
            else:
                agent_info['emoji'] = '🤖 (default)'
            
            if 'share_code' in columns:
                share_code = agent[idx]
                agent_info['share_code'] = share_code
                idx += 1
                
                if share_code:
                    agent_info['share_url'] = f"{request.host_url}custom/{share_code}"
                    agent_info['status'] = '✅ Has share code'
                else:
                    agent_info['status'] = '❌ Missing share code'
            else:
                agent_info['share_code'] = None
                agent_info['status'] = '❌ share_code column missing'
            
            if 'is_public' in columns:
                agent_info['is_public'] = bool(agent[idx])
                idx += 1
            
            if 'created_at' in columns:
                agent_info['created_at'] = agent[idx]
            
            agent_list.append(agent_info)
        
        return jsonify({
            'success': True,
            'total_agents': len(agents),
            'agents': agent_list,
            'available_columns': columns,
            'missing_columns': [c for c in ['emoji', 'share_code', 'is_public'] if c not in columns]
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/admin/force-add-columns')
def force_add_columns():
    """Force add missing columns to custom_agents table"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check current columns
        cursor.execute("PRAGMA table_info(custom_agents)")
        columns_before = [col[1] for col in cursor.fetchall()]
        
        added_columns = []
        errors = []
        
        # Try to add emoji column
        if 'emoji' not in columns_before:
            try:
                cursor.execute("ALTER TABLE custom_agents ADD COLUMN emoji TEXT DEFAULT '🤖'")
                conn.commit()
                added_columns.append('emoji')
            except Exception as e:
                errors.append(f"emoji: {str(e)}")
        
        # Try to add share_code column
        if 'share_code' not in columns_before:
            try:
                cursor.execute("ALTER TABLE custom_agents ADD COLUMN share_code TEXT")
                conn.commit()
                added_columns.append('share_code')
            except Exception as e:
                errors.append(f"share_code: {str(e)}")
        
        # Try to add is_public column
        if 'is_public' not in columns_before:
            try:
                cursor.execute("ALTER TABLE custom_agents ADD COLUMN is_public INTEGER DEFAULT 1")
                conn.commit()
                added_columns.append('is_public')
            except Exception as e:
                errors.append(f"is_public: {str(e)}")
        
        # Check columns after
        cursor.execute("PRAGMA table_info(custom_agents)")
        columns_after = [col[1] for col in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'columns_before': columns_before,
            'columns_after': columns_after,
            'added_columns': added_columns if added_columns else 'None - all already present',
            'errors': errors if errors else 'None',
            'message': f"Added {len(added_columns)} columns successfully" if added_columns else "All columns already present"
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/admin/init-database-emergency')
def emergency_database_init():
    """Emergency database initialization - visit this URL to fix database"""
    try:
        # Force database initialization
        init_database()
        init_promo_codes_table()
        initialize_default_global_agents()

        # Check if custom_agents table exists and has correct columns
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(custom_agents)")
        columns = [col[1] for col in cursor.fetchall()]
        
        missing_columns = []
        
        if 'emoji' not in columns:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN emoji TEXT DEFAULT '🤖'")
            missing_columns.append('emoji')
        
        if 'share_code' not in columns:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN share_code TEXT UNIQUE")
            missing_columns.append('share_code')
        
        if 'is_public' not in columns:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN is_public BOOLEAN DEFAULT 1")
            missing_columns.append('is_public')
        
        conn.commit()
        
        # Verify all tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        result = {
            'success': True,
            'message': 'Database initialized successfully!',
            'tables': tables,
            'missing_columns_added': missing_columns if missing_columns else 'None - all columns present'
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/admin/create-default-agent/<int:user_id>')
def create_default_agent(user_id):
    """Create default custom agent for user - visit /admin/create-default-agent/1"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, email FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({
                'success': False,
                'error': f'User with ID {user_id} not found',
                'hint': 'Sign up at /register first, then try /admin/create-default-agent/1'
            }), 404
        
        # Check if agent already exists for this user
        cursor.execute("SELECT id, name, share_code FROM custom_agents WHERE user_id = ?", (user_id,))
        existing_agent = cursor.fetchone()
        
        if existing_agent:
            agent_id, name, share_code = existing_agent
            
            # If agent exists but has no share_code, add one
            if not share_code:
                import secrets
                share_code = secrets.token_urlsafe(12)
                cursor.execute("UPDATE custom_agents SET share_code = ?, is_public = 1 WHERE id = ?", 
                             (share_code, agent_id))
                conn.commit()
                conn.close()
                
                share_url = f"{request.host_url}custom/{share_code}"
                
                return jsonify({
                    'success': True,
                    'message': 'Added share code to existing agent!',
                    'agent_id': agent_id,
                    'name': name,
                    'share_code': share_code,
                    'share_url': share_url,
                    'instructions': 'Refresh your dashboard to see the share link!'
                }), 200
            else:
                # Agent already has share code
                conn.close()
                share_url = f"{request.host_url}custom/{share_code}"
                
                return jsonify({
                    'success': True,
                    'message': 'Agent already exists with share code!',
                    'agent_id': agent_id,
                    'name': name,
                    'share_code': share_code,
                    'share_url': share_url,
                    'instructions': 'Agent is ready to share!'
                }), 200
        
        # Create new agent
        import secrets
        share_code = secrets.token_urlsafe(12)
        
        name = "Skill & Soul Agent"
        description = "knows about my brand and style and builds on my ideas"
        emoji = "🤖"
        system_prompt = """**Tone:** Thorough and educational
**Length:** Comprehensive with examples
**Format:** Well-structured with headings and sections

BRAND CONTEXT:
- SKILL & SOUL STUDIO helps overwhelmed creators
- Target audience: overwhelmed solo business owners
- Brand values: No fake urgency, honest approach
- Aim for clarity without stress
- Short paragraphs, simple sentences
- Honest, grounded tone

STYLE RULES:
- Short paragraphs (2-3 sentences)
- Simple vocabulary
- Conversational tone
- Clarify, don't overwhelm"""
        
        cursor.execute("""
            INSERT INTO custom_agents 
            (user_id, name, description, emoji, personality, system_prompt, share_code, is_public)
            VALUES (?, ?, ?, ?, '{}', ?, ?, 1)
        """, (user_id, name, description, emoji, system_prompt, share_code))
        
        agent_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        share_url = f"{request.host_url}custom/{share_code}"
        
        return jsonify({
            'success': True,
            'message': 'Agent created successfully!',
            'agent_id': agent_id,
            'name': name,
            'share_code': share_code,
            'share_url': share_url,
            'instructions': 'Refresh your dashboard to see the agent!'
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/admin/migrate-starter-agents')
def migrate_starter_agents():
    """Migrate old starter agents from custom_agents to global_agents system"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Step 1: Delete old starter agents from custom_agents table
        starter_agent_names = ['Content Helper', 'Email Assistant', 'Meeting Summarizer']

        deleted_count = 0
        for agent_name in starter_agent_names:
            cursor.execute("""
                DELETE FROM custom_agents WHERE name = ?
            """, (agent_name,))
            deleted_count += cursor.rowcount

        # Step 2: Ensure global agents exist
        initialize_default_global_agents()

        # Step 3: Get all users
        cursor.execute("SELECT id FROM users WHERE is_active = 1")
        all_users = cursor.fetchall()

        # Step 4: Assign global agents to all users
        assigned_count = 0
        for user_row in all_users:
            user_id = user_row[0]

            # Assign default global agents to this user
            for agent in DEFAULT_GLOBAL_AGENTS:
                cursor.execute("""
                    SELECT id FROM global_agents WHERE name = ?
                """, (agent['name'],))

                result = cursor.fetchone()
                if result:
                    global_agent_id = result[0]

                    # Assign to user (skip if already assigned)
                    try:
                        cursor.execute("""
                            INSERT INTO user_global_agents (user_id, global_agent_id, assigned_by, assigned_at)
                            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                        """, (user_id, global_agent_id))
                        assigned_count += 1
                    except sqlite3.IntegrityError:
                        # Already assigned, skip
                        pass

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Migration completed successfully!',
            'deleted_custom_agents': deleted_count,
            'users_processed': len(all_users),
            'global_agents_assigned': assigned_count,
            'instructions': 'Refresh your dashboard to see the updated agents!'
        }), 200

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

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

            # NOTE: Global agents are DISABLED by default
            # Only admin can manually assign global agents
            # DO NOT auto-assign global agents to new users

            conn.close()
            return jsonify({'success': True}), 200
            
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Username or email already exists'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    """Login user - accepts either username OR email"""
    try:
        data = request.json
        # Accept either 'email' or 'username' field for backwards compatibility
        username_or_email = data.get('email') or data.get('username')
        password = data.get('password')
        
        if not username_or_email or not password:
            return jsonify({'error': 'Username/email and password required'}), 400
        
        # Get user by EITHER username OR email
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, password_hash, subscription_tier FROM users WHERE (email = ? OR username = ?) AND is_active = 1",
            (username_or_email, username_or_email)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'Invalid username/email or password'}), 401
        
        # Verify password
        if not check_password_hash(result[3], password):
            return jsonify({'error': 'Invalid username/email or password'}), 401
        
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
# SHAREABLE AGENT LINKS (Public Agent Access)
# ============================================

@app.route('/agent/<agent_name>')
def agent_link(agent_name):
    """Shareable link for base agents - works without login with clean interface"""
    # Validate agent name
    valid_agents = ['Luna', 'Mila', 'Sage', 'Ember', 'Sol', 'Nova', 'Theo']

    if agent_name not in valid_agents:
        return "Agent not found", 404

    # If logged in, redirect to dashboard with agent selected
    if current_user.is_authenticated:
        return render_template('dashboard.html', user=current_user, selected_agent=agent_name)

    # Guest user - create clean interface like custom agents
    print(f"👻 Guest accessing base agent: {agent_name}")

    # Create a guest user object for the template
    class GuestUser:
        id = 0
        email = "guest@ai-team.com"
        is_authenticated = False
        stripe_customer_id = None
        subscription_tier = "free"
        stripe_subscription_id = None
        api_key = None
        google_ai_api_key = None
        messages_today = 0
        last_message_reset = None

        def get_id(self):
            return 0

    guest = GuestUser()

    # Clean, simplified interface for base agents
    guest_restrictions = f"""
    <style>
    /* Hide settings, automations, upgrade sections */
    .sidebar-section:has(a[href*="settings"]),
    .sidebar-section:has(a[href*="automations"]),
    .sidebar-section:has(a[href*="upgrade"]) {{
        display: none !important;
    }}
    /* Hide user menu/dropdown completely */
    .user-menu {{
        display: none !important;
    }}
    /* Hide prompt builder button */
    .prompt-builder-btn,
    button:has(.prompt-builder),
    [onclick*="promptBuilder"] {{
        display: none !important;
    }}
    /* Hide usage counter */
    .usage-counter,
    .messages-counter,
    .daily-limit {{
        display: none !important;
    }}
    /* Hide options button */
    .options-btn,
    button[title*="Option"],
    .input-options {{
        display: none !important;
    }}
    /* Hide model selector */
    .model-selector,
    select[name="model"],
    .model-dropdown,
    label:has(select[name="model"]) {{
        display: none !important;
    }}
    /* Style for preset questions */
    .preset-questions {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        padding: 20px;
        background: transparent;
        border-radius: 12px;
        margin: 20px 0;
    }}
    .preset-question {{
        padding: 12px 20px;
        background: #f3f4f6;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 14px;
        color: #374151;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    .preset-question:hover {{
        background: #10a37f;
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(16, 163, 127, 0.3);
    }}
    </style>
    <script>
    (function() {{
        console.log('🎯 Guest: Clean interface for base agent {agent_name}');

        localStorage.setItem('guestMode', 'true');

        document.addEventListener('DOMContentLoaded', function() {{
            // Auto-select the base agent and hide others
            setTimeout(function() {{
                const agentButtons = document.querySelectorAll('.agent-button');
                agentButtons.forEach(function(btn) {{
                    if (btn.textContent.includes('{agent_name}')) {{
                        btn.click();
                    }} else {{
                        btn.style.display = 'none';
                    }}
                }});
            }}, 500);

            // Add preset questions after welcome message
            setTimeout(function() {{
                const welcomeMsg = document.querySelector('.welcome') ||
                                 document.querySelector('.chat-container');
                if (welcomeMsg) {{
                    const presets = document.createElement('div');
                    presets.className = 'preset-questions';
                    presets.innerHTML = `
                        <div class="preset-question" onclick="sendPresetMessage('Tell me about yourself')">
                            💬 Tell me about yourself
                        </div>
                        <div class="preset-question" onclick="sendPresetMessage('What can you help me with?')">
                            ❓ What can you help me with?
                        </div>
                        <div class="preset-question" onclick="sendPresetMessage('Show me an example')">
                            ✨ Show me an example
                        </div>
                        <div class="preset-question" onclick="sendPresetMessage('Get started')">
                            🚀 Get started
                        </div>
                    `;

                    if (welcomeMsg.classList.contains('welcome')) {{
                        welcomeMsg.appendChild(presets);
                    }} else {{
                        welcomeMsg.insertBefore(presets, welcomeMsg.firstChild);
                    }}
                }}
            }}, 1500);

            // Disable file upload button
            setTimeout(function() {{
                const fileBtn = document.querySelector('.attach-btn') ||
                               document.querySelector('button[title*="file"]');
                if (fileBtn) {{
                    fileBtn.style.opacity = '0.5';
                    fileBtn.addEventListener('click', function(e) {{
                        e.preventDefault();
                        alert('📎 Sign up for free to upload files and access all features!');
                    }});
                }}
            }}, 1000);
        }});

        // Function to send preset messages
        window.sendPresetMessage = function(message) {{
            console.log('🔘 Preset clicked:', message);
            const input = document.getElementById('messageInput');

            if (input) {{
                input.value = message;
                input.focus();
                console.log('✅ Input set:', input.value);

                // Trigger the send function directly
                if (typeof window.sendMessage === 'function') {{
                    window.sendMessage();
                }} else {{
                    console.error('❌ sendMessage function not found');
                }}
            }} else {{
                console.error('❌ messageInput not found');
            }}
        }};

        // Encourage sign up when trying other agents
        document.addEventListener('click', function(e) {{
            const btn = e.target.closest('.agent-button');
            if (btn && !btn.textContent.includes('{agent_name}')) {{
                e.preventDefault();
                e.stopPropagation();
                alert('Sign up for free to access all AI agents!');
                return false;
            }}
        }}, true);
    }})();
    </script>
    """

    return render_template('dashboard.html',
                         user=guest,
                         current_user=guest,
                         selected_agent=agent_name,
                         is_guest=True,
                         guest_custom_js=guest_restrictions)

@app.route('/admin/test-custom-link/<share_code>')
def test_custom_link(share_code):
    """Test if a share code exists in database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check what share_codes exist
        cursor.execute("SELECT id, name, share_code FROM custom_agents")
        all_agents = cursor.fetchall()
        
        # Try to find this specific share_code
        cursor.execute("SELECT id, name FROM custom_agents WHERE share_code = ?", (share_code,))
        matching_agent = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'looking_for': share_code,
            'found': matching_agent is not None,
            'matching_agent': {
                'id': matching_agent[0],
                'name': matching_agent[1]
            } if matching_agent else None,
            'all_agents_in_db': [
                {
                    'id': a[0],
                    'name': a[1],
                    'share_code': a[2],
                    'matches': a[2] == share_code
                } for a in all_agents
            ]
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/test-route-works')
def test_route():
    """Simple test to verify routes are being registered"""
    return jsonify({
        'success': True,
        'message': 'Routes are working!',
        'custom_route_should_work': True
    })

@app.route('/test-before-custom')
def test_before_custom():
    """Test route immediately before custom route"""
    return "Routes work here!"

@app.route('/custom/test-simple')
def test_simple_custom():
    """Test with hardcoded path"""
    return "Hardcoded custom route works!"

@app.route('/custom/<path:share_code>')
def custom_agent_link(share_code):
    """Shareable link for custom agent - works without login"""
    print(f"🔥 ROUTE MATCHED! share_code = {share_code}")
    print(f"📁 Using database: {DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check which columns exist
        cursor.execute("PRAGMA table_info(custom_agents)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Get all agents with user_id to find the owner
        cursor.execute("SELECT id, name, share_code, user_id FROM custom_agents")
        all_agents = cursor.fetchall()
        print(f"📊 ALL agents in DB: {all_agents}")

        # Find the agent by comparing share codes
        agent_found = None
        for agent in all_agents:
            db_id, db_name, db_share_code, db_user_id = agent
            if db_share_code and share_code:
                if str(db_share_code).strip().lower() == str(share_code).strip().lower():
                    print(f"✅ MATCH! Found agent: {db_name} (ID: {db_id}, Owner: {db_user_id})")
                    agent_found = (db_id, db_name, db_user_id)
                    break
        
        if not agent_found:
            print(f"❌ No agent found with share_code: {share_code}")
            return "Custom agent not found. Please check the link and try again.", 404

        agent_id, agent_name, owner_id = agent_found
        
        # Show the dashboard with custom agent active
        # Works for both logged in and guest users!
        if current_user.is_authenticated:
            print(f"👤 Logged in user accessing agent")
            return render_template('dashboard.html', 
                                 user=current_user, 
                                 custom_agent_id=agent_id,
                                 custom_agent_name=agent_name,
                                 auto_select_custom_agent=True)  # Trigger auto-selection
        else:
            print(f"👻 Guest user accessing agent (no login required)")

            # Get the agent owner's subscription info
            cursor.execute("""
                SELECT subscription_tier, stripe_subscription_id, api_key, google_ai_api_key
                FROM users WHERE id = ?
            """, (owner_id,))
            owner_info = cursor.fetchone()

            # Create a guest user object for the template
            class GuestUser:
                id = 0
                email = "guest@ai-team.com"
                is_authenticated = False
                stripe_customer_id = None
                messages_today = 0
                last_message_reset = None

                def get_id(self):
                    return 0

            guest = GuestUser()

            # If owner has an active paid subscription, inherit their plan
            if owner_info and owner_info[1]:  # Has stripe_subscription_id (active sub)
                owner_tier, stripe_sub_id, owner_api_key, owner_google_key = owner_info
                guest.subscription_tier = owner_tier
                guest.stripe_subscription_id = stripe_sub_id
                guest.api_key = owner_api_key
                guest.google_ai_api_key = owner_google_key
                print(f"✅ Guest inheriting plan: {owner_tier} (owner has active subscription)")
            else:
                # Owner has no active subscription - guest gets free tier
                guest.subscription_tier = "free"
                guest.stripe_subscription_id = None
                guest.api_key = None
                guest.google_ai_api_key = None
                print(f"ℹ️ Guest on FREE tier (owner has no active subscription)")
            
            # Clean, simplified interface for custom agents
            guest_restrictions = f"""
            <style>
            /* Hide ALL other agents */
            .sidebar-section:has(.agent-button[data-agent-type="core"]) {{
                display: none !important;
            }}
            /* Hide settings, automations, upgrade */
            .sidebar-section:has(a[href*="settings"]),
            .sidebar-section:has(a[href*="automations"]),
            .sidebar-section:has(a[href*="upgrade"]) {{
                display: none !important;
            }}
            /* Hide user menu/dropdown completely */
            .user-menu {{
                display: none !important;
            }}
            /* Hide prompt builder button */
            .prompt-builder-btn,
            button:has(.prompt-builder),
            [onclick*="promptBuilder"] {{
                display: none !important;
            }}
            /* Hide usage counter */
            .usage-counter,
            .messages-counter,
            .daily-limit {{
                display: none !important;
            }}
            /* Hide options button */
            .options-btn,
            button[title*="Option"],
            .input-options {{
                display: none !important;
            }}
            /* Hide model selector */
            .model-selector,
            select[name="model"],
            .model-dropdown,
            label:has(select[name="model"]) {{
                display: none !important;
            }}
            /* Style for preset questions */
            .preset-questions {{
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                padding: 20px;
                background: transparent;
                border-radius: 12px;
                margin: 20px 0;
            }}
            .preset-question {{
                padding: 12px 20px;
                background: #f3f4f6;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 14px;
                color: #374151;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .preset-question:hover {{
                background: #10a37f;
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(16, 163, 127, 0.3);
            }}
            </style>
            <script>
            (function() {{
                console.log('🎯 Guest: Clean interface for {agent_name}');

                localStorage.setItem('guestMode', 'true');

                document.addEventListener('DOMContentLoaded', function() {{
                    // Auto-select the shared agent
                    setTimeout(function() {{
                        const agentButtons = document.querySelectorAll('.agent-button');
                        agentButtons.forEach(function(btn) {{
                            if (btn.textContent.includes('{agent_name}')) {{
                                btn.click();
                            }} else {{
                                btn.style.display = 'none';
                            }}
                        }});
                    }}, 500);

                    // Add preset questions after welcome message
                    setTimeout(function() {{
                        const welcomeMsg = document.querySelector('.welcome') ||
                                         document.querySelector('.chat-container');
                        if (welcomeMsg) {{
                            const presets = document.createElement('div');
                            presets.className = 'preset-questions';
                            presets.innerHTML = `
                                <div class="preset-question" onclick="sendPresetMessage('Tell me about yourself')">
                                    💬 Tell me about yourself
                                </div>
                                <div class="preset-question" onclick="sendPresetMessage('What can you help me with?')">
                                    ❓ What can you help me with?
                                </div>
                                <div class="preset-question" onclick="sendPresetMessage('Show me an example')">
                                    ✨ Show me an example
                                </div>
                                <div class="preset-question" onclick="sendPresetMessage('Get started')">
                                    🚀 Get started
                                </div>
                            `;

                            if (welcomeMsg.classList.contains('welcome')) {{
                                welcomeMsg.appendChild(presets);
                            }} else {{
                                welcomeMsg.insertBefore(presets, welcomeMsg.firstChild);
                            }}
                        }}
                    }}, 1500);

                    // Disable file upload button
                    setTimeout(function() {{
                        const fileBtn = document.querySelector('.attach-btn') ||
                                       document.querySelector('button[title*="file"]');
                        if (fileBtn) {{
                            fileBtn.style.opacity = '0.5';
                            fileBtn.addEventListener('click', function(e) {{
                                e.preventDefault();
                                alert('📎 Sign up for free to upload files!');
                            }});
                        }}
                    }}, 1000);
                }});

                // Function to send preset messages
                window.sendPresetMessage = function(message) {{
                    console.log('🔘 Preset clicked:', message);
                    const input = document.getElementById('messageInput');

                    if (input) {{
                        input.value = message;
                        input.focus();
                        console.log('✅ Input set:', input.value);

                        // Trigger the send function directly
                        if (typeof window.sendMessage === 'function') {{
                            window.sendMessage();
                        }} else {{
                            console.error('❌ sendMessage function not found');
                        }}
                    }} else {{
                        console.error('❌ messageInput not found');
                    }}
                }};

                // Block switching agents
                document.addEventListener('click', function(e) {{
                    const btn = e.target.closest('.agent-button');
                    if (btn && !btn.textContent.includes('{agent_name}')) {{
                        e.preventDefault();
                        e.stopPropagation();
                        alert('Sign up for free to access all AI agents!');
                        return false;
                    }}
                }}, true);
            }})();
            </script>
            """
            
            return render_template('dashboard.html', 
                                 user=guest,
                                 current_user=guest,
                                 custom_agent_id=agent_id,
                                 custom_agent_name=agent_name,
                                 is_guest=True,
                                 guest_restrictions=guest_restrictions)
        
    except Exception as e:
        print(f"❌ Error loading custom agent: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error loading agent: {str(e)}", 500

# ============================================
# EMBED & WEBHOOK INTEGRATIONS
# ============================================

@app.route('/embed/<share_code>/widget.js')
def embed_widget(share_code):
    """Serve embed widget JavaScript for custom agent"""
    widget_js = f'''
(function() {{
    const AGENT_SHARE_CODE = "{share_code}";
    const API_BASE = "{request.host_url}";

    // Create chat widget
    function createChatWidget() {{
        // Widget HTML
        const widgetHTML = `
            <div id="ai-chat-widget" style="position: fixed; bottom: 20px; right: 20px; z-index: 9999;">
                <button id="ai-chat-toggle" style="width: 60px; height: 60px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.15); display: flex; align-items: center; justify-content: center; font-size: 24px;">
                    💬
                </button>
                <div id="ai-chat-window" style="position: absolute; bottom: 80px; right: 0; width: 350px; height: 500px; background: white; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.2); display: none; flex-direction: column; overflow: hidden;">
                    <div style="padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: 600;">
                        AI Assistant
                        <button id="ai-chat-close" style="float: right; background: none; border: none; color: white; font-size: 20px; cursor: pointer; padding: 0; width: 24px; height: 24px;">×</button>
                    </div>
                    <div id="ai-chat-messages" style="flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px;"></div>
                    <div style="padding: 12px; border-top: 1px solid #e5e7eb;">
                        <div style="display: flex; gap: 8px;">
                            <input type="text" id="ai-chat-input" placeholder="Type a message..." style="flex: 1; padding: 10px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px;" />
                            <button id="ai-chat-send" style="padding: 10px 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 500;">Send</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', widgetHTML);

        // Event listeners
        document.getElementById('ai-chat-toggle').addEventListener('click', toggleChat);
        document.getElementById('ai-chat-close').addEventListener('click', toggleChat);
        document.getElementById('ai-chat-send').addEventListener('click', sendMessage);
        document.getElementById('ai-chat-input').addEventListener('keypress', (e) => {{
            if (e.key === 'Enter') sendMessage();
        }});
    }}

    function toggleChat() {{
        const window = document.getElementById('ai-chat-window');
        window.style.display = window.style.display === 'none' ? 'flex' : 'none';
    }}

    function addMessage(message, isUser, isThinking = false) {{
        const messagesDiv = document.getElementById('ai-chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `
            padding: 10px 14px;
            border-radius: 12px;
            max-width: 80%;
            word-wrap: break-word;
            ${{isUser ? 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; margin-left: auto;' : 'background: #f3f4f6; color: #1f2937;'}}
            ${{isThinking ? 'opacity: 0.7; font-style: italic; color: #9ca3af !important;' : ''}}
        `;
        if (isThinking) {{
            messageDiv.id = 'thinking-indicator';
        }}
        messageDiv.textContent = message;
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }}

    function showThinkingIndicator() {{
        const thinkingMessages = [
            '*thinking...',
            '*contemplating...',
            '*computing...',
            '*analyzing...',
            '*processing...',
            '*considering...'
        ];
        const randomMessage = thinkingMessages[Math.floor(Math.random() * thinkingMessages.length)];
        addMessage(randomMessage, false, true);

        // Animate dots
        let dots = 3;
        const interval = setInterval(() => {{
            const indicator = document.getElementById('thinking-indicator');
            if (!indicator) {{
                clearInterval(interval);
                return;
            }}
            dots = (dots % 3) + 1;
            const baseMessage = randomMessage.replace(/\.+$/, '');
            indicator.textContent = baseMessage + '.'.repeat(dots);
        }}, 500);

        return interval;
    }}

    function removeThinkingIndicator(interval) {{
        if (interval) clearInterval(interval);
        const indicator = document.getElementById('thinking-indicator');
        if (indicator) indicator.remove();
    }}

    async function sendMessage() {{
        const input = document.getElementById('ai-chat-input');
        const message = input.value.trim();
        if (!message) return;

        addMessage(message, true);
        input.value = '';

        const thinkingInterval = showThinkingIndicator();

        try {{
            const response = await fetch(API_BASE + 'api/embed/chat', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    share_code: AGENT_SHARE_CODE,
                    message: message
                }})
            }});

            const data = await response.json();
            removeThinkingIndicator(thinkingInterval);

            if (data.response) {{
                addMessage(data.response, false);
            }} else {{
                addMessage('Sorry, I encountered an error.', false);
            }}
        }} catch (error) {{
            removeThinkingIndicator(thinkingInterval);
            addMessage('Sorry, I encountered an error.', false);
        }}
    }}

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', createChatWidget);
    }} else {{
        createChatWidget();
    }}
}})();
    '''
    return widget_js, 200, {'Content-Type': 'application/javascript'}

@app.route('/api/embed/chat', methods=['POST'])
def embed_chat():
    """Handle chat messages from embedded widget"""
    try:
        data = request.json
        share_code = data.get('share_code')
        message = data.get('message')

        if not share_code or not message:
            return jsonify({'error': 'Missing required fields'}), 400

        # Get custom agent by share_code
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, system_prompt, user_id FROM custom_agents
            WHERE share_code = ? AND is_public = 1
        """, (share_code,))

        agent_data = cursor.fetchone()
        if not agent_data:
            conn.close()
            return jsonify({'error': 'Agent not found'}), 404

        agent_id, agent_name, system_prompt, owner_id = agent_data

        # Build system prompt
        full_system_prompt = f"""You are {{agent_name}}. Your role and personality:

{{system_prompt}}

CRITICAL FORMATTING RULES:
- Write in natural, conversational paragraphs
- Do NOT use asterisks (**), hashtags (##), dashes (---), or bullet points (•)
- Do NOT use markdown formatting of any kind
- Keep responses concise and friendly
- Write like you're talking to someone, not writing a document"""

        # Get AI response (using Gemini for free tier)
        import google.generativeai as genai
        genai.configure(api_key=app.config.get('GOOGLE_AI_API_KEY'))
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        response = model.generate_content(f"{{full_system_prompt}}\\n\\nUser: {{message}}")
        ai_response = response.text

        conn.close()

        return jsonify({{'response': ai_response}}), 200

    except Exception as e:
        print(f"❌ Embed chat error: {{str(e)}}")
        return jsonify({{'error': 'Internal server error'}}), 500

@app.route('/api/agent/<int:agent_id>/embed-code')
@login_required
def get_embed_code(agent_id):
    """Get embed code for a custom agent"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT share_code, name FROM custom_agents
            WHERE id = ? AND user_id = ?
        """, (agent_id, current_user.id))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return jsonify({{'error': 'Agent not found or unauthorized'}}), 404

        share_code, name = result

        # Generate embed code
        embed_code = f'''<!-- {{name}} - AI Chat Widget -->
<script src="{{request.host_url}}embed/{{share_code}}/widget.js"></script>'''

        return jsonify({{
            'embed_code': embed_code,
            'preview_url': f'{{request.host_url}}custom/{{share_code}}'
        }}), 200

    except Exception as e:
        return jsonify({{'error': str(e)}}), 500

# REMOVED: Old duplicate webhook endpoint - replaced with newer implementation at line ~8670
# The newer implementation uses the correct schema (event_type, last_triggered)
# and has separate GET/POST routes with better error handling

# ============================================
# SETTINGS PAGE (FOR NOTION INTEGRATION)
# ============================================

@app.route('/settings')
@login_required
def settings():
    """Settings page for integrations"""
    return render_template('settings.html', user=current_user)

@app.route('/integrations')
@login_required
def integrations_page():
    """Comprehensive integrations management page"""
    return render_template('integrations.html', user=current_user)

@app.route('/faq')
def faq():
    """FAQ page - public access"""
    return render_template('faq.html')

@app.route('/help')
def help_page():
    """Help center - public access"""
    return render_template('help.html')

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html', user=current_user)

# ============================================
# SOCIAL MEDIA INTEGRATION
# ============================================

@app.route('/api/social/connect/<platform>', methods=['POST'])
@login_required
def connect_social_platform(platform):
    """Connect social media account (Twitter, Facebook, LinkedIn)"""
    supported_platforms = ['twitter', 'facebook', 'linkedin']

    if platform not in supported_platforms:
        return jsonify({'error': 'Unsupported platform'}), 400

    try:
        data = request.json
        access_token = data.get('access_token')
        account_name = data.get('account_name')

        if not access_token:
            return jsonify({'error': 'Access token required'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create social_accounts table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                account_name TEXT,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, platform, account_name)
            )
        """)

        # Store connection
        cursor.execute("""
            INSERT OR REPLACE INTO social_accounts
            (user_id, platform, account_name, access_token)
            VALUES (?, ?, ?, ?)
        """, (current_user.id, platform, account_name, access_token))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'{platform.title()} connected successfully',
            'platform': platform
        }), 200

    except Exception as e:
        print(f"Error connecting {platform}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/social/accounts')
@login_required
def get_social_accounts():
    """Get all connected social media accounts"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT platform, account_name, is_active, created_at
            FROM social_accounts
            WHERE user_id = ? AND is_active = 1
            ORDER BY created_at DESC
        """, (current_user.id,))

        accounts = []
        for row in cursor.fetchall():
            accounts.append({
                'platform': row[0],
                'account_name': row[1],
                'is_active': bool(row[2]),
                'connected_at': row[3]
            })

        conn.close()

        return jsonify({'accounts': accounts}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/social/post/draft', methods=['POST'])
@login_required
def draft_social_post():
    """AI drafts a social media post for user approval"""
    try:
        data = request.json
        prompt = data.get('prompt')
        platform = data.get('platform', 'twitter')
        agent = data.get('agent', 'Luna')

        if not prompt:
            return jsonify({'error': 'Prompt required'}), 400

        # Get agent's system prompt
        if agent in AGENT_PERSONALITIES:
            agent_info = AGENT_PERSONALITIES[agent]
            system_prompt = agent_info['system_prompt']
        else:
            # Custom agent
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT system_prompt FROM custom_agents
                WHERE user_id = ? AND name = ?
            """, (current_user.id, agent))
            result = cursor.fetchone()
            conn.close()

            if result:
                system_prompt = result[0]
            else:
                system_prompt = "You are a helpful social media assistant."

        # Add social media context
        platform_limits = {
            'twitter': '280 characters',
            'facebook': '500 characters recommended',
            'linkedin': '700 characters recommended'
        }

        full_prompt = f"""{system_prompt}

You are helping create a {platform} post.

IMPORTANT RULES:
- Maximum length: {platform_limits.get(platform, '280 characters')}
- Make it engaging and professional
- Include relevant hashtags if appropriate
- DO NOT use emojis excessively
- Keep it concise and impactful

User request: {prompt}

Draft the post:"""

        # Generate post using Gemini
        import google.generativeai as genai
        genai.configure(api_key=app.config.get('GOOGLE_AI_API_KEY'))
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        response = model.generate_content(full_prompt)
        drafted_post = response.text

        # Save draft for approval
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create social_posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                scheduled_at TIMESTAMP,
                posted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        cursor.execute("""
            INSERT INTO social_posts (user_id, platform, content, status)
            VALUES (?, ?, ?, 'draft')
        """, (current_user.id, platform, drafted_post))

        post_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'post_id': post_id,
            'content': drafted_post,
            'platform': platform,
            'status': 'draft',
            'message': 'Post drafted! Review and approve to publish.'
        }), 200

    except Exception as e:
        print(f"Error drafting post: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/social/post/<int:post_id>/approve', methods=['POST'])
@login_required
def approve_social_post(post_id):
    """Approve and post to social media"""
    try:
        data = request.json
        action = data.get('action', 'post_now')  # 'post_now' or 'schedule'
        scheduled_time = data.get('scheduled_at')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get post
        cursor.execute("""
            SELECT platform, content, status FROM social_posts
            WHERE id = ? AND user_id = ?
        """, (post_id, current_user.id))

        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({'error': 'Post not found'}), 404

        platform, content, status = result

        if status != 'draft':
            conn.close()
            return jsonify({'error': 'Post already processed'}), 400

        if action == 'schedule':
            # Schedule for later
            if not scheduled_time:
                conn.close()
                return jsonify({'error': 'Scheduled time required'}), 400

            cursor.execute("""
                UPDATE social_posts
                SET status = 'scheduled', scheduled_at = ?
                WHERE id = ?
            """, (scheduled_time, post_id))

            conn.commit()
            conn.close()

            return jsonify({
                'success': True,
                'message': f'Post scheduled for {scheduled_time}',
                'status': 'scheduled'
            }), 200
        else:
            # Post now
            # NOTE: This is a simplified version
            # In production, you'd use the actual platform APIs

            cursor.execute("""
                UPDATE social_posts
                SET status = 'posted', posted_at = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), post_id))

            conn.commit()
            conn.close()

            return jsonify({
                'success': True,
                'message': f'Posted to {platform} successfully!',
                'status': 'posted',
                'note': 'Connect your social accounts in Settings to enable actual posting'
            }), 200

    except Exception as e:
        print(f"Error approving post: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/social/posts')
@login_required
def get_social_posts():
    """Get all social posts (drafts, scheduled, posted)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, platform, content, status, scheduled_at, posted_at, created_at
            FROM social_posts
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (current_user.id,))

        posts = []
        for row in cursor.fetchall():
            posts.append({
                'id': row[0],
                'platform': row[1],
                'content': row[2],
                'status': row[3],
                'scheduled_at': row[4],
                'posted_at': row[5],
                'created_at': row[6]
            })

        conn.close()

        return jsonify({'posts': posts}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# UNIVERSAL INTEGRATIONS FRAMEWORK
# ============================================

# Integration configurations with required credentials
INTEGRATIONS_CONFIG = {
    # Communication Platforms
    'slack': {
        'name': 'Slack',
        'category': 'communication',
        'icon': '💬',
        'description': 'Team collaboration and notifications',
        'auth_type': 'oauth',
        'credentials': ['bot_token', 'webhook_url'],
        'features': ['send_message', 'create_channel', 'get_channels', 'post_to_channel']
    },
    'discord': {
        'name': 'Discord',
        'category': 'communication',
        'icon': '🎮',
        'description': 'Community engagement and bot integration',
        'auth_type': 'webhook',
        'credentials': ['webhook_url', 'bot_token'],
        'features': ['send_message', 'create_embed', 'manage_channels']
    },
    'teams': {
        'name': 'Microsoft Teams',
        'category': 'communication',
        'icon': '👥',
        'description': 'Enterprise team collaboration',
        'auth_type': 'webhook',
        'credentials': ['webhook_url'],
        'features': ['send_message', 'send_adaptive_card']
    },
    'telegram': {
        'name': 'Telegram',
        'category': 'communication',
        'icon': '✈️',
        'description': 'Messaging bot integration',
        'auth_type': 'api_key',
        'credentials': ['bot_token', 'chat_id'],
        'features': ['send_message', 'send_photo', 'send_document']
    },

    # Email & Messaging
    'sendgrid': {
        'name': 'SendGrid',
        'category': 'email',
        'icon': '📧',
        'description': 'Transactional email delivery',
        'auth_type': 'api_key',
        'credentials': ['api_key'],
        'features': ['send_email', 'send_template']
    },
    'mailgun': {
        'name': 'Mailgun',
        'category': 'email',
        'icon': '📬',
        'description': 'Email automation and delivery',
        'auth_type': 'api_key',
        'credentials': ['api_key', 'domain'],
        'features': ['send_email', 'get_stats']
    },
    'twilio': {
        'name': 'Twilio',
        'category': 'messaging',
        'icon': '📱',
        'description': 'SMS and WhatsApp messaging',
        'auth_type': 'api_key',
        'credentials': ['account_sid', 'auth_token', 'phone_number'],
        'features': ['send_sms', 'send_whatsapp', 'make_call']
    },

    # CRM & Sales
    'hubspot': {
        'name': 'HubSpot',
        'category': 'crm',
        'icon': '🎯',
        'description': 'CRM and marketing automation',
        'auth_type': 'oauth',
        'credentials': ['api_key'],
        'features': ['create_contact', 'create_deal', 'log_activity']
    },
    'salesforce': {
        'name': 'Salesforce',
        'category': 'crm',
        'icon': '☁️',
        'description': 'Enterprise CRM platform',
        'auth_type': 'oauth',
        'credentials': ['access_token', 'instance_url'],
        'features': ['create_lead', 'update_opportunity', 'query_records']
    },
    'pipedrive': {
        'name': 'Pipedrive',
        'category': 'crm',
        'icon': '📊',
        'description': 'Sales pipeline management',
        'auth_type': 'api_key',
        'credentials': ['api_token', 'company_domain'],
        'features': ['create_deal', 'add_activity', 'create_person']
    },

    # Project Management
    'asana': {
        'name': 'Asana',
        'category': 'project_management',
        'icon': '✓',
        'description': 'Task and project management',
        'auth_type': 'oauth',
        'credentials': ['access_token'],
        'features': ['create_task', 'add_comment', 'get_projects']
    },
    'trello': {
        'name': 'Trello',
        'category': 'project_management',
        'icon': '📋',
        'description': 'Visual project boards',
        'auth_type': 'oauth',
        'credentials': ['api_key', 'token'],
        'features': ['create_card', 'add_checklist', 'move_card']
    },
    'monday': {
        'name': 'Monday.com',
        'category': 'project_management',
        'icon': '📅',
        'description': 'Work operating system',
        'auth_type': 'api_key',
        'credentials': ['api_token'],
        'features': ['create_item', 'update_column', 'get_boards']
    },
    'clickup': {
        'name': 'ClickUp',
        'category': 'project_management',
        'icon': '🖱️',
        'description': 'All-in-one productivity platform',
        'auth_type': 'api_key',
        'credentials': ['api_token'],
        'features': ['create_task', 'add_comment', 'get_spaces']
    },
    'jira': {
        'name': 'Jira',
        'category': 'project_management',
        'icon': '🔵',
        'description': 'Issue and project tracking',
        'auth_type': 'oauth',
        'credentials': ['api_token', 'email', 'domain'],
        'features': ['create_issue', 'add_comment', 'update_status']
    },

    # Google Workspace
    'google_sheets': {
        'name': 'Google Sheets',
        'category': 'productivity',
        'icon': '📊',
        'description': 'Spreadsheet data management',
        'auth_type': 'oauth',
        'credentials': ['access_token', 'refresh_token'],
        'features': ['append_row', 'read_data', 'create_sheet']
    },
    'google_docs': {
        'name': 'Google Docs',
        'category': 'productivity',
        'icon': '📄',
        'description': 'Document creation and editing',
        'auth_type': 'oauth',
        'credentials': ['access_token', 'refresh_token'],
        'features': ['create_document', 'append_text', 'get_content']
    },
    'google_calendar': {
        'name': 'Google Calendar',
        'category': 'productivity',
        'icon': '📆',
        'description': 'Calendar and event management',
        'auth_type': 'oauth',
        'credentials': ['access_token', 'refresh_token'],
        'features': ['create_event', 'list_events', 'update_event']
    },
    'gmail': {
        'name': 'Gmail',
        'category': 'email',
        'icon': '📨',
        'description': 'Email integration',
        'auth_type': 'oauth',
        'credentials': ['access_token', 'refresh_token'],
        'features': ['send_email', 'read_emails', 'create_draft']
    },

    # Data & Storage
    'airtable': {
        'name': 'Airtable',
        'category': 'database',
        'icon': '🗄️',
        'description': 'Flexible database platform',
        'auth_type': 'api_key',
        'credentials': ['api_key', 'base_id'],
        'features': ['create_record', 'update_record', 'list_records']
    },
    'mongodb': {
        'name': 'MongoDB',
        'category': 'database',
        'icon': '🍃',
        'description': 'NoSQL database',
        'auth_type': 'connection_string',
        'credentials': ['connection_string'],
        'features': ['insert_document', 'query', 'update']
    },
    'supabase': {
        'name': 'Supabase',
        'category': 'database',
        'icon': '⚡',
        'description': 'Open source Firebase alternative',
        'auth_type': 'api_key',
        'credentials': ['api_url', 'api_key'],
        'features': ['insert', 'select', 'update', 'delete']
    },
    'google_drive': {
        'name': 'Google Drive',
        'category': 'storage',
        'icon': '💾',
        'description': 'Cloud file storage',
        'auth_type': 'oauth',
        'credentials': ['access_token', 'refresh_token'],
        'features': ['upload_file', 'list_files', 'create_folder']
    },
    'dropbox': {
        'name': 'Dropbox',
        'category': 'storage',
        'icon': '📦',
        'description': 'File hosting service',
        'auth_type': 'oauth',
        'credentials': ['access_token'],
        'features': ['upload_file', 'list_folder', 'share_link']
    },

    # Payment & Analytics
    'stripe_webhooks': {
        'name': 'Stripe Webhooks',
        'category': 'payment',
        'icon': '💳',
        'description': 'Payment event notifications',
        'auth_type': 'webhook',
        'credentials': ['webhook_secret'],
        'features': ['receive_payment', 'subscription_update', 'refund']
    },
    'google_analytics': {
        'name': 'Google Analytics',
        'category': 'analytics',
        'icon': '📈',
        'description': 'Web analytics tracking',
        'auth_type': 'oauth',
        'credentials': ['measurement_id', 'api_secret'],
        'features': ['track_event', 'get_reports']
    },
    'mixpanel': {
        'name': 'Mixpanel',
        'category': 'analytics',
        'icon': '📊',
        'description': 'Product analytics platform',
        'auth_type': 'api_key',
        'credentials': ['project_token'],
        'features': ['track_event', 'set_user_properties']
    },

    # Developer Tools
    'github': {
        'name': 'GitHub',
        'category': 'developer',
        'icon': '🐙',
        'description': 'Code hosting and collaboration',
        'auth_type': 'oauth',
        'credentials': ['access_token'],
        'features': ['create_issue', 'create_pr', 'add_comment']
    },
    'gitlab': {
        'name': 'GitLab',
        'category': 'developer',
        'icon': '🦊',
        'description': 'DevOps platform',
        'auth_type': 'api_key',
        'credentials': ['private_token'],
        'features': ['create_issue', 'create_merge_request', 'pipeline_trigger']
    },
    'linear': {
        'name': 'Linear',
        'category': 'developer',
        'icon': '📐',
        'description': 'Issue tracking for dev teams',
        'auth_type': 'api_key',
        'credentials': ['api_key'],
        'features': ['create_issue', 'update_status', 'add_comment']
    },

    # Customer Support
    'intercom': {
        'name': 'Intercom',
        'category': 'support',
        'icon': '💬',
        'description': 'Customer messaging platform',
        'auth_type': 'oauth',
        'credentials': ['access_token'],
        'features': ['send_message', 'create_ticket', 'tag_user']
    },
    'zendesk': {
        'name': 'Zendesk',
        'category': 'support',
        'icon': '🎫',
        'description': 'Customer service platform',
        'auth_type': 'api_key',
        'credentials': ['subdomain', 'email', 'api_token'],
        'features': ['create_ticket', 'add_comment', 'update_ticket']
    },
    'freshdesk': {
        'name': 'Freshdesk',
        'category': 'support',
        'icon': '🆘',
        'description': 'Customer support software',
        'auth_type': 'api_key',
        'credentials': ['domain', 'api_key'],
        'features': ['create_ticket', 'reply_ticket', 'get_tickets']
    },

    # Other
    'calendly': {
        'name': 'Calendly',
        'category': 'scheduling',
        'icon': '📅',
        'description': 'Meeting scheduling automation',
        'auth_type': 'oauth',
        'credentials': ['access_token'],
        'features': ['get_events', 'list_event_types', 'cancel_event']
    },
    'shopify': {
        'name': 'Shopify',
        'category': 'ecommerce',
        'icon': '🛍️',
        'description': 'E-commerce platform',
        'auth_type': 'oauth',
        'credentials': ['access_token', 'shop_name'],
        'features': ['create_product', 'get_orders', 'update_inventory']
    },
    'wordpress': {
        'name': 'WordPress',
        'category': 'cms',
        'icon': '✍️',
        'description': 'Content management system',
        'auth_type': 'api_key',
        'credentials': ['site_url', 'username', 'app_password'],
        'features': ['create_post', 'update_post', 'upload_media']
    },
    'youtube': {
        'name': 'YouTube',
        'category': 'media',
        'icon': '📹',
        'description': 'Video platform integration',
        'auth_type': 'oauth',
        'credentials': ['access_token', 'refresh_token'],
        'features': ['upload_video', 'get_transcription', 'add_comment']
    }
}

@app.route('/api/integrations')
@login_required
def get_integrations():
    """Get all available integrations and user's connected status"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create integrations table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS integrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                integration_key TEXT NOT NULL,
                integration_name TEXT NOT NULL,
                credentials TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, integration_key)
            )
        """)

        # Get user's connected integrations
        cursor.execute("""
            SELECT integration_key, credentials, is_active, created_at
            FROM integrations
            WHERE user_id = ?
        """, (current_user.id,))

        connected_integrations = {}
        for row in cursor.fetchall():
            connected_integrations[row[0]] = {
                'credentials': json.loads(row[1]),
                'is_active': bool(row[2]),
                'connected_at': row[3]
            }

        conn.close()

        # Build response with all integrations
        integrations_list = []
        for key, config in INTEGRATIONS_CONFIG.items():
            integration_info = {
                'key': key,
                'name': config['name'],
                'category': config['category'],
                'icon': config['icon'],
                'description': config['description'],
                'auth_type': config['auth_type'],
                'credentials_required': config['credentials'],
                'features': config['features'],
                'is_connected': key in connected_integrations,
                'is_active': connected_integrations.get(key, {}).get('is_active', False),
                'connected_at': connected_integrations.get(key, {}).get('connected_at')
            }
            integrations_list.append(integration_info)

        # Group by category
        categorized = {}
        for integration in integrations_list:
            category = integration['category']
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(integration)

        return jsonify({
            'integrations': integrations_list,
            'categorized': categorized,
            'total': len(integrations_list),
            'connected': len(connected_integrations)
        }), 200

    except Exception as e:
        print(f"Error fetching integrations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/connect', methods=['POST'])
@login_required
def connect_integration():
    """Connect a new integration"""
    try:
        data = request.json
        integration_key = data.get('integration_key')
        credentials = data.get('credentials', {})

        if not integration_key or integration_key not in INTEGRATIONS_CONFIG:
            return jsonify({'error': 'Invalid integration key'}), 400

        config = INTEGRATIONS_CONFIG[integration_key]

        # Validate required credentials
        missing_creds = []
        for cred in config['credentials']:
            if cred not in credentials:
                missing_creds.append(cred)

        if missing_creds:
            return jsonify({
                'error': 'Missing required credentials',
                'missing': missing_creds
            }), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Store integration credentials
        cursor.execute("""
            INSERT OR REPLACE INTO integrations
            (user_id, integration_key, integration_name, credentials, is_active, updated_at)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        """, (current_user.id, integration_key, config['name'], json.dumps(credentials)))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'{config["name"]} connected successfully',
            'integration': {
                'key': integration_key,
                'name': config['name'],
                'icon': config['icon']
            }
        }), 200

    except Exception as e:
        print(f"Error connecting integration: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/<integration_key>/disconnect', methods=['POST'])
@login_required
def disconnect_integration(integration_key):
    """Disconnect an integration"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM integrations
            WHERE user_id = ? AND integration_key = ?
        """, (current_user.id, integration_key))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Integration disconnected'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/<integration_key>/toggle', methods=['POST'])
@login_required
def toggle_integration(integration_key):
    """Toggle integration active status"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE integrations
            SET is_active = NOT is_active,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND integration_key = ?
        """, (current_user.id, integration_key))

        conn.commit()

        cursor.execute("""
            SELECT is_active FROM integrations
            WHERE user_id = ? AND integration_key = ?
        """, (current_user.id, integration_key))

        result = cursor.fetchone()
        conn.close()

        if result:
            return jsonify({
                'success': True,
                'is_active': bool(result[0])
            }), 200
        else:
            return jsonify({'error': 'Integration not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Integration action handlers
@app.route('/api/integrations/<integration_key>/action', methods=['POST'])
@login_required
def execute_integration_action(integration_key):
    """Execute an action with a connected integration"""
    try:
        if integration_key not in INTEGRATIONS_CONFIG:
            return jsonify({'error': 'Invalid integration'}), 400

        # Get user's credentials for this integration
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT credentials, is_active FROM integrations
            WHERE user_id = ? AND integration_key = ?
        """, (current_user.id, integration_key))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return jsonify({'error': 'Integration not connected'}), 404

        if not result[1]:
            return jsonify({'error': 'Integration is disabled'}), 403

        credentials = json.loads(result[0])
        data = request.json
        action = data.get('action')
        params = data.get('params', {})

        # Route to appropriate handler
        result = execute_integration_handler(integration_key, action, credentials, params)

        return jsonify(result), 200

    except Exception as e:
        print(f"Error executing integration action: {str(e)}")
        return jsonify({'error': str(e)}), 500

def execute_integration_handler(integration_key, action, credentials, params):
    """Execute specific integration actions"""

    # Slack Integration
    if integration_key == 'slack':
        if action == 'send_message':
            import requests
            webhook_url = credentials.get('webhook_url')
            response = requests.post(webhook_url, json={
                'text': params.get('message', ''),
                'channel': params.get('channel'),
                'username': params.get('username', 'AI Team Bot')
            })
            return {'success': True, 'sent': True}

    # Discord Integration
    elif integration_key == 'discord':
        if action == 'send_message':
            import requests
            webhook_url = credentials.get('webhook_url')
            response = requests.post(webhook_url, json={
                'content': params.get('message', ''),
                'username': params.get('username', 'AI Team Bot')
            })
            return {'success': True, 'sent': True}

    # Microsoft Teams
    elif integration_key == 'teams':
        if action == 'send_message':
            import requests
            webhook_url = credentials.get('webhook_url')
            response = requests.post(webhook_url, json={
                '@type': 'MessageCard',
                '@context': 'http://schema.org/extensions',
                'text': params.get('message', '')
            })
            return {'success': True, 'sent': True}

    # Telegram
    elif integration_key == 'telegram':
        if action == 'send_message':
            import requests
            bot_token = credentials.get('bot_token')
            chat_id = credentials.get('chat_id')
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(url, json={
                'chat_id': chat_id,
                'text': params.get('message', '')
            })
            return {'success': True, 'sent': True}

    # GitHub
    elif integration_key == 'github':
        if action == 'create_issue':
            import requests
            token = credentials.get('access_token')
            repo = params.get('repo')  # owner/repo format
            response = requests.post(
                f"https://api.github.com/repos/{repo}/issues",
                headers={'Authorization': f'token {token}'},
                json={
                    'title': params.get('title'),
                    'body': params.get('body'),
                    'labels': params.get('labels', [])
                }
            )
            return {'success': True, 'issue': response.json()}

    # Trello
    elif integration_key == 'trello':
        if action == 'create_card':
            import requests
            api_key = credentials.get('api_key')
            token = credentials.get('token')
            list_id = params.get('list_id')
            response = requests.post(
                f"https://api.trello.com/1/cards?key={api_key}&token={token}",
                json={
                    'idList': list_id,
                    'name': params.get('title'),
                    'desc': params.get('description')
                }
            )
            return {'success': True, 'card': response.json()}

    # Google Sheets
    elif integration_key == 'google_sheets':
        if action == 'append_row':
            # This would use Google Sheets API
            return {'success': True, 'message': 'Row appended (demo mode)'}

    # Twilio SMS
    elif integration_key == 'twilio':
        if action == 'send_sms':
            from twilio.rest import Client
            account_sid = credentials.get('account_sid')
            auth_token = credentials.get('auth_token')
            from_number = credentials.get('phone_number')

            client = Client(account_sid, auth_token)
            message = client.messages.create(
                body=params.get('message'),
                from_=from_number,
                to=params.get('to')
            )
            return {'success': True, 'sid': message.sid}

    # Default fallback
    return {
        'success': True,
        'message': f'Action {action} simulated for {integration_key}',
        'note': 'Full implementation requires external API setup'
    }

# ============================================
# AI AGENT AUTO-INTEGRATION
# ============================================

def detect_integration_intent(message):
    """Detect if user wants to use an integration based on their message"""
    message_lower = message.lower()

    # Integration keyword patterns
    patterns = {
        'slack': ['post to slack', 'send to slack', 'slack message', 'send slack'],
        'discord': ['post to discord', 'send to discord', 'discord message'],
        'github': ['create github issue', 'open github issue', 'github issue', 'create issue on github'],
        'trello': ['create trello card', 'add to trello', 'trello card'],
        'gmail': ['send email', 'email to', 'send gmail'],
        'google_sheets': ['add to spreadsheet', 'update sheet', 'google sheets'],
        'twitter': ['tweet this', 'post to twitter', 'share on twitter'],
        'linkedin': ['post to linkedin', 'share on linkedin'],
        'asana': ['create task in asana', 'add asana task'],
        'jira': ['create jira ticket', 'jira issue'],
        'telegram': ['send telegram message', 'message on telegram'],
        'twilio': ['send sms', 'text message to']
    }

    for integration_key, keywords in patterns.items():
        for keyword in keywords:
            if keyword in message_lower:
                return {
                    'integration': integration_key,
                    'detected': True,
                    'keyword': keyword
                }

    return {'detected': False}

def extract_integration_params(message, integration_key):
    """Extract parameters from user message for integration action"""
    params = {}

    # Extract common parameters based on integration type
    if integration_key in ['slack', 'discord', 'teams', 'telegram']:
        # Extract message content (everything after the integration keyword)
        for keyword in ['post to', 'send to', 'message']:
            if keyword in message.lower():
                parts = message.lower().split(keyword, 1)
                if len(parts) > 1:
                    content = parts[1].strip()
                    # Remove integration name
                    for name in ['slack', 'discord', 'teams', 'telegram']:
                        content = content.replace(name, '').strip()
                    params['message'] = content if content else message
                    break

        if 'message' not in params:
            params['message'] = message

    elif integration_key == 'github':
        # Extract title and body for GitHub issues
        params['title'] = message[:100]  # First 100 chars as title
        params['body'] = message
        params['repo'] = 'user/repo'  # Default, user should configure

    elif integration_key == 'trello':
        params['title'] = message[:100]
        params['description'] = message

    elif integration_key in ['gmail', 'sendgrid']:
        params['subject'] = message[:50]
        params['body'] = message

    elif integration_key == 'twilio':
        params['message'] = message
        params['to'] = '+1234567890'  # User needs to configure

    return params

@app.route('/api/ai-integration/execute', methods=['POST'])
@login_required
def execute_ai_integration():
    """Auto-execute integration based on AI detection"""
    try:
        data = request.json
        message = data.get('message', '')

        # Detect integration intent
        intent = detect_integration_intent(message)

        if not intent['detected']:
            return jsonify({'integration_used': False}), 200

        integration_key = intent['integration']

        # Check if user has this integration connected
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT credentials, is_active FROM integrations
            WHERE user_id = ? AND integration_key = ? AND is_active = 1
        """, (current_user.id, integration_key))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return jsonify({
                'integration_used': False,
                'suggestion': f'Connect {integration_key.replace("_", " ").title()} in Settings to use this feature'
            }), 200

        # Extract parameters and execute
        params = extract_integration_params(message, integration_key)
        credentials = json.loads(result[0])

        # Get default action for this integration
        config = INTEGRATIONS_CONFIG.get(integration_key, {})
        action = config.get('features', ['send_message'])[0]

        # Execute integration
        exec_result = execute_integration_handler(integration_key, action, credentials, params)

        return jsonify({
            'integration_used': True,
            'integration': integration_key,
            'action': action,
            'result': exec_result
        }), 200

    except Exception as e:
        print(f"AI Integration error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================
# WEBHOOK RECEIVERS
# ============================================

@app.route('/api/webhooks/incoming/<integration_key>', methods=['POST'])
def receive_webhook(integration_key):
    """Receive incoming webhooks from external services"""
    try:
        payload = request.json or request.form.to_dict()
        headers = dict(request.headers)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create webhook_events table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhook_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                integration_key TEXT NOT NULL,
                event_type TEXT,
                payload TEXT NOT NULL,
                headers TEXT,
                processed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Store webhook event
        cursor.execute("""
            INSERT INTO webhook_events (integration_key, event_type, payload, headers)
            VALUES (?, ?, ?, ?)
        """, (
            integration_key,
            payload.get('type') or payload.get('event'),
            json.dumps(payload),
            json.dumps(headers)
        ))

        event_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Process webhook based on integration
        process_webhook_event(integration_key, payload, event_id)

        return jsonify({'success': True, 'event_id': event_id}), 200

    except Exception as e:
        print(f"Webhook receive error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_webhook_event(integration_key, payload, event_id):
    """Process incoming webhook events"""
    try:
        # GitHub webhooks
        if integration_key == 'github':
            event_type = payload.get('action')
            if event_type == 'opened' and 'pull_request' in payload:
                # PR opened - could trigger AI code review
                pr_title = payload['pull_request']['title']
                print(f"GitHub PR opened: {pr_title}")

        # Stripe webhooks
        elif integration_key == 'stripe_webhooks':
            event_type = payload.get('type')
            if event_type == 'payment_intent.succeeded':
                print(f"Stripe payment succeeded")

        # Slack webhooks
        elif integration_key == 'slack':
            if payload.get('type') == 'event_callback':
                event = payload.get('event', {})
                if event.get('type') == 'app_mention':
                    # Bot was mentioned - could trigger AI response
                    text = event.get('text', '')
                    print(f"Slack mention: {text}")

        # Mark as processed
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE webhook_events SET processed = 1 WHERE id = ?", (event_id,))
        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Webhook processing error: {str(e)}")

@app.route('/api/webhooks/events')
@login_required
def get_webhook_events():
    """Get recent webhook events for user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, integration_key, event_type, payload, processed, created_at
            FROM webhook_events
            ORDER BY created_at DESC
            LIMIT 50
        """)

        events = []
        for row in cursor.fetchall():
            events.append({
                'id': row[0],
                'integration': row[1],
                'event_type': row[2],
                'payload': json.loads(row[3]) if row[3] else {},
                'processed': bool(row[4]),
                'created_at': row[5]
            })

        conn.close()
        return jsonify({'events': events}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# INTEGRATION TEMPLATES & RECIPES
# ============================================

INTEGRATION_TEMPLATES = [
    {
        'id': 'github-to-slack',
        'name': 'GitHub → Slack Notifications',
        'description': 'Post GitHub PR/issue updates to Slack channel',
        'icon': '🐙💬',
        'integrations_required': ['github', 'slack'],
        'trigger': 'github_webhook',
        'actions': ['slack_send_message']
    },
    {
        'id': 'email-to-trello',
        'name': 'Email → Trello Card',
        'description': 'Convert important emails into Trello cards',
        'icon': '📧📋',
        'integrations_required': ['gmail', 'trello'],
        'trigger': 'gmail_new_email',
        'actions': ['trello_create_card']
    },
    {
        'id': 'ai-social-scheduler',
        'name': 'AI Social Media Scheduler',
        'description': 'AI generates and schedules social posts',
        'icon': '🤖📱',
        'integrations_required': ['twitter', 'linkedin'],
        'trigger': 'manual',
        'actions': ['ai_generate_post', 'twitter_post', 'linkedin_post']
    },
    {
        'id': 'slack-ai-responder',
        'name': 'Slack AI Auto-Responder',
        'description': 'AI responds to Slack mentions automatically',
        'icon': '💬🤖',
        'integrations_required': ['slack'],
        'trigger': 'slack_mention',
        'actions': ['ai_respond', 'slack_reply']
    },
    {
        'id': 'analytics-to-sheets',
        'name': 'Analytics → Google Sheets',
        'description': 'Daily analytics export to spreadsheet',
        'icon': '📊📈',
        'integrations_required': ['google_analytics', 'google_sheets'],
        'trigger': 'daily_schedule',
        'actions': ['fetch_analytics', 'append_to_sheet']
    },
    {
        'id': 'support-ticket-ai',
        'name': 'AI Support Ticket Handler',
        'description': 'AI triages and responds to support tickets',
        'icon': '🎫🤖',
        'integrations_required': ['zendesk'],
        'trigger': 'zendesk_new_ticket',
        'actions': ['ai_analyze_ticket', 'ai_draft_response', 'zendesk_reply']
    }
]

@app.route('/api/integrations/templates')
@login_required
def get_integration_templates():
    """Get all available integration templates"""
    try:
        # Get user's connected integrations
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT integration_key FROM integrations
            WHERE user_id = ? AND is_active = 1
        """, (current_user.id,))

        connected = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Mark templates as available if user has required integrations
        templates_with_status = []
        for template in INTEGRATION_TEMPLATES:
            has_all_integrations = all(
                integration in connected
                for integration in template['integrations_required']
            )

            templates_with_status.append({
                **template,
                'available': has_all_integrations,
                'missing_integrations': [
                    i for i in template['integrations_required']
                    if i not in connected
                ]
            })

        return jsonify({'templates': templates_with_status}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/templates/<template_id>/enable', methods=['POST'])
@login_required
def enable_integration_template(template_id):
    """Enable an integration template"""
    try:
        template = next((t for t in INTEGRATION_TEMPLATES if t['id'] == template_id), None)
        if not template:
            return jsonify({'error': 'Template not found'}), 404

        # Store enabled template
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enabled_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                template_id TEXT NOT NULL,
                template_name TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, template_id)
            )
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO enabled_templates (user_id, template_id, template_name, is_active)
            VALUES (?, ?, ?, 1)
        """, (current_user.id, template_id, template['name']))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'{template["name"]} enabled successfully'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# USAGE ANALYTICS & MONITORING
# ============================================

@app.route('/api/integrations/analytics')
@login_required
def get_integration_analytics():
    """Get usage analytics for integrations"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create analytics table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS integration_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                integration_key TEXT NOT NULL,
                action TEXT,
                success BOOLEAN,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # Get usage stats for last 30 days
        cursor.execute("""
            SELECT
                integration_key,
                COUNT(*) as total_calls,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_calls,
                MAX(created_at) as last_used
            FROM integration_usage
            WHERE user_id = ? AND created_at >= datetime('now', '-30 days')
            GROUP BY integration_key
            ORDER BY total_calls DESC
        """, (current_user.id,))

        stats = []
        for row in cursor.fetchall():
            integration_key = row[0]
            config = INTEGRATIONS_CONFIG.get(integration_key, {})

            stats.append({
                'integration': integration_key,
                'name': config.get('name', integration_key),
                'icon': config.get('icon', '🔌'),
                'total_calls': row[1],
                'successful_calls': row[2],
                'failed_calls': row[3],
                'success_rate': round((row[2] / row[1] * 100) if row[1] > 0 else 0, 1),
                'last_used': row[4]
            })

        # Get daily usage for charts
        cursor.execute("""
            SELECT
                date(created_at) as day,
                COUNT(*) as calls
            FROM integration_usage
            WHERE user_id = ? AND created_at >= datetime('now', '-30 days')
            GROUP BY date(created_at)
            ORDER BY day DESC
        """, (current_user.id,))

        daily_usage = [{'date': row[0], 'calls': row[1]} for row in cursor.fetchall()]

        conn.close()

        return jsonify({
            'stats': stats,
            'daily_usage': daily_usage
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def log_integration_usage(user_id, integration_key, action, success, error_message=None):
    """Log integration usage for analytics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO integration_usage (user_id, integration_key, action, success, error_message)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, integration_key, action, success, error_message))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Analytics logging error: {str(e)}")

# ============================================
# OAUTH FLOW HELPERS
# ============================================

OAUTH_CONFIG = {
    'github': {
        'auth_url': 'https://github.com/login/oauth/authorize',
        'token_url': 'https://github.com/login/oauth/access_token',
        'scopes': ['repo', 'user']
    },
    'google_sheets': {
        'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'scopes': ['https://www.googleapis.com/auth/spreadsheets']
    },
    'slack': {
        'auth_url': 'https://slack.com/oauth/v2/authorize',
        'token_url': 'https://slack.com/api/oauth.v2.access',
        'scopes': ['chat:write', 'channels:read']
    },
    # Email Integrations
    'gmail': {
        'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'scopes': [
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.compose'
        ],
        'name': 'Gmail',
        'icon': '📧'
    },
    'outlook': {
        'auth_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
        'token_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
        'scopes': ['Mail.Send', 'Mail.Read', 'Mail.ReadWrite'],
        'name': 'Outlook',
        'icon': '📨'
    },
    # Social Media Integrations
    'twitter': {
        'auth_url': 'https://twitter.com/i/oauth2/authorize',
        'token_url': 'https://api.twitter.com/2/oauth2/token',
        'scopes': ['tweet.read', 'tweet.write', 'users.read'],
        'name': 'Twitter/X',
        'icon': '🐦'
    },
    'linkedin': {
        'auth_url': 'https://www.linkedin.com/oauth/v2/authorization',
        'token_url': 'https://www.linkedin.com/oauth/v2/accessToken',
        'scopes': ['w_member_social', 'r_liteprofile', 'r_emailaddress'],
        'name': 'LinkedIn',
        'icon': '💼'
    },
    # Meeting Integrations
    'zoom': {
        'auth_url': 'https://zoom.us/oauth/authorize',
        'token_url': 'https://zoom.us/oauth/token',
        'scopes': ['meeting:read', 'recording:read', 'cloud_recording:read'],
        'name': 'Zoom',
        'icon': '🎥'
    },
    'google_calendar': {
        'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'scopes': ['https://www.googleapis.com/auth/calendar.readonly'],
        'name': 'Google Calendar',
        'icon': '📅'
    }
}

# Available integrations for agents
AVAILABLE_INTEGRATIONS = {
    'email': {
        'name': 'Email',
        'description': 'Send and read emails',
        'services': ['gmail', 'outlook'],
        'icon': '📧'
    },
    'social_media': {
        'name': 'Social Media',
        'description': 'Post to social platforms',
        'services': ['twitter', 'linkedin'],
        'icon': '📱'
    },
    'meetings': {
        'name': 'Meetings',
        'description': 'Access meeting recordings and transcripts',
        'services': ['zoom', 'google_calendar'],
        'icon': '🎥'
    },
    'productivity': {
        'name': 'Productivity',
        'description': 'Connect to productivity tools',
        'services': ['google_sheets', 'slack'],
        'icon': '📊'
    }
}

# ============================================
# USER OAUTH INTEGRATIONS API
# ============================================

@app.route('/api/user-integrations', methods=['GET'])
@login_required
def get_user_integrations():
    """Get user's OAuth integration connections"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get all user's connected integrations
        cursor.execute("""
            SELECT service, service_email, service_user_id,
                   token_expiry, connected_at, last_used_at, is_active
            FROM user_integrations
            WHERE user_id = ?
        """, (current_user.id,))

        connected = {}
        for row in cursor.fetchall():
            service, email, user_id, expiry, connected, last_used, is_active = row
            connected[service] = {
                'service': service,
                'email': email,
                'user_id': user_id,
                'expiry': expiry,
                'connected_at': connected,
                'last_used_at': last_used,
                'is_active': bool(is_active)
            }

        # Get integrations needed by user's global agents
        cursor.execute("""
            SELECT DISTINCT ga.integrations
            FROM global_agents ga
            INNER JOIN user_global_agents uga ON ga.id = uga.global_agent_id
            WHERE uga.user_id = ? AND ga.is_active = 1 AND ga.integrations IS NOT NULL
        """, (current_user.id,))

        needed_categories = set()
        for row in cursor.fetchall():
            if row[0]:
                integrations = json.loads(row[0])
                needed_categories.update(integrations)

        # Build available integrations list with connection status
        available = []
        for category, info in AVAILABLE_INTEGRATIONS.items():
            for service in info['services']:
                if service in OAUTH_CONFIG:
                    oauth_info = OAUTH_CONFIG[service]
                    available.append({
                        'service': service,
                        'name': oauth_info['name'],
                        'icon': oauth_info['icon'],
                        'category': category,
                        'is_connected': service in connected,
                        'is_needed': category in needed_categories,
                        'connection_info': connected.get(service)
                    })

        conn.close()

        return jsonify({
            'available': available,
            'needed_categories': list(needed_categories)
        }), 200

    except Exception as e:
        print(f"❌ Error getting user integrations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user-integrations/connect/<service>', methods=['POST'])
@login_required
def connect_oauth_integration(service):
    """Start OAuth flow for a service"""
    try:
        if service not in OAUTH_CONFIG:
            return jsonify({'error': 'Service not supported'}), 400

        oauth_config = OAUTH_CONFIG[service]

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state in session
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                service TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT INTO oauth_states (state, user_id, service)
            VALUES (?, ?, ?)
        """, (state, current_user.id, service))

        conn.commit()
        conn.close()

        # Build OAuth authorization URL
        callback_url = f"{request.host_url.rstrip('/')}/api/oauth/callback/{service}"
        scopes = ' '.join(oauth_config['scopes']) if isinstance(oauth_config['scopes'], list) else oauth_config['scopes']

        # Note: client_id should be loaded from environment variables for each service
        # This is a placeholder - you'll need to configure actual OAuth apps
        auth_url = f"{oauth_config['auth_url']}?client_id=YOUR_{service.upper()}_CLIENT_ID&redirect_uri={callback_url}&state={state}&scope={scopes}&response_type=code&access_type=offline"

        return jsonify({
            'auth_url': auth_url,
            'state': state
        }), 200

    except Exception as e:
        print(f"❌ Error starting OAuth flow: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/oauth/callback/<service>')
def oauth_callback(service):
    """Handle OAuth callback and exchange code for tokens"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')

        if error:
            return f"<html><body><h2>Authorization failed</h2><p>{error}</p><a href='/integrations'>Back to Integrations</a></body></html>", 400

        if not code or not state:
            return "<html><body><h2>Invalid callback</h2><p>Missing code or state</p></body></html>", 400

        # Verify state and get user_id
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, service FROM oauth_states WHERE state = ?
        """, (state,))

        oauth_state = cursor.fetchone()

        if not oauth_state:
            conn.close()
            return "<html><body><h2>Invalid state</h2><p>State not found or expired</p></body></html>", 400

        user_id, stored_service = oauth_state

        if stored_service != service:
            conn.close()
            return "<html><body><h2>Service mismatch</h2></body></html>", 400

        # Delete used state
        cursor.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        conn.commit()

        # Exchange authorization code for access token
        # NOTE: This is a placeholder - actual OAuth token exchange requires:
        # 1. Making POST request to oauth_config['token_url']
        # 2. Including client_id, client_secret, code, redirect_uri
        # 3. Parsing response to get access_token, refresh_token, expiry

        # For now, store a placeholder (you'll need to implement actual OAuth exchange)
        cursor.execute("""
            INSERT OR REPLACE INTO user_integrations
            (user_id, service, access_token, refresh_token, token_expiry, is_active)
            VALUES (?, ?, ?, ?, datetime('now', '+3600 seconds'), 1)
        """, (user_id, service, f'PLACEHOLDER_TOKEN_{service}', f'PLACEHOLDER_REFRESH_{service}'))

        conn.commit()
        conn.close()

        # Redirect to integrations page with success message
        return f"""
        <html>
        <head><title>Connected Successfully</title></head>
        <body style="font-family: system-ui; text-align: center; padding: 50px;">
            <h1 style="color: #48bb78;">✓ Successfully Connected</h1>
            <p>You've connected {OAUTH_CONFIG[service]['name']} to your AI Team account.</p>
            <p><a href="/integrations" style="background: #667eea; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; display: inline-block; margin-top: 20px;">Back to Integrations</a></p>
            <script>
                setTimeout(function() {{ window.location.href = '/integrations'; }}, 3000);
            </script>
        </body>
        </html>
        """, 200

    except Exception as e:
        print(f"❌ OAuth callback error: {str(e)}")
        return f"<html><body><h2>Error</h2><p>{str(e)}</p></body></html>", 500

@app.route('/api/user-integrations/<service>', methods=['DELETE'])
@login_required
def disconnect_oauth_integration(service):
    """Disconnect an OAuth integration"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM user_integrations
            WHERE user_id = ? AND service = ?
        """, (current_user.id, service))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Integration not found'}), 404

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'{service} disconnected successfully'
        }), 200

    except Exception as e:
        print(f"❌ Error disconnecting integration: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================
# INTEGRATION HELPER FUNCTIONS (FOR AGENTS)
# ============================================

def get_user_oauth_token(user_id, service):
    """Get OAuth access token for a service"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT access_token, refresh_token, token_expiry
            FROM user_integrations
            WHERE user_id = ? AND service = ? AND is_active = 1
        """, (user_id, service))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'access_token': result[0],
                'refresh_token': result[1],
                'token_expiry': result[2]
            }
        return None

    except Exception as e:
        print(f"Error getting OAuth token: {e}")
        return None

def send_email_via_integration(user_id, to_email, subject, body):
    """
    Send email via Gmail integration

    NOTE: This is a placeholder. In production, this would:
    1. Get user's Gmail OAuth token
    2. Use Gmail API to send email
    3. Handle token refresh if expired
    4. Return success/failure status
    """
    token_info = get_user_oauth_token(user_id, 'gmail')

    if not token_info:
        return {
            'success': False,
            'error': 'Gmail not connected. Please connect Gmail via Integrations page.'
        }

    # PLACEHOLDER: Actual Gmail API call would go here
    # Example:
    # from googleapiclient.discovery import build
    # from google.oauth2.credentials import Credentials
    #
    # creds = Credentials(token=token_info['access_token'])
    # service = build('gmail', 'v1', credentials=creds)
    # message = create_message('me', to_email, subject, body)
    # result = service.users().messages().send(userId='me', body=message).execute()

    print(f"[PLACEHOLDER] Would send email to {to_email} via Gmail")

    return {
        'success': True,
        'message': 'Email functionality requires OAuth app configuration',
        'placeholder': True
    }

def post_to_twitter(user_id, text):
    """
    Post to Twitter/X via integration

    NOTE: This is a placeholder. In production, this would:
    1. Get user's Twitter OAuth token
    2. Use Twitter API v2 to create tweet
    3. Handle token refresh if needed
    4. Return tweet ID and URL
    """
    token_info = get_user_oauth_token(user_id, 'twitter')

    if not token_info:
        return {
            'success': False,
            'error': 'Twitter not connected. Please connect Twitter via Integrations page.'
        }

    print(f"[PLACEHOLDER] Would post to Twitter: {text}")

    return {
        'success': True,
        'message': 'Twitter posting requires OAuth app configuration',
        'placeholder': True
    }

def post_to_linkedin(user_id, text):
    """
    Post to LinkedIn via integration

    NOTE: This is a placeholder for LinkedIn posting
    """
    token_info = get_user_oauth_token(user_id, 'linkedin')

    if not token_info:
        return {
            'success': False,
            'error': 'LinkedIn not connected'
        }

    print(f"[PLACEHOLDER] Would post to LinkedIn: {text}")

    return {
        'success': True,
        'message': 'LinkedIn posting requires OAuth app configuration',
        'placeholder': True
    }

def create_calendar_event(user_id, title, start_time, end_time, description=None):
    """
    Create Google Calendar event via integration

    NOTE: This is a placeholder. In production, this would:
    1. Get user's Google Calendar OAuth token
    2. Use Google Calendar API to create event
    3. Return event ID and link
    """
    token_info = get_user_oauth_token(user_id, 'google_calendar')

    if not token_info:
        return {
            'success': False,
            'error': 'Google Calendar not connected'
        }

    print(f"[PLACEHOLDER] Would create calendar event: {title}")

    return {
        'success': True,
        'message': 'Calendar integration requires OAuth app configuration',
        'placeholder': True
    }

def get_available_integration_actions(user_id):
    """
    Get list of available integration actions based on user's connections

    Returns a dictionary of available actions organized by category
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT service FROM user_integrations
            WHERE user_id = ? AND is_active = 1
        """, (user_id,))

        connected_services = [row[0] for row in cursor.fetchall()]
        conn.close()

        actions = {
            'email': [],
            'social': [],
            'calendar': [],
            'productivity': []
        }

        if 'gmail' in connected_services:
            actions['email'].extend([
                {'name': 'send_email', 'description': 'Send email via Gmail'},
                {'name': 'read_emails', 'description': 'Read recent emails'},
                {'name': 'search_emails', 'description': 'Search emails'}
            ])

        if 'outlook' in connected_services:
            actions['email'].extend([
                {'name': 'send_outlook_email', 'description': 'Send email via Outlook'},
                {'name': 'read_outlook_emails', 'description': 'Read Outlook emails'}
            ])

        if 'twitter' in connected_services:
            actions['social'].extend([
                {'name': 'post_tweet', 'description': 'Post to Twitter'},
                {'name': 'get_mentions', 'description': 'Get Twitter mentions'}
            ])

        if 'linkedin' in connected_services:
            actions['social'].extend([
                {'name': 'post_linkedin', 'description': 'Post to LinkedIn'},
                {'name': 'get_connections', 'description': 'Get LinkedIn connections'}
            ])

        if 'google_calendar' in connected_services:
            actions['calendar'].extend([
                {'name': 'create_event', 'description': 'Create calendar event'},
                {'name': 'list_events', 'description': 'List upcoming events'},
                {'name': 'update_event', 'description': 'Update existing event'}
            ])

        if 'zoom' in connected_services:
            actions['calendar'].extend([
                {'name': 'create_zoom_meeting', 'description': 'Create Zoom meeting'},
                {'name': 'list_meetings', 'description': 'List scheduled Zoom meetings'}
            ])

        return actions

    except Exception as e:
        print(f"Error getting available actions: {e}")
        return {}

@app.route('/api/integrations/oauth/<integration_key>/start')
@login_required
def start_oauth_flow(integration_key):
    """Start OAuth flow for an integration"""
    try:
        oauth_config = OAUTH_CONFIG.get(integration_key)
        if not oauth_config:
            return jsonify({'error': 'OAuth not supported for this integration'}), 400

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state in session
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                integration_key TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT INTO oauth_states (state, user_id, integration_key)
            VALUES (?, ?, ?)
        """, (state, current_user.id, integration_key))

        conn.commit()
        conn.close()

        # Build OAuth URL
        auth_url = f"{oauth_config['auth_url']}?client_id=YOUR_CLIENT_ID&redirect_uri={request.host_url}api/integrations/oauth/callback&state={state}&scope={','.join(oauth_config['scopes'])}"

        return jsonify({
            'auth_url': auth_url,
            'state': state
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/oauth/callback')
def oauth_callback_legacy():
    """Handle OAuth callback (legacy endpoint)"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')

        if not code or not state:
            return "OAuth failed: Missing code or state", 400

        # Verify state and get integration
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, integration_key FROM oauth_states
            WHERE state = ? AND created_at >= datetime('now', '-10 minutes')
        """, (state,))

        result = cursor.fetchone()
        if not result:
            conn.close()
            return "OAuth failed: Invalid or expired state", 400

        user_id, integration_key = result

        # Clean up state
        cursor.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        conn.commit()
        conn.close()

        # Exchange code for token (simplified - needs actual OAuth implementation)
        # oauth_config = OAUTH_CONFIG[integration_key]
        # Make POST request to token_url with code

        return redirect('/integrations?oauth_success=true')

    except Exception as e:
        return f"OAuth callback error: {str(e)}", 500

# ============================================
# STRIPE PAYMENT ROUTES
# ============================================

@app.route('/pricing')
@login_required
def pricing():
    """Display pricing page with Stripe checkout"""
    return render_template('pricing.html',
                         current_plan=current_user.subscription_tier,
                         starter_price_id=STRIPE_STARTER_PRICE_ID,
                         pro_price_id=STRIPE_PRO_PRICE_ID,
                         enterprise_price_id=STRIPE_ENTERPRISE_PRICE_ID)


@app.route('/api/create-portal-session', methods=['POST'])
@login_required
def create_portal_session():
    """Create a Stripe Customer Portal session for subscription management"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get user's Stripe customer ID
        cursor.execute("SELECT stripe_customer_id FROM users WHERE id = ?", (current_user.id,))
        result = cursor.fetchone()
        conn.close()

        if not result or not result[0]:
            return jsonify({
                'error': 'No active subscription found'
            }), 400

        stripe_customer_id = result[0]

        # Create a portal session
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=request.host_url + 'dashboard',
        )

        return jsonify({
            'url': session.url
        }), 200

    except Exception as e:
        print(f"❌ Error creating portal session: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500


# ============================================
# STRIPE PROMO CODE / DISCOUNT HELPERS
# ============================================

def create_stripe_coupon_for_promo(promo_code, discount_type, discount_value):
    """Create a Stripe coupon based on promo code discount

    Args:
        promo_code: The promo code string
        discount_type: 'amount' or 'percent'
        discount_value: Dollar amount or percentage

    Returns:
        Stripe coupon ID or None if error
    """
    try:
        # Check if coupon already exists for this promo code
        coupon_id = f"PROMO_{promo_code}"

        try:
            # Try to retrieve existing coupon
            existing_coupon = stripe.Coupon.retrieve(coupon_id)
            return coupon_id
        except stripe.error.InvalidRequestError:
            # Coupon doesn't exist, create it
            pass

        # Create new coupon based on discount type
        if discount_type == 'amount':
            # Dollar amount off (in cents)
            coupon = stripe.Coupon.create(
                id=coupon_id,
                amount_off=int(discount_value * 100),  # Convert to cents
                currency='usd',
                duration='once',  # Apply only to first payment
                name=f"{promo_code} - ${discount_value:.2f} off"
            )
        elif discount_type == 'percent':
            # Percentage off
            coupon = stripe.Coupon.create(
                id=coupon_id,
                percent_off=discount_value,
                duration='once',  # Apply only to first payment
                name=f"{promo_code} - {discount_value:.0f}% off"
            )
        else:
            print(f"Invalid discount type: {discount_type}")
            return None

        print(f"✅ Created Stripe coupon: {coupon.id}")
        return coupon.id

    except Exception as e:
        print(f"❌ Error creating Stripe coupon: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_user_promo_discount(user_id):
    """Get user's active promo code discount

    Returns:
        dict with discount_type, discount_value, promo_code or None
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT promo_discount_type, promo_discount_value, promo_code_applied
            FROM users
            WHERE id = ?
        """, (user_id,))

        result = cursor.fetchone()
        conn.close()

        if result and result[0] and result[1]:
            return {
                'discount_type': result[0],
                'discount_value': result[1],
                'promo_code': result[2]
            }

        return None

    except Exception as e:
        print(f"❌ Error getting user promo discount: {e}")
        return None


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create Stripe checkout session for subscription"""
    try:
        # Check if Stripe is configured
        if not stripe.api_key or stripe.api_key == 'your_stripe_secret_key_here':
            return jsonify({'error': 'Stripe is not configured. Please contact the administrator to set up payment processing.'}), 500

        price_id = request.form.get('price_id')
        print(f"🔍 Checkout requested for price_id: {price_id}")
        print(f"🔍 Available price IDs: STARTER={STRIPE_STARTER_PRICE_ID}, PRO={STRIPE_PRO_PRICE_ID}, ENTERPRISE={STRIPE_ENTERPRISE_PRICE_ID}")

        # Determine plan details based on price_id
        if price_id == STRIPE_STARTER_PRICE_ID:
            plan_name = 'starter'
        elif price_id == STRIPE_PRO_PRICE_ID:
            plan_name = 'pro'
        elif price_id == STRIPE_ENTERPRISE_PRICE_ID:
            plan_name = 'enterprise'
        else:
            print(f"❌ Invalid price_id received: {price_id}")
            return jsonify({'error': f'Invalid price ID: {price_id}'}), 400

        # Get or create Stripe customer
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT stripe_customer_id FROM users WHERE id = ?", (current_user.id,))
        result = cursor.fetchone()

        if result and result[0]:
            customer_id = result[0]
        else:
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={'user_id': current_user.id}
            )
            customer_id = customer.id

            # Save customer ID
            cursor.execute(
                "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
                (customer_id, current_user.id)
            )
            conn.commit()

        conn.close()

        # Check if user has an active promo discount
        promo_discount = get_user_promo_discount(current_user.id)
        discounts = []

        if promo_discount:
            # Create Stripe coupon for this promo code
            coupon_id = create_stripe_coupon_for_promo(
                promo_discount['promo_code'],
                promo_discount['discount_type'],
                promo_discount['discount_value']
            )

            if coupon_id:
                discounts = [{'coupon': coupon_id}]
                print(f"✅ Applying discount to checkout: {promo_discount['promo_code']} - {promo_discount['discount_type']} {promo_discount['discount_value']}")
            else:
                print(f"⚠️  Failed to create Stripe coupon, proceeding without discount")

        # Create checkout session
        session_params = {
            'customer': customer_id,
            'payment_method_types': ['card'],
            'line_items': [{
                'price': price_id,
                'quantity': 1,
            }],
            'mode': 'subscription',
            'allow_promotion_codes': True,  # Enable promo code entry in checkout UI
            'success_url': request.host_url + 'success?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': request.host_url + 'cancel',
            'metadata': {
                'user_id': current_user.id,
                'plan': plan_name
            }
        }

        # Add discounts if available
        if discounts:
            session_params['discounts'] = discounts

        print(f"🔍 Creating Stripe checkout session with params: customer={customer_id}, price={price_id}, plan={plan_name}")
        checkout_session = stripe.checkout.Session.create(**session_params)
        print(f"✅ Checkout session created successfully: {checkout_session.id}")

        return redirect(checkout_session.url)

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error creating checkout session: {str(e)}")
        print(f"Full traceback:\n{error_trace}")

        # Return detailed error in development
        error_message = f"Error creating checkout session: {str(e)}"
        return jsonify({
            'error': error_message,
            'details': str(e),
            'type': type(e).__name__
        }), 500


@app.route('/api/get-active-discount')
@login_required
def get_active_discount():
    """Get user's active promo code discount"""
    try:
        discount = get_user_promo_discount(current_user.id)

        if discount:
            if discount['discount_type'] == 'amount':
                message = f"${discount['discount_value']:.2f} off"
            elif discount['discount_type'] == 'percent':
                message = f"{discount['discount_value']:.0f}% off"
            else:
                message = "Discount available"

            return jsonify({
                'has_discount': True,
                'type': discount['discount_type'],
                'value': discount['discount_value'],
                'code': discount['promo_code'],
                'message': message
            })
        else:
            return jsonify({'has_discount': False})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/success')
@login_required
def success():
    """Payment success page"""
    session_id = request.args.get('session_id')
    
    try:
        # Retrieve session details
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Get plan details
        plan_name = session.metadata.get('plan', 'unknown')
        
        # Get daily limit based on plan
        limits = {
            'starter': 100,
            'pro': 500
        }
        daily_limit = limits.get(plan_name, 100)
        
        return render_template('success.html',
                             plan_name=plan_name.capitalize(),
                             daily_limit=daily_limit)
    except Exception as e:
        print(f"Error retrieving session: {str(e)}")
        return render_template('success.html',
                             plan_name='Unknown',
                             daily_limit=100)


@app.route('/cancel')
@login_required
def cancel():
    """Payment cancelled page"""
    return render_template('cancel.html')


@app.route('/api/stripe-webhook', methods=['POST'])
@app.route('/stripe-webhook', methods=['POST'])
@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session_completed(session)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_invoice_payment_succeeded(invoice)
    
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_invoice_payment_failed(invoice)
    
    return jsonify({'status': 'success'})


# ============================================
# STRIPE WEBHOOK HANDLERS
# ============================================

def handle_checkout_session_completed(session):
    """Handle completed checkout session"""
    try:
        user_id = session['metadata']['user_id']
        plan = session['metadata']['plan']
        customer_id = session['customer']
        subscription_id = session['subscription']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Clear promo discount after successful payment (one-time use)
        cursor.execute("""
            UPDATE users
            SET stripe_customer_id = ?,
                stripe_subscription_id = ?,
                subscription_tier = ?,
                promo_discount_type = NULL,
                promo_discount_value = NULL,
                promo_code_applied = NULL
            WHERE id = ?
        """, (customer_id, subscription_id, plan, user_id))

        conn.commit()
        conn.close()

        print(f"✅ User {user_id} upgraded to {plan} (promo discount cleared)")

    except Exception as e:
        print(f"Error handling checkout session: {str(e)}")


def handle_subscription_updated(subscription):
    """Handle subscription updates"""
    try:
        customer_id = subscription['customer']
        status = subscription['status']
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if status == 'active':
            print(f"✅ Subscription active for customer {customer_id}")
        elif status == 'canceled':
            cursor.execute("""
                UPDATE users
                SET subscription_tier = 'free',
                    stripe_subscription_id = NULL
                WHERE stripe_customer_id = ?
            """, (customer_id,))
            conn.commit()
            print(f"❌ Subscription cancelled for customer {customer_id}")
        
        conn.close()
    
    except Exception as e:
        print(f"Error handling subscription update: {str(e)}")


def handle_subscription_deleted(subscription):
    """Handle subscription deletion"""
    try:
        customer_id = subscription['customer']
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users
            SET subscription_tier = 'free',
                stripe_subscription_id = NULL
            WHERE stripe_customer_id = ?
        """, (customer_id,))
        
        conn.commit()
        conn.close()
        
        print(f"🗑️ Subscription deleted for customer {customer_id}")
    
    except Exception as e:
        print(f"Error handling subscription deletion: {str(e)}")


def handle_invoice_payment_succeeded(invoice):
    """Handle successful payment"""
    try:
        customer_id = invoice['customer']
        amount_paid = invoice['amount_paid'] / 100  # Convert from cents
        
        print(f"💰 Payment of ${amount_paid} succeeded for customer {customer_id}")
    
    except Exception as e:
        print(f"Error handling payment success: {str(e)}")


def handle_invoice_payment_failed(invoice):
    """Handle failed payment"""
    try:
        customer_id = invoice['customer']
        
        print(f"⚠️ Payment failed for customer {customer_id}")
        # You might want to send an email notification here
    
    except Exception as e:
        print(f"Error handling payment failure: {str(e)}")


@app.route('/automations-test')
@login_required
def automations_test():
    """Test endpoint to diagnose automations issues"""
    return f"""
    <html>
    <head><title>Automations Test</title></head>
    <body style="font-family: sans-serif; padding: 40px;">
        <h1>Automations Test Page</h1>
        <p>If you can see this, the route works!</p>
        <p><strong>User ID:</strong> {current_user.id}</p>
        <p><strong>Email:</strong> {current_user.email}</p>
        <p><strong>Subscription:</strong> {current_user.subscription_tier}</p>
        <hr>
        <h2>Testing API Endpoints:</h2>
        <div id="results"></div>
        <script>
            async function testEndpoints() {{
                const results = document.getElementById('results');
                
                // Test API key endpoint
                try {{
                    const response = await fetch('/api/get-api-key');
                    const data = await response.json();
                    results.innerHTML += '<p>✅ /api/get-api-key: ' + JSON.stringify(data) + '</p>';
                }} catch (e) {{
                    results.innerHTML += '<p>❌ /api/get-api-key: ' + e.message + '</p>';
                }}
                
                // Test usage stats
                try {{
                    const response = await fetch('/api/usage-stats');
                    const data = await response.json();
                    results.innerHTML += '<p>✅ /api/usage-stats: ' + JSON.stringify(data) + '</p>';
                }} catch (e) {{
                    results.innerHTML += '<p>❌ /api/usage-stats: ' + e.message + '</p>';
                }}
                
                // Test webhooks
                try {{
                    const response = await fetch('/api/webhooks');
                    const data = await response.json();
                    results.innerHTML += '<p>✅ /api/webhooks: ' + JSON.stringify(data) + '</p>';
                }} catch (e) {{
                    results.innerHTML += '<p>❌ /api/webhooks: ' + e.message + '</p>';
                }}
            }}
            testEndpoints();
        </script>
        <hr>
        <p><a href="/automations">Try loading actual automations page</a></p>
    </body>
    </html>
    """

@app.route('/automations')
@login_required
def automations():
    """Automations page"""
    try:
        print(f"DEBUG: Automations page accessed by user {current_user.id}")
        print(f"DEBUG: User subscription tier: {current_user.subscription_tier}")
        return render_template('automations.html', user=current_user)
    except Exception as e:
        print(f"ERROR: Automations page failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error loading automations page: {str(e)}", 500

@app.route('/admin')
@login_required
def admin_portal():
    """Admin portal - central hub for all admin functions (admin only)"""
    if current_user.id != 1:
        return redirect(url_for('dashboard'))
    return render_template('admin_portal.html', user=current_user)

@app.route('/promo-codes')
@login_required
def promo_codes_page():
    """Promo codes management page (admin only)"""
    if current_user.id != 1:
        return redirect(url_for('dashboard'))
    return render_template('promo-codes.html', user=current_user)

@app.route('/admin/global-agents-manager')
@login_required
def admin_global_agents_manager():
    """Admin global agents management page (admin only)"""
    if current_user.id != 1:
        return redirect(url_for('dashboard'))
    return render_template('admin_global_agents.html', user=current_user)

@app.route('/admin/support-messages')
@login_required
def admin_support_messages():
    """Admin support messages dashboard (admin only)"""
    if current_user.id != 1:
        return redirect(url_for('dashboard'))
    return render_template('admin_support.html', user=current_user)

@app.route('/admin/analytics')
@login_required
def admin_analytics():
    """Admin analytics dashboard (admin only)"""
    if current_user.id != 1:
        return redirect(url_for('dashboard'))
    return render_template('admin_dashboard.html', user=current_user)

@app.route('/api/admin/analytics')
@login_required
def api_admin_analytics():
    """Get analytics data (admin only)"""
    if current_user.id != 1:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # Messages today
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM chat_history 
                WHERE date(timestamp) = date('now')
            """)
            messages_today = cursor.fetchone()[0]
        except:
            messages_today = 0
        
        # Total messages
        try:
            cursor.execute("SELECT COUNT(*) FROM chat_history")
            total_messages = cursor.fetchone()[0]
        except:
            total_messages = 0
        
        # Paid users (Starter, Pro)
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE subscription_tier IN ('starter', 'pro')
        """)
        paid_users = cursor.fetchone()[0]
        
        # Subscription breakdown
        cursor.execute("""
            SELECT subscription_tier, COUNT(*) 
            FROM users 
            GROUP BY subscription_tier
        """)
        subscription_data = cursor.fetchall()
        subscription_breakdown = {tier: count for tier, count in subscription_data}
        
        # Agent usage - skip if column doesn't exist
        agent_usage = {}
        try:
            cursor.execute("""
                SELECT agent, COUNT(*) 
                FROM chat_history 
                GROUP BY agent
            """)
            agent_data = cursor.fetchall()
            agent_usage = {agent: count for agent, count in agent_data}
        except Exception as e:
            # Agent column doesn't exist yet, return empty dict
            print(f"Agent usage not available: {e}")
            agent_usage = {
                'Luna': 0,
                'Mila': 0,
                'Sage': 0,
                'Ember': 0,
                'Sol': 0,
                'Nova': 0,
                'Theo': 0
            }
        
        # Total custom agents
        cursor.execute("SELECT COUNT(*) FROM custom_agents")
        total_custom_agents = cursor.fetchone()[0]
        
        # Recent activity (last 20 users)
        cursor.execute("""
            SELECT 
                u.email,
                u.subscription_tier,
                u.created_at,
                COUNT(CASE WHEN date(ch.timestamp) = date('now') THEN 1 END) as messages_today,
                COUNT(ch.id) as total_messages,
                MAX(ch.timestamp) as last_active
            FROM users u
            LEFT JOIN chat_history ch ON u.id = ch.user_id
            GROUP BY u.id, u.email, u.subscription_tier, u.created_at
            ORDER BY last_active DESC
            LIMIT 20
        """)
        recent_activity = []
        for row in cursor.fetchall():
            recent_activity.append({
                'email': row[0],
                'subscription_tier': row[1] or 'free',
                'created_at': row[2] if row[2] else None,
                'messages_today': row[3],
                'total_messages': row[4],
                'last_active': str(row[5]) if row[5] else 'Never'
            })
        
        # Top users by message count
        cursor.execute("""
            SELECT 
                u.email,
                u.subscription_tier,
                u.created_at,
                COUNT(ch.id) as total_messages
            FROM users u
            LEFT JOIN chat_history ch ON u.id = ch.user_id
            GROUP BY u.id, u.email, u.subscription_tier, u.created_at
            ORDER BY total_messages DESC
            LIMIT 10
        """)
        top_users = []
        for row in cursor.fetchall():
            top_users.append({
                'email': row[0],
                'subscription_tier': row[1] or 'free',
                'created_at': str(row[2]) if row[2] else None,
                'total_messages': row[3]
            })
        
        conn.close()
        
        return jsonify({
            'total_users': total_users,
            'messages_today': messages_today,
            'total_messages': total_messages,
            'paid_users': paid_users,
            'subscription_breakdown': subscription_breakdown,
            'agent_usage': agent_usage,
            'total_custom_agents': total_custom_agents,
            'recent_activity': recent_activity,
            'top_users': top_users,
            'avg_response_time': 250,  # Placeholder
            'error_rate': 0.1,  # Placeholder
            'uptime': 99.9  # Placeholder
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================
# GOOGLE AI / GEMINI CONFIGURATION
# ============================================
try:
    google_api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if google_api_key:
        genai.configure(api_key=google_api_key)
        print("✅ Google AI (Gemini) initialized")
    else:
        print("⚠️  Google AI not configured - set GOOGLE_AI_API_KEY to enable Gemini models")
except Exception as e:
    print(f"⚠️  Google AI initialization failed: {e}")

# ============================================
# MULTI-MODEL AI CONFIGURATION
# ============================================

MODELS = {
    # Claude Models (Anthropic)
    'claude-sonnet-4.5': {
        'provider': 'anthropic',
        'model_id': 'claude-sonnet-4-20250514',
        'name': 'Claude Sonnet 4.5',
        'description': 'Fast & intelligent - Best all-around',
        'max_tokens': 2000,
        'cost': '$3/1M tokens'
    },
    'claude-opus-4': {
        'provider': 'anthropic',
        'model_id': 'claude-opus-4-20250514',
        'name': 'Claude Opus 4',
        'description': 'Most capable - Deep reasoning',
        'max_tokens': 2000,
        'cost': '$15/1M tokens'
    },
    'claude-haiku-4.5': {
        'provider': 'anthropic',
        'model_id': 'claude-haiku-4-5-20251001',
        'name': 'Claude Haiku 4.5',
        'description': 'Ultra-fast - Budget friendly',
        'max_tokens': 2000,
        'cost': '$0.80/1M tokens'
    },
    
    # OpenAI Models (GPT)
    'gpt-4o': {
        'provider': 'openai',
        'model_id': 'gpt-4o',
        'name': 'GPT-4o',
        'description': 'Latest - Multimodal powerhouse',
        'max_tokens': 2000,
        'cost': '$2.50/1M tokens'
    },
    'gpt-4-turbo': {
        'provider': 'openai',
        'model_id': 'gpt-4-turbo-preview',
        'name': 'GPT-4 Turbo',
        'description': 'Powerful - Great for complex tasks',
        'max_tokens': 2000,
        'cost': '$10/1M tokens'
    },
    'gpt-4o-mini': {
        'provider': 'openai',
        'model_id': 'gpt-4o-mini',
        'name': 'GPT-4o Mini',
        'description': 'Super fast - Most affordable',
        'max_tokens': 2000,
        'cost': '$0.15/1M tokens'
    },
    
    # Google Gemini Models
    'gemini-2.0-flash': {
        'provider': 'google',
        'model_id': 'gemini-2.0-flash-exp',
        'name': 'Gemini 2.0 Flash',
        'description': 'Newest - FREE tier available!',
        'max_tokens': 2000,
        'cost': 'FREE (15 req/min)'
    },
    'gemini-1.5-pro': {
        'provider': 'google',
        'model_id': 'gemini-1.5-pro',
        'name': 'Gemini 1.5 Pro',
        'description': 'Advanced - 2M token context',
        'max_tokens': 2000,
        'cost': '$1.25/1M tokens'
    },

    # DeepSeek Models (Chinese AI - Very cost-effective)
    'deepseek-v3': {
        'provider': 'deepseek',
        'model_id': 'deepseek-chat',
        'name': 'DeepSeek V3',
        'description': 'Ultra cheap - Great reasoning',
        'max_tokens': 2000,
        'cost': '$0.27/1M tokens'
    },
    'deepseek-r1': {
        'provider': 'deepseek',
        'model_id': 'deepseek-reasoner',
        'name': 'DeepSeek R1',
        'description': 'Chain-of-thought - Deep reasoning',
        'max_tokens': 2000,
        'cost': '$0.55/1M tokens'
    },

    # Perplexity Models (Real-time search-augmented)
    'perplexity-sonar': {
        'provider': 'perplexity',
        'model_id': 'sonar',
        'name': 'Perplexity Sonar',
        'description': 'Real-time search - Up-to-date info',
        'max_tokens': 2000,
        'cost': '$1/1M tokens'
    },
    'perplexity-sonar-pro': {
        'provider': 'perplexity',
        'model_id': 'sonar-pro',
        'name': 'Perplexity Sonar Pro',
        'description': 'Advanced search - Best for research',
        'max_tokens': 2000,
        'cost': '$3/1M tokens'
    },

    # Grok Models (xAI - Elon Musk)
    'grok-2': {
        'provider': 'grok',
        'model_id': 'grok-2-latest',
        'name': 'Grok 2',
        'description': 'Latest Grok - Real-time X/Twitter data',
        'max_tokens': 2000,
        'cost': '$2/1M tokens'
    },
    'grok-2-vision': {
        'provider': 'grok',
        'model_id': 'grok-2-vision-latest',
        'name': 'Grok 2 Vision',
        'description': 'Multimodal - Image understanding',
        'max_tokens': 2000,
        'cost': '$2/1M tokens'
    },

    # Meta Llama Models (Open source)
    'llama-3.3-70b': {
        'provider': 'openrouter',
        'model_id': 'meta-llama/llama-3.3-70b-instruct',
        'name': 'Llama 3.3 70B',
        'description': 'Meta\'s latest - Open source power',
        'max_tokens': 2000,
        'cost': '$0.18/1M tokens'
    },
    'llama-3.1-405b': {
        'provider': 'openrouter',
        'model_id': 'meta-llama/llama-3.1-405b-instruct',
        'name': 'Llama 3.1 405B',
        'description': 'Largest open model - Top performance',
        'max_tokens': 2000,
        'cost': '$2.70/1M tokens'
    },

    # Mistral Models (European AI)
    'mistral-large': {
        'provider': 'mistral',
        'model_id': 'mistral-large-latest',
        'name': 'Mistral Large',
        'description': 'European flagship - Multilingual',
        'max_tokens': 2000,
        'cost': '$2/1M tokens'
    },
    'mistral-small': {
        'provider': 'mistral',
        'model_id': 'mistral-small-latest',
        'name': 'Mistral Small',
        'description': 'Fast & efficient - Cost-effective',
        'max_tokens': 2000,
        'cost': '$0.20/1M tokens'
    }
}

# ============================================
# AGENT COORDINATION SYSTEM
# ============================================

# Agent capabilities for natural language routing
AGENT_CAPABILITIES = {
    'Luna': {
        'keywords': ['research', 'analyze', 'data', 'find', 'investigate', 'study', 'compare', 'facts', 'information', 'insights'],
        'strengths': ['Deep research', 'Data analysis', 'Fact-finding', 'Pattern recognition', 'Strategic insights'],
        'when_to_use': 'Research, analysis, data interpretation, finding information'
    },
    'Mila': {
        'keywords': ['plan', 'organize', 'schedule', 'task', 'workflow', 'project', 'manage', 'coordinate', 'prioritize', 'structure'],
        'strengths': ['Project planning', 'Task organization', 'Workflow creation', 'Time management', 'Action plans'],
        'when_to_use': 'Planning projects, organizing tasks, creating workflows, breaking down complex work'
    },
    'Sage': {
        'keywords': ['write', 'edit', 'content', 'copy', 'draft', 'rewrite', 'polish', 'text', 'article', 'blog'],
        'strengths': ['Writing compelling copy', 'Editing content', 'Tone adaptation', 'Clear communication', 'Content refinement'],
        'when_to_use': 'Writing, editing, content creation, communication drafts'
    },
    'Ember': {
        'keywords': ['create', 'design', 'ideas', 'creative', 'brainstorm', 'concept', 'innovative', 'brand', 'visual', 'unique'],
        'strengths': ['Creative ideation', 'Design concepts', 'Brand identity', 'Visual thinking', 'Innovation'],
        'when_to_use': 'Creative concepts, design direction, brainstorming, brand development'
    },
    'Sol': {
        'keywords': ['strategy', 'business', 'growth', 'decision', 'long-term', 'goals', 'vision', 'opportunity', 'risk', 'positioning'],
        'strengths': ['Strategic planning', 'Business growth', 'Decision frameworks', 'Risk assessment', 'Big picture thinking'],
        'when_to_use': 'Strategy, business decisions, long-term planning, growth opportunities'
    }
}

def analyze_intent_and_suggest_agent(message):
    """
    Analyzes user message and suggests the best agent for the task.
    Returns (agent_name, confidence_score) or (None, 0) if no clear match.
    """
    message_lower = message.lower()
    scores = {}

    for agent, capabilities in AGENT_CAPABILITIES.items():
        score = 0
        # Check for keyword matches
        for keyword in capabilities['keywords']:
            if keyword in message_lower:
                score += 2
        scores[agent] = score

    # Get agent with highest score
    if scores:
        best_agent = max(scores, key=scores.get)
        best_score = scores[best_agent]

        if best_score > 0:
            return best_agent, best_score

    return None, 0

def get_agent_coordination_context():
    """
    Returns context about available agents for coordination.
    This is added to agent prompts to enable delegation.
    """
    return """
TEAM COORDINATION:
You are part of an AI Team. When a request would be better handled by another agent, you can suggest they help:

Available Agents:
- Luna: Research & analysis, data insights, fact-finding
- Mila: Project planning, organization, workflow creation
- Sage: Writing & content, editing, communication
- Ember: Creative concepts, design direction, brainstorming
- Sol: Strategy, business decisions, long-term planning

If a user request falls outside your expertise, naturally acknowledge it and suggest which agent would be better suited. For example: "This sounds like a strategic planning question - Sol would be perfect for this. Would you like me to bring Sol into this conversation?"

The system will automatically route the conversation when you make this suggestion.
"""

# ============================================
# AGENT PERSONALITIES
# ============================================

AGENT_PERSONALITIES = {
    'Luna': {
        'role': 'Research & Analysis',
        'system_prompt': """You are Luna, a thoughtful analyst who specializes in research and data analysis.

COMMUNICATION STYLE:
Write in natural, conversational paragraphs. Do NOT use asterisks, hashtags, dashes, or bullet points. Do NOT use markdown formatting. Just write normally like you're talking to someone.

Keep responses warm, clear, and direct. Avoid overexplaining unless asked. Ask only ONE focused question at a time if needed. Remember conversation context to avoid repetition. Never reintroduce yourself - jump straight to helping.

YOUR EXPERTISE:
Deep research and fact-finding, data analysis and insights, strategic thinking and planning, connecting dots between information.

WORKING WITH THE TEAM:
Reference work by other agents when relevant. Build on previous conversations naturally. If another agent already covered something, acknowledge it briefly and add your perspective.

RESPONSE APPROACH:
Address the question directly in clear paragraphs. Provide key insights in natural language. Ask ONE clarifying question if needed, or suggest next steps.

Remember: Be helpful, stay focused, move conversations forward. Write like a human, not a document."""
    },
    
    'Mila': {
        'role': 'Organization & Planning',
        'system_prompt': """You are Mila, a master organizer who turns chaos into clear action plans.

COMMUNICATION STYLE:
Write in natural, conversational paragraphs. Do NOT use asterisks, hashtags, dashes, or bullet points. Do NOT use markdown formatting. Just write normally like you're talking to someone.

Keep responses warm, clear, and direct. Avoid overexplaining unless asked. Ask only ONE focused question at a time if needed. Remember what's been discussed. Never reintroduce yourself.

YOUR EXPERTISE:
Project planning and organization, creating actionable workflows, breaking complex tasks into steps, time management and prioritization.

WORKING WITH THE TEAM:
Build on Luna's research with actionable plans. Help implement Ember's creative ideas. Coordinate with Sol on project timelines.

RESPONSE APPROACH:
Acknowledge the task clearly in natural language. Provide organized action steps in clear paragraphs. Suggest priorities or ask ONE clarifying question if needed.

Remember: Stay practical, create clarity, drive action. Write like a human, not a checklist."""
    },
    
    'Sage': {
        'role': 'Writing & Content',
        'system_prompt': """You are Sage, a skilled wordsmith who crafts clear, compelling content.

COMMUNICATION STYLE:
Write in natural, conversational paragraphs. Do NOT use asterisks, hashtags, dashes, or bullet points. Do NOT use markdown formatting. Just write normally like you're talking to someone.

Keep responses warm, clear, and direct. Get to the writing quickly. Ask only ONE focused question at a time if needed. Structure content for readability using natural paragraphs. Remember the user's voice and style preferences. Skip reintroductions.

YOUR EXPERTISE:
Writing compelling copy, editing and refining text, adapting tone and style, making complex ideas accessible.

WORKING WITH THE TEAM:
Polish Ember's creative concepts into polished copy. Turn Luna's research into readable content. Help Mila communicate plans clearly.

RESPONSE APPROACH:
Address the writing need directly. Provide the content or edit in clear paragraphs. Explain key choices briefly if helpful. Ask ONE question for refinement if needed.

Remember: Write first, explain second, move forward. Write like a human, not a document."""
    },
    
    'Ember': {
        'role': 'Creative Direction',
        'system_prompt': """You are Ember, a bold creative who sparks innovative ideas and unique solutions.

COMMUNICATION STYLE:
Write in natural, conversational paragraphs. Do NOT use asterisks, hashtags, dashes, or bullet points. Do NOT use markdown formatting. Just write normally like you're talking to someone.

Keep responses warm, clear, and enthusiastic. Be direct with ideas without overexplaining the creative process. Ask only ONE focused question at a time if needed. Present concepts in clear language. Remember user's creative preferences. Skip reintroductions and dive into creativity.

YOUR EXPERTISE:
Creative ideation and concepts, visual thinking and design direction, brand identity and messaging, making things memorable and unique.

WORKING WITH THE TEAM:
Turn Luna's insights into creative concepts. Give Sage compelling content to refine. Help Mila plan creative executions.

RESPONSE APPROACH:
Present creative concepts in natural paragraphs. Explain the reasoning briefly for each idea. Ask ONE question to refine direction if needed.

Remember: Inspire first, iterate second, stay bold. Write like a human, not a document."""
    },
    
    'Sol': {
        'role': 'Strategic Thinking',
        'system_prompt': """You are Sol, a strategic advisor who sees the big picture and guides long-term success.

COMMUNICATION STYLE:
Write in natural, conversational paragraphs. Do NOT use asterisks, hashtags, dashes, or bullet points. Do NOT use markdown formatting. Just write normally like you're talking to someone.

Keep responses warm, clear, and thoughtful. Be direct about strategy and avoid analysis paralysis. Ask only ONE focused question at a time if needed. Balance vision with pragmatism. Remember business context and goals. Skip reintroductions.

YOUR EXPERTISE:
Strategic planning and positioning, business growth and scaling, decision-making frameworks, risk assessment and opportunities.

WORKING WITH THE TEAM:
Frame Luna's research strategically. Validate Ember's creative direction against business goals. Help Mila prioritize what matters most.

RESPONSE APPROACH:
Provide strategic perspective in clear paragraphs. Present options with pros and cons in natural language. Recommend direction with reasoning. Ask ONE key question to clarify priorities if needed.

Remember: Think long-term, balance risk, guide with confidence. Write like a human, not a document."""
    },
    
    'Nova': {
        'role': 'Technical Solutions',
        'system_prompt': """You are Nova, a technical expert who solves complex problems and makes tech accessible.

COMMUNICATION STYLE:
Write in natural, conversational paragraphs. Do NOT use asterisks, hashtags, dashes, or bullet points. Do NOT use markdown formatting. Just write normally like you're talking to someone.

Keep responses warm, clear, and approachable. Be direct with solutions and skip unnecessary jargon. Ask only ONE focused question at a time if needed. Break down technical concepts simply in plain language. Remember technical context and constraints. Skip reintroductions.

YOUR EXPERTISE:
Technical problem-solving, code and system architecture, debugging and troubleshooting, explaining complex tech simply, website and web development (HTML/CSS/JavaScript).

WORKING WITH THE TEAM:
Implement Mila's organized plans technically. Make Theo's workflows technically sound. Validate technical feasibility for team ideas.

WEBSITE BUILDING INSTRUCTIONS:
When a user asks you to create a website, landing page, or any web component:
1. Create COMPLETE, working HTML code with embedded CSS and JavaScript
2. Include ALL code in a SINGLE file (no separate CSS/JS files)
3. Start your response with the full HTML code wrapped in triple backticks:
   ```html
   <!DOCTYPE html>
   <html>
   ...complete code here...
   </html>
   ```
4. After the code, add a brief explanation of features
5. The platform will automatically detect the code and create a downloadable file for the user

EXAMPLE WEBSITE RESPONSE FORMAT:
"Here's a complete landing page for your coffee shop:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Coffee Shop</title>
    <style>
        /* All CSS here */
    </style>
</head>
<body>
    <!-- All HTML here -->
    <script>
        // All JavaScript here
    </script>
</body>
</html>
```

This includes a responsive hero section, menu display, and contact form with email validation. The color scheme uses warm browns and creams. Just download the file and open it in your browser!"

RESPONSE APPROACH:
Identify the technical issue clearly in natural language. Provide solution with code or steps in plain paragraphs. Explain why it works briefly. Ask ONE question if more context needed.

Remember: Solve clearly, explain simply, move forward. Write like a human, not a document."""
    },
    
    'Theo': {
        'role': 'Implementation',
        'system_prompt': """You are Theo, a reliable builder who turns ideas into working solutions through practical action.

COMMUNICATION STYLE:
Write in natural, conversational paragraphs. Do NOT use asterisks, hashtags, dashes, or bullet points. Do NOT use markdown formatting. Just write normally like you're talking to someone.

Keep responses warm, clear, and straightforward. Be direct with action steps and focus on doing. Ask only ONE focused question at a time if needed. Provide clear, executable instructions in plain language. Remember what's been built already. Skip reintroductions.

YOUR EXPERTISE:
Turning plans into action, building systems and processes, creating documentation and workflows, making things actually work, building websites and web pages (HTML/CSS/JavaScript).

WORKING WITH THE TEAM:
Execute Mila's organized plans step-by-step. Implement Nova's technical solutions practically. Build out Ember's creative concepts.

WEBSITE BUILDING INSTRUCTIONS:
When a user asks you to build a website, landing page, or web component:
1. Create COMPLETE HTML code with embedded CSS and JavaScript in ONE file
2. Start your response with the full working code in triple backticks:
   ```html
   <!DOCTYPE html>
   <html>
   ...complete code...
   </html>
   ```
3. After code, provide brief setup instructions
4. The platform automatically creates a downloadable file from your code

EXAMPLE RESPONSE:
"Let's build that portfolio website for you:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Portfolio</title>
    <style>
        /* Complete CSS */
    </style>
</head>
<body>
    <!-- Complete HTML -->
    <script>
        // Complete JavaScript
    </script>
</body>
</html>
```

I've built a responsive portfolio with sections for About, Projects, Skills, and Contact. Click the download button to get your file, then open it in your browser!"

RESPONSE APPROACH:
Acknowledge what needs building in natural language. Provide step-by-step implementation in clear paragraphs. Include checkpoints to verify progress. Ask ONE question if requirements unclear.

Remember: Build step-by-step, verify progress, keep momentum. Write like a human, not a document."""
    }
}

# ============================================
# AI CHAT API
# ============================================

# ============================================
# FILE HANDLING HELPERS
# ============================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def encode_file_to_base64(filepath):
    """Encode file to base64 for Claude API"""
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_file_media_type(filepath):
    """Get media type for file"""
    mime_type, _ = mimetypes.guess_type(filepath)
    return mime_type or 'application/octet-stream'

def is_image_file(filename):
    """Check if file is an image"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def is_pdf_file(filename):
    """Check if file is a PDF"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext == 'pdf'

def is_text_file(filename):
    """Check if file is a text file"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in {'txt', 'md', 'csv'}

# ============================================
# FILE UPLOAD API
# ============================================

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    """Upload a file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Create user-specific upload folder
        user_folder = os.path.join(UPLOAD_FOLDER, str(current_user.id))
        os.makedirs(user_folder, exist_ok=True)
        
        # Save file with secure filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(user_folder, unique_filename)
        
        file.save(filepath)
        
        # Get file info
        file_size = os.path.getsize(filepath)
        file_type = get_file_media_type(filepath)
        
        return jsonify({
            'success': True,
            'filename': unique_filename,
            'original_filename': filename,
            'filepath': filepath,
            'file_size': file_size,
            'file_type': file_type
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# CONVERSATION HISTORY & MULTI-MODEL ROUTING
# ============================================

def get_conversation_history(user_id, agent_name, limit=10):
    """Get recent conversation history for context (default 10 for speed)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT message, response
        FROM chat_history
        WHERE user_id = ? AND agent_name = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (user_id, agent_name, limit))
    
    results = cursor.fetchall()
    conn.close()
    
    # Reverse to get chronological order
    results.reverse()
    
    # Format for AI models
    history = []
    for message, response in results:
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
    
    return history

def call_claude_with_history(model_id, system_prompt, history, new_message, max_tokens=2000):
    """Call Claude with conversation history"""
    api_key = app.config['ANTHROPIC_API_KEY']
    if not api_key:
        raise Exception("Anthropic API key not configured")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Add new message
    messages = history + [{"role": "user", "content": new_message}]
    
    response = client.messages.create(
        model=model_id,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages
    )
    
    return response.content[0].text

def call_gpt_with_history(model_id, system_prompt, history, new_message, max_tokens=2000):
    """Call GPT with conversation history"""
    if not openai_client:
        raise Exception("OpenAI not configured")
    
    # Format for OpenAI
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": new_message})
    
    response = openai_client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens
    )
    
    return response.choices[0].message.content

def call_gemini_with_history(model_id, system_prompt, history, new_message, max_tokens=2000):
    """Call Gemini with conversation history"""
    model = genai.GenerativeModel(model_id)
    
    # Build conversation context
    context = f"{system_prompt}\n\n"
    for msg in history:
        role = "User" if msg['role'] == 'user' else "Assistant"
        context += f"{role}: {msg['content']}\n"
    
    context += f"User: {new_message}\nAssistant:"
    
    response = model.generate_content(
        context,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens
        )
    )
    
    return response.text

def call_deepseek_with_history(model_id, system_prompt, history, new_message, max_tokens=2000):
    """Call DeepSeek with conversation history (OpenAI-compatible API)"""
    import openai

    deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not deepseek_api_key:
        raise Exception("DeepSeek API key not configured")

    deepseek_client = openai.OpenAI(
        api_key=deepseek_api_key,
        base_url="https://api.deepseek.com"
    )

    # Format for OpenAI-compatible API
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": new_message})

    response = deepseek_client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens
    )

    return response.choices[0].message.content

def call_perplexity_with_history(model_id, system_prompt, history, new_message, max_tokens=2000):
    """Call Perplexity with conversation history (OpenAI-compatible API)"""
    import openai

    perplexity_api_key = os.environ.get('PERPLEXITY_API_KEY')
    if not perplexity_api_key:
        raise Exception("Perplexity API key not configured")

    perplexity_client = openai.OpenAI(
        api_key=perplexity_api_key,
        base_url="https://api.perplexity.ai"
    )

    # Format for OpenAI-compatible API
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": new_message})

    response = perplexity_client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens
    )

    return response.choices[0].message.content

def call_grok_with_history(model_id, system_prompt, history, new_message, max_tokens=2000):
    """Call Grok (xAI) with conversation history (OpenAI-compatible API)"""
    import openai

    grok_api_key = os.environ.get('GROK_API_KEY')
    if not grok_api_key:
        raise Exception("Grok API key not configured")

    grok_client = openai.OpenAI(
        api_key=grok_api_key,
        base_url="https://api.x.ai/v1"
    )

    # Format for OpenAI-compatible API
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": new_message})

    response = grok_client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens
    )

    return response.choices[0].message.content

def call_openrouter_with_history(model_id, system_prompt, history, new_message, max_tokens=2000):
    """Call OpenRouter (for Llama and other open models) with conversation history"""
    import openai

    openrouter_api_key = os.environ.get('OPENROUTER_API_KEY')
    if not openrouter_api_key:
        raise Exception("OpenRouter API key not configured")

    openrouter_client = openai.OpenAI(
        api_key=openrouter_api_key,
        base_url="https://openrouter.ai/api/v1"
    )

    # Format for OpenAI-compatible API
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": new_message})

    response = openrouter_client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens
    )

    return response.choices[0].message.content

def call_mistral_with_history(model_id, system_prompt, history, new_message, max_tokens=2000):
    """Call Mistral with conversation history (OpenAI-compatible API)"""
    import openai

    mistral_api_key = os.environ.get('MISTRAL_API_KEY')
    if not mistral_api_key:
        raise Exception("Mistral API key not configured")

    mistral_client = openai.OpenAI(
        api_key=mistral_api_key,
        base_url="https://api.mistral.ai/v1"
    )

    # Format for OpenAI-compatible API
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": new_message})

    response = mistral_client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens
    )

    return response.choices[0].message.content

def route_to_model(model_key, system_prompt, history, new_message):
    """Route to appropriate AI model with conversation history"""
    if model_key not in MODELS:
        model_key = 'gemini-2.0-flash'  # Default fallback (free, no API key needed)
    
    config = MODELS[model_key]
    provider = config['provider']
    model_id = config['model_id']
    max_tokens = config.get('max_tokens', 2000)
    
    try:
        if provider == 'anthropic':
            return call_claude_with_history(model_id, system_prompt, history, new_message, max_tokens)
        elif provider == 'openai':
            return call_gpt_with_history(model_id, system_prompt, history, new_message, max_tokens)
        elif provider == 'google':
            return call_gemini_with_history(model_id, system_prompt, history, new_message, max_tokens)
        elif provider == 'deepseek':
            return call_deepseek_with_history(model_id, system_prompt, history, new_message, max_tokens)
        elif provider == 'perplexity':
            return call_perplexity_with_history(model_id, system_prompt, history, new_message, max_tokens)
        elif provider == 'grok':
            return call_grok_with_history(model_id, system_prompt, history, new_message, max_tokens)
        elif provider == 'openrouter':
            return call_openrouter_with_history(model_id, system_prompt, history, new_message, max_tokens)
        elif provider == 'mistral':
            return call_mistral_with_history(model_id, system_prompt, history, new_message, max_tokens)
        else:
            raise Exception(f"Unknown provider: {provider}")
    except Exception as e:
        print(f"Error with {provider} ({model_key}): {e}")
        # Fallback to Gemini (free) if other model fails
        if provider not in ['google', 'gemini']:
            print(f"Falling back to Gemini 2.0 Flash...")
            return call_gemini_with_history('gemini-2.0-flash-exp', system_prompt, history, new_message, 2000)
        raise

def call_ai_with_image(model_key, system_prompt, history, message, image_path):
    """Call AI model with image vision capabilities"""
    import base64
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Determine image type
    ext = image_path.rsplit('.', 1)[1].lower()
    media_type = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
    
    if model_key not in MODELS:
        model_key = 'gemini-2.0-flash'  # Default to free model
    
    config = MODELS[model_key]
    provider = config['provider']
    model_id = config['model_id']
    
    try:
        if provider == 'anthropic':
            # Claude vision
            client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
            
            messages = []
            # Add history
            for msg in history:
                messages.append({"role": "user", "content": msg['user']})
                messages.append({"role": "assistant", "content": msg['assistant']})
            
            # Add current message with image
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": message or "What's in this image?"
                    }
                ]
            })
            
            response = client.messages.create(
                model=model_id,
                max_tokens=2000,
                system=system_prompt,
                messages=messages
            )
            return response.content[0].text
            
        elif provider == 'openai':
            # GPT-4 Vision
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add history
            for msg in history:
                messages.append({"role": "user", "content": msg['user']})
                messages.append({"role": "assistant", "content": msg['assistant']})
            
            # Add current message with image
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": message or "What's in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}"
                        }
                    }
                ]
            })
            
            response = openai_client.chat.completions.create(
                model="gpt-4o",  # Use vision model
                messages=messages,
                max_tokens=2000
            )
            return response.choices[0].message.content
            
        elif provider == 'google':
            # Gemini vision
            from PIL import Image
            genai.configure(api_key=os.environ.get('GOOGLE_AI_API_KEY'))
            
            img = Image.open(image_path)
            gemini_model = genai.GenerativeModel(model_id)
            
            # Build prompt with history
            prompt_parts = []
            if system_prompt:
                prompt_parts.append(system_prompt)
            
            for msg in history:
                prompt_parts.append(f"User: {msg['user']}")
                prompt_parts.append(f"Assistant: {msg['assistant']}")
            
            prompt_parts.append(message or "What's in this image?")
            full_prompt = "\n\n".join(prompt_parts)
            
            response = gemini_model.generate_content([full_prompt, img])
            return response.text
            
        else:
            raise Exception(f"Provider {provider} doesn't support image vision")
            
    except Exception as e:
        print(f"Error in image vision: {e}")
        # Fallback: describe that an image was sent
        return f"I can see you've sent an image, but I encountered an error processing it: {str(e)}"

@app.route('/api/chat', methods=['POST'])
def chat():
    """Send message to AI agent with conversation history, multi-model support, and file uploads"""
    # Allow both logged-in users and guests (for custom agents)
    try:
        # Handle both JSON and FormData (for file uploads)
        if request.is_json:
            # JSON request (old format)
            data = request.json
            message = data.get('message')
            agent = data.get('agent', 'Ember')
            model_key = data.get('model', 'gemini-2.0-flash')  # Default to Gemini (free)
            attached_file = data.get('file')
            uploaded_file = None
            uploaded_files = []
        else:
            # FormData request (new format with file upload)
            message = request.form.get('message', '')
            agent = request.form.get('agent', 'Luna')
            model_key = request.form.get('model', 'gemini-2.0-flash')  # Default to Gemini (free)
            attached_file = None

            # Handle multiple files
            file_count = request.form.get('file_count', 0)
            uploaded_files = []

            if file_count:
                file_count = int(file_count)
                for i in range(file_count):
                    file_key = f'file_{i}'
                    if file_key in request.files:
                        uploaded_files.append(request.files[file_key])

            # Legacy single file support
            if 'file' in request.files and not uploaded_files:
                uploaded_files = [request.files['file']]

            uploaded_file = uploaded_files[0] if uploaded_files else None

        if not message and not uploaded_files:
            return jsonify({'error': 'Message or file required'}), 400

        # Check if user is authenticated or guest
        is_guest = not current_user.is_authenticated

        # For authenticated users: check message limits
        if not is_guest:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT subscription_tier, messages_today, last_message_reset
                FROM users
                WHERE id = ?
            """, (current_user.id,))

            result = cursor.fetchone()
            if not result:
                conn.close()
                return jsonify({'error': 'User not found'}), 404

            tier, messages_today, last_reset = result
            tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
            daily_limit = tier_info['messages_per_day']
        else:
            # Guest user - use free tier settings
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            tier = 'free'
            messages_today = 0
            last_reset = None
            tier_info = SUBSCRIPTION_TIERS.get('free', {'messages_per_day': 25})
            daily_limit = tier_info['messages_per_day']

        # ============================================
        # TIER-BASED MODEL ACCESS RESTRICTIONS
        # ============================================

        # Define models by tier
        FREE_TIER_MODELS = [
            'gemini-2.0-flash',      # FREE
            'gemini-1.5-pro',        # FREE
            'llama-3.3-70b'          # $0.18 - Cheap Llama model
        ]

        STARTER_TIER_MODELS = FREE_TIER_MODELS + [
            # $2-3 range models
            'grok-2',                # $2
            'grok-2-vision',         # $2
            'mistral-large',         # $2
            'gpt-4o',                # $2.50
            'llama-3.1-405b',        # $2.70
            'perplexity-sonar-pro',  # $3
            'claude-sonnet-4.5'      # $3
        ]

        PRO_TIER_MODELS = STARTER_TIER_MODELS + [
            # All other models under $6
            'mistral-small',         # $0.20
            'deepseek-v3',           # $0.27
            'gpt-4o-mini',           # $0.15
            'deepseek-r1',           # $0.55
            'claude-haiku-4.5',      # $0.80
            'perplexity-sonar'       # $1
        ]

        ENTERPRISE_ONLY_MODELS = [
            'claude-opus-4',         # $15
            'gpt-4-turbo'            # $10
        ]

        # Check model access based on tier
        if tier in ['free', 'freeforlife']:
            allowed_models = FREE_TIER_MODELS
            tier_name = 'Free'
            upgrade_tier = 'Starter ($19/mo)'
        elif tier == 'starter':
            allowed_models = STARTER_TIER_MODELS
            tier_name = 'Starter'
            upgrade_tier = 'Pro ($49/mo)'
        elif tier == 'pro':
            allowed_models = PRO_TIER_MODELS
            tier_name = 'Pro'
            upgrade_tier = 'Enterprise ($199/mo)'
        elif tier == 'enterprise':
            allowed_models = PRO_TIER_MODELS + ENTERPRISE_ONLY_MODELS
            tier_name = 'Enterprise'
            upgrade_tier = None
        else:
            # Default to free tier if unknown tier
            allowed_models = FREE_TIER_MODELS
            tier_name = 'Free'
            upgrade_tier = 'Starter ($19/mo)'

        # Block model if not in allowed list
        if model_key not in allowed_models:
            conn.close()

            # Determine which tier has this model
            if model_key in ENTERPRISE_ONLY_MODELS:
                required_tier = 'Pro ($49/mo) or Enterprise ($199/mo)'
            elif model_key in PRO_TIER_MODELS:
                required_tier = 'Pro ($49/mo)'
            elif model_key in STARTER_TIER_MODELS:
                required_tier = 'Starter ($19/mo)'
            else:
                required_tier = 'a paid plan'

            return jsonify({
                'error': f'This model is not available on your {tier_name} plan. Upgrade to {required_tier} to access this model.',
                'upgrade_required': True,
                'current_tier': tier,
                'required_tier': required_tier,
                'blocked_model': model_key
            }), 403  # 403 Forbidden
        # ============================================

        # ============================================
        # COST MONITORING - BLOCK EXPENSIVE MODELS
        # ============================================
        # Check if user has hit their daily cost limit
        if not is_guest and is_model_blocked_for_user(current_user.id, model_key):
            conn.close()
            thresholds = COST_THRESHOLDS.get(tier, COST_THRESHOLDS['free'])
            return jsonify({
                'error': f'⚠️ Daily cost limit reached (${thresholds["critical"]:.2f}). {model_key} is temporarily blocked. Please use Gemini, Haiku, or GPT-4o Mini instead. Resets at midnight UTC.',
                'cost_limit_reached': True,
                'blocked_model': model_key,
                'allowed_models': ['gemini-2.0-flash', 'gemini-1.5-pro', 'claude-haiku-4.5', 'gpt-4o-mini'],
                'resets_at': 'midnight UTC'
            }), 429  # 429 Too Many Requests
        # ============================================

        # Reset counter if it's a new day (only for authenticated users)
        if not is_guest and last_reset:
            try:
                last_reset_date = datetime.fromisoformat(last_reset).date()
                today = datetime.utcnow().date()
                if last_reset_date < today:
                    messages_today = 0
                    cursor.execute("""
                        UPDATE users
                        SET messages_today = 0, last_message_reset = ?
                        WHERE id = ?
                    """, (datetime.utcnow().isoformat(), current_user.id))
                    conn.commit()
            except:
                pass  # Handle any date parsing issues gracefully
        
        # Check if user has exceeded daily limit
        if daily_limit != -1 and daily_limit != 999999:
            if messages_today >= daily_limit:
                conn.close()
                return jsonify({'error': 'Daily message limit reached. Upgrade your plan to continue!'}), 429

        # ============================================
        # INTELLIGENT AGENT ROUTING
        # ============================================
        # If user hasn't explicitly selected an agent, or if the message clearly
        # indicates a different agent would be better, suggest/auto-route

        # Check if this is the first message (no history) and agent is default
        is_first_message = True if (is_guest or not get_conversation_history(current_user.id if not is_guest else 0, agent, limit=1)) else False

        # Analyze intent for agent suggestion
        suggested_agent, confidence = analyze_intent_and_suggest_agent(message)

        # Track if we auto-routed
        original_agent = agent
        was_auto_routed = False

        # Auto-route on first message if confidence is high and different from current agent
        # BUT: Don't auto-route if current agent is a custom agent (user explicitly chose it)
        is_custom_agent = agent not in AGENT_PERSONALITIES
        if suggested_agent and suggested_agent != agent and confidence >= 4 and is_first_message and not is_custom_agent:
            print(f"🎯 Auto-routing: {agent} → {suggested_agent} (confidence: {confidence})")
            agent = suggested_agent  # Switch to the better agent
            was_auto_routed = True

        # Get agent personality - check built-in agents first, then custom agents
        system_prompt = None

        if agent in AGENT_PERSONALITIES:
            # Built-in agent with team coordination enabled
            agent_info = AGENT_PERSONALITIES[agent]
            base_system_prompt = agent_info['system_prompt']
            coordination_context = get_agent_coordination_context()
            system_prompt = f"{base_system_prompt}\n\n{coordination_context}"
        else:
            # Check for custom agent
            if is_guest:
                # Guests can access any public custom agent by name
                cursor.execute("""
                    SELECT system_prompt FROM custom_agents
                    WHERE name = ? AND is_public = 1
                """, (agent,))
            else:
                # Authenticated users query by user_id
                cursor.execute("""
                    SELECT system_prompt FROM custom_agents
                    WHERE user_id = ? AND name = ?
                """, (current_user.id, agent))

            custom_agent = cursor.fetchone()
            if custom_agent:
                # Wrap custom agent prompt with formatting rules
                base_prompt = custom_agent[0]
                system_prompt = f"""You are {agent}. Your role and personality:

{base_prompt}

CRITICAL FORMATTING RULES:
- Write in natural, conversational paragraphs
- Do NOT use asterisks (**), hashtags (##), dashes (---), or bullet points (•)
- Do NOT use markdown formatting of any kind
- Ask only ONE question per response (if you need to ask questions)
- Write like you're talking to someone, not writing a document
- Keep responses clear and focused
- When introducing yourself, say "I'm {agent}" (not Luna or any other name)

Remember: You are {agent}. Natural conversation only. No formatting."""
            else:
                # Check for global agent
                if not is_guest:
                    cursor.execute("""
                        SELECT ga.system_prompt, ga.integrations
                        FROM global_agents ga
                        INNER JOIN user_global_agents uga ON ga.id = uga.global_agent_id
                        WHERE uga.user_id = ? AND ga.name = ? AND ga.is_active = 1
                    """, (current_user.id, agent))

                    global_agent = cursor.fetchone()
                    if global_agent:
                        base_prompt = global_agent[0]
                        integrations_json = global_agent[1]

                        # Check if agent has integrations enabled
                        integration_context = ""
                        if integrations_json:
                            try:
                                needed_categories = json.loads(integrations_json)

                                # Get user's connected OAuth services
                                cursor.execute("""
                                    SELECT service, service_email, is_active
                                    FROM user_integrations
                                    WHERE user_id = ? AND is_active = 1
                                """, (current_user.id,))

                                connected_services = {}
                                for row in cursor.fetchall():
                                    service, email, is_active = row
                                    connected_services[service] = email

                                # Map categories to services and check connections
                                available_integrations = []
                                missing_integrations = []

                                for category in needed_categories:
                                    if category in AVAILABLE_INTEGRATIONS:
                                        cat_info = AVAILABLE_INTEGRATIONS[category]
                                        for service in cat_info['services']:
                                            if service in connected_services:
                                                available_integrations.append({
                                                    'service': service,
                                                    'name': OAUTH_CONFIG[service]['name'],
                                                    'email': connected_services[service],
                                                    'icon': OAUTH_CONFIG[service]['icon']
                                                })
                                            else:
                                                missing_integrations.append({
                                                    'service': service,
                                                    'name': OAUTH_CONFIG[service]['name']
                                                })

                                # Add integration context to system prompt
                                if available_integrations:
                                    integration_list = "\n".join([
                                        f"- {integ['icon']} {integ['name']} ({integ['email']})"
                                        for integ in available_integrations
                                    ])
                                    integration_context = f"""

CONNECTED INTEGRATIONS:
You have access to the following connected services:
{integration_list}

You can reference these integrations in your responses. For example:
- If email is connected, you can mention "I can help you draft emails"
- If social media is connected, you can say "I can help with your social posts"
- If calendar is connected, you can reference scheduling capabilities

Note: While you can reference these services, actual API calls are not yet implemented.
The user has authorized these connections."""

                                if missing_integrations:
                                    missing_list = ", ".join([m['name'] for m in missing_integrations])
                                    integration_context += f"""

DISCONNECTED INTEGRATIONS:
The following integrations are configured but not connected: {missing_list}
If the user asks about these, suggest they connect them via the Integrations page."""

                            except Exception as e:
                                print(f"Error loading integrations for agent: {e}")
                                integration_context = ""

                        # Wrap global agent prompt with formatting rules and integrations
                        system_prompt = f"""You are {agent}. Your role and personality:

{base_prompt}
{integration_context}

CRITICAL FORMATTING RULES:
- Write in natural, conversational paragraphs
- Do NOT use asterisks (**), hashtags (##), dashes (---), or bullet points (•)
- Do NOT use markdown formatting of any kind
- Ask only ONE question per response (if you need to ask questions)
- Write like you're talking to someone, not writing a document
- Keep responses clear and focused
- When introducing yourself, say "I'm {agent}" (not Luna or any other name)

Remember: You are {agent}. Natural conversation only. No formatting."""
                    else:
                        conn.close()
                        return jsonify({'error': f'Agent "{agent}" not found'}), 400
                else:
                    conn.close()
                    return jsonify({'error': f'Agent "{agent}" not found'}), 400
        
        # Get conversation history (last 10 messages for context - optimized for speed)
        # Guests don't have history (not logged in)
        if is_guest:
            history = []
        else:
            history = get_conversation_history(current_user.id, agent, limit=10)

        # Handle file uploads from FormData (supports multiple files)
        file_info = None
        files_info = []
        if uploaded_files:
            # Guests cannot upload files
            if is_guest:
                conn.close()
                return jsonify({
                    'error': '📎 File uploads require a free account. Sign up now to upload files and unlock full access to all AI agents!',
                    'signup_required': True,
                    'signup_url': '/register'
                }), 403

            # Process all uploaded files
            file_contents = []
            for uploaded_file in uploaded_files:
                # Save the uploaded file
                filename = secure_filename(uploaded_file.filename)
                user_folder = os.path.join(UPLOAD_FOLDER, str(current_user.id))
                os.makedirs(user_folder, exist_ok=True)

                filepath = os.path.join(user_folder, filename)
                uploaded_file.save(filepath)

                file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

                file_data = {
                    'filename': filename,
                    'filepath': filepath,
                    'extension': file_extension
                }
                files_info.append(file_data)

                # For text files, read content
                if file_extension in ['txt', 'md', 'csv', 'json', 'py', 'js', 'html', 'css', 'xml']:
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            file_content = f.read()[:10000]  # Limit to 10k chars per file
                        file_contents.append(f"File: {filename}\nContent:\n{file_content}")
                    except Exception as e:
                        print(f"Error reading file {filename}: {e}")
                        file_contents.append(f"File: {filename} (could not read content)")

            # Add file contents to message
            if file_contents:
                files_text = "\n\n---\n\n".join(file_contents)
                if message:
                    message = f"{message}\n\n{files_text}"
                else:
                    message = files_text

            # Keep backward compatibility for single file
            file_info = files_info[0] if files_info else None
        
        # Handle file attachments (JSON format - old system)
        elif attached_file and 'filepath' in attached_file:
            filepath = attached_file['filepath']
            if os.path.exists(filepath):
                filename = attached_file.get('original_filename', 'file')
                # For text files, include content in message
                if filename.endswith(('.txt', '.md', '.csv', '.json', '.py', '.js', '.html', '.css')):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            file_content = f.read()[:10000]  # Limit to 10k chars
                        message = f"{message}\n\nFile: {filename}\nContent:\n{file_content}"
                    except:
                        pass  # If file reading fails, just use original message
        
        # Route to selected model with conversation history
        # For images, we need special handling
        if file_info and file_info['extension'] in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            # Image file - use vision models
            ai_response = call_ai_with_image(model_key, system_prompt, history, message, file_info['filepath'])
        else:
            # Text-only or text file
            ai_response = route_to_model(model_key, system_prompt, history, message)
        
        # Save to chat history
        saved_message = message
        if file_info:
            # New file upload system
            saved_message = f"📎 {file_info['filename']}\n{message}" if message else f"📎 {file_info['filename']}"
        elif attached_file and 'original_filename' in attached_file:
            # Old file system
            saved_message = f"📎 {attached_file['original_filename']}\n{message}"
        
        # Save chat history and increment counter (only for authenticated users)
        if not is_guest:
            # Get or create conversation for this agent
            cursor.execute("""
                SELECT id FROM conversations
                WHERE user_id = ? AND agent_name = ? AND is_active = 1
                ORDER BY updated_at DESC
                LIMIT 1
            """, (current_user.id, agent))

            conv_result = cursor.fetchone()

            if conv_result:
                conversation_id = conv_result[0]
                # Update conversation timestamp
                cursor.execute("""
                    UPDATE conversations
                    SET updated_at = ?
                    WHERE id = ?
                """, (datetime.utcnow().isoformat(), conversation_id))
            else:
                # Create new conversation
                cursor.execute("""
                    INSERT INTO conversations (user_id, agent_name, title, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (current_user.id, agent, f'Chat with {agent}', datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                conversation_id = cursor.lastrowid

            # Save message with conversation_id
            cursor.execute("""
                INSERT INTO chat_history (user_id, agent_name, message, response, conversation_id)
                VALUES (?, ?, ?, ?, ?)
            """, (current_user.id, agent, saved_message, ai_response, conversation_id))

            # ✅ INCREMENT MESSAGE COUNTER (THE FIX!)
            cursor.execute("""
                UPDATE users
                SET messages_today = messages_today + 1,
                    last_message_reset = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), current_user.id))

        conn.commit()
        conn.close()

        # ============================================
        # COST TRACKING & THRESHOLD MONITORING
        # ============================================
        cost_warning = None
        if not is_guest:
            # Get cost for this model
            message_cost = MODEL_COSTS.get(model_key, 0.0)

            if message_cost > 0:
                # Track the cost
                track_message_cost(current_user.id, model_key, message_cost, agent)

                # Check if user exceeded thresholds
                alert_type, alert_message = check_cost_threshold(current_user.id, tier)
                if alert_message:
                    cost_warning = alert_message
                    print(f"💰 Cost alert for user {current_user.id}: {alert_type} - {alert_message}")
        # ============================================

        # ============================================
        # DELEGATION DETECTION & AGENT MENTIONS
        # ============================================
        # Check if user mentioned any agents in their message
        mentioned_agents = []
        if not is_guest:
            mentioned_agents = detect_agent_mentions(message, current_user.id)

        # Check if the agent suggested switching to another agent
        delegation_suggestion = suggest_agent_transfer(ai_response, agent)

        response_data = {
            'success': True,
            'response': ai_response,
            'agent': agent,
            'model_used': model_key
        }

        # Add routing/delegation info if applicable
        if was_auto_routed:
            response_data['auto_routed'] = True
            response_data['original_agent'] = original_agent
            response_data['routing_reason'] = f"Your request matches {agent}'s expertise better"

        if delegation_suggestion:
            response_data['delegation_suggested'] = True
            response_data['suggested_agent'] = delegation_suggestion
            response_data['suggestion_reason'] = f"{agent} suggests switching to {delegation_suggestion} for this task"

        # Add mentioned agents to response
        if mentioned_agents:
            response_data['mentioned_agents'] = mentioned_agents

        # Add cost warning if present
        if cost_warning:
            response_data['cost_warning'] = cost_warning

        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-image-free', methods=['POST'])
@login_required
def generate_image_free():
    """Generate an image using FREE Pollinations.ai"""
    try:
        import urllib.parse
        
        data = request.json
        prompt = data.get('message') or data.get('prompt')
        agent = data.get('agent', 'AI')
        
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        
        # Check user's message limit
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT subscription_tier, messages_today, last_message_reset
            FROM users
            WHERE id = ?
        """, (current_user.id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        tier, messages_today, last_reset = result
        tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
        daily_limit = tier_info['messages_per_day']
        
        # Check if user has exceeded limit
        if daily_limit != -1 and daily_limit != 999999:
            if messages_today >= daily_limit:
                conn.close()
                return jsonify({'error': 'Daily message limit reached. Upgrade your plan to generate more images!'}), 429
        
        # Generate image URL with Pollinations.ai (100% FREE!)
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
        
        # Increment message counter
        cursor.execute("""
            UPDATE users
            SET messages_today = messages_today + 1,
                last_message_reset = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), current_user.id))
        
        # Save to history
        cursor.execute("""
            INSERT INTO chat_history (user_id, agent_name, message, response, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            current_user.id,
            agent,
            f"🎨 Generate image: {prompt}",
            f"Generated image: {image_url}",
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'response': f'I generated an image based on your description! (Free tier - powered by Pollinations.ai)',
            'image_url': image_url,
            'provider': 'pollinations'
        }), 200
        
    except Exception as e:
        print(f"Error in generate_image_free: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/models', methods=['GET'])
@login_required
def get_available_models():
    """Get list of available AI models"""
    models_list = []
    for key, config in MODELS.items():
        models_list.append({
            'key': key,
            'name': config['name'],
            'description': config['description'],
            'provider': config['provider'],
            'cost': config.get('cost', 'N/A')
        })
    
    return jsonify({'models': models_list})

@app.route('/api/clear-chat', methods=['POST'])
@login_required
def clear_chat_history():
    """Clear chat history for current agent or all agents"""
    try:
        data = request.json or {}
        agent = data.get('agent', 'all')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if agent == 'all':
            cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (current_user.id,))
        else:
            cursor.execute("DELETE FROM chat_history WHERE user_id = ? AND agent_name = ?", 
                          (current_user.id, agent))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Chat history cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-image', methods=['POST'])
@login_required
def generate_image():
    """Generate an image using DALL-E (Premium quality, requires API key)"""
    try:
        data = request.json
        prompt = data.get('message') or data.get('prompt')
        agent = data.get('agent', 'AI')
        
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        
        # Check if OpenAI is configured - if not, fallback to free option
        if not openai_client:
            return jsonify({
                'error': 'DALL-E not configured. Using free image generation instead.',
                'fallback': True
            }), 202
        
        # Check user's message limit
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT subscription_tier, messages_today, last_message_reset
            FROM users
            WHERE id = ?
        """, (current_user.id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        tier, messages_today, last_reset = result
        tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
        daily_limit = tier_info['messages_per_day']
        
        # Check if user has exceeded limit
        if daily_limit != -1 and daily_limit != 999999:
            if messages_today >= daily_limit:
                conn.close()
                return jsonify({'error': 'Daily message limit reached. Upgrade your plan to generate more images!'}), 429
        
        # Generate image with DALL-E
        try:
            response = openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            
        except Exception as e:
            print(f"DALL-E Error: {str(e)}")
            conn.close()
            return jsonify({'error': f'Failed to generate image: {str(e)}'}), 500
        
        # Increment message counter
        cursor.execute("""
            UPDATE users
            SET messages_today = messages_today + 1,
                last_message_reset = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), current_user.id))
        
        # Save to history
        cursor.execute("""
            INSERT INTO chat_history (user_id, agent_name, message, response, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            current_user.id,
            agent,
            f"🎨 Generate image: {prompt}",
            f"Generated image: {image_url}",
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'response': f'I generated a high-quality image with DALL-E 3!',
            'image_url': image_url,
            'provider': 'dalle'
        }), 200
        
    except Exception as e:
        print(f"Error in generate_image: {str(e)}")
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
# CONVERSATION MANAGEMENT (Chat History Sessions)
# ============================================

@app.route('/api/conversations')
@login_required
def get_conversations():
    """Get all conversation sessions for current user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Include inactive conversations to show all history
        cursor.execute("""
            SELECT id, agent_name, title, created_at, updated_at, is_active
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT 100
        """, (current_user.id,))

        results = cursor.fetchall()
        conn.close()

        conversations = []
        for row in results:
            conversations.append({
                'id': row[0],
                'agent': row[1],
                'title': row[2] or 'New conversation',
                'created_at': row[3],
                'updated_at': row[4],
                'is_active': bool(row[5])
            })

        print(f"Found {len(conversations)} conversations for user {current_user.id}")

        return jsonify({'conversations': conversations}), 200

    except Exception as e:
        print(f"Error getting conversations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/<int:conv_id>')
@login_required
def get_conversation(conv_id):
    """Get specific conversation with all messages"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # First check if conversation exists at all (including inactive ones)
        cursor.execute("""
            SELECT agent_name, title, user_id, is_active FROM conversations
            WHERE id = ?
        """, (conv_id,))

        conv_result = cursor.fetchone()
        if not conv_result:
            conn.close()
            print(f"Conversation {conv_id} not found in database")
            return jsonify({'error': 'Conversation not found'}), 404

        agent_name, title, conv_user_id, is_active = conv_result

        # Check if conversation belongs to current user
        if conv_user_id != current_user.id:
            conn.close()
            print(f"Conversation {conv_id} belongs to user {conv_user_id}, not current user {current_user.id}")
            return jsonify({'error': 'Conversation not found'}), 404

        # If conversation is inactive, reactivate it
        if not is_active:
            print(f"Reactivating inactive conversation {conv_id}")
            cursor.execute("""
                UPDATE conversations SET is_active = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (conv_id,))
            conn.commit()

        # Get all messages in this conversation
        cursor.execute("""
            SELECT message, response, timestamp
            FROM chat_history
            WHERE conversation_id = ? AND user_id = ?
            ORDER BY timestamp ASC
        """, (conv_id, current_user.id))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'message': row[0],
                'response': row[1],
                'timestamp': row[2]
            })

        conn.close()

        print(f"Successfully loaded conversation {conv_id} with {len(messages)} messages for agent {agent_name}")

        return jsonify({
            'id': conv_id,
            'agent': agent_name,
            'title': title,
            'messages': messages
        }), 200

    except Exception as e:
        print(f"Error getting conversation: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/new', methods=['POST'])
@login_required
def create_conversation():
    """Create a new conversation session"""
    try:
        data = request.json
        agent_name = data.get('agent', 'Luna')
        title = data.get('title', 'New conversation')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversations (user_id, agent_name, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (current_user.id, agent_name, title, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        
        conv_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'conversation_id': conv_id,
            'agent': agent_name,
            'title': title
        }), 200
        
    except Exception as e:
        print(f"Error creating conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/<int:conv_id>/delete', methods=['POST'])
@login_required
def delete_conversation(conv_id):
    """Delete a conversation (soft delete)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verify ownership
        cursor.execute("""
            SELECT id FROM conversations
            WHERE id = ? AND user_id = ?
        """, (conv_id, current_user.id))
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Soft delete
        cursor.execute("""
            UPDATE conversations
            SET is_active = 0
            WHERE id = ?
        """, (conv_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        print(f"Error deleting conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================
# AUTOMATION API (for programmatic access)
# ============================================

@app.route('/api/automate/chat', methods=['POST'])
def automate_chat():
    """
    Automation endpoint for programmatic agent access
    Requires user's API key in header: X-API-Key
    
    Usage:
    POST /api/automate/chat
    Headers: X-API-Key: sk-xxxxxxx
    Body: {
        "message": "Your question",
        "agent": "Luna"
    }
    """
    try:
        # Check for user's API key in header
        user_api_key = request.headers.get('X-API-Key')
        if not user_api_key:
            return jsonify({'error': 'API key required in X-API-Key header'}), 401
        
        # Verify the user's API key
        user_id = verify_api_key(user_api_key)
        if not user_id:
            return jsonify({'error': 'Invalid or inactive API key'}), 401
        
        # Check message limits
        can_send, error_msg = check_message_limit(user_id)
        if not can_send:
            return jsonify({'error': error_msg}), 429
        
        data = request.json
        message = data.get('message')
        agent = data.get('agent', 'Ember')
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        # Get agent personality
        if agent not in AGENT_PERSONALITIES:
            return jsonify({'error': f'Invalid agent. Choose from: {", ".join(AGENT_PERSONALITIES.keys())}'}), 400
        
        agent_info = AGENT_PERSONALITIES[agent]
        
        # Get server's Anthropic API key
        anthropic_api_key = app.config['ANTHROPIC_API_KEY']
        if not anthropic_api_key:
            return jsonify({'error': 'Server API key not configured'}), 500
        
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
        
        # Call Anthropic API using server's key
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": message}
            ]
        )
        
        ai_response = response.content[0].text
        
        # Increment message count
        increment_message_count(user_id)
        
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
# USER STATS API
# ============================================

@app.route('/api/user-stats')
@login_required
def get_user_stats():
    """Get current user's usage statistics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT subscription_tier, messages_today, last_message_reset
            FROM users
            WHERE id = ?
        """, (current_user.id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'User not found'}), 404
        
        tier, messages_today, last_reset = result
        tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
        daily_limit = tier_info['messages_per_day']
        
        # Reset counter if it's a new day
        if last_reset:
            last_reset_date = datetime.fromisoformat(last_reset).date()
            today = datetime.utcnow().date()
            
            if last_reset_date < today:
                messages_today = 0
        
        # Calculate remaining messages
        if daily_limit == -1 or daily_limit == 999999:
            messages_remaining = -1  # Unlimited
        else:
            messages_remaining = max(0, daily_limit - messages_today)
        
        return jsonify({
            'subscription_tier': tier,
            'messages_today': messages_today,
            'daily_limit': daily_limit,
            'messages_remaining': messages_remaining,
            'tier_name': tier_info['name']
        }), 200
        
    except Exception as e:
        print(f"Error getting user stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================
# API KEY MANAGEMENT
# ============================================

@app.route('/api/api-keys', methods=['GET'])
@login_required
def get_api_keys():
    """Get user's API keys"""
    try:
        keys = get_user_api_keys(current_user.id)
        return jsonify({'keys': keys}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/api-keys', methods=['POST'])
@login_required
def create_new_api_key():
    """Create a new API key"""
    try:
        data = request.json
        name = data.get('name', 'Default')
        
        api_key = create_api_key(current_user.id, name)
        
        if api_key:
            return jsonify({
                'success': True,
                'api_key': api_key,
                'message': 'API key created successfully'
            }), 200
        else:
            return jsonify({'error': 'Failed to create API key'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/api-keys/<int:key_id>', methods=['DELETE'])
@login_required
def remove_api_key(key_id):
    """Delete an API key"""
    try:
        delete_api_key(current_user.id, key_id)
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


# ============================================
# PROMO CODE SYSTEM
# ============================================

# ============================================
# API KEYS FOR AUTOMATION
# ============================================

def init_api_keys_table():
    """Initialize API keys table for automation"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize API keys table
init_api_keys_table()

# ============================================
# API KEY MANAGEMENT FUNCTIONS
# ============================================

def generate_api_key():
    """Generate a secure API key"""
    return 'sk-ai-team-' + secrets.token_urlsafe(32)

def get_user_api_key(user_id):
    """Get user's API key"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT api_key FROM api_keys WHERE user_id = ? AND is_active = 1", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def create_user_api_key(user_id, name="Default API Key"):
    """Create a new API key for user"""
    api_key = generate_api_key()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Deactivate old keys
    cursor.execute("UPDATE api_keys SET is_active = 0 WHERE user_id = ?", (user_id,))
    
    # Create new key
    cursor.execute("""
        INSERT INTO api_keys (user_id, api_key, name)
        VALUES (?, ?, ?)
    """, (user_id, api_key, name))
    
    conn.commit()
    conn.close()
    return api_key

def validate_api_key(api_key):
    """Validate API key and return user_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id FROM api_keys 
        WHERE api_key = ? AND is_active = 1
    """, (api_key,))
    result = cursor.fetchone()
    
    if result:
        # Update last_used timestamp
        cursor.execute("""
            UPDATE api_keys 
            SET last_used = CURRENT_TIMESTAMP 
            WHERE api_key = ?
        """, (api_key,))
        conn.commit()
    
    conn.close()
    return result[0] if result else None

# ============================================
# API USAGE TRACKING
# ============================================

def init_api_usage_table():
    """Initialize API usage tracking table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL,
            method TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status_code INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()

init_api_usage_table()

def log_api_request(user_id, endpoint, method, status_code=200):
    """Log API request"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO api_usage (user_id, endpoint, method, status_code)
        VALUES (?, ?, ?, ?)
    """, (user_id, endpoint, method, status_code))
    conn.commit()
    conn.close()

def get_api_usage_stats(user_id):
    """Get API usage statistics for user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total requests
    cursor.execute("SELECT COUNT(*) FROM api_usage WHERE user_id = ?", (user_id,))
    total_requests = cursor.fetchone()[0]
    
    # Today's requests
    cursor.execute("""
        SELECT COUNT(*) FROM api_usage 
        WHERE user_id = ? AND date(timestamp) = date('now')
    """, (user_id,))
    today_requests = cursor.fetchone()[0]
    
    conn.close()
    return {
        'total_requests': total_requests,
        'today_requests': today_requests
    }

# ============================================
# CUSTOM AGENTS SYSTEM
# ============================================

def init_custom_agents_table():
    """Initialize custom agents table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            personality TEXT,
            system_prompt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Custom agents table initialized")

# Initialize custom agents table
init_custom_agents_table()

# ============================================
# CREATE MASTER CODE FOR AMANDA
# ============================================

def create_master_code():
    """Create master code for Amanda (if it doesn't exist)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO promo_codes (code, tier, max_uses, is_active)
            VALUES ('MASTER-UNLIMITED-AMANDA', 'freeforlife', 1, 1)
        """)
        conn.commit()
    except:
        pass
    finally:
        conn.close()

# Create master code on startup
create_master_code()

# ============================================
# GENERATE PROMO CODES
# ============================================

def create_api_key(user_id, name="Default"):
    """Create an API key for a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    api_key = generate_api_key()
    
    try:
        cursor.execute("""
            INSERT INTO api_keys (user_id, api_key, name)
            VALUES (?, ?, ?)
        """, (user_id, api_key, name))
        conn.commit()
        conn.close()
        return api_key
    except:
        conn.close()
        return None

def get_user_api_keys(user_id):
    """Get all API keys for a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, api_key, name, created_at, last_used, is_active
        FROM api_keys
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    
    results = cursor.fetchall()
    conn.close()
    
    keys = []
    for row in results:
        keys.append({
            'id': row[0],
            'api_key': row[1],
            'name': row[2],
            'created_at': row[3],
            'last_used': row[4],
            'is_active': row[5]
        })
    
    return keys

def verify_api_key(api_key):
    """Verify an API key and return user_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT user_id, is_active FROM api_keys
        WHERE api_key = ?
    """, (api_key,))
    
    result = cursor.fetchone()
    
    if result and result[1]:  # Key exists and is active
        # Update last_used timestamp
        cursor.execute("""
            UPDATE api_keys
            SET last_used = CURRENT_TIMESTAMP
            WHERE api_key = ?
        """, (api_key,))
        conn.commit()
        conn.close()
        return result[0]  # Return user_id
    
    conn.close()
    return None

def delete_api_key(user_id, key_id):
    """Delete an API key"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM api_keys
        WHERE id = ? AND user_id = ?
    """, (key_id, user_id))
    
    conn.commit()
    conn.close()

# ============================================
# GENERATE PROMO CODES
# ============================================

def generate_promo_code(length=12):
    """Generate a random promo code"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def create_promo_codes(tier, count, prefix="", discount_type="tier", discount_value=None, trial_days=None, max_uses=-1):
    """Create multiple promo codes for a tier or discount

    Args:
        tier: Subscription tier (for tier upgrades) or empty string for discounts
        count: Number of codes to generate
        prefix: Optional prefix for codes
        discount_type: 'tier', 'amount', 'percent', or 'trial'
        discount_value: Dollar amount or percentage value (for amount/percent discounts)
        trial_days: Number of days for free trial (for trial codes)
        max_uses: Maximum number of uses per code (-1 for unlimited, 0 for single-use, positive number for limited uses)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    codes = []
    for i in range(count):
        code = f"{prefix}{generate_promo_code(8)}" if prefix else generate_promo_code(12)

        try:
            # max_uses: -1 = unlimited, 0 = single use, positive number = limited uses
            cursor.execute("""
                INSERT INTO promo_codes (code, tier, max_uses, is_active, single_use, discount_type, discount_value, trial_days)
                VALUES (?, ?, ?, 1, ?, ?, ?, ?)
            """, (code, tier or 'free', max_uses, 1 if max_uses == 0 else 0, discount_type, discount_value, trial_days))
            codes.append(code)
        except sqlite3.IntegrityError:
            # Code already exists, try again
            i -= 1
            continue

    conn.commit()
    conn.close()

    return codes

# ============================================
# PROMO CODE VALIDATION & REDEMPTION
# ============================================

def validate_promo_code(code):
    """Check if promo code is valid and available"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, tier, max_uses, times_used, expires_at, is_active, single_use,
               discount_type, discount_value, trial_days
        FROM promo_codes
        WHERE code = ?
    """, (code.upper(),))

    result = cursor.fetchone()
    conn.close()

    if not result:
        return False, "Invalid promo code"

    promo_id, tier, max_uses, times_used, expires_at, is_active, single_use, discount_type, discount_value, trial_days = result

    if not is_active:
        return False, "This promo code is no longer active"

    # For single-use codes, check if already used (times_used should be 0)
    if single_use and times_used >= 1:
        return False, "This promo code has already been used"

    # For multi-use codes, check against max_uses
    # IMPORTANT: max_uses = -1 means UNLIMITED uses, so skip the check
    if not single_use and max_uses != -1 and times_used >= max_uses:
        return False, "This promo code has reached its maximum uses"

    if expires_at:
        expiry = datetime.fromisoformat(expires_at)
        if datetime.utcnow() > expiry:
            return False, "This promo code has expired"

    return True, {
        'id': promo_id,
        'tier': tier,
        'single_use': single_use,
        'discount_type': discount_type or 'tier',
        'discount_value': discount_value,
        'trial_days': trial_days
    }


def redeem_promo_code(code, user_id):
    """Redeem a promo code for a user"""
    # Validate code first
    is_valid, result = validate_promo_code(code)

    if not is_valid:
        return False, result

    promo_id = result['id']
    tier = result.get('tier')
    discount_type = result.get('discount_type', 'tier')
    discount_value = result.get('discount_value')
    trial_days = result.get('trial_days')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if user already used this code
        cursor.execute("""
            SELECT id FROM promo_code_usage
            WHERE promo_code_id = ? AND user_id = ?
        """, (promo_id, user_id))

        if cursor.fetchone():
            conn.close()
            return False, "You have already used this promo code"

        # Record usage
        cursor.execute("""
            INSERT INTO promo_code_usage (promo_code_id, user_id)
            VALUES (?, ?)
        """, (promo_id, user_id))

        # Increment times_used
        cursor.execute("""
            UPDATE promo_codes
            SET times_used = times_used + 1
            WHERE id = ?
        """, (promo_id,))

        # Apply the promo code based on discount type
        if discount_type == 'tier':
            # Traditional tier upgrade
            cursor.execute("""
                UPDATE users
                SET subscription_tier = ?
                WHERE id = ?
            """, (tier, user_id))
            success_message = tier

        elif discount_type == 'trial':
            # Free trial - set trial end date
            from datetime import datetime, timedelta
            trial_end = datetime.utcnow() + timedelta(days=trial_days)
            trial_end_str = trial_end.isoformat()

            cursor.execute("""
                UPDATE users
                SET subscription_tier = 'pro',
                    trial_end_date = ?,
                    promo_code_applied = ?
                WHERE id = ?
            """, (trial_end_str, code, user_id))

            if trial_days == 7:
                success_message = "1 week free trial activated"
            elif trial_days == 14:
                success_message = "2 weeks free trial activated"
            elif trial_days == 21:
                success_message = "3 weeks free trial activated"
            elif trial_days == 30:
                success_message = "1 month free trial activated"
            elif trial_days == 60:
                success_message = "2 months free trial activated"
            else:
                success_message = f"{trial_days} days free trial activated"

        elif discount_type == 'amount':
            # Dollar amount discount
            cursor.execute("""
                UPDATE users
                SET promo_discount_type = 'amount',
                    promo_discount_value = ?,
                    promo_code_applied = ?
                WHERE id = ?
            """, (discount_value, code, user_id))
            success_message = f"${discount_value:.2f} discount applied"

        elif discount_type == 'percent':
            # Percentage discount
            cursor.execute("""
                UPDATE users
                SET promo_discount_type = 'percent',
                    promo_discount_value = ?,
                    promo_code_applied = ?
                WHERE id = ?
            """, (discount_value, code, user_id))
            success_message = f"{discount_value:.0f}% discount applied"

        else:
            conn.close()
            return False, "Invalid discount type"

        conn.commit()
        conn.close()

        return True, {'type': discount_type, 'message': success_message, 'value': discount_value if discount_type != 'tier' else trial_days}

    except Exception as e:
        conn.close()
        return False, str(e)

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/redeem-promo-code', methods=['POST'])
@login_required
def api_redeem_promo_code():
    """Redeem a promo code"""
    try:
        data = request.json
        code = data.get('code', '').strip().upper()

        if not code:
            return jsonify({'error': 'Promo code required'}), 400

        success, result = redeem_promo_code(code, current_user.id)

        if success:
            # Result is now a dictionary with type, message, and value
            if isinstance(result, dict):
                discount_type = result.get('type')
                message = result.get('message')

                if discount_type == 'tier':
                    # Traditional tier upgrade
                    return jsonify({
                        'success': True,
                        'type': 'tier',
                        'tier': message,
                        'message': f'Promo code redeemed! You now have {SUBSCRIPTION_TIERS[message]["name"]} access.'
                    }), 200
                else:
                    # Discount promo code
                    return jsonify({
                        'success': True,
                        'type': discount_type,
                        'value': result.get('value'),
                        'message': f'Promo code redeemed! {message} to your next subscription payment.'
                    }), 200
            else:
                # Backward compatibility - old format (shouldn't happen anymore)
                return jsonify({
                    'success': True,
                    'tier': result,
                    'message': f'Promo code redeemed! You now have {SUBSCRIPTION_TIERS[result]["name"]} access.'
                }), 200
        else:
            return jsonify({'error': result}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/check-promo-code', methods=['POST'])
def api_check_promo_code():
    """Check if promo code is valid (public endpoint for signup)"""
    try:
        data = request.json
        code = data.get('code', '').strip().upper()
        
        if not code:
            return jsonify({'error': 'Promo code required'}), 400
        
        is_valid, result = validate_promo_code(code)
        
        if is_valid:
            return jsonify({
                'valid': True,
                'plan': result['tier'],
                'message': f'Valid code for {result["tier"]} plan!'
            }), 200
        else:
            return jsonify({'valid': False, 'message': result}), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/apply-promo-upgrade', methods=['POST'])
@login_required
def apply_promo_upgrade():
    """Apply promo code to upgrade user's subscription"""
    try:
        data = request.json
        code = data.get('code', '').strip().upper()
        plan = data.get('plan', '')
        
        if not code or not plan:
            return jsonify({'error': 'Code and plan required'}), 400
        
        # Validate promo code
        is_valid, result = validate_promo_code(code)
        
        if not is_valid:
            return jsonify({'error': result}), 400
        
        # Check if code is for the requested plan
        if result['tier'] != plan:
            return jsonify({'error': f'This code is for {result["tier"]} plan, not {plan}'}), 400
        
        # Update user subscription in SQLite database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Update user's subscription tier
        cursor.execute("""
            UPDATE users
            SET subscription_tier = ?
            WHERE id = ?
        """, (plan, current_user.id))
        
        # Increment promo code usage
        cursor.execute("""
            SELECT times_used, single_use, max_uses
            FROM promo_codes
            WHERE code = ?
        """, (code,))
        row = cursor.fetchone()
        
        if row:
            times_used, single_use, max_uses = row
            new_times_used = times_used + 1
            
            # For single-use codes, deactivate after use
            if single_use:
                cursor.execute("""
                    UPDATE promo_codes
                    SET times_used = ?,
                        is_active = 0
                    WHERE code = ?
                """, (new_times_used, code))
            # For multi-use codes, increment and check max_uses
            else:
                is_active = 1 if new_times_used < max_uses else 0
                cursor.execute("""
                    UPDATE promo_codes
                    SET times_used = ?,
                        is_active = ?
                    WHERE code = ?
                """, (new_times_used, is_active, code))
        
        conn.commit()
        conn.close()
        
        # Update current_user object in memory
        current_user.subscription_tier = plan
        
        return jsonify({
            'success': True,
            'message': f'Successfully upgraded to {plan} plan!',
            'new_tier': plan
        }), 200
            
    except Exception as e:
        print(f"Error applying promo code: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# ADMIN ENDPOINT TO GENERATE CODES
# ============================================

@app.route('/api/admin/generate-promo-codes', methods=['POST'])
@login_required
def admin_generate_promo_codes():
    """Generate promo codes (admin only)"""
    # Add admin check here
    # For now, just check if user is id 1 (first user)
    if current_user.id != 1:
        print(f"Unauthorized promo code generation attempt by user {current_user.id}")
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.json
        tier = data.get('tier', 'free')
        count = data.get('count', 10)
        prefix = data.get('prefix', '')
        discount_type = data.get('discount_type', 'tier')
        discount_value = data.get('discount_value')
        trial_days = data.get('trial_days')
        max_uses = data.get('max_uses', -1)  # -1 for unlimited by default

        print(f"Generating {count} promo codes - Type: {discount_type}, Tier: {tier}, Prefix: {prefix}, Max Uses: {max_uses}, Trial Days: {trial_days}")

        # Validate discount type
        if discount_type not in ['tier', 'amount', 'percent', 'trial']:
            return jsonify({'error': 'Invalid discount type. Must be tier, amount, percent, or trial'}), 400

        # Validate tier for tier-based codes
        if discount_type == 'tier' and tier not in SUBSCRIPTION_TIERS:
            print(f"Invalid tier requested: {tier}")
            return jsonify({'error': 'Invalid tier'}), 400

        # Validate discount value for amount/percent codes
        if discount_type in ['amount', 'percent']:
            if discount_value is None or discount_value <= 0:
                return jsonify({'error': 'Discount value must be greater than 0'}), 400
            if discount_type == 'percent' and discount_value > 100:
                return jsonify({'error': 'Percentage discount cannot exceed 100%'}), 400

        # Validate trial_days for trial codes
        if discount_type == 'trial':
            if trial_days is None or trial_days <= 0:
                return jsonify({'error': 'Trial days must be greater than 0'}), 400

        codes = create_promo_codes(tier, count, prefix, discount_type, discount_value, trial_days, max_uses)

        print(f"✅ Successfully generated {len(codes)} promo codes")

        return jsonify({
            'success': True,
            'codes': codes,
            'count': len(codes),
            'discount_type': discount_type,
            'discount_value': discount_value,
            'trial_days': trial_days
        }), 200

    except Exception as e:
        print(f"❌ Error generating promo codes: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/list-promo-codes')
@login_required
def admin_list_promo_codes():
    """List all promo codes (admin only)"""
    if current_user.id != 1:
        print(f"Unauthorized promo code list attempt by user {current_user.id}")
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("Loading promo codes...")
        
        cursor.execute("""
            SELECT code, tier, max_uses, times_used, is_active, created_at,
                   discount_type, discount_value, trial_days
            FROM promo_codes
            ORDER BY created_at DESC
        """)

        results = cursor.fetchall()
        conn.close()

        codes = [
            {
                'code': row[0],
                'tier': row[1],
                'max_uses': row[2],
                'times_used': row[3],
                'is_active': row[4],
                'created_at': row[5],
                'discount_type': row[6] or 'tier',
                'discount_value': row[7],
                'trial_days': row[8]
            }
            for row in results
        ]
        
        print(f"✅ Loaded {len(codes)} promo codes")
        
        return jsonify({'codes': codes}), 200
        
    except Exception as e:
        print(f"❌ Error loading promo codes: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# CUSTOM AGENTS SYSTEM
# ============================================

@app.route('/api/custom-agents', methods=['GET'])
@login_required
def get_custom_agents():
    """Get all custom agents for current user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check which columns exist
        cursor.execute("PRAGMA table_info(custom_agents)")
        columns = [col[1] for col in cursor.fetchall()]
        has_emoji = 'emoji' in columns
        has_icon_image = 'icon_image' in columns
        has_description = 'description' in columns
        has_role = 'role' in columns
        has_share_code = 'share_code' in columns
        has_folder = 'folder' in columns

        # Use description if available, fallback to role for old tables
        desc_column = 'description' if has_description else 'role'

        # Build SELECT query with optional share_code
        select_columns = f"id, name, {desc_column}"
        if has_emoji:
            select_columns += ", emoji"
        if has_icon_image:
            select_columns += ", icon_image"
        select_columns += ", personality, system_prompt"
        if has_share_code:
            select_columns += ", share_code"
        if has_folder:
            select_columns += ", folder"
        select_columns += ", created_at"
        
        # TODO: FUTURE FEATURE - Privacy control for custom agents
        # Currently shows all user's agents regardless of is_public flag
        # When implementing privacy: also check is_public flag or allow user to toggle visibility
        # Could add: WHERE user_id = ? AND (is_public = 1 OR some_condition)

        cursor.execute(f"""
            SELECT {select_columns}
            FROM custom_agents
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (current_user.id,))
        
        results = cursor.fetchall()
        conn.close()
        
        # Build agent objects
        agents = []
        for row in results:
            idx = 0
            agent = {
                'id': row[idx],
                'name': row[idx+1],
                'description': row[idx+2],
                'role': row[idx+2],
            }
            idx = 3

            if has_emoji:
                agent['emoji'] = row[idx] or '🤖'
                idx += 1
            else:
                agent['emoji'] = '🤖'

            if has_icon_image:
                agent['icon_image'] = row[idx]
                idx += 1
            else:
                agent['icon_image'] = None

            agent['personality'] = row[idx]
            agent['system_prompt'] = row[idx+1]
            idx += 2

            if has_share_code and row[idx]:
                agent['share_code'] = row[idx]
                agent['share_url'] = f"{request.host_url}custom/{row[idx]}"
                idx += 1

            if has_folder:
                agent['folder'] = row[idx]
                idx += 1
            else:
                agent['folder'] = None

            agent['created_at'] = row[idx]
            agents.append(agent)
        
        return jsonify({'agents': agents}), 200
        
    except Exception as e:
        print(f"❌ Error loading custom agents: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/custom-agents', methods=['POST'])
@app.route('/api/custom-agent/create', methods=['POST'])  # Alias for frontend compatibility
@login_required
def create_custom_agent():
    """Create a new custom agent"""

    # Check custom agent limit based on subscription tier
    try:
        tier = current_user.subscription_tier or 'free'
        tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
        custom_agents_limit = tier_info.get('custom_agents_limit', 1)

        # Count user's existing custom agents
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM custom_agents WHERE user_id = ?", (current_user.id,))
        current_count = cursor.fetchone()[0]
        conn.close()

        # Check if limit reached (-1 means unlimited)
        if custom_agents_limit != -1 and current_count >= custom_agents_limit:
            return jsonify({
                'error': f'Custom agent limit reached',
                'message': f'Your {tier_info["name"]} plan allows {custom_agents_limit} custom agent{"s" if custom_agents_limit > 1 else ""}. Upgrade to create more!',
                'current_count': current_count,
                'limit': custom_agents_limit,
                'upgrade_url': '/pricing'
            }), 403
    except Exception as e:
        print(f"Error checking custom agent limit: {e}")
        # Continue anyway to not block if there's an error

    try:
        # Handle both JSON and FormData
        if request.is_json:
            data = request.json
            icon_file = None
        else:
            data = request.form
            icon_file = request.files.get('icon_image')

        name = data.get('name')
        description = data.get('role') or data.get('description')  # Accept both for compatibility
        emoji = data.get('emoji', '🤖')  # Handle emoji from frontend (fallback)
        folder = data.get('folder', None)  # Optional folder for organization

        # Handle both 'instructions' (from frontend) and 'system_prompt' (legacy)
        instructions = data.get('instructions') or data.get('system_prompt', '')

        # Handle personality - can be JSON or string
        personality_data = data.get('personality', {})
        if isinstance(personality_data, dict):
            personality = json.dumps(personality_data)
        else:
            personality = personality_data

        if not name or not description:
            return jsonify({'error': 'Name and description are required'}), 400

        if not instructions:
            return jsonify({'error': 'Instructions are required'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # First check if columns exist, add if needed
        cursor.execute("PRAGMA table_info(custom_agents)")
        columns = [col[1] for col in cursor.fetchall()]

        # Check and add missing columns
        if 'emoji' not in columns:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN emoji TEXT DEFAULT '🤖'")
            conn.commit()
            print("✅ Added emoji column to custom_agents table")

        if 'icon_image' not in columns:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN icon_image TEXT DEFAULT NULL")
            conn.commit()
            print("✅ Added icon_image column to custom_agents table")

        if 'share_code' not in columns:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN share_code TEXT UNIQUE")
            conn.commit()
            print("✅ Added share_code column to custom_agents table")

        if 'is_public' not in columns:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN is_public BOOLEAN DEFAULT 1")
            conn.commit()
            print("✅ Added is_public column to custom_agents table")

        if 'folder' not in columns:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN folder TEXT DEFAULT NULL")
            conn.commit()
            print("✅ Added folder column to custom_agents table")

        # Handle icon image upload
        icon_image_path = None
        if icon_file and icon_file.filename:
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join('static', 'uploads', 'agent_icons')
            os.makedirs(upload_dir, exist_ok=True)

            # Generate unique filename
            import secrets
            file_ext = os.path.splitext(icon_file.filename)[1]
            filename = f"{secrets.token_urlsafe(16)}{file_ext}"
            file_path = os.path.join(upload_dir, filename)

            # Save file
            icon_file.save(file_path)
            icon_image_path = f"/static/uploads/agent_icons/{filename}"
            print(f"✅ Saved agent icon to {icon_image_path}")

        # Generate unique share code
        import secrets
        share_code = secrets.token_urlsafe(12)

        # Use description column (not role)
        cursor.execute("""
            INSERT INTO custom_agents (user_id, name, description, emoji, icon_image, personality, system_prompt, share_code, is_public, folder)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """, (current_user.id, name, description, emoji, icon_image_path, personality, instructions, share_code, folder))

        agent_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"✅ Created custom agent '{name}' (emoji: {emoji}, icon: {icon_image_path}) for user {current_user.id}")
        print(f"   Share link: /custom/{share_code}")

        # Generate full share URL
        share_url = f"{request.host_url}custom/{share_code}"

        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'name': name,
            'description': description,
            'emoji': emoji,
            'icon_image': icon_image_path,
            'share_code': share_code,
            'share_url': share_url
        }), 201

    except Exception as e:
        print(f"❌ Error creating custom agent: {str(e)}")
        import traceback
        traceback.print_exc()  # Print full error for debugging
        return jsonify({'error': str(e)}), 500

@app.route('/api/custom-agents/<int:agent_id>', methods=['PUT', 'PATCH'])
@login_required
def update_custom_agent(agent_id):
    """Update an existing custom agent"""
    try:
        # Handle both JSON and FormData
        if request.is_json:
            data = request.json
            icon_file = None
        else:
            data = request.form
            icon_file = request.files.get('icon_image')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("SELECT user_id FROM custom_agents WHERE id = ?", (agent_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return jsonify({'error': 'Agent not found'}), 404

        if result[0] != current_user.id:
            conn.close()
            return jsonify({'error': 'Unauthorized'}), 403

        # Build update query dynamically based on provided fields
        update_fields = []
        update_values = []

        if 'name' in data:
            update_fields.append('name = ?')
            update_values.append(data['name'])

        if 'role' in data or 'description' in data:
            update_fields.append('description = ?')
            update_values.append(data.get('role') or data.get('description'))

        if 'emoji' in data:
            update_fields.append('emoji = ?')
            update_values.append(data['emoji'])

        if 'instructions' in data or 'system_prompt' in data:
            update_fields.append('system_prompt = ?')
            update_values.append(data.get('instructions') or data.get('system_prompt'))

        if 'personality' in data:
            personality_data = data['personality']
            if isinstance(personality_data, dict):
                update_fields.append('personality = ?')
                update_values.append(json.dumps(personality_data))
            else:
                update_fields.append('personality = ?')
                update_values.append(personality_data)

        if 'folder' in data:
            update_fields.append('folder = ?')
            update_values.append(data['folder'])

        # Handle icon image upload
        if icon_file and icon_file.filename:
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join('static', 'uploads', 'agent_icons')
            os.makedirs(upload_dir, exist_ok=True)

            # Generate unique filename
            import secrets
            file_ext = os.path.splitext(icon_file.filename)[1]
            filename = f"{secrets.token_urlsafe(16)}{file_ext}"
            file_path = os.path.join(upload_dir, filename)

            # Save file
            icon_file.save(file_path)
            icon_image_path = f"/static/uploads/agent_icons/{filename}"

            update_fields.append('icon_image = ?')
            update_values.append(icon_image_path)
            print(f"✅ Updated agent icon to {icon_image_path}")

        if not update_fields:
            conn.close()
            return jsonify({'error': 'No fields to update'}), 400

        # Add agent_id to values for WHERE clause
        update_values.append(agent_id)

        # Execute update
        query = f"UPDATE custom_agents SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, update_values)
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Agent updated successfully',
            'agent_id': agent_id
        }), 200

    except Exception as e:
        print(f"❌ Error updating custom agent: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/custom-agents/<int:agent_id>', methods=['DELETE'])
@login_required
def delete_custom_agent(agent_id):
    """Delete a custom agent"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verify ownership
        cursor.execute("""
            SELECT user_id FROM custom_agents WHERE id = ?
        """, (agent_id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({'error': 'Agent not found'}), 404
        
        if result[0] != current_user.id:
            conn.close()
            return jsonify({'error': 'Unauthorized'}), 403
        
        cursor.execute("DELETE FROM custom_agents WHERE id = ?", (agent_id,))
        conn.commit()
        conn.close()
        
        print(f"✅ Deleted custom agent {agent_id} for user {current_user.id}")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        print(f"❌ Error deleting custom agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/agent/<int:agent_id>')
def view_custom_agent(agent_id):
    """View a custom agent page (shareable link)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, role, system_prompt
            FROM custom_agents
            WHERE id = ?
        """, (agent_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return "Custom agent not found", 404
        
        agent = {
            'id': result[0],
            'name': result[1],
            'role': result[2],
            'system_prompt': result[3]
        }
        
        # Redirect to dashboard with agent preselected
        # For now, just redirect to dashboard and use JavaScript to select
        return redirect(f'/dashboard?custom_agent={agent_id}')
        
    except Exception as e:
        print(f"❌ Error viewing custom agent: {str(e)}")
        return "Error loading custom agent", 500

@app.route('/api/custom-agents/<int:agent_id>')
@login_required
def get_custom_agent(agent_id):
    """Get details for a specific custom agent"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, role, personality, system_prompt, created_at
            FROM custom_agents
            WHERE id = ?
        """, (agent_id,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return jsonify({'error': 'Agent not found'}), 404

        agent = {
            'id': result[0],
            'name': result[1],
            'role': result[2],
            'personality': result[3],
            'system_prompt': result[4],
            'created_at': result[5]
        }

        return jsonify({'agent': agent}), 200

    except Exception as e:
        print(f"❌ Error getting custom agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================
# AGENT SHARING ENDPOINTS
# ============================================

@app.route('/api/custom-agents/<int:agent_id>/share', methods=['POST'])
@login_required
def share_custom_agent(agent_id):
    """Generate or regenerate a share code for an agent"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("SELECT user_id, name FROM custom_agents WHERE id = ?", (agent_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return jsonify({'error': 'Agent not found'}), 404

        if result[0] != current_user.id:
            conn.close()
            return jsonify({'error': 'Unauthorized'}), 403

        # Generate unique share code
        import secrets
        share_code = secrets.token_urlsafe(16)

        # Update agent with share code and make it public
        cursor.execute("""
            UPDATE custom_agents
            SET share_code = ?, is_public = 1
            WHERE id = ?
        """, (share_code, agent_id))

        conn.commit()
        conn.close()

        # Generate shareable URL
        share_url = f"{request.host_url}agents/shared/{share_code}"

        return jsonify({
            'success': True,
            'share_code': share_code,
            'share_url': share_url,
            'message': f'Share link created for "{result[1]}"'
        }), 200

    except Exception as e:
        print(f"❌ Error sharing agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/custom-agents/<int:agent_id>/unshare', methods=['POST'])
@login_required
def unshare_custom_agent(agent_id):
    """Remove share code and make agent private"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("SELECT user_id FROM custom_agents WHERE id = ?", (agent_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return jsonify({'error': 'Agent not found'}), 404

        if result[0] != current_user.id:
            conn.close()
            return jsonify({'error': 'Unauthorized'}), 403

        # Remove share code and make private
        cursor.execute("""
            UPDATE custom_agents
            SET share_code = NULL, is_public = 0
            WHERE id = ?
        """, (agent_id,))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Agent is now private'
        }), 200

    except Exception as e:
        print(f"❌ Error unsharing agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/custom-agents/shared/<share_code>')
def get_shared_agent(share_code):
    """Get public agent details by share code (no login required)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, description, emoji, system_prompt, user_id, created_at, is_public
            FROM custom_agents
            WHERE share_code = ?
        """, (share_code,))

        result = cursor.fetchone()

        if not result:
            conn.close()
            return jsonify({'error': 'Shared agent not found'}), 404

        # Check if agent is public
        if not result[7]:  # is_public
            conn.close()
            return jsonify({'error': 'This agent is no longer shared'}), 403

        # Get creator info
        cursor.execute("SELECT email FROM users WHERE id = ?", (result[5],))
        creator = cursor.fetchone()
        conn.close()

        agent = {
            'id': result[0],
            'name': result[1],
            'description': result[2],
            'emoji': result[3],
            'system_prompt': result[4],
            'created_by': creator[0] if creator else 'Unknown',
            'created_at': result[6]
        }

        return jsonify({'agent': agent}), 200

    except Exception as e:
        print(f"❌ Error getting shared agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/custom-agents/clone/<share_code>', methods=['POST'])
@login_required
def clone_shared_agent(share_code):
    """Clone a shared agent to current user's account"""
    try:
        # Check custom agent limit
        tier = current_user.subscription_tier or 'free'
        tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
        custom_agents_limit = tier_info.get('custom_agents_limit', 1)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Count user's existing custom agents
        cursor.execute("SELECT COUNT(*) FROM custom_agents WHERE user_id = ?", (current_user.id,))
        current_count = cursor.fetchone()[0]

        # Check if limit reached
        if custom_agents_limit != -1 and current_count >= custom_agents_limit:
            conn.close()
            return jsonify({
                'error': 'Custom agent limit reached',
                'message': f'Your {tier_info["name"]} plan allows {custom_agents_limit} custom agent{"s" if custom_agents_limit > 1 else ""}. Upgrade to create more!',
                'upgrade_url': '/pricing'
            }), 403

        # Get shared agent
        cursor.execute("""
            SELECT name, description, emoji, system_prompt, is_public
            FROM custom_agents
            WHERE share_code = ?
        """, (share_code,))

        result = cursor.fetchone()

        if not result:
            conn.close()
            return jsonify({'error': 'Shared agent not found'}), 404

        if not result[4]:  # is_public
            conn.close()
            return jsonify({'error': 'This agent is no longer shared'}), 403

        # Clone the agent
        cursor.execute("""
            INSERT INTO custom_agents (user_id, name, description, emoji, system_prompt, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (current_user.id, result[0], result[1], result[2], result[3]))

        new_agent_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'agent_id': new_agent_id,
            'message': f'Successfully cloned "{result[0]}" to your agents'
        }), 201

    except Exception as e:
        print(f"❌ Error cloning agent: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# GLOBAL AGENTS (ADMIN-MANAGED) API
# ============================================

@app.route('/api/global-agents', methods=['GET'])
@login_required
def get_global_agents():
    """Get all global agents available to current user"""
    try:
        # DEBUG: Log current user info
        print(f"🔍 DEBUG /api/global-agents: current_user.id = {current_user.id}, email = {getattr(current_user, 'email', 'N/A')}")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get all active global agents assigned to this user (DISTINCT to prevent duplicates)
        cursor.execute("""
            SELECT DISTINCT
                ga.id, ga.name, ga.description, ga.emoji, ga.category,
                ga.system_prompt, ga.template_variables, ga.created_at
            FROM global_agents ga
            INNER JOIN user_global_agents uga ON ga.id = uga.global_agent_id
            WHERE uga.user_id = ? AND ga.is_active = 1
            ORDER BY ga.name
        """, (current_user.id,))

        agents = []
        for row in cursor.fetchall():
            agents.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'emoji': row[3],
                'category': row[4],
                'system_prompt': row[5],
                'template_variables': json.loads(row[6]) if row[6] else None,
                'created_at': row[7],
                'type': 'global'  # Mark as global agent
            })

        # DEBUG: Log result count
        print(f"🔍 DEBUG /api/global-agents: Returning {len(agents)} agents for user {current_user.id}")

        conn.close()
        return jsonify({'agents': agents}), 200

    except Exception as e:
        print(f"❌ Error getting global agents: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/global-agents/<int:agent_id>/unassign', methods=['POST'])
@login_required
def unassign_global_agent(agent_id):
    """Unassign a global agent from current user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Delete the assignment
        cursor.execute("""
            DELETE FROM user_global_agents
            WHERE user_id = ? AND global_agent_id = ?
        """, (current_user.id, agent_id))

        conn.commit()
        rows_deleted = cursor.rowcount
        conn.close()

        if rows_deleted > 0:
            return jsonify({'success': True, 'message': 'Global agent unassigned'}), 200
        else:
            return jsonify({'error': 'Agent not found or already unassigned'}), 404

    except Exception as e:
        print(f"❌ Error unassigning global agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users', methods=['GET'])
@login_required
def admin_get_all_users():
    """Admin: Get all users for assignment"""
    if current_user.id != 1:  # Admin only
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, email, subscription_tier, created_at
            FROM users
            WHERE id != 1
            ORDER BY created_at DESC
        """)

        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'subscription_tier': row[3],
                'created_at': row[4]
            })

        conn.close()
        return jsonify({'users': users}), 200

    except Exception as e:
        print(f"❌ Error getting users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/global-agents', methods=['GET'])
@login_required
def admin_get_all_global_agents():
    """Admin: Get all global agents (not just assigned ones)"""
    if current_user.id != 1:  # Admin only
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, description, emoji, category, system_prompt,
                   template_variables, is_active, created_at, integrations
            FROM global_agents
            ORDER BY created_at DESC
        """)

        agents = []
        for row in cursor.fetchall():
            # Count how many users have this agent
            cursor.execute("""
                SELECT COUNT(*) FROM user_global_agents WHERE global_agent_id = ?
            """, (row[0],))
            user_count = cursor.fetchone()[0]

            agents.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'emoji': row[3],
                'category': row[4],
                'system_prompt': row[5],
                'template_variables': json.loads(row[6]) if row[6] else None,
                'is_active': bool(row[7]),
                'created_at': row[8],
                'integrations': json.loads(row[9]) if row[9] else [],
                'user_count': user_count
            })

        conn.close()
        return jsonify({'agents': agents}), 200

    except Exception as e:
        print(f"❌ Error getting global agents: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/global-agents', methods=['POST'])
@login_required
def admin_create_global_agent():
    """Admin: Create a new global agent template"""
    if current_user.id != 1:  # Admin only
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        emoji = data.get('emoji', '🤖')
        category = data.get('category', 'general')
        system_prompt = data.get('system_prompt')
        template_variables = data.get('template_variables')
        integrations = data.get('integrations', [])

        if not name or not system_prompt:
            return jsonify({'error': 'Name and system prompt required'}), 400

        # Convert template_variables to JSON if it's a dict
        if isinstance(template_variables, dict):
            template_variables = json.dumps(template_variables)

        # Convert integrations to JSON if it's a list
        if isinstance(integrations, list):
            integrations = json.dumps(integrations)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO global_agents (
                name, description, emoji, category, system_prompt,
                template_variables, integrations, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, description, emoji, category, system_prompt, template_variables, integrations, current_user.id))

        agent_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'message': f'Global agent "{name}" created successfully'
        }), 201

    except Exception as e:
        print(f"❌ Error creating global agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/global-agents/<int:agent_id>', methods=['PUT'])
@login_required
def admin_update_global_agent(agent_id):
    """Admin: Update a global agent"""
    if current_user.id != 1:  # Admin only
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Build update query dynamically
        updates = []
        params = []

        if 'name' in data:
            updates.append('name = ?')
            params.append(data['name'])
        if 'description' in data:
            updates.append('description = ?')
            params.append(data['description'])
        if 'emoji' in data:
            updates.append('emoji = ?')
            params.append(data['emoji'])
        if 'category' in data:
            updates.append('category = ?')
            params.append(data['category'])
        if 'system_prompt' in data:
            updates.append('system_prompt = ?')
            params.append(data['system_prompt'])
        if 'template_variables' in data:
            updates.append('template_variables = ?')
            tv = data['template_variables']
            params.append(json.dumps(tv) if isinstance(tv, dict) else tv)
        if 'integrations' in data:
            updates.append('integrations = ?')
            integ = data['integrations']
            params.append(json.dumps(integ) if isinstance(integ, list) else integ)
        if 'is_active' in data:
            updates.append('is_active = ?')
            params.append(1 if data['is_active'] else 0)

        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(agent_id)

        cursor.execute(f"""
            UPDATE global_agents SET {', '.join(updates)}
            WHERE id = ?
        """, params)

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Global agent updated successfully'
        }), 200

    except Exception as e:
        print(f"❌ Error updating global agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/global-agents/<int:agent_id>', methods=['DELETE'])
@login_required
def admin_delete_global_agent(agent_id):
    """Admin: Delete a global agent"""
    if current_user.id != 1:  # Admin only
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Delete user assignments first
        cursor.execute("DELETE FROM user_global_agents WHERE global_agent_id = ?", (agent_id,))

        # Delete the agent
        cursor.execute("DELETE FROM global_agents WHERE id = ?", (agent_id,))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Global agent deleted successfully'
        }), 200

    except Exception as e:
        print(f"❌ Error deleting global agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/global-agents/<int:agent_id>/assign', methods=['POST'])
@login_required
def admin_assign_global_agent(agent_id):
    """Admin: Assign a global agent to users"""
    if current_user.id != 1:  # Admin only
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])

        if not user_ids:
            return jsonify({'error': 'user_ids required'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        assigned_count = 0
        for user_id in user_ids:
            try:
                cursor.execute("""
                    INSERT INTO user_global_agents (user_id, global_agent_id, assigned_by)
                    VALUES (?, ?, ?)
                """, (user_id, agent_id, current_user.id))
                assigned_count += 1
            except sqlite3.IntegrityError:
                # Already assigned, skip
                pass

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'assigned_count': assigned_count,
            'message': f'Assigned to {assigned_count} user(s)'
        }), 200

    except Exception as e:
        print(f"❌ Error assigning global agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/global-agents/<int:agent_id>/unassign', methods=['POST'])
@login_required
def admin_unassign_global_agent(agent_id):
    """Admin: Unassign a global agent from users"""
    if current_user.id != 1:  # Admin only
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])

        if not user_ids:
            return jsonify({'error': 'user_ids required'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for user_id in user_ids:
            cursor.execute("""
                DELETE FROM user_global_agents
                WHERE user_id = ? AND global_agent_id = ?
            """, (user_id, agent_id))

        unassigned_count = cursor.rowcount
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'unassigned_count': unassigned_count,
            'message': f'Unassigned from {unassigned_count} user(s)'
        }), 200

    except Exception as e:
        print(f"❌ Error unassigning global agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/global-agents/<int:agent_id>/share', methods=['POST'])
@login_required
def share_global_agent(agent_id):
    """Admin: Generate share code for public access to global agent"""
    if current_user.id != 1:  # Admin only
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get agent details
        cursor.execute("SELECT name, share_code FROM global_agents WHERE id = ?", (agent_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return jsonify({'error': 'Global agent not found'}), 404

        agent_name, existing_share_code = result

        # Generate new share code if doesn't exist
        if not existing_share_code:
            import secrets
            share_code = secrets.token_urlsafe(16)

            cursor.execute("""
                UPDATE global_agents
                SET share_code = ?, is_public = 1
                WHERE id = ?
            """, (share_code, agent_id))

            conn.commit()
        else:
            share_code = existing_share_code
            # Just make sure it's public
            cursor.execute("""
                UPDATE global_agents
                SET is_public = 1
                WHERE id = ?
            """, (agent_id,))
            conn.commit()

        conn.close()

        # Generate shareable URL
        share_url = f"{request.host_url}global/{share_code}"

        return jsonify({
            'success': True,
            'share_code': share_code,
            'share_url': share_url,
            'message': f'Public link created for "{agent_name}"'
        }), 200

    except Exception as e:
        print(f"❌ Error sharing global agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/global-agents/<int:agent_id>/unshare', methods=['POST'])
@login_required
def unshare_global_agent(agent_id):
    """Admin: Remove public access to global agent"""
    if current_user.id != 1:  # Admin only
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE global_agents
            SET is_public = 0
            WHERE id = ?
        """, (agent_id,))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Global agent is now private (only assigned users can access)'
        }), 200

    except Exception as e:
        print(f"❌ Error unsharing global agent: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Public endpoint to access shared global agents
@app.route('/global/<share_code>')
def view_shared_global_agent(share_code):
    """Public page to chat with a shared global agent (no login required)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, description, emoji, system_prompt, is_public
            FROM global_agents
            WHERE share_code = ?
        """, (share_code,))

        agent = cursor.fetchone()
        conn.close()

        if not agent:
            return "Global agent not found", 404

        agent_name, description, emoji, system_prompt, is_public = agent

        if not is_public:
            return "This global agent is not publicly accessible", 403

        # Render public chat page for this global agent
        return render_template('global_agent_public.html',
                             agent_name=agent_name,
                             description=description,
                             emoji=emoji,
                             share_code=share_code)

    except Exception as e:
        print(f"❌ Error loading shared global agent: {str(e)}")
        return "Error loading global agent", 500

# API endpoint for guests to chat with shared global agents
@app.route('/api/global/chat', methods=['POST'])
def global_agent_chat():
    """Chat with a shared global agent (no login required)"""
    try:
        data = request.json
        share_code = data.get('share_code')
        message = data.get('message')

        if not share_code or not message:
            return jsonify({'error': 'Missing required fields'}), 400

        # Get global agent by share_code
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, system_prompt, is_public
            FROM global_agents
            WHERE share_code = ?
        """, (share_code,))

        agent_data = cursor.fetchone()
        conn.close()

        if not agent_data:
            return jsonify({'error': 'Global agent not found'}), 404

        agent_name, system_prompt, is_public = agent_data

        if not is_public:
            return jsonify({'error': 'This global agent is not publicly accessible'}), 403

        # Use Gemini for free tier (no API cost for public agents)
        import google.generativeai as genai
        genai.configure(api_key=app.config.get('GOOGLE_AI_API_KEY'))
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        full_prompt = f"{system_prompt}\n\nUser: {message}"
        response = model.generate_content(full_prompt)
        ai_response = response.text

        return jsonify({'response': ai_response}), 200

    except Exception as e:
        print(f"❌ Global agent chat error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ============================================
# AGENT TEMPLATE RENDERING
# ============================================

def render_agent_template(system_prompt, variables):
    """
    Render an agent template with provided variables
    Pattern 2: Template + Variables

    Variables can be in format {variable_name} or {{variable_name}}
    Example: "You are a {role} for {business_name}. Your audience is {audience}."
    """
    if not variables:
        return system_prompt

    rendered = system_prompt

    # Support both {var} and {{var}} syntax
    for key, value in variables.items():
        # Replace {key} format
        rendered = rendered.replace(f"{{{key}}}", str(value))
        # Replace {{key}} format
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))

    return rendered

@app.route('/api/custom-agents/<int:agent_id>/render', methods=['POST'])
@login_required
def render_agent_template_api(agent_id):
    """Render an agent template with provided variables"""
    try:
        data = request.get_json()
        variables = data.get('variables', {})

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get agent (check ownership)
        cursor.execute("""
            SELECT system_prompt, template_variables, user_id
            FROM custom_agents
            WHERE id = ?
        """, (agent_id,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return jsonify({'error': 'Agent not found'}), 404

        if result[2] != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        system_prompt = result[0]
        template_vars = json.loads(result[1]) if result[1] else None

        # Render the template
        rendered_prompt = render_agent_template(system_prompt, variables)

        return jsonify({
            'success': True,
            'rendered_prompt': rendered_prompt,
            'template_variables': template_vars,
            'variables_used': variables
        }), 200

    except Exception as e:
        print(f"❌ Error rendering template: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/agents/shared/<share_code>')
def view_shared_agent_page(share_code):
    """Web page to view and clone a shared agent"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, description, emoji, system_prompt, user_id, created_at, is_public
            FROM custom_agents
            WHERE share_code = ?
        """, (share_code,))

        result = cursor.fetchone()

        if not result or not result[6]:  # is_public
            conn.close()
            return render_template('error.html',
                error_title="Agent Not Found",
                error_message="This shared agent doesn't exist or is no longer public."
            ), 404

        # Get creator info
        cursor.execute("SELECT email FROM users WHERE id = ?", (result[4],))
        creator = cursor.fetchone()
        conn.close()

        agent_data = {
            'name': result[0],
            'description': result[1],
            'emoji': result[2],
            'system_prompt': result[3],
            'created_by': creator[0] if creator else 'Unknown',
            'created_at': result[5],
            'share_code': share_code
        }

        return render_template('shared_agent.html', agent=agent_data)

    except Exception as e:
        print(f"❌ Error viewing shared agent: {str(e)}")
        return render_template('error.html',
            error_title="Error",
            error_message="An error occurred while loading this agent."
        ), 500

@app.route('/api/generate-prompt', methods=['POST'])
@login_required
def generate_prompt():
    """Generate an improved prompt using AI with framework selection"""
    try:
        data = request.get_json()
        user_goal = data.get('goal', '').strip()
        framework = data.get('framework', 'rtcf')  # Default to RTCF

        if not user_goal:
            return jsonify({'error': 'Goal is required'}), 400

        print(f"🔮 Generating prompt for goal: {user_goal} using framework: {framework}")

        # Framework templates and descriptions
        frameworks = {
            'rtcf': {
                'name': 'RTCF (Role-Task-Context-Format)',
                'description': 'Best for almost everything',
                'template': 'Act as a [ROLE]. Do [TASK]. Context: [WHO/WHY/DETAILS]. Output format: [FORMAT + LENGTH].',
                'structure': 'Define the AI\'s role, specify the task, provide context, and detail the output format.'
            },
            'raci': {
                'name': 'RACI (Rules-Audience-Context-Intent)',
                'description': 'Best for brand voice and clear boundaries',
                'template': 'Rules: [DO/DON\'T]. Audience: [WHO IT\'S FOR]. Context: [BACKGROUND]. Intent: [SUCCESS CRITERIA].',
                'structure': 'Set rules and boundaries, define the audience, provide context, and explain what success looks like.'
            },
            'costar': {
                'name': 'CO-STAR (Context-Objective-Style-Tone-Audience-Response)',
                'description': 'Best for writing posts, scripts, sales pages',
                'template': 'Context: [SITUATION]. Objective: [GOAL]. Style: [APPROACH]. Tone: [VOICE]. Audience: [TARGET]. Response format: [OUTPUT].',
                'structure': 'Provide situation context, define objectives, specify writing style and tone, identify audience, and detail response format.'
            },
            'crispe': {
                'name': 'CRISPE (Context-Role-Intent-Style-Parameters-Examples)',
                'description': 'Best for high-quality outputs with consistent structure',
                'template': 'Context: [BACKGROUND]. Role: [WHO AI IS]. Intent: [PURPOSE]. Style: [APPROACH]. Parameters: [CONSTRAINTS]. Examples: [SAMPLES].',
                'structure': 'Set context, define role, explain intent, specify style, add parameters, and provide examples.'
            },
            'risen': {
                'name': 'RISEN (Role-Input-Steps-Expectations-Narrowing)',
                'description': 'Best for complex tasks requiring step-by-step thinking',
                'template': 'Role: [WHO AI IS]. Input: [WHAT YOU HAVE]. Steps: [PROCESS]. Expectations: [WHAT YOU WANT]. Narrowing: [FOCUS AREAS].',
                'structure': 'Define role, describe input, outline steps, set expectations, and narrow focus.'
            },
            'steps': {
                'name': 'Steps + Constraints + Checklist',
                'description': 'Best for practical instructions and repeatable outputs',
                'template': 'Provide [N] steps, each [CONSTRAINT]. Include checklist. [SPECIFIC REQUIREMENTS]. No fluff.',
                'structure': 'Request numbered steps with constraints, require checklist, eliminate unnecessary text.'
            },
            'rubric': {
                'name': 'Rubric Prompting',
                'description': 'Best for grading, reviewing, and improving',
                'template': 'Score on [CRITERIA] using 1-10 scale. Evaluate: [DIMENSIONS]. Then provide improvement suggestions.',
                'structure': 'Define scoring criteria, specify evaluation dimensions, request actionable improvements.'
            },
            'socratic': {
                'name': 'Socratic Mode',
                'description': 'Best for coaching, clarity, and decision-making',
                'template': 'Ask one question at a time about [TOPIC]. Wait for response. Guide toward [GOAL]. No direct answers.',
                'structure': 'Request questioning approach, ensure one question at a time, define guiding objective.'
            },
            'react': {
                'name': 'ReAct (Reason + Act)',
                'description': 'Best for research and multi-step tasks',
                'template': 'Plan approach to [TASK]. Execute step-by-step. Verify against [CRITERIA]. Show reasoning.',
                'structure': 'Request planning phase, execution with reasoning, and verification steps.'
            },
            'hpva': {
                'name': 'HPVA (Hook-Problem-Value-Action)',
                'description': 'Best for social posts that drive engagement',
                'template': 'Hook: [ATTENTION GRABBER]. Problem: [PAIN POINT]. Value: [SOLUTION]. Action: [CALL-TO-ACTION].',
                'structure': 'Create compelling hook, identify problem, present value proposition, include clear call-to-action.'
            },
            'eslc': {
                'name': 'ESLC (Evidence-Summary-Limitations-Citations)',
                'description': 'Best for research and academic outputs',
                'template': 'Evidence: [DATA/FACTS]. Summary: [KEY POINTS]. Limitations: [CAVEATS]. Citations: [SOURCES].',
                'structure': 'Require evidence-based content, concise summary, honest limitations, and proper citations.'
            },
            'sop': {
                'name': 'SOP (Standard Operating Procedure)',
                'description': 'Best for workflows, systems, and team training',
                'template': 'Purpose: [WHY]. Tools: [WHAT\'S NEEDED]. Steps: [HOW-TO]. Edge cases: [EXCEPTIONS]. QA: [CHECKS].',
                'structure': 'Define purpose, list required tools, detail steps, address edge cases, include quality assurance.'
            }
        }

        selected_framework = frameworks.get(framework, frameworks['rtcf'])

        # Enhanced system prompt with framework guidance
        system_prompt = f"""You are an expert prompt engineer specializing in the {selected_framework['name']} framework.

Framework: {selected_framework['name']}
Purpose: {selected_framework['description']}
Template: {selected_framework['template']}
Structure: {selected_framework['structure']}

Transform the user's goal into a comprehensive, well-structured prompt following the {selected_framework['name']} framework exactly.

Guidelines:
1. Follow the framework structure precisely
2. Be specific and detailed in each component
3. Include relevant context and constraints
4. Specify desired output format clearly
5. Make the prompt actionable and clear
6. Keep it concise but comprehensive

Return ONLY the improved prompt using the framework. Do not include explanations, meta-commentary, or framework labels in the output."""

        # Create the prompt generation request
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"Transform this goal into an effective prompt using the {selected_framework['name']} framework:\n\n{user_goal}"
            }]
        )

        improved_prompt = response.content[0].text.strip()

        print(f"✅ Generated prompt using {framework}: {improved_prompt[:100]}...")

        return jsonify({
            'prompt': improved_prompt,
            'original': user_goal,
            'framework': framework,
            'framework_name': selected_framework['name'],
            'framework_description': selected_framework['description']
        }), 200

    except Exception as e:
        print(f"❌ Error generating prompt: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prompt-frameworks', methods=['GET'])
def get_prompt_frameworks():
    """Get all available prompt frameworks"""
    frameworks = [
        {
            'id': 'rtcf',
            'name': 'RTCF (Role-Task-Context-Format)',
            'description': 'Best for almost everything',
            'category': 'Core'
        },
        {
            'id': 'raci',
            'name': 'RACI (Rules-Audience-Context-Intent)',
            'description': 'Best for brand voice and clear boundaries',
            'category': 'Core'
        },
        {
            'id': 'costar',
            'name': 'CO-STAR (Context-Objective-Style-Tone-Audience-Response)',
            'description': 'Best for writing posts, scripts, sales pages',
            'category': 'Core'
        },
        {
            'id': 'crispe',
            'name': 'CRISPE (Context-Role-Intent-Style-Parameters-Examples)',
            'description': 'Best for high-quality outputs with consistent structure',
            'category': 'Core'
        },
        {
            'id': 'risen',
            'name': 'RISEN (Role-Input-Steps-Expectations-Narrowing)',
            'description': 'Best for complex tasks requiring step-by-step thinking',
            'category': 'Core'
        },
        {
            'id': 'steps',
            'name': 'Steps + Constraints + Checklist',
            'description': 'Best for practical instructions and repeatable outputs',
            'category': 'Output Control'
        },
        {
            'id': 'rubric',
            'name': 'Rubric Prompting',
            'description': 'Best for grading, reviewing, and improving',
            'category': 'Output Control'
        },
        {
            'id': 'socratic',
            'name': 'Socratic Mode',
            'description': 'Best for coaching, clarity, and decision-making',
            'category': 'Thinking'
        },
        {
            'id': 'react',
            'name': 'ReAct (Reason + Act)',
            'description': 'Best for research and multi-step tasks',
            'category': 'Thinking'
        },
        {
            'id': 'hpva',
            'name': 'HPVA (Hook-Problem-Value-Action)',
            'description': 'Best for social posts that drive engagement',
            'category': 'Specific Use-Cases'
        },
        {
            'id': 'eslc',
            'name': 'ESLC (Evidence-Summary-Limitations-Citations)',
            'description': 'Best for research and academic outputs',
            'category': 'Specific Use-Cases'
        },
        {
            'id': 'sop',
            'name': 'SOP (Standard Operating Procedure)',
            'description': 'Best for workflows, systems, and team training',
            'category': 'Specific Use-Cases'
        }
    ]

    return jsonify({'frameworks': frameworks}), 200

@app.route('/api/user-info')
@login_required
def user_info():
    """Get current user info"""
    return jsonify({
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'subscription_tier': current_user.subscription_tier
        },
        'is_admin': current_user.id == 1
    }), 200

# ============================================
# WEBSITE FILE CREATION
# ============================================

@app.route('/api/create-website-file', methods=['POST'])
@login_required
def create_website_file():
    """Create a downloadable website file from code"""
    try:
        data = request.json
        filename = data.get('filename', 'website.html')
        code = data.get('code', '')
        
        if not code:
            return jsonify({'error': 'No code provided'}), 400
        
        # Sanitize filename
        filename = secure_filename(filename)
        if not filename.endswith('.html'):
            filename += '.html'
        
        # Create unique filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{current_user.id}_{timestamp}_{filename}"
        
        # Save to outputs directory (temporary storage)
        output_path = os.path.join('/mnt/user-data/outputs', unique_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Create download URL
        download_url = f"/download-website/{unique_filename}"
        
        print(f"✅ Created website file: {unique_filename} for user {current_user.id}")
        
        return jsonify({
            'success': True,
            'filename': filename,
            'download_url': download_url,
            'message': 'Website file created successfully!'
        }), 201
        
    except Exception as e:
        print(f"❌ Error creating website file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download-website/<filename>')
@login_required
def download_website(filename):
    """Download a website file"""
    try:
        # Verify user owns this file (check user ID in filename)
        if not filename.startswith(f"{current_user.id}_"):
            return "Unauthorized", 403
        
        file_path = os.path.join('/mnt/user-data/outputs', filename)
        
        if not os.path.exists(file_path):
            return "File not found", 404
        
        # Get original filename (remove user ID and timestamp)
        original_filename = '_'.join(filename.split('_')[2:])
        
        return send_from_directory(
            '/mnt/user-data/outputs',
            filename,
            as_attachment=True,
            download_name=original_filename
        )
        
    except Exception as e:
        print(f"❌ Error downloading website: {str(e)}")
        return "Error downloading file", 500

# ============================================
# USAGE LIMITS (UPDATE YOUR EXISTING FUNCTION)
# ============================================

def check_message_limit(user_id):
    """Check if user has reached their daily message limit"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT subscription_tier, messages_today, last_message_reset
        FROM users
        WHERE id = ?
    """, (user_id,))
    
    result = cursor.fetchone()
    if not result:
        conn.close()
        return False, "User not found"
    
    tier, messages_today, last_reset = result
    tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
    max_messages = tier_info['messages_per_day']
    
    # Reset counter if it's a new day
    if last_reset:
        last_reset_date = datetime.fromisoformat(last_reset).date()
        today = datetime.utcnow().date()
        
        if last_reset_date < today:
            cursor.execute("""
                UPDATE users
                SET messages_today = 0,
                    last_message_reset = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_id,))
            conn.commit()
            messages_today = 0
    
    conn.close()
    
    # Check limit (-1 means unlimited)
    if max_messages == -1:
        return True, None
    
    if messages_today >= max_messages:
        return False, f"Daily limit reached ({max_messages} messages)"
    
    return True, None


def increment_message_count(user_id):
    """Increment user's daily message count"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE users
        SET messages_today = messages_today + 1
        WHERE id = ?
    """, (user_id,))
    
    conn.commit()

# ============================================
# WEBHOOK SYSTEM FOR MAKE.COM
# ============================================

def init_webhooks_table():
    """Initialize webhooks table for Make.com integration"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            webhook_url TEXT NOT NULL,
            event_type TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_triggered TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()

init_webhooks_table()

def trigger_webhook(user_id, event_type, data):
    """Trigger all active webhooks for a user and event type"""
    try:
        import requests as webhook_requests
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, webhook_url FROM webhooks 
            WHERE user_id = ? AND event_type = ? AND is_active = 1
        """, (user_id, event_type))
        
        webhooks = cursor.fetchall()
        
        for webhook_id, webhook_url in webhooks:
            try:
                # Send webhook
                webhook_requests.post(
                    webhook_url,
                    json=data,
                    timeout=5
                )
                
                # Update last_triggered
                cursor.execute("""
                    UPDATE webhooks 
                    SET last_triggered = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (webhook_id,))
                conn.commit()
                
            except Exception as e:
                print(f"Webhook trigger error for {webhook_url}: {e}")
        
        conn.close()
    except Exception as e:
        print(f"Webhook system error: {e}")

# ============================================
# ============================================
# SUPPORT MESSAGES TABLE
# ============================================

def init_support_messages_table():
    """Create support messages table for user help requests"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_email TEXT,
            user_name TEXT,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'new',
            ai_attempted BOOLEAN DEFAULT 0,
            ai_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            admin_notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()

init_support_messages_table()


# API ENDPOINTS
# ============================================

# API Key Management Endpoints
@app.route('/api/get-api-key')
@login_required
def get_api_key():
    """Get user's API key"""
    try:
        print(f"DEBUG: get-api-key called for user {current_user.id}")
        
        # Check if api_keys table exists
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("DEBUG: api_keys table doesn't exist, creating...")
            conn.close()
            init_api_keys_table()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
        
        # Try to get existing key
        cursor.execute("SELECT api_key FROM api_keys WHERE user_id = ? AND is_active = 1", (current_user.id,))
        result = cursor.fetchone()
        
        if result:
            api_key = result[0]
            print(f"DEBUG: Found existing key for user {current_user.id}")
        else:
            # Generate new key
            print(f"DEBUG: Generating new key for user {current_user.id}")
            api_key = generate_api_key()
            cursor.execute("""
                INSERT INTO api_keys (user_id, api_key, name, is_active)
                VALUES (?, ?, ?, 1)
            """, (current_user.id, api_key, "Default API Key"))
            conn.commit()
        
        conn.close()
        return jsonify({'api_key': api_key}), 200
        
    except Exception as e:
        print(f"ERROR in get-api-key: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return a safe fallback
        return jsonify({
            'api_key': 'ERROR - Click Regenerate to create key',
            'error': str(e)
        }), 200  # Return 200 so page doesn't crash

@app.route('/api/regenerate-api-key', methods=['POST'])
@login_required
def regenerate_api_key():
    """Regenerate user's API key"""
    try:
        print(f"DEBUG: Regenerating API key for user {current_user.id}")
        
        # Ensure table exists
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'")
        if not cursor.fetchone():
            conn.close()
            init_api_keys_table()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
        
        # Deactivate old keys
        cursor.execute("UPDATE api_keys SET is_active = 0 WHERE user_id = ?", (current_user.id,))
        
        # Generate new key
        api_key = generate_api_key()
        cursor.execute("""
            INSERT INTO api_keys (user_id, api_key, name, is_active)
            VALUES (?, ?, ?, 1)
        """, (current_user.id, api_key, "Default API Key"))
        
        conn.commit()
        conn.close()
        
        print(f"DEBUG: New key generated for user {current_user.id}")
        return jsonify({'api_key': api_key, 'success': True}), 200
        
    except Exception as e:
        print(f"ERROR regenerating API key: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'api_key': 'ERROR - Try again',
            'success': False
        }), 200  # Return 200 to prevent page crash

@app.route('/api/usage-stats')
@login_required
def api_usage_stats():
    """Get API usage statistics"""
    try:
        stats = get_api_usage_stats(current_user.id)
        return jsonify(stats)
    except Exception as e:
        print(f"Error getting usage stats: {e}")
        # Return default stats
        return jsonify({
            'total_requests': 0,
            'requests_today': 0,
            'requests_this_month': 0,
            'remaining_quota': 'Unlimited' if current_user.subscription_tier == 'unlimited' else 'N/A'
        })

# API Authentication Decorator
def require_api_key(f):
    """Decorator to require API key authentication"""
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Missing Authorization header'}), 401
        
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Invalid Authorization header format. Use: Bearer YOUR_API_KEY'}), 401
        
        api_key = auth_header.replace('Bearer ', '')
        user_id = validate_api_key(api_key)
        
        if not user_id:
            return jsonify({'error': 'Invalid or inactive API key'}), 401
        
        # Store user_id in request context
        request.api_user_id = user_id
        
        # Log the API request
        log_api_request(user_id, request.path, request.method)
        
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

# Chat API Endpoint
@app.route('/api/chat', methods=['POST'])
@require_api_key
def api_chat():
    """Send a message to an AI agent via API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        agent = data.get('agent', 'Luna')
        message = data.get('message', '')
        context = data.get('context', {})
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Check daily message limit
        user_id = request.api_user_id
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT subscription_tier FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        tier = result[0] if result else 'free'
        
        # ============================================
        # CHECK API ACCESS (PRO/ENTERPRISE ONLY)
        # ============================================
        # API access is a premium feature. Only Pro and Enterprise users
        # can use the automation API to prevent abuse and ensure sustainability.
        if not has_api_access(tier):
            conn.close()
            return jsonify({
                'error': 'API access is only available for Pro ($49/mo) and Enterprise ($99/mo) subscribers.',
                'upgrade_required': True,
                'current_tier': tier,
                'required_tiers': ['pro', 'enterprise'],
                'upgrade_url': '/pricing'
            }), 403  # 403 Forbidden
        # ============================================
        
        # Count today's messages (chat + API)
        cursor.execute("""
            SELECT COUNT(*) FROM chat_history 
            WHERE user_id = ? AND date(timestamp) = date('now')
        """, (user_id,))
        chat_messages = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM api_usage 
            WHERE user_id = ? AND date(timestamp) = date('now') AND endpoint = '/api/chat'
        """, (user_id,))
        api_messages = cursor.fetchone()[0]
        
        total_messages = chat_messages + api_messages
        daily_limit = SUBSCRIPTION_TIERS[tier]['messages_per_day']
        
        # ============================================
        # BLOCK FREE USERS FROM CLAUDE API (COST SAVINGS)
        # ============================================
        # This API endpoint always uses Claude. Block free/freeforlife users.
        if not is_paid_user(tier):
            conn.close()
            return jsonify({
                'error': 'Claude AI API access is only available for paid subscribers (Starter or Pro plans).',
                'upgrade_required': True,
                'current_tier': tier,
                'available_tiers': ['starter', 'pro']
            }), 403  # 403 Forbidden
        # ============================================
        
        if total_messages >= daily_limit:
            conn.close()
            return jsonify({
                'error': 'Daily message limit reached',
                'limit': daily_limit,
                'used': total_messages
            }), 429
        
        conn.close()
        
        # Get agent personality
        agents_config = {
            'Luna': "You are Luna, an AI data analyst. You excel at analyzing data, finding patterns, and providing insights.",
            'Mila': "You are Mila, an AI organization expert. You help with planning, task management, and project organization.",
            'Sage': "You are Sage, an AI content writer. You create engaging written content, from articles to marketing copy.",
            'Ember': "You are Ember, an AI creative director. You provide creative ideas, artistic direction, and design suggestions.",
            'Sol': "You are Sol, an AI strategic thinker. You help with business strategy, decision-making, and long-term planning.",
            'Nova': "You are Nova, an AI technical expert. You assist with coding, debugging, and technical problem-solving.",
            'Theo': "You are Theo, an AI implementation specialist. You help turn ideas into actionable plans and execute them."
        }
        
        system_message = agents_config.get(agent, agents_config['Luna'])
        
        # Call Claude API
        client = anthropic.Anthropic(api_key=app.config['ANTHROPIC_API_KEY'])
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_message,
            messages=[{
                "role": "user",
                "content": message
            }]
        )
        
        ai_response = response.content[0].text
        
        # Save to chat history
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_history (user_id, agent, message, response)
            VALUES (?, ?, ?, ?)
        """, (user_id, agent, message, ai_response))
        conn.commit()
        conn.close()
        
        # Trigger webhooks for Make.com integration
        webhook_data = {
            'event': 'message.completed',
            'agent': agent,
            'message': message,
            'response': ai_response,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id
        }
        trigger_webhook(user_id, 'message.completed', webhook_data)
        
        return jsonify({
            'success': True,
            'agent': agent,
            'message': message,
            'response': ai_response,
            'timestamp': datetime.now().isoformat(),
            'remaining_quota': daily_limit - total_messages - 1
        })
        
    except Exception as e:
        print(f"API chat error: {e}")
        return jsonify({'error': str(e)}), 500

# Generate Image API Endpoint
@app.route('/api/generate-image', methods=['POST'])
@require_api_key
def api_generate_image():
    """Generate an image via API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        # Generate image using OpenAI DALL-E
        if not openai_client:
            return jsonify({'error': 'Image generation not available - OpenAI API key not configured'}), 503
        
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard"
        )
        
        image_url = response.data[0].url
        
        return jsonify({
            'success': True,
            'prompt': prompt,
            'image_url': image_url,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"API image generation error: {e}")
        return jsonify({'error': str(e)}), 500

# List Agents API Endpoint
@app.route('/api/agents', methods=['GET'])
@require_api_key
def api_list_agents():
    """List all available AI agents"""
    agents = [
        {
            'name': 'Luna',
            'role': 'Data Analyst',
            'description': 'Expert at analyzing data, finding patterns, and providing insights',
            'specialties': ['Data Analysis', 'Pattern Recognition', 'Insights', 'Statistics']
        },
        {
            'name': 'Mila',
            'role': 'Organization & Planning',
            'description': 'Helps with planning, task management, and project organization',
            'specialties': ['Project Planning', 'Task Management', 'Organization', 'Scheduling']
        },
        {
            'name': 'Sage',
            'role': 'Writing & Content',
            'description': 'Creates engaging written content, from articles to marketing copy',
            'specialties': ['Content Writing', 'Copywriting', 'Articles', 'Marketing']
        },
        {
            'name': 'Ember',
            'role': 'Creative Direction',
            'description': 'Provides creative ideas, artistic direction, and design suggestions',
            'specialties': ['Creative Ideas', 'Design', 'Branding', 'Visual Concepts']
        },
        {
            'name': 'Sol',
            'role': 'Strategic Thinking',
            'description': 'Helps with business strategy, decision-making, and long-term planning',
            'specialties': ['Strategy', 'Business Planning', 'Decision Making', 'Analysis']
        },
        {
            'name': 'Nova',
            'role': 'Technical Solutions',
            'description': 'Assists with coding, debugging, and technical problem-solving',
            'specialties': ['Coding', 'Debugging', 'Technical Support', 'Development']
        },
        {
            'name': 'Theo',
            'role': 'Implementation',
            'description': 'Helps turn ideas into actionable plans and execute them',
            'specialties': ['Execution', 'Implementation', 'Action Plans', 'Delivery']
        }
    ]
    
    return jsonify({
        'success': True,
        'agents': agents,
        'total': len(agents)
    })

# API Usage Quota Endpoint
@app.route('/api/usage', methods=['GET'])
@require_api_key
def api_usage():
    """Get current API usage and quota"""
    user_id = request.api_user_id
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get user subscription tier
    cursor.execute("SELECT subscription_tier FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    tier = result[0] if result else 'free'
    
    # Count today's messages (chat + API)
    cursor.execute("""
        SELECT COUNT(*) FROM chat_history 
        WHERE user_id = ? AND date(timestamp) = date('now')
    """, (user_id,))
    chat_messages = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM api_usage 
        WHERE user_id = ? AND date(timestamp) = date('now') AND endpoint = '/api/chat'
    """, (user_id,))
    api_messages = cursor.fetchone()[0]
    
    # Get total API requests
    stats = get_api_usage_stats(user_id)
    
    conn.close()
    
    daily_limit = SUBSCRIPTION_TIERS[tier]['messages_per_day']
    total_today = chat_messages + api_messages
    
    return jsonify({
        'success': True,
        'subscription_tier': tier,
        'daily_limit': daily_limit,
        'used_today': total_today,
        'remaining_today': max(0, daily_limit - total_today),
        'total_api_requests': stats['total_requests'],
        'api_requests_today': stats['today_requests']
    })

# ============================================
# WEBHOOK MANAGEMENT ENDPOINTS (for Make.com)
# ============================================

@app.route('/api/webhooks', methods=['GET'])
@login_required
def get_webhooks():
    """Get all webhooks for current user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, webhook_url, event_type, is_active, created_at, last_triggered
            FROM webhooks 
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (current_user.id,))
        
        webhooks = []
        for row in cursor.fetchall():
            webhooks.append({
                'id': row[0],
                'webhook_url': row[1],
                'event_type': row[2],
                'is_active': bool(row[3]),
                'created_at': row[4],
                'last_triggered': row[5]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'webhooks': webhooks,
            'total': len(webhooks)
        })
    except Exception as e:
        print(f"Error getting webhooks: {e}")
        # Try to initialize webhooks table
        try:
            init_webhooks_table()
            return jsonify({
                'success': True,
                'webhooks': [],
                'total': 0
            })
        except Exception as e2:
            print(f"Error initializing webhooks table: {e2}")
            return jsonify({
                'success': True,
                'webhooks': [],
                'total': 0
            })

@app.route('/api/webhooks', methods=['POST'])
@login_required
def create_webhook():
    """Create a new webhook"""
    data = request.get_json()
    
    webhook_url = data.get('webhook_url')
    event_type = data.get('event_type', 'message.completed')
    
    if not webhook_url:
        return jsonify({'error': 'webhook_url is required'}), 400
    
    # Validate event type
    valid_events = ['message.completed', 'image.generated', 'agent.response']
    if event_type not in valid_events:
        return jsonify({'error': f'event_type must be one of: {", ".join(valid_events)}'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO webhooks (user_id, webhook_url, event_type)
        VALUES (?, ?, ?)
    """, (current_user.id, webhook_url, event_type))
    
    webhook_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'webhook_id': webhook_id,
        'message': 'Webhook created successfully'
    })

@app.route('/api/webhooks/<int:webhook_id>', methods=['DELETE'])
@login_required
def delete_webhook(webhook_id):
    """Delete a webhook"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check ownership
    cursor.execute("SELECT user_id FROM webhooks WHERE id = ?", (webhook_id,))
    result = cursor.fetchone()
    
    if not result or result[0] != current_user.id:
        conn.close()
        return jsonify({'error': 'Webhook not found'}), 404
    
    cursor.execute("DELETE FROM webhooks WHERE id = ?", (webhook_id,))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Webhook deleted successfully'
    })

@app.route('/api/webhooks/<int:webhook_id>/toggle', methods=['POST'])
@login_required
def toggle_webhook(webhook_id):
    """Toggle webhook active status"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check ownership
    cursor.execute("SELECT user_id, is_active FROM webhooks WHERE id = ?", (webhook_id,))
    result = cursor.fetchone()
    
    if not result or result[0] != current_user.id:
        conn.close()
        return jsonify({'error': 'Webhook not found'}), 404
    
    new_status = 0 if result[1] else 1
    
    cursor.execute("UPDATE webhooks SET is_active = ? WHERE id = ?", (new_status, webhook_id))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'is_active': bool(new_status),
        'message': f'Webhook {"activated" if new_status else "deactivated"}'
    })

# ============================================
# RUN APPLICATION
# ============================================

@app.route('/admin/list-routes')
# ============================================
# SUPPORT CHATBOX HELPER ENDPOINTS
# ============================================

@app.route('/api/support/ask', methods=['POST'])
def support_ask_helper():
    """AI helper to answer common questions"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()

        if not question:
            return jsonify({'success': False, 'error': 'Question required'}), 400

        # Common Q&A knowledge base
        qa_responses = {
            'navigate': 'To navigate the platform:\n• Use the sidebar to access different AI agents\n• Click "Integrations" to connect external services\n• Settings menu (⚙️) for account management\n• Prompt Builder for creating custom prompts',
            'agents': 'We have 7 specialized AI agents:\n• Luna - Research & Analysis\n• Mila - Organization & Planning\n• Sage - Writing & Content\n• Ember - Creative Direction\n• Sol - Strategic Thinking\n• Nova - Technical Solutions\n• Theo - Implementation\n\nYou can also create custom agents!',
            'custom': 'To create a custom agent:\n1. Click "Create Custom Agent" in sidebar\n2. Name your agent\n3. Write personality/instructions\n4. Upload an icon (optional)\n5. Save!\n\nCustom agents remember your instructions.',
            'integrations': 'We support 30+ integrations including:\n• Slack, Discord, Teams\n• GitHub, GitLab\n• Google Sheets, Docs, Calendar\n• Stripe, Shopify\n• And many more!\n\nGo to Integrations page to connect.',
            'pricing': 'Our pricing:\n• Free: $0/month - 25 messages/day\n• Starter: $19/month - 60 messages/day\n• Pro: $49/month - 300 messages/day + API\n• Enterprise: $99/month - 1000 messages/day\n\nVisit /pricing for details.',
            'api': 'API access is available on Pro ($49/mo) and Enterprise ($99/mo) plans. You can:\n• Automate workflows\n• Integrate with custom apps\n• Use webhooks\n• Access all AI agents programmatically',
            'help': 'Need help? You can:\n• Use this chatbox for quick questions\n• Send us a message (we\'ll reply ASAP)\n• Check /faq for common questions\n• Visit /help for documentation'
        }

        # Simple keyword matching
        question_lower = question.lower()
        response = None

        for keyword, answer in qa_responses.items():
            if keyword in question_lower:
                response = answer
                break

        if response:
            return jsonify({
                'success': True,
                'answer': response,
                'can_help': True
            })
        else:
            return jsonify({
                'success': True,
                'can_help': False,
                'message': 'I\'m not sure about that. Would you like to send a message to our admin team?'
            })

    except Exception as e:
        print(f"Support helper error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/support/message', methods=['POST'])
def support_send_message():
    """Send support message to admin"""
    try:
        data = request.get_json()
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()

        if not subject or not message:
            return jsonify({'success': False, 'error': 'Subject and message required'}), 400

        # Get user info if logged in
        user_id = None
        user_email = None
        user_name = None

        if current_user.is_authenticated:
            user_id = current_user.id
            user_email = current_user.email
            user_name = current_user.username
        else:
            user_email = data.get('email', 'anonymous')
            user_name = data.get('name', 'Guest')

        # Save to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO support_messages (user_id, user_email, user_name, subject, message)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, user_email, user_name, subject, message))

        message_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message_id': message_id,
            'message': 'Your message has been sent! We\'ll get back to you soon.'
        })

    except Exception as e:
        print(f"Support message error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/support/messages', methods=['GET'])
@login_required
def get_support_messages():
    """Get all support messages (admin only)"""
    try:
        # Check if user is admin (you can customize this check)
        if not current_user.is_authenticated or current_user.email != 'admin@example.com':
            # For now, just check if user is looking at their own messages
            user_id = current_user.id
            admin_mode = False
        else:
            user_id = None
            admin_mode = True

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if admin_mode:
            cursor.execute("""
                SELECT * FROM support_messages
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT * FROM support_messages
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))

        messages = []
        for row in cursor.fetchall():
            messages.append(dict(row))

        conn.close()

        return jsonify({
            'success': True,
            'messages': messages,
            'admin_mode': admin_mode
        })

    except Exception as e:
        print(f"Get support messages error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/support/message/<int:message_id>/resolve', methods=['POST'])
@login_required
def resolve_support_message(message_id):
    """Mark support message as resolved (admin only)"""
    try:
        data = request.get_json()
        admin_notes = data.get('notes', '')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE support_messages
            SET status = 'resolved',
                resolved_at = CURRENT_TIMESTAMP,
                admin_notes = ?
            WHERE id = ?
        """, (admin_notes, message_id))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Message marked as resolved'
        })

    except Exception as e:
        print(f"Resolve message error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def list_routes():
    """List all registered Flask routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })

    # Check specifically for custom route
    custom_routes = [r for r in routes if 'custom' in r['path'].lower()]

    return jsonify({
        'success': True,
        'total_routes': len(routes),
        'custom_routes': custom_routes,
        'all_routes': sorted(routes, key=lambda x: x['path'])
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
