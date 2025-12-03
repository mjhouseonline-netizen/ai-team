"""
Notion OAuth Integration Routes
Handles OAuth flow and Notion API interactions
"""

from flask import Blueprint, request, redirect, url_for, jsonify, session
from flask_login import login_required, current_user
import requests
import os
import sqlite3
import base64

notion_bp = Blueprint('notion', __name__)

# Notion OAuth Configuration
NOTION_CLIENT_ID = os.environ.get('NOTION_CLIENT_ID')
NOTION_CLIENT_SECRET = os.environ.get('NOTION_CLIENT_SECRET')
NOTION_REDIRECT_URI = os.environ.get('NOTION_REDIRECT_URI', 'https://ai-team.skillsoul.store/notion-callback')

DB_PATH = 'users.db'

@notion_bp.route('/notion/auth')
@login_required
def notion_auth():
    """Initiate Notion OAuth flow"""
    if not NOTION_CLIENT_ID:
        return jsonify({'error': 'Notion integration not configured'}), 500
    
    # Build authorization URL
    auth_url = (
        f"https://api.notion.com/v1/oauth/authorize?"
        f"client_id={NOTION_CLIENT_ID}&"
        f"response_type=code&"
        f"owner=user&"
        f"redirect_uri={NOTION_REDIRECT_URI}"
    )
    
    return redirect(auth_url)


@notion_bp.route('/notion-callback')
@login_required
def notion_callback():
    """Handle Notion OAuth callback"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return f"""
        <html>
        <head>
            <title>Notion Connection Failed</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #1a5f3f 0%, #2d8659 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 16px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                    text-align: center;
                    max-width: 400px;
                }}
                h1 {{ color: #c33; margin-bottom: 20px; }}
                p {{ color: #666; line-height: 1.6; margin-bottom: 20px; }}
                a {{
                    display: inline-block;
                    background: #10a37f;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: 600;
                }}
                a:hover {{ background: #0d8c6f; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>❌ Connection Failed</h1>
                <p>Error: {error}</p>
                <p>Please try again or contact support.</p>
                <a href="/settings">Back to Settings</a>
            </div>
        </body>
        </html>
        """
    
    if not code:
        return """
        <html>
        <head>
            <title>Notion Connection Failed</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #1a5f3f 0%, #2d8659 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 16px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                    text-align: center;
                    max-width: 400px;
                }}
                h1 {{ color: #c33; margin-bottom: 20px; }}
                p {{ color: #666; line-height: 1.6; margin-bottom: 20px; }}
                a {{
                    display: inline-block;
                    background: #10a37f;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: 600;
                }}
                a:hover {{ background: #0d8c6f; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>❌ No Authorization Code</h1>
                <p>The authorization code was not received from Notion.</p>
                <a href="/settings">Back to Settings</a>
            </div>
        </body>
        </html>
        """
    
    # Exchange code for access token using Basic Auth
    try:
        # Create Basic Auth header
        credentials = f"{NOTION_CLIENT_ID}:{NOTION_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        token_response = requests.post(
            'https://api.notion.com/v1/oauth/token',
            headers={
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json',
                'Notion-Version': '2022-06-28'
            },
            json={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': NOTION_REDIRECT_URI
            }
        )
        
        if token_response.status_code != 200:
            error_data = token_response.json()
            return f"""
            <html>
            <head>
                <title>Notion Connection Failed</title>
                <style>
                    body {{ 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #1a5f3f 0%, #2d8659 100%);
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 16px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                        text-align: center;
                        max-width: 400px;
                    }}
                    h1 {{ color: #c33; margin-bottom: 20px; }}
                    p {{ color: #666; line-height: 1.6; margin-bottom: 20px; }}
                    .error {{ background: #fee; padding: 12px; border-radius: 8px; margin: 20px 0; font-size: 14px; color: #c33; }}
                    a {{
                        display: inline-block;
                        background: #10a37f;
                        color: white;
                        padding: 12px 24px;
                        border-radius: 8px;
                        text-decoration: none;
                        font-weight: 600;
                    }}
                    a:hover {{ background: #0d8c6f; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>❌ Token Exchange Failed</h1>
                    <p>Could not exchange authorization code for access token.</p>
                    <div class="error">Error: {error_data.get('error', 'Unknown error')}</div>
                    <a href="/settings">Back to Settings</a>
                </div>
            </body>
            </html>
            """
        
        token_data = token_response.json()
        access_token = token_data.get('access_token')
        workspace_id = token_data.get('workspace_id')
        workspace_name = token_data.get('workspace_name')
        
        # Store token in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create integrations table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS integrations (
                user_id INTEGER,
                service TEXT,
                access_token TEXT,
                workspace_id TEXT,
                workspace_name TEXT,
                PRIMARY KEY (user_id, service)
            )
        ''')
        
        # Store or update Notion connection
        cursor.execute('''
            INSERT OR REPLACE INTO integrations (user_id, service, access_token, workspace_id, workspace_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (current_user.id, 'notion', access_token, workspace_id, workspace_name))
        
        conn.commit()
        conn.close()
        
        # Success page
        return f"""
        <html>
        <head>
            <title>Notion Connected!</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #1a5f3f 0%, #2d8659 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 16px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                    text-align: center;
                    max-width: 400px;
                }}
                h1 {{ color: #10a37f; margin-bottom: 20px; }}
                p {{ color: #666; line-height: 1.6; margin-bottom: 20px; }}
                .workspace {{ 
                    background: #e6f7f3; 
                    padding: 12px; 
                    border-radius: 8px; 
                    margin: 20px 0;
                    font-weight: 600;
                    color: #10a37f;
                }}
                a {{
                    display: inline-block;
                    background: #10a37f;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: 600;
                    margin-top: 10px;
                }}
                a:hover {{ background: #0d8c6f; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ Notion Connected!</h1>
                <p>Your Notion workspace has been successfully connected to AI Team.</p>
                <div class="workspace">📝 {workspace_name or 'Workspace'}</div>
                <p>You can now use AI agents to access your Notion content.</p>
                <a href="/dashboard">Back to Dashboard</a>
                <a href="/settings" style="background: transparent; color: #10a37f; border: 2px solid #10a37f;">Settings</a>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <html>
        <head>
            <title>Connection Error</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #1a5f3f 0%, #2d8659 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 16px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                    text-align: center;
                    max-width: 400px;
                }}
                h1 {{ color: #c33; margin-bottom: 20px; }}
                p {{ color: #666; line-height: 1.6; margin-bottom: 20px; }}
                .error {{ background: #fee; padding: 12px; border-radius: 8px; margin: 20px 0; font-size: 14px; color: #c33; }}
                a {{
                    display: inline-block;
                    background: #10a37f;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: 600;
                }}
                a:hover {{ background: #0d8c6f; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>❌ Connection Error</h1>
                <p>An unexpected error occurred while connecting to Notion.</p>
                <div class="error">{str(e)}</div>
                <p>Please try again or contact support.</p>
                <a href="/settings">Back to Settings</a>
            </div>
        </body>
        </html>
        """


@notion_bp.route('/api/notion/status')
@login_required
def notion_status():
    """Check if user has Notion connected"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT workspace_name FROM integrations 
            WHERE user_id = ? AND service = 'notion'
        ''', (current_user.id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                'connected': True,
                'workspace': result[0]
            })
        else:
            return jsonify({'connected': False})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@notion_bp.route('/api/notion/disconnect', methods=['POST'])
@login_required
def notion_disconnect():
    """Disconnect Notion integration"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM integrations 
            WHERE user_id = ? AND service = 'notion'
        ''', (current_user.id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Notion disconnected'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
