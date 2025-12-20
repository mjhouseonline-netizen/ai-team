# AI TEAM - COST MONITORING & ALERT SYSTEM
# Add this to your web_app_auth.py

import os
from datetime import datetime, timedelta
import sqlite3
from flask import jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================================
# MODEL COSTS (per message average)
# ============================================

MODEL_COSTS = {
    # Anthropic Claude
    'claude-sonnet-4.5': 0.003,
    'claude-opus-4': 0.006,
    'claude-haiku-4.5': 0.0008,
    
    # OpenAI GPT
    'gpt-4o': 0.0025,
    'gpt-4-turbo': 0.004,
    'gpt-4o-mini': 0.0002,
    
    # Google Gemini
    'gemini-2.0-flash': 0.0,
    'gemini-1.5-pro': 0.0,
    'gemini-pro': 0.0,
}

# ============================================
# COST THRESHOLDS & ALERTS
# ============================================

COST_THRESHOLDS = {
    'starter': {
        'daily_warning': 1.0,      # Alert if user costs >$1/day
        'daily_critical': 2.0,      # Block expensive models if >$2/day
        'monthly_max': 19.0         # Max cost = their subscription price
    },
    'pro': {
        'daily_warning': 3.0,       # Alert if >$3/day
        'daily_critical': 5.0,       # Block expensive models if >$5/day
        'monthly_max': 49.0
    },
    'enterprise': {
        'daily_warning': 5.0,       # Alert if >$5/day
        'daily_critical': 10.0,      # Block expensive models if >$10/day
        'monthly_max': 99.0
    }
}

# Your admin email for alerts
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'your-email@example.com')
ALERT_EMAIL_ENABLED = os.getenv('ALERT_EMAIL_ENABLED', 'false').lower() == 'true'

# ============================================
# DATABASE SETUP - ADD TO INIT
# ============================================

