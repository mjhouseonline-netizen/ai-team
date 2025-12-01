# 🚀 INTEGRATION GUIDE - FOR YOUR UPLOADED FILES

## ✅ **Ready to Integrate!**

I've reviewed your uploaded files. Here's exactly what to add and where.

---

## 📁 **FILES READY:**

1. ✅ **requirements.txt** - [Updated](computer:///mnt/user-data/outputs/requirements.txt) - Added google-generativeai
2. ✅ **routes/notion_routes.py** - [Complete file](computer:///mnt/user-data/outputs/routes/notion_routes.py) - Upload as-is
3. ⏳ **web_app_auth.py** - Add code sections below
4. ⏳ **dashboard.html** - Add code sections below

---

## 🔧 **STEP 1: Upload Files**

### **1a. Requirements** ✅
[Download updated requirements.txt](computer:///mnt/user-data/outputs/requirements.txt)

Upload to: `/requirements.txt`

### **1b. Notion Routes** ✅
[Download notion_routes.py](computer:///mnt/user-data/outputs/routes/notion_routes.py)

Upload to: `/routes/notion_routes.py`

Make sure routes/ directory exists!

---

## 🔧 **STEP 2: Update web_app_auth.py**

Open your `web_app_auth.py` and make these additions:

### **Addition 1: Import Google AI**

**Find line 22** (after `from openai import OpenAI`)

**Add:**
```python
import google.generativeai as genai
```

**Result:**
```python
from openai import OpenAI
import google.generativeai as genai  # NEW!
```

---

### **Addition 2: Multi-Model Configuration**

**Find line ~60-70** (after OPENAI configuration, before AGENT_PERSONALITIES)

**Add this entire section:**
```python
# ============================================
# GOOGLE AI / GEMINI CONFIGURATION  
# ============================================
try:
    google_api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if google_api_key:
        genai.configure(api_key=google_api_key)
        print("✅ Google AI (Gemini) initialized")
    else:
        print("⚠️  Google AI not configured - set GOOGLE_AI_API_KEY")
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
```

---

### **Addition 3: Conversation History Functions**

**Find your chat route** (search for `@app.route('/api/chat')`)

**BEFORE that route, add these helper functions:**

```python
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
```

---

### **Addition 4: Replace Chat Endpoint**

**Find your existing `@app.route('/api/chat')` function**

**Replace the ENTIRE function with this updated version:**

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
                pass  # Handle any date parsing issues
        
        # Check limit
        if daily_limit != -1 and daily_limit != 999999:
            if messages_today >= daily_limit:
                conn.close()
                return jsonify({'error': 'Daily message limit reached. Upgrade to continue!'}), 429
        
        # Get agent personality
        if agent not in AGENT_PERSONALITIES:
            conn.close()
            return jsonify({'error': 'Invalid agent'}), 400
        
        agent_info = AGENT_PERSONALITIES[agent]
        system_prompt = agent_info['system_prompt']
        
        # Get conversation history (last 20 messages for context)
        history = get_conversation_history(current_user.id, agent, limit=20)
        
        # Handle file attachments (simplified)
        if attached_file and 'filepath' in attached_file:
            filepath = attached_file['filepath']
            if os.path.exists(filepath):
                filename = attached_file.get('original_filename', 'file')
                # For text files, include content
                if filename.endswith(('.txt', '.md', '.csv', '.json', '.py', '.js', '.html', '.css')):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            file_content = f.read()[:10000]  # Limit to 10k chars
                        message = f"{message}\n\nFile: {filename}\nContent:\n{file_content}"
                    except:
                        pass
        
        # Route to selected model with conversation history
        ai_response = route_to_model(model_key, system_prompt, history, message)
        
        # Save to chat history
        saved_message = message
        if attached_file and 'original_filename' in attached_file:
            saved_message = f"📎 {attached_file['original_filename']}\n{message}"
        
        cursor.execute("""
            INSERT INTO chat_history (user_id, agent_name, message, response)
            VALUES (?, ?, ?, ?)
        """, (current_user.id, agent, saved_message, ai_response))
        
        # INCREMENT MESSAGE COUNTER (THE FIX!)
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
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
```

---

### **Addition 5: New API Endpoints**

**After your chat endpoint, add these new endpoints:**

```python
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
```

---

## 🎨 **STEP 3: Update dashboard.html**

Your dashboard.html is very long. Here are the key sections to add:

### **HTML Addition: Model Selector**

**Find the area around line 500-600** (near the header/stats area)

**Add this HTML:**
```html
<!-- Model Selector -->
<div style="margin: 20px auto; max-width: 800px; text-align: center;">
    <label for="modelSelect" style="color: #90EE90; font-weight: 600; margin-right: 10px; font-size: 1.1em;">
        🤖 AI Model:
    </label>
    <select id="modelSelect" class="model-select">
        <optgroup label="⚡ Claude (Anthropic)">
            <option value="claude-sonnet-4.5" selected>Sonnet 4.5 - Fast & Smart ($3/1M)</option>
            <option value="claude-opus-4">Opus 4 - Most Capable ($15/1M)</option>
            <option value="claude-haiku-4.5">Haiku 4.5 - Ultra Fast ($0.80/1M)</option>
        </optgroup>
        <optgroup label="🚀 GPT (OpenAI)">
            <option value="gpt-4o">GPT-4o - Latest Multimodal ($2.50/1M)</option>
            <option value="gpt-4-turbo">GPT-4 Turbo - Powerful ($10/1M)</option>
            <option value="gpt-4o-mini">GPT-4o Mini - Cheapest! ($0.15/1M)</option>
        </optgroup>
        <optgroup label="✨ Gemini (Google)">
            <option value="gemini-2.0-flash">Gemini 2.0 Flash - FREE Tier! 🎉</option>
            <option value="gemini-1.5-pro">Gemini 1.5 Pro - 2M Context ($1.25/1M)</option>
        </optgroup>
    </select>
</div>
```

### **CSS Addition: Model Selector Styling**

**In your `<style>` section, add:**
```css
.model-select {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
    border: 2px solid rgba(144, 238, 144, 0.3);
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 1em;
    min-width: 400px;
    cursor: pointer;
    transition: all 0.3s;
}

.model-select:hover {
    border-color: rgba(144, 238, 144, 0.6);
    background: rgba(255, 255, 255, 0.15);
}

.model-select optgroup {
    background: #1a4d2e;
    color: #FFD700;
    font-weight: bold;
}

.model-select option {
    background: #1a4d2e;
    color: #fff;
    padding: 10px;
}

.model-badge {
    display: inline-block;
    background: rgba(144, 238, 144, 0.2);
    color: #90EE90;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.85em;
    margin-left: 10px;
    border: 1px solid rgba(144, 238, 144, 0.4);
}

@media (max-width: 768px) {
    .model-select {
        min-width: 100%;
        font-size: 0.9em;
    }
}
```

### **JavaScript Update: sendMessage Function**

**Find your `sendMessage()` function**

**Update it to include the model selection:**

Find this line:
```javascript
let requestBody = {
    message: message || 'Please analyze this file',
    agent: currentAgent,
    file: uploadedFile
};
```

**Replace with:**
```javascript
// Get selected model
const selectedModel = document.getElementById('modelSelect').value;

let requestBody = {
    message: message || 'Please analyze this file',
    agent: currentAgent,
    model: selectedModel,  // NEW: Include selected model
    file: uploadedFile
};
```

**Also find where you add agent messages, and add model badge:**

Find:
```javascript
addMessage(data.response, 'agent', currentAgent);
```

**Replace with:**
```javascript
// Add model badge to response
const modelBadge = `<span class="model-badge">${getModelName(data.model_used || selectedModel)}</span>`;
addMessage(data.response + modelBadge, 'agent', currentAgent);
```

### **JavaScript Addition: Helper Functions**

**At the end of your JavaScript (before closing `</script>`), add:**

```javascript
// Get friendly model name
function getModelName(modelKey) {
    const models = {
        'claude-sonnet-4.5': 'Claude Sonnet 4.5',
        'claude-opus-4': 'Claude Opus 4',
        'claude-haiku-4.5': 'Claude Haiku 4.5',
        'gpt-4o': 'GPT-4o',
        'gpt-4-turbo': 'GPT-4 Turbo',
        'gpt-4o-mini': 'GPT-4o Mini',
        'gemini-2.0-flash': 'Gemini 2.0 Flash',
        'gemini-1.5-pro': 'Gemini 1.5 Pro'
    };
    return models[modelKey] || modelKey;
}

// Clear chat history
async function clearChat() {
    if (!confirm('Clear all chat history with ' + currentAgent + '?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/clear-chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify({agent: currentAgent})
        });
        
        const data = await response.json();
        
        if (data.success) {
            const container = document.getElementById('chatContainer');
            container.innerHTML = '<div class="welcome-message">Chat cleared! Start fresh.</div>';
            alert('Chat history cleared!');
        }
    } catch (error) {
        console.error('Error:', error);
    }
}
```

---

## ✅ **DEPLOYMENT CHECKLIST:**

- [ ] Upload updated `requirements.txt`
- [ ] Upload `routes/notion_routes.py`
- [ ] Update `web_app_auth.py` with 5 additions above
- [ ] Update `dashboard.html` with HTML/CSS/JS additions
- [ ] Add to Render environment:
  ```
  GOOGLE_AI_API_KEY=AIza...your_key
  ```
- [ ] Push to GitHub
- [ ] Wait for Render deploy
- [ ] Test!

---

## 🧪 **TESTING:**

1. **Conversation History:**
   - Send "Hi" to Luna
   - Send "What did I say?"
   - Luna should remember

2. **Model Selector:**
   - Choose "GPT-4o" from dropdown
   - Send message
   - Should work with GPT-4o

3. **Message Counter:**
   - Check count (e.g., 25/25)
   - Send message
   - Should decrease to 24/25

---

**All set! These additions will give you:**
- ✅ 8 AI models
- ✅ Conversation memory
- ✅ Fixed message counter
- ✅ Model selection UI
- ✅ Zapier (already working)
- ✅ Notion (restored)

**Ready to deploy!** 🚀
