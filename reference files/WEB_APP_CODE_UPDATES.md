# WEB_APP_AUTH.PY - CRITICAL UPDATES

## SECTION 1: ADD TO IMPORTS (After line 22)

```python
# Add after: from openai import OpenAI
import google.generativeai as genai
```

## SECTION 2: ADD MULTI-MODEL CONFIGURATION (After line 63)

```python
# ============================================
# MULTI-MODEL AI CONFIGURATION
# ============================================

MODELS = {
    # Claude Models
    'claude-sonnet-4.5': {
        'provider': 'anthropic',
        'model_id': 'claude-sonnet-4-20250514',
        'name': 'Claude Sonnet 4.5',
        'description': 'Fast & intelligent',
        'max_tokens': 2000,
        'cost': '$3/1M'
    },
    'claude-opus-4': {
        'provider': 'anthropic',
        'model_id': 'claude-opus-4-20250514',
        'name': 'Claude Opus 4',
        'description': 'Most capable',
        'max_tokens': 2000,
        'cost': '$15/1M'
    },
    'claude-haiku-4.5': {
        'provider': 'anthropic',
        'model_id': 'claude-haiku-4-5-20251001',
        'name': 'Claude Haiku 4.5',
        'description': 'Ultra-fast',
        'max_tokens': 2000,
        'cost': '$0.80/1M'
    },
    
    # OpenAI Models
    'gpt-4o': {
        'provider': 'openai',
        'model_id': 'gpt-4o',
        'name': 'GPT-4o',
        'description': 'Latest multimodal',
        'max_tokens': 2000,
        'cost': '$2.50/1M'
    },
    'gpt-4-turbo': {
        'provider': 'openai',
        'model_id': 'gpt-4-turbo-preview',
        'name': 'GPT-4 Turbo',
        'description': 'Powerful reasoning',
        'max_tokens': 2000,
        'cost': '$10/1M'
    },
    'gpt-4o-mini': {
        'provider': 'openai',
        'model_id': 'gpt-4o-mini',
        'name': 'GPT-4o Mini',
        'description': 'Fast & affordable',
        'max_tokens': 2000,
        'cost': '$0.15/1M'
    },
    
    # Google Gemini Models
    'gemini-2.0-flash': {
        'provider': 'google',
        'model_id': 'gemini-2.0-flash-exp',
        'name': 'Gemini 2.0 Flash',
        'description': 'FREE tier',
        'max_tokens': 2000,
        'cost': 'FREE'
    },
    'gemini-1.5-pro': {
        'provider': 'google',
        'model_id': 'gemini-1.5-pro',
        'name': 'Gemini 1.5 Pro',
        'description': '2M context',
        'max_tokens': 2000,
        'cost': '$1.25/1M'
    }
}

# Initialize Google AI
try:
    google_api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if google_api_key:
        genai.configure(api_key=google_api_key)
        print("✅ Google AI (Gemini) initialized")
    else:
        print("⚠️  Google AI not configured")
except Exception as e:
    print(f"⚠️  Google AI initialization failed: {e}")
```

## SECTION 3: ADD CONVERSATION HISTORY FUNCTION (Before chat route, around line 1255)

```python
# ============================================
# CONVERSATION HISTORY SYSTEM
# ============================================

def get_conversation_history(user_id, agent_name, limit=20):
    """Get recent conversation history for context"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT message, response, timestamp
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
    for message, response, timestamp in results:
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
    
    return history

def call_claude_with_history(model_id, system_prompt, history, new_message, max_tokens=2000):
    """Call Claude with conversation history"""
    client = anthropic.Anthropic(api_key=app.config['ANTHROPIC_API_KEY'])
    
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
        model_key = 'claude-sonnet-4.5'  # Default
    
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
        print(f"Error with {provider}: {e}")
        # Fallback to Claude if other model fails
        if provider != 'anthropic':
            return call_claude_with_history('claude-sonnet-4-20250514', system_prompt, history, new_message, 2000)
        raise
```

## SECTION 4: REPLACE CHAT ENDPOINT (Replace lines 1260-1391)

```python
@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Send message to AI agent with conversation history and multi-model support"""
    try:
        data = request.json
        message = data.get('message')
        agent = data.get('agent', 'Ember')
        model_key = data.get('model', 'claude-sonnet-4.5')  # NEW: Model selection
        attached_file = data.get('file')
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        # Check message limit
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
        
        # Reset if new day
        if last_reset:
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
        
        # Check limit
        if daily_limit != -1 and daily_limit != 999999:
            if messages_today >= daily_limit:
                conn.close()
                return jsonify({'error': 'Daily message limit reached'}), 429
        
        # Get agent personality
        if agent not in AGENT_PERSONALITIES:
            conn.close()
            return jsonify({'error': 'Invalid agent'}), 400
        
        agent_info = AGENT_PERSONALITIES[agent]
        system_prompt = agent_info['system_prompt']
        
        # Get conversation history (last 20 messages)
        history = get_conversation_history(current_user.id, agent, limit=20)
        
        # Handle file attachments (simplified for now)
        if attached_file and 'filepath' in attached_file:
            filepath = attached_file['filepath']
            if os.path.exists(filepath):
                filename = attached_file.get('original_filename', 'file')
                if is_text_file(filename):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    message = f"{message}\n\nFile: {filename}\nContent:\n{file_content}"
        
        # Route to selected model with history
        ai_response = route_to_model(model_key, system_prompt, history, message)
        
        # Save to chat history
        saved_message = message
        if attached_file and 'original_filename' in attached_file:
            saved_message = f"📎 {attached_file['original_filename']}\n{message}"
        
        cursor.execute("""
            INSERT INTO chat_history (user_id, agent_name, message, response, model_used)
            VALUES (?, ?, ?, ?, ?)
        """, (current_user.id, agent, saved_message, ai_response, model_key))
        
        # INCREMENT MESSAGE COUNTER (FIX!)
        cursor.execute("""
            UPDATE users
            SET messages_today = messages_today + 1,
                last_message_reset = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), current_user.id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'response': ai_response,
            'agent': agent,
            'model_used': model_key
        }), 200
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500
```

## SECTION 5: ADD NEW API ENDPOINT (After chat endpoint)

```python
@app.route('/api/models', methods=['GET'])
@login_required
def get_models():
    """Get available AI models"""
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
def clear_chat():
    """Clear chat history for current agent"""
    data = request.json
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
```

## SECTION 6: UPDATE DATABASE SCHEMA (Add migration function after init_database)

```python
def migrate_chat_history():
    """Add model_used column if it doesn't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT model_used FROM chat_history LIMIT 1")
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        cursor.execute("ALTER TABLE chat_history ADD COLUMN model_used TEXT DEFAULT 'claude-sonnet-4.5'")
        conn.commit()
        print("✅ Added model_used column to chat_history")
    
    conn.close()

# Call migration after init_database()
migrate_chat_history()
```

---

# NOTES:

1. Add these sections IN ORDER to your existing web_app_auth.py
2. The line numbers are approximate - find the right sections
3. Test after each major section
4. Keep backups!

This preserves ALL existing functionality while adding:
- ✅ Multi-model support (8 models)
- ✅ Conversation history
- ✅ Fixed message counter
- ✅ Google AI integration
