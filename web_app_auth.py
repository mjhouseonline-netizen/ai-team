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
        'api_access': False,
        'features': [
            '25 messages per day',
            'Access to all 7 agents',
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
        'api_access': False,  # NO API access for promo users
        'features': [
            'Unlimited messages',
            'All 7 AI agents',
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
        'api_access': False,  # NO API access
        'features': [
            '60 messages per day',
            'Claude AI access',
            'All 7 AI agents',
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
        'api_access': True,  # API access included
        'features': [
            '300 messages per day',
            'Claude AI access',
            'All 7 AI agents',
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
        'api_access': True,
        'features': [
            '1,000 messages per day',
            'Claude AI access',
            'All 7 AI agents',
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
    'gemini-1.5-flash': 0.0
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
            cursor.execute("ALTER TABLE users ADD COLUMN last_cost_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
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

# Initialize database on startup
try:
    init_database()
    init_promo_codes_table()
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


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create Stripe checkout session for subscription"""
    try:
        price_id = request.form.get('price_id')
        
        # Determine plan details based on price_id
        if price_id == STRIPE_STARTER_PRICE_ID:
            plan_name = 'starter'
        elif price_id == STRIPE_PRO_PRICE_ID:
            plan_name = 'pro'
        elif price_id == STRIPE_ENTERPRISE_PRICE_ID:
            plan_name = 'enterprise'
        else:
            return jsonify({'error': 'Invalid price ID'}), 400
        
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
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.host_url + 'success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url + 'cancel',
            metadata={
                'user_id': current_user.id,
                'plan': plan_name
            }
        )
        
        return redirect(checkout_session.url)
        
    except Exception as e:
        print(f"Error creating checkout session: {str(e)}")
        return jsonify({'error': 'Error creating checkout session'}), 500


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
        
        cursor.execute("""
            UPDATE users
            SET stripe_customer_id = ?,
                stripe_subscription_id = ?,
                subscription_tier = ?
            WHERE id = ?
        """, (customer_id, subscription_id, plan, user_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ User {user_id} upgraded to {plan}")
        
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

def get_conversation_history(user_id, agent_name, limit=20):
    """Get recent conversation history for context"""
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

def route_to_model(model_key, system_prompt, history, new_message):
    """Route to appropriate AI model with conversation history"""
    if model_key not in MODELS:
        model_key = 'claude-sonnet-4.5'  # Default fallback
    
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
        else:
            raise Exception(f"Unknown provider: {provider}")
    except Exception as e:
        print(f"Error with {provider} ({model_key}): {e}")
        # Fallback to Claude if other model fails
        if provider != 'anthropic':
            print(f"Falling back to Claude Sonnet...")
            return call_claude_with_history('claude-sonnet-4-20250514', system_prompt, history, new_message, 2000)
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
            genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
            
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
            model_key = data.get('model', 'claude-sonnet-4.5')
            attached_file = data.get('file')
            uploaded_file = None
        else:
            # FormData request (new format with file upload)
            message = request.form.get('message', '')
            agent = request.form.get('agent', 'Luna')
            model_key = request.form.get('model', 'gemini-2.0-flash')
            attached_file = None
            uploaded_file = request.files.get('file')
        
        if not message and not uploaded_file:
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
        # BLOCK FREE USERS FROM CLAUDE API (COST SAVINGS)
        # ============================================
        # Claude API costs money per request. Only allow paid subscribers
        # (starter and pro) to use Claude models to prevent API cost overruns
        # from free and freeforlife promo code users.
        if model_key in ['claude-sonnet-4.5', 'claude-opus-4', 'claude-haiku']:
            if not is_paid_user(tier):
                conn.close()
                return jsonify({
                    'error': 'Claude AI models are only available for paid subscribers. Upgrade to Starter ($19/mo) or Pro ($49/mo) to access Claude\'s advanced AI capabilities with superior reasoning and coding abilities.',
                    'upgrade_required': True,
                    'current_tier': tier,
                    'available_tiers': ['starter', 'pro']
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
        if suggested_agent and suggested_agent != agent and confidence >= 4 and is_first_message:
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
                conn.close()
                return jsonify({'error': f'Agent "{agent}" not found'}), 400
        
        # Get conversation history (last 20 messages for context)
        # Guests don't have history (not logged in)
        if is_guest:
            history = []
        else:
            history = get_conversation_history(current_user.id, agent, limit=20)

        # Handle file uploads from FormData
        file_info = None
        if uploaded_file:
            # Guests cannot upload files
            if is_guest:
                conn.close()
                return jsonify({
                    'error': '📎 File uploads require a free account. Sign up now to upload files and unlock full access to all AI agents!',
                    'signup_required': True,
                    'signup_url': '/register'
                }), 403

            # Save the uploaded file
            filename = secure_filename(uploaded_file.filename)
            user_folder = os.path.join(UPLOAD_FOLDER, str(current_user.id))
            os.makedirs(user_folder, exist_ok=True)
            
            filepath = os.path.join(user_folder, filename)
            uploaded_file.save(filepath)
            
            file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            
            file_info = {
                'filename': filename,
                'filepath': filepath,
                'extension': file_extension
            }
            
            # For text files, read content
            if file_extension in ['txt', 'md', 'csv', 'json', 'py', 'js', 'html', 'css']:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        file_content = f.read()[:10000]  # Limit to 10k chars
                    if message:
                        message = f"{message}\n\nFile: {filename}\nContent:\n{file_content}"
                    else:
                        message = f"File: {filename}\nContent:\n{file_content}"
                except Exception as e:
                    print(f"Error reading file: {e}")
                    if not message:
                        message = f"I received a file named {filename} but couldn't read its content."
        
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
            cursor.execute("""
                INSERT INTO chat_history (user_id, agent_name, message, response)
                VALUES (?, ?, ?, ?)
            """, (current_user.id, agent, saved_message, ai_response))

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
        # DELEGATION DETECTION
        # ============================================
        # Check if the agent suggested switching to another agent
        delegation_suggestion = None
        for other_agent in AGENT_CAPABILITIES.keys():
            if other_agent != agent:
                # Look for phrases like "Sol would be perfect for this" or "bring Sol into"
                if f"{other_agent} would be" in ai_response or f"bring {other_agent}" in ai_response:
                    delegation_suggestion = other_agent
                    break

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
            response_data['suggestion_reason'] = f"{agent} suggests {delegation_suggestion} for this task"

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
        
        cursor.execute("""
            SELECT id, agent_name, title, created_at, updated_at
            FROM conversations
            WHERE user_id = ? AND is_active = 1
            ORDER BY updated_at DESC
            LIMIT 50
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
                'updated_at': row[4]
            })
        
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
        
        # Verify conversation belongs to user
        cursor.execute("""
            SELECT agent_name, title FROM conversations
            WHERE id = ? AND user_id = ?
        """, (conv_id, current_user.id))
        
        conv_result = cursor.fetchone()
        if not conv_result:
            conn.close()
            return jsonify({'error': 'Conversation not found'}), 404
        
        agent_name, title = conv_result
        
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
        
        return jsonify({
            'id': conv_id,
            'agent': agent_name,
            'title': title,
            'messages': messages
        }), 200
        
    except Exception as e:
        print(f"Error getting conversation: {str(e)}")
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


def create_promo_codes(tier, count, prefix=""):
    """Create multiple promo codes for a tier"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    codes = []
    for i in range(count):
        code = f"{prefix}{generate_promo_code(8)}" if prefix else generate_promo_code(12)
        
        try:
            # Set max_uses = -1 for unlimited uses (default behavior)
            max_uses = -1  # -1 means unlimited uses
            
            cursor.execute("""
                INSERT INTO promo_codes (code, tier, max_uses, is_active, single_use)
                VALUES (?, ?, ?, 1, 0)
            """, (code, tier, max_uses))
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
        SELECT id, tier, max_uses, times_used, expires_at, is_active, single_use
        FROM promo_codes
        WHERE code = ?
    """, (code.upper(),))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return False, "Invalid promo code"
    
    promo_id, tier, max_uses, times_used, expires_at, is_active, single_use = result
    
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
    
    return True, {'id': promo_id, 'tier': tier, 'single_use': single_use}


def redeem_promo_code(code, user_id):
    """Redeem a promo code for a user"""
    # Validate code first
    is_valid, result = validate_promo_code(code)
    
    if not is_valid:
        return False, result
    
    promo_id = result['id']
    tier = result['tier']
    
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
        
        # Update user's tier
        cursor.execute("""
            UPDATE users
            SET subscription_tier = ?
            WHERE id = ?
        """, (tier, user_id))
        
        conn.commit()
        conn.close()
        
        return True, tier
        
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
        tier = data.get('tier', 'freeforlife')
        count = data.get('count', 10)
        prefix = data.get('prefix', '')
        
        print(f"Generating {count} promo codes for tier: {tier}, prefix: {prefix}")
        
        if tier not in SUBSCRIPTION_TIERS:
            print(f"Invalid tier requested: {tier}")
            return jsonify({'error': 'Invalid tier'}), 400
        
        codes = create_promo_codes(tier, count, prefix)
        
        print(f"✅ Successfully generated {len(codes)} promo codes")
        
        return jsonify({
            'success': True,
            'codes': codes,
            'count': len(codes)
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
            SELECT code, tier, max_uses, times_used, is_active, created_at
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
                'created_at': row[5]
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
        has_description = 'description' in columns
        has_role = 'role' in columns
        has_share_code = 'share_code' in columns
        
        # Use description if available, fallback to role for old tables
        desc_column = 'description' if has_description else 'role'
        
        # Build SELECT query with optional share_code
        select_columns = f"id, name, {desc_column}"
        if has_emoji:
            select_columns += ", emoji"
        select_columns += ", personality, system_prompt"
        if has_share_code:
            select_columns += ", share_code"
        select_columns += ", created_at"
        
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
            
            agent['personality'] = row[idx]
            agent['system_prompt'] = row[idx+1]
            idx += 2
            
            if has_share_code and row[idx]:
                agent['share_code'] = row[idx]
                agent['share_url'] = f"{request.host_url}custom/{row[idx]}"
                idx += 1
            
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
    try:
        data = request.json
        name = data.get('name')
        description = data.get('role') or data.get('description')  # Accept both for compatibility
        emoji = data.get('emoji', '🤖')  # Handle emoji from frontend
        
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
        
        # First check if emoji column exists, add if needed
        cursor.execute("PRAGMA table_info(custom_agents)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Check and add missing columns
        if 'emoji' not in columns:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN emoji TEXT DEFAULT '🤖'")
            conn.commit()
            print("✅ Added emoji column to custom_agents table")
        
        if 'share_code' not in columns:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN share_code TEXT UNIQUE")
            conn.commit()
            print("✅ Added share_code column to custom_agents table")
        
        if 'is_public' not in columns:
            cursor.execute("ALTER TABLE custom_agents ADD COLUMN is_public BOOLEAN DEFAULT 1")
            conn.commit()
            print("✅ Added is_public column to custom_agents table")
        
        # Generate unique share code
        import secrets
        share_code = secrets.token_urlsafe(12)
        
        # Use description column (not role)
        cursor.execute("""
            INSERT INTO custom_agents (user_id, name, description, emoji, personality, system_prompt, share_code, is_public)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (current_user.id, name, description, emoji, personality, instructions, share_code))
        
        agent_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Created custom agent '{name}' (emoji: {emoji}) for user {current_user.id}")
        print(f"   Share link: /custom/{share_code}")
        
        # Generate full share URL
        share_url = f"{request.host_url}custom/{share_code}"
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'name': name,
            'description': description,
            'emoji': emoji,
            'share_code': share_code,
            'share_url': share_url
        }), 201
        
        print(f"✅ Created custom agent '{name}' (emoji: {emoji}) for user {current_user.id}")
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'name': name,
            'description': description,
            'emoji': emoji
        }), 201
        
    except Exception as e:
        print(f"❌ Error creating custom agent: {str(e)}")
        import traceback
        traceback.print_exc()  # Print full error for debugging
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

@app.route('/api/generate-prompt', methods=['POST'])
@login_required
def generate_prompt():
    """Generate an improved prompt using AI"""
    try:
        data = request.get_json()
        user_goal = data.get('goal', '').strip()
        
        if not user_goal:
            return jsonify({'error': 'Goal is required'}), 400
        
        print(f"🔮 Generating prompt for goal: {user_goal}")
        
        # System prompt for the prompt builder
        system_prompt = """You are an expert prompt engineer. Your job is to take a user's simple request and transform it into a clear, effective, detailed prompt that will get the best results from an AI assistant.

When creating prompts, you should:
1. Be specific and detailed
2. Include context that helps the AI understand the task
3. Specify the desired format, tone, or style when relevant
4. Break complex requests into clear steps
5. Add relevant constraints or requirements
6. Keep it concise but comprehensive

Transform the user's simple goal into a well-structured prompt. Return ONLY the improved prompt, no explanations or meta-commentary."""

        # Create the prompt generation request
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"Transform this simple request into an effective, detailed prompt:\n\n{user_goal}"
            }]
        )
        
        improved_prompt = response.content[0].text.strip()
        
        print(f"✅ Generated prompt: {improved_prompt[:100]}...")
        
        return jsonify({
            'prompt': improved_prompt,
            'original': user_goal
        }), 200
        
    except Exception as e:
        print(f"❌ Error generating prompt: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
