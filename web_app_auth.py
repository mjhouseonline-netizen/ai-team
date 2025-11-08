"""
AI Team Web Application with Authentication
Includes user signup, login, and session management
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import os
import secrets
import sqlite3
from ai_team import AITeam
from auth import setup_login_manager, AuthManager
from integrations import integrations_manager

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Setup authentication
auth_manager = setup_login_manager(app)

# Run database migration on startup
print("🔧 Running database migration...")
try:
    import migrate_db
    migrate_db.migrate_database()
    print("✅ Database migration complete!")
except Exception as e:
    print(f"⚠️ Migration error: {e}")

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
    
    # Check message limit
    can_send, limit_message = auth_manager.check_message_limit(current_user.id)
    if not can_send:
        subscription = auth_manager.get_user_subscription(current_user.id)
        return jsonify({
            'error': 'limit_reached',
            'message': limit_message,
            'tier': subscription['tier'],
            'messages_today': subscription['messages_today']
        }), 429
    
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
        
        # Increment message count
        auth_manager.increment_message_count(current_user.id)
        
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

@app.route('/api/subscription', methods=['GET'])
@login_required
def get_subscription():
    """Get user's subscription details"""
    subscription = auth_manager.get_user_subscription(current_user.id)
    
    # Calculate limits
    limits = {
        'free': 10,
        'pro': 100,
        'business': 999999
    }
    
    return jsonify({
        'success': True,
        'tier': subscription['tier'],
        'messages_today': subscription['messages_today'],
        'limit': limits[subscription['tier']],
        'percentage': (subscription['messages_today'] / limits[subscription['tier']]) * 100
    })

@app.route('/pricing')
def pricing():
    """Pricing page"""
    return render_template('pricing.html')

