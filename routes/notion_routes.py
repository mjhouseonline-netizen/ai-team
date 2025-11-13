# notion_routes.py
# Notion OAuth integration routes - SQLite version

from flask import Blueprint, request, redirect, url_for, jsonify, session
from flask_login import login_required, current_user
import requests
import os
import sqlite3
from datetime import datetime

notion_bp = Blueprint('notion', __name__, url_prefix='/api/integrations/notion')

# Notion OAuth credentials
NOTION_CLIENT_ID = os.environ.get('NOTION_CLIENT_ID', '2a9d872b-594c-80ad-8daf-00377201a165')
NOTION_CLIENT_SECRET = os.environ.get('NOTION_CLIENT_SECRET', 'secret_czBFLUvsAUiqfbhlJXR5jNbLois0GNVjYFZqA8T0DiM')
NOTION_REDIRECT_URI = os.environ.get('NOTION_REDIRECT_URI', 'https://ai-team-q84h.onrender.com/api/integrations/notion/callback')

NOTION_OAUTH_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"

def get_db_connection():
    """Get connection to users database"""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

@notion_bp.route('/connect')
@login_required
def connect():
    """Initiate Notion OAuth flow"""
    # Store user ID in session to retrieve after callback
    session['oauth_user_id'] = current_user.id
    
    # Build authorization URL
    auth_url = (
        f"{NOTION_OAUTH_URL}"
        f"?client_id={NOTION_CLIENT_ID}"
        f"&redirect_uri={NOTION_REDIRECT_URI}"
        f"&response_type=code"
        f"&owner=user"
    )
    
    return redirect(auth_url)

@notion_bp.route('/callback')
def callback():
    """Handle Notion OAuth callback"""
    # Get authorization code from query params
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return redirect('/settings?notion_error=' + error)
    
    if not code:
        return redirect('/settings?notion_error=no_code')
    
    # Get user ID from session
    user_id = session.get('oauth_user_id')
    if not user_id:
        return redirect('/settings?notion_error=session_expired')
    
    try:
        # Exchange code for access token
        token_response = requests.post(
            NOTION_TOKEN_URL,
            auth=(NOTION_CLIENT_ID, NOTION_CLIENT_SECRET),
            json={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': NOTION_REDIRECT_URI
            },
            headers={
                'Content-Type': 'application/json'
            }
        )
        
        if token_response.status_code != 200:
            print(f"Notion token error: {token_response.text}")
            return redirect('/settings?notion_error=token_exchange_failed')
        
        token_data = token_response.json()
        
        # Extract token and workspace info
        access_token = token_data.get('access_token')
        workspace_id = token_data.get('workspace_id')
        workspace_name = token_data.get('workspace_name')
        workspace_icon = token_data.get('workspace_icon')
        bot_id = token_data.get('bot_id')
        
        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user already has integration
        cursor.execute('SELECT id FROM notion_integrations WHERE user_id = ?', (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            cursor.execute('''
                UPDATE notion_integrations 
                SET access_token = ?, 
                    workspace_id = ?, 
                    workspace_name = ?, 
                    workspace_icon = ?, 
                    bot_id = ?, 
                    connected_at = ?, 
                    is_active = 1
                WHERE user_id = ?
            ''', (access_token, workspace_id, workspace_name, workspace_icon, bot_id, 
                  datetime.utcnow(), user_id))
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO notion_integrations 
                (user_id, access_token, workspace_id, workspace_name, workspace_icon, bot_id, connected_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', (user_id, access_token, workspace_id, workspace_name, workspace_icon, bot_id, datetime.utcnow()))
        
        conn.commit()
        conn.close()
        
        # Clear session
        session.pop('oauth_user_id', None)
        
        # Redirect to settings with success message
        return redirect('/settings?notion_success=true')
        
    except Exception as e:
        print(f"Notion OAuth error: {str(e)}")
        return redirect('/settings?notion_error=' + str(e))

@notion_bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect():
    """Disconnect Notion integration"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE notion_integrations 
            SET is_active = 0 
            WHERE user_id = ?
        ''', (current_user.id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Notion disconnected successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@notion_bp.route('/status')
@login_required
def status():
    """Get Notion connection status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT workspace_name, workspace_icon, connected_at, last_synced, is_active
            FROM notion_integrations 
            WHERE user_id = ? AND is_active = 1
        ''', (current_user.id,))
        
        integration = cursor.fetchone()
        conn.close()
        
        if integration:
            return jsonify({
                'connected': True,
                'integration': {
                    'workspace_name': integration['workspace_name'],
                    'workspace_icon': integration['workspace_icon'],
                    'connected_at': integration['connected_at'],
                    'last_synced': integration['last_synced'],
                    'is_active': bool(integration['is_active'])
                }
            })
        else:
            return jsonify({'connected': False})
    
    except Exception as e:
        print(f"Error checking Notion status: {e}")
        return jsonify({'connected': False, 'error': str(e)})
