"""
AI Team Web Application
Simple web interface to chat with your AI team
"""

from flask import Flask, render_template, request, jsonify, session
import os
import secrets
from ai_team import AITeam

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Global team instance
team = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/init', methods=['POST'])
def init_team():
    """Initialize the AI team with API key"""
    global team
    data = request.json
    api_key = data.get('api_key')
    
    if not api_key:
        return jsonify({'error': 'API key required'}), 400
    
    try:
        team = AITeam(api_key=api_key)
        session['api_key'] = api_key
        
        agents = team.list_agents()
        return jsonify({
            'success': True,
            'agents': agents
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process a chat request"""
    global team
    
    if team is None:
        # Try to reinitialize from session
        api_key = session.get('api_key')
        if api_key:
            team = AITeam(api_key=api_key)
        else:
            return jsonify({'error': 'Team not initialized'}), 400
    
    data = request.json
    message = data.get('message')
    agent = data.get('agent')  # Optional specific agent
    project_id = data.get('project_id')  # Optional
    
    if not message:
        return jsonify({'error': 'Message required'}), 400
    
    try:
        result = team.process_request(
            message,
            specific_agent=agent if agent and agent != 'auto' else None,
            project_id=project_id
        )
        
        return jsonify({
            'success': True,
            'responses': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/context', methods=['POST'])
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
        team.set_context(key, value, "User")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/context', methods=['GET'])
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

if __name__ == '__main__':
    print("\n🚀 Starting AI Team Web Interface...")
    print("📱 Opening in your browser...")
    print("\n⚠️  To stop: Press Ctrl+C in this window\n")
    
    # Try to open browser automatically
    import webbrowser
    import threading
    
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open('http://127.0.0.1:5000')
    
    threading.Thread(target=open_browser).start()
    
    app.run(debug=False, host='127.0.0.1', port=5000)