@app.route('/api/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create Stripe checkout session"""
    try:
        data = request.json
        tier = data.get('tier', 'pro')
        
        # Stripe prices (you'll need to set these up in Stripe Dashboard)
        prices = {
            'pro': os.environ.get('STRIPE_PRO_PRICE_ID', 'price_pro'),
            'business': os.environ.get('STRIPE_BUSINESS_PRICE_ID', 'price_business')
        }
        
        import stripe
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[{
                'price': prices[tier],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('dashboard', _external=True) + '?upgraded=true',
            cancel_url=url_for('pricing', _external=True),
            metadata={
                'user_id': current_user.id,
                'tier': tier
            }
        )
        
        return jsonify({'checkout_url': checkout_session.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    import stripe
    
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        # Handle successful subscription
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session['metadata']['user_id']
            tier = session['metadata']['tier']
            
            # Update user's subscription
            auth_manager.update_subscription(
                user_id=user_id,
                tier=tier,
                stripe_customer_id=session['customer'],
                stripe_subscription_id=session['subscription']
            )
        
        # Handle subscription cancellation
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            # Find user by stripe_subscription_id and downgrade to free
            conn = sqlite3.connect(auth_manager.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET subscription_tier = 'free' WHERE stripe_subscription_id = ?",
                (subscription['id'],)
            )
            conn.commit()
            conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
Integration Routes - Add these to web_app_auth.py
"""

from integrations import integrations_manager

# Import at top of file
# from integrations import integrations_manager

# Add these routes:

@app.route('/integrations')
@login_required
def integrations_page():
    """Integrations settings page"""
    return render_template('integrations.html', user=current_user)

@app.route('/api/integrations')
@login_required
def get_integrations():
    """Get all user integrations"""
    try:
        integrations = integrations_manager.get_all_integrations(current_user.id)
        return jsonify({
            'success': True,
            'integrations': integrations
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/save', methods=['POST'])
@login_required
def save_integration():
    """Save integration credentials"""
    try:
        data = request.json
        integration_type = data.get('integration_type')
        api_key = data.get('api_key')
        access_token = data.get('access_token')
        
        if not integration_type:
            return jsonify({
                'success': False,
                'error': 'Integration type required'
            }), 400
        
        success = integrations_manager.save_integration(
            user_id=current_user.id,
            integration_type=integration_type,
            api_key=api_key,
            access_token=access_token
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save integration'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/delete/<integration_type>', methods=['DELETE'])
@login_required
def delete_integration(integration_type):
    """Delete integration"""
    try:
        success = integrations_manager.delete_integration(
            user_id=current_user.id,
            integration_type=integration_type
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete integration'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/generate-image', methods=['POST'])
@login_required
def generate_image_api():
    """Generate image with DALL-E"""
    try:
        data = request.json
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Prompt required'
            }), 400
        
        image_url = integrations_manager.generate_image(
            user_id=current_user.id,
            prompt=prompt
        )
        
        if image_url:
            return jsonify({
                'success': True,
                'image_url': image_url
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate image. Make sure OpenAI is connected.'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/post-facebook', methods=['POST'])
@login_required
def post_facebook_api():
    """Post to Facebook"""
    try:
        data = request.json
        message = data.get('message')
        image_url = data.get('image_url')
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message required'
            }), 400
        
        post_id = integrations_manager.post_to_facebook(
            user_id=current_user.id,
            message=message,
            image_url=image_url
        )
        
        if post_id:
            return jsonify({
                'success': True,
                'post_id': post_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to post. Make sure Facebook is connected.'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/post-instagram', methods=['POST'])
@login_required
def post_instagram_api():
    """Post to Instagram"""
    try:
        data = request.json
        image_url = data.get('image_url')
        caption = data.get('caption')
        
        if not image_url or not caption:
            return jsonify({
                'success': False,
                'error': 'Image URL and caption required'
            }), 400
        
        post_id = integrations_manager.post_to_instagram(
            user_id=current_user.id,
            image_url=image_url,
            caption=caption
        )
        
        if post_id:
            return jsonify({
                'success': True,
                'post_id': post_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to post. Make sure Instagram is connected.'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/usage')
@login_required
def get_usage_stats():
    """Get integration usage stats"""
    try:
        stats = integrations_manager.get_usage_stats(current_user.id)
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("\n🚀 Starting AI Team Web Interface...")
    
    # Run database migration
    print("🔧 Checking database schema...")
    try:
        import migrate_db
        migrate_db.migrate_database()
    except Exception as e:
        print(f"⚠️ Migration warning: {e}")
    
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

from integrations import integrations_manager

# Import at top of file
# from integrations import integrations_manager

# Add these routes:

@app.route('/integrations')
@login_required
def integrations_page():
    """Integrations settings page"""
    return render_template('integrations.html', user=current_user)

@app.route('/api/integrations')
@login_required
def get_integrations():
    """Get all user integrations"""
    try:
        integrations = integrations_manager.get_all_integrations(current_user.id)
        return jsonify({
            'success': True,
            'integrations': integrations
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/save', methods=['POST'])
@login_required
def save_integration():
    """Save integration credentials"""
    try:
        data = request.json
        integration_type = data.get('integration_type')
        api_key = data.get('api_key')
        access_token = data.get('access_token')
        
        if not integration_type:
            return jsonify({
                'success': False,
                'error': 'Integration type required'
            }), 400
        
        success = integrations_manager.save_integration(
            user_id=current_user.id,
            integration_type=integration_type,
            api_key=api_key,
            access_token=access_token
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save integration'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/delete/<integration_type>', methods=['DELETE'])
@login_required
def delete_integration(integration_type):
    """Delete integration"""
    try:
        success = integrations_manager.delete_integration(
            user_id=current_user.id,
            integration_type=integration_type
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete integration'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/generate-image', methods=['POST'])
@login_required
def generate_image_api():
    """Generate image with DALL-E"""
    try:
        data = request.json
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Prompt required'
            }), 400
        
        image_url = integrations_manager.generate_image(
            user_id=current_user.id,
            prompt=prompt
        )
        
        if image_url:
            return jsonify({
                'success': True,
                'image_url': image_url
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate image. Make sure OpenAI is connected.'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/post-facebook', methods=['POST'])
@login_required
def post_facebook_api():
    """Post to Facebook"""
    try:
        data = request.json
        message = data.get('message')
        image_url = data.get('image_url')
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message required'
            }), 400
        
        post_id = integrations_manager.post_to_facebook(
            user_id=current_user.id,
            message=message,
            image_url=image_url
        )
        
        if post_id:
            return jsonify({
                'success': True,
                'post_id': post_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to post. Make sure Facebook is connected.'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/post-instagram', methods=['POST'])
@login_required
def post_instagram_api():
    """Post to Instagram"""
    try:
        data = request.json
        image_url = data.get('image_url')
        caption = data.get('caption')
        
        if not image_url or not caption:
            return jsonify({
                'success': False,
                'error': 'Image URL and caption required'
            }), 400
        
        post_id = integrations_manager.post_to_instagram(
            user_id=current_user.id,
            image_url=image_url,
            caption=caption
        )
        
        if post_id:
            return jsonify({
                'success': True,
                'post_id': post_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to post. Make sure Instagram is connected.'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/usage')
@login_required
def get_usage_stats():
    """Get integration usage stats"""
    try:
        stats = integrations_manager.get_usage_stats(current_user.id)
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

