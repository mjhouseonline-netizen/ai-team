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
from flask import Flask, request, jsonify, session, redirect, url_for, render_template, send_from_directory
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

# ============================================
# NOTION INTEGRATION IMPORT
# ============================================
from routes.notion_routes import notion_bp

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
app.register_blueprint(notion_bp)

# Database path
DB_PATH = 'users.db'

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
        'messages_per_day': 25,
        'agents_available': 7,
        'features': [
            '25 messages per day',
            'Access to all 7 agents',
            'Basic chat history'
        ]
    },
    'freeforlife': {
        'name': 'Free For Life',
        'messages_per_day': -1,  # Unlimited
        'agents_available': 7,
        'features': [
            'Unlimited messages',
            'All 7 AI agents',
            'Full chat history',
            'Priority support',
            'Automation API access'
        ]
    },
    'starter': {
        'name': 'Starter',
        'price': 19,
        'messages_per_day': 100,
        'agents_available': 7,
        'features': [
            '100 messages per day',
            'All 7 AI agents',
            'Full chat history'
        ]
    },
    'pro': {
        'name': 'Pro',
        'price': 49,
        'messages_per_day': 500,
        'agents_available': 7,
        'features': [
            '500 messages per day',
            'All 7 AI agents',
            'Unlimited chat history',
            'Automation API access'
        ]
    }
}

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
    print("✅ Database initialization complete")

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
                         pro_price_id=STRIPE_PRO_PRICE_ID)


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


@app.route('/automations')
@login_required
def automations():
    """Automations page"""
    return render_template('automations.html', user=current_user)

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
• **Website & web development** (HTML/CSS/JavaScript)

WORKING WITH THE TEAM:
- Implement Mila's organized plans technically
- Make Theo's workflows technically sound
- Validate technical feasibility for team ideas

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
• **Building websites & web pages** (HTML/CSS/JavaScript)

WORKING WITH THE TEAM:
- Execute Mila's organized plans step-by-step
- Implement Nova's technical solutions practically
- Build out Ember's creative concepts

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

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Send message to AI agent with optional file attachment"""
    try:
        data = request.json
        message = data.get('message')
        agent = data.get('agent', 'Ember')
        attached_file = data.get('file')  # File info from upload
        
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
        
        # Build message content with file if provided
        message_content = []
        
        # Add file if provided
        if attached_file and 'filepath' in attached_file:
            filepath = attached_file['filepath']
            
            if os.path.exists(filepath):
                filename = attached_file.get('original_filename', 'file')
                
                # Handle images
                if is_image_file(filename):
                    base64_data = encode_file_to_base64(filepath)
                    media_type = get_file_media_type(filepath)
                    
                    message_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_data
                        }
                    })
                
                # Handle PDFs
                elif is_pdf_file(filename):
                    base64_data = encode_file_to_base64(filepath)
                    
                    message_content.append({
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": base64_data
                        }
                    })
                
                # Handle text files
                elif is_text_file(filename):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    message = f"{message}\n\nFile: {filename}\nContent:\n{file_content}"
        
        # Add text message
        message_content.append({
            "type": "text",
            "text": message
        })
        
        # If only text, simplify to string
        if len(message_content) == 1 and message_content[0]["type"] == "text":
            message_content = message
        
        # Call Anthropic API with proper system prompt
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,  # Reduced from 1024 for shorter responses
            system=system_prompt,
            messages=[
                {"role": "user", "content": message_content}
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
        
        # Include filename in message if file was attached
        saved_message = message
        if attached_file and 'original_filename' in attached_file:
            saved_message = f"📎 {attached_file['original_filename']}\n{message}"
        
        cursor.execute(
            "INSERT INTO chat_history (user_id, agent_name, message, response) VALUES (?, ?, ?, ?)",
            (current_user.id, agent, saved_message, ai_response)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'response': ai_response,
            'agent': agent
        }), 200
        
    except Exception as e:
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
# DATABASE INITIALIZATION - ADD PROMO CODES TABLE
# ============================================

def init_promo_codes_table():
    """Initialize promo codes table with migration support"""
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
            is_active BOOLEAN DEFAULT 1
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
    
    conn.commit()
    conn.close()
    print("✅ Promo codes tables initialized")

# Call this after your existing init_database()
init_promo_codes_table()

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

def generate_api_key():
    """Generate a secure API key"""
    return f"sk-{secrets.token_urlsafe(32)}"

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
            cursor.execute("""
                INSERT INTO promo_codes (code, tier, max_uses)
                VALUES (?, ?, 1)
            """, (code, tier))
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
        SELECT id, tier, max_uses, times_used, expires_at, is_active
        FROM promo_codes
        WHERE code = ?
    """, (code.upper(),))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return False, "Invalid promo code"
    
    promo_id, tier, max_uses, times_used, expires_at, is_active = result
    
    if not is_active:
        return False, "This promo code is no longer active"
    
    if times_used >= max_uses:
        return False, "This promo code has already been used"
    
    if expires_at:
        expiry = datetime.fromisoformat(expires_at)
        if datetime.utcnow() > expiry:
            return False, "This promo code has expired"
    
    return True, {'id': promo_id, 'tier': tier}


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
            tier_info = SUBSCRIPTION_TIERS[result['tier']]
            return jsonify({
                'valid': True,
                'tier': result['tier'],
                'tier_name': tier_info['name'],
                'features': tier_info['features']
            }), 200
        else:
            return jsonify({'valid': False, 'error': result}), 200
            
    except Exception as e:
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
        
        cursor.execute("""
            SELECT id, name, role, personality, system_prompt, created_at
            FROM custom_agents
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (current_user.id,))
        
        results = cursor.fetchall()
        conn.close()
        
        agents = [
            {
                'id': row[0],
                'name': row[1],
                'role': row[2],
                'personality': row[3],
                'system_prompt': row[4],
                'created_at': row[5]
            }
            for row in results
        ]
        
        return jsonify({'agents': agents}), 200
        
    except Exception as e:
        print(f"❌ Error loading custom agents: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/custom-agents', methods=['POST'])
@login_required
def create_custom_agent():
    """Create a new custom agent"""
    try:
        data = request.json
        name = data.get('name')
        role = data.get('role')
        personality = json.dumps(data.get('personality', {}))
        system_prompt = data.get('system_prompt', '')
        
        if not name or not role:
            return jsonify({'error': 'Name and role are required'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO custom_agents (user_id, name, role, personality, system_prompt)
            VALUES (?, ?, ?, ?, ?)
        """, (current_user.id, name, role, personality, system_prompt))
        
        agent_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Created custom agent '{name}' for user {current_user.id}")
        
        return jsonify({
            'success': True,
            'agent_id': agent_id
        }), 201
        
    except Exception as e:
        print(f"❌ Error creating custom agent: {str(e)}")
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
        }
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
