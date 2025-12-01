"""
Notion OAuth Integration for AI Team
Handles Notion authentication and workspace access
"""

from flask import Blueprint, redirect, request, session, url_for, jsonify, render_template
import requests
import os
from functools import wraps

notion_bp = Blueprint('notion', __name__, url_prefix='/notion')

# Notion OAuth credentials
NOTION_CLIENT_ID = os.environ.get('NOTION_CLIENT_ID')
NOTION_CLIENT_SECRET = os.environ.get('NOTION_CLIENT_SECRET')
NOTION_REDIRECT_URI = os.environ.get('NOTION_REDIRECT_URI', 'https://ai-team.skillsoul.store/notion/callback')

def notion_required(f):
    """Decorator to require Notion authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'notion_access_token' not in session:
            return redirect(url_for('notion.connect'))
        return f(*args, **kwargs)
    return decorated_function

@notion_bp.route('/connect')
def connect():
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

@notion_bp.route('/callback')
def callback():
    """Handle Notion OAuth callback"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return f"Notion authentication failed: {error}", 400
    
    if not code:
        return "No authorization code received", 400
    
    # Exchange code for access token
    token_url = "https://api.notion.com/v1/oauth/token"
    
    auth = (NOTION_CLIENT_ID, NOTION_CLIENT_SECRET)
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': NOTION_REDIRECT_URI
    }
    
    response = requests.post(token_url, auth=auth, json=data)
    
    if response.status_code != 200:
        return f"Failed to get access token: {response.text}", 400
    
    token_data = response.json()
    
    # Store access token in session
    session['notion_access_token'] = token_data.get('access_token')
    session['notion_workspace_id'] = token_data.get('workspace_id')
    session['notion_workspace_name'] = token_data.get('workspace_name')
    session['notion_bot_id'] = token_data.get('bot_id')
    
    return redirect(url_for('settings'))

@notion_bp.route('/disconnect')
def disconnect():
    """Disconnect Notion integration"""
    session.pop('notion_access_token', None)
    session.pop('notion_workspace_id', None)
    session.pop('notion_workspace_name', None)
    session.pop('notion_bot_id', None)
    
    return redirect(url_for('settings'))

@notion_bp.route('/status')
def status():
    """Check Notion connection status"""
    connected = 'notion_access_token' in session
    
    if connected:
        return jsonify({
            'connected': True,
            'workspace_name': session.get('notion_workspace_name'),
            'workspace_id': session.get('notion_workspace_id')
        })
    else:
        return jsonify({'connected': False})

@notion_bp.route('/pages', methods=['GET'])
@notion_required
def list_pages():
    """List accessible Notion pages"""
    access_token = session.get('notion_access_token')
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Notion-Version': '2022-06-28'
    }
    
    # Search for pages
    search_url = 'https://api.notion.com/v1/search'
    data = {
        'filter': {
            'property': 'object',
            'value': 'page'
        }
    }
    
    response = requests.post(search_url, headers=headers, json=data)
    
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch pages'}), 500
    
    return jsonify(response.json())

@notion_bp.route('/create-page', methods=['POST'])
@notion_required
def create_page():
    """Create a new Notion page"""
    access_token = session.get('notion_access_token')
    data = request.json
    
    parent_id = data.get('parent_id')
    title = data.get('title', 'New Page from AI Team')
    content = data.get('content', '')
    
    if not parent_id:
        return jsonify({'error': 'parent_id required'}), 400
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
    
    # Build page data
    page_data = {
        'parent': {'page_id': parent_id},
        'properties': {
            'title': {
                'title': [
                    {
                        'text': {
                            'content': title
                        }
                    }
                ]
            }
        },
        'children': [
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [
                        {
                            'type': 'text',
                            'text': {
                                'content': content
                            }
                        }
                    ]
                }
            }
        ]
    }
    
    response = requests.post(
        'https://api.notion.com/v1/pages',
        headers=headers,
        json=page_data
    )
    
    if response.status_code != 200:
        return jsonify({'error': 'Failed to create page', 'details': response.text}), 500
    
    return jsonify(response.json())

@notion_bp.route('/append-content', methods=['POST'])
@notion_required
def append_content():
    """Append content to existing Notion page"""
    access_token = session.get('notion_access_token')
    data = request.json
    
    page_id = data.get('page_id')
    content = data.get('content', '')
    
    if not page_id:
        return jsonify({'error': 'page_id required'}), 400
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
    
    # Build block data
    block_data = {
        'children': [
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [
                        {
                            'type': 'text',
                            'text': {
                                'content': content
                            }
                        }
                    ]
                }
            }
        ]
    }
    
    response = requests.patch(
        f'https://api.notion.com/v1/blocks/{page_id}/children',
        headers=headers,
        json=block_data
    )
    
    if response.status_code != 200:
        return jsonify({'error': 'Failed to append content', 'details': response.text}), 500
    
    return jsonify(response.json())