def setup_cost_tracking():
    """Add cost tracking tables to database"""
    conn = sqlite3.connect('ai_team.db')
    cursor = conn.cursor()
    
    # Create cost tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            model TEXT NOT NULL,
            cost REAL NOT NULL,
            message_count INTEGER DEFAULT 1,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cost_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            cost REAL NOT NULL,
            threshold REAL NOT NULL,
            message TEXT,
            timestamp TEXT NOT NULL,
            resolved INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Add cost tracking columns to users table if not exists
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN daily_cost REAL DEFAULT 0.0")
        cursor.execute("ALTER TABLE users ADD COLUMN monthly_cost REAL DEFAULT 0.0")
        cursor.execute("ALTER TABLE users ADD COLUMN last_cost_reset TEXT")
        cursor.execute("ALTER TABLE users ADD COLUMN expensive_models_blocked INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Columns already exist
    
    conn.commit()
    conn.close()
    print("✅ Cost tracking database setup complete!")

# ============================================
# COST TRACKING FUNCTIONS
# ============================================

def track_message_cost(user_id, model, message_count=1):
    """Track cost of a message and update user totals"""
    cost_per_message = MODEL_COSTS.get(model, 0.003)  # Default to Sonnet cost
    total_cost = cost_per_message * message_count
    
    conn = sqlite3.connect('ai_team.db')
    cursor = conn.cursor()
    
    # Log the usage
    cursor.execute("""
        INSERT INTO usage_costs (user_id, model, cost, message_count, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, model, total_cost, message_count, datetime.utcnow().isoformat()))
    
    # Get user's current costs and tier
    cursor.execute("""
        SELECT daily_cost, monthly_cost, last_cost_reset, subscription_tier
        FROM users
        WHERE id = ?
    """, (user_id,))
    
    result = cursor.fetchone()
    if not result:
        conn.close()
        return
    
    daily_cost, monthly_cost, last_reset, tier = result
    
    # Reset if new day
    if last_reset:
        try:
            last_reset_date = datetime.fromisoformat(last_reset).date()
            today = datetime.utcnow().date()
            if last_reset_date < today:
                daily_cost = 0.0
        except:
            daily_cost = 0.0
    
    # Update user costs
    new_daily_cost = daily_cost + total_cost
    new_monthly_cost = monthly_cost + total_cost
    
    cursor.execute("""
        UPDATE users
        SET daily_cost = ?,
            monthly_cost = ?,
            last_cost_reset = ?
        WHERE id = ?
    """, (new_daily_cost, new_monthly_cost, datetime.utcnow().isoformat(), user_id))
    
    conn.commit()
    
    # Check if we need to send alerts or block expensive models
    check_cost_thresholds(user_id, tier, new_daily_cost, new_monthly_cost)
    
    conn.close()
    return total_cost

def check_cost_thresholds(user_id, tier, daily_cost, monthly_cost):
    """Check if user has exceeded cost thresholds"""
    if tier not in COST_THRESHOLDS:
        return
    
    thresholds = COST_THRESHOLDS[tier]
    conn = sqlite3.connect('ai_team.db')
    cursor = conn.cursor()
    
    # Check daily warning threshold
    if daily_cost > thresholds['daily_warning'] and daily_cost <= thresholds['daily_critical']:
        # Send warning alert
        send_cost_alert(user_id, 'warning', daily_cost, thresholds['daily_warning'], tier)
    
    # Check daily critical threshold - BLOCK EXPENSIVE MODELS
    if daily_cost > thresholds['daily_critical']:
        cursor.execute("""
            UPDATE users
            SET expensive_models_blocked = 1
            WHERE id = ?
        """, (user_id,))
        conn.commit()
        
        # Send critical alert
        send_cost_alert(user_id, 'critical', daily_cost, thresholds['daily_critical'], tier)
    
    # Check monthly max
    if monthly_cost > thresholds['monthly_max']:
        # Send monthly limit alert
        send_cost_alert(user_id, 'monthly_max', monthly_cost, thresholds['monthly_max'], tier)
    
    conn.close()

def send_cost_alert(user_id, alert_type, cost, threshold, tier):
    """Send cost alert and log it"""
    conn = sqlite3.connect('ai_team.db')
    cursor = conn.cursor()
    
    # Check if we already sent this alert today
    cursor.execute("""
        SELECT id FROM cost_alerts
        WHERE user_id = ?
        AND alert_type = ?
        AND date(timestamp) = date('now')
        AND resolved = 0
    """, (user_id, alert_type))
    
    if cursor.fetchone():
        conn.close()
        return  # Already alerted today
    
    # Get user email
    cursor.execute("SELECT email, username FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return
    
    user_email, username = result
    
    # Create alert message
    messages = {
        'warning': f"⚠️ User {username} (ID: {user_id}) on {tier} plan has cost ${cost:.2f} today (threshold: ${threshold:.2f})",
        'critical': f"🚨 CRITICAL: User {username} (ID: {user_id}) has cost ${cost:.2f} today! Expensive models BLOCKED.",
        'monthly_max': f"🔴 MONTHLY LIMIT: User {username} (ID: {user_id}) has cost ${cost:.2f} this month (plan: ${threshold:.2f})"
    }
    
    message = messages.get(alert_type, f"Cost alert for user {user_id}")
    
    # Log alert
    cursor.execute("""
        INSERT INTO cost_alerts (user_id, alert_type, cost, threshold, message, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, alert_type, cost, threshold, message, datetime.utcnow().isoformat()))
    
    conn.commit()
    conn.close()
    
    # Send email alert if enabled
    if ALERT_EMAIL_ENABLED:
        send_email_alert(message, alert_type, user_email, username, cost, threshold)
    
    # Print to console (will show in Render logs)
    print(f"\n{'='*60}")
    print(f"💰 COST ALERT - {alert_type.upper()}")
    print(f"{'='*60}")
    print(message)
    print(f"{'='*60}\n")

def send_email_alert(message, alert_type, user_email, username, cost, threshold):
    """Send email alert to admin"""
    try:
        msg = MIMEMultipart()
        msg['From'] = os.getenv('SMTP_FROM_EMAIL')
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = f"🚨 AI Team Cost Alert: {alert_type.upper()}"
        
        body = f"""
        <html>
        <body>
        <h2>Cost Alert Triggered</h2>
        <p><strong>Alert Type:</strong> {alert_type.upper()}</p>
        <p><strong>User:</strong> {username} ({user_email})</p>
        <p><strong>Current Cost:</strong> ${cost:.2f}</p>
        <p><strong>Threshold:</strong> ${threshold:.2f}</p>
        <hr>
        <p>{message}</p>
        <p><a href="https://ai-team.skillsoul.store/admin/usage">View Usage Dashboard</a></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        print(f"✅ Email alert sent to {ADMIN_EMAIL}")
    except Exception as e:
        print(f"❌ Failed to send email alert: {e}")

def is_expensive_model_blocked(user_id):
    """Check if expensive models are blocked for this user"""
    conn = sqlite3.connect('ai_team.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT expensive_models_blocked
        FROM users
        WHERE id = ?
    """, (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] == 1 if result else False

# Expensive models list
EXPENSIVE_MODELS = ['claude-opus-4', 'gpt-4-turbo']

# ============================================
# MODIFY YOUR CHAT ENDPOINT
# ============================================

# In your /api/chat route, ADD THIS BEFORE processing the message:

"""
@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    message = data.get('message', '')
    agent = data.get('agent', 'luna')
    model_key = data.get('model', 'gemini-2.0-flash')  # Default to free model
    
    # NEW: Check if expensive models are blocked
    if is_expensive_model_blocked(current_user.id):
        if model_key in EXPENSIVE_MODELS:
            return jsonify({
                'error': 'Expensive models temporarily blocked due to high usage. Please use Gemini or GPT-4o Mini.',
                'blocked': True,
                'allowed_models': ['gemini-2.0-flash', 'gemini-1.5-pro', 'gpt-4o-mini', 'claude-haiku-4.5']
            }), 403
    
    # ... rest of your chat logic ...
    
    # AFTER getting AI response, track the cost:
    cost = track_message_cost(current_user.id, model_key, message_count=1)
    
    return jsonify({
        'response': ai_response,
        'agent': agent,
        'model': model_key,
        'cost': f"${cost:.4f}" if cost else None
    }), 200
"""

# ============================================
# ADMIN DASHBOARD ROUTES
# ============================================

@app.route('/admin/usage')
@login_required
def admin_usage_dashboard():
    """Admin dashboard to view user costs"""
    # Check if user is admin (add this check)
    if not current_user.email.endswith('@skillsoul.store'):  # Change to your admin email domain
        return "Unauthorized", 403
    
    conn = sqlite3.connect('ai_team.db')
    cursor = conn.cursor()
    
    # Get top cost users (last 30 days)
    cursor.execute("""
        SELECT 
            u.id,
            u.username,
            u.email,
            u.subscription_tier,
            u.daily_cost,
            u.monthly_cost,
            u.expensive_models_blocked,
            COUNT(uc.id) as total_messages
        FROM users u
        LEFT JOIN usage_costs uc ON u.id = uc.user_id
        WHERE u.subscription_tier != 'free'
        GROUP BY u.id
        ORDER BY u.monthly_cost DESC
        LIMIT 50
    """)
    
    users = cursor.fetchall()
    
    # Get recent alerts
    cursor.execute("""
        SELECT 
            ca.id,
            u.username,
            ca.alert_type,
            ca.cost,
            ca.threshold,
            ca.message,
            ca.timestamp
        FROM cost_alerts ca
        JOIN users u ON ca.user_id = u.id
        WHERE ca.resolved = 0
        ORDER BY ca.timestamp DESC
        LIMIT 20
    """)
    
    alerts = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin_usage.html', users=users, alerts=alerts)

@app.route('/admin/usage/stats')
@login_required
def usage_stats_api():
    """API endpoint for usage statistics"""
    conn = sqlite3.connect('ai_team.db')
    cursor = conn.cursor()
    
    # Total costs today
    cursor.execute("""
        SELECT SUM(cost) FROM usage_costs
        WHERE date(timestamp) = date('now')
    """)
    today_cost = cursor.fetchone()[0] or 0.0
    
    # Total costs this month
    cursor.execute("""
        SELECT SUM(cost) FROM usage_costs
        WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
    """)
    month_cost = cursor.fetchone()[0] or 0.0
    
    # Revenue (from paid subscriptions)
    cursor.execute("""
        SELECT COUNT(*) as count, subscription_tier
        FROM users
        WHERE subscription_tier IN ('starter', 'pro', 'enterprise')
        GROUP BY subscription_tier
    """)
    
    revenue_data = cursor.fetchall()
    monthly_revenue = 0
    for count, tier in revenue_data:
        tier_prices = {'starter': 19, 'pro': 49, 'enterprise': 99}
        monthly_revenue += count * tier_prices.get(tier, 0)
    
    # Model usage breakdown
    cursor.execute("""
        SELECT model, COUNT(*) as count, SUM(cost) as total_cost
        FROM usage_costs
        WHERE date(timestamp) = date('now')
        GROUP BY model
        ORDER BY total_cost DESC
    """)
    
    model_usage = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'today_cost': round(today_cost, 2),
        'month_cost': round(month_cost, 2),
        'monthly_revenue': monthly_revenue,
        'profit_margin': round(((monthly_revenue - month_cost) / monthly_revenue * 100), 1) if monthly_revenue > 0 else 0,
        'model_usage': [
            {'model': m[0], 'count': m[1], 'cost': round(m[2], 2)}
            for m in model_usage
        ]
    })

# ============================================
# RESET EXPENSIVE MODEL BLOCKS (Daily cron)
# ============================================

def reset_daily_blocks():
    """Reset expensive model blocks at start of new day"""
    conn = sqlite3.connect('ai_team.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE users
        SET expensive_models_blocked = 0,
            daily_cost = 0.0
        WHERE expensive_models_blocked = 1
    """)
    
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    print(f"✅ Reset {affected} users' expensive model blocks")
    return affected

# Call this in a scheduled task or at midnight
# You can use Render's cron jobs or a background scheduler

if __name__ == '__main__':
    setup_cost_tracking()
    print("✅ Cost tracking system ready!")
