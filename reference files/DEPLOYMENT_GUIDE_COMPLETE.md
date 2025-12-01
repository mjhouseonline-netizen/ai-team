# 🚀 COMPLETE SYSTEM UPGRADE - DEPLOYMENT GUIDE

## 📦 **What's Being Deployed:**

### **1. Notion Integration** ✅
- File: `routes/notion_routes.py`
- OAuth authentication with Notion
- Create/edit Notion pages from AI Team
- Full workspace access

### **2. Multi-Model AI Backend** ✅
- 8 AI Models across 3 providers
- Full conversation history (chat memory)
- Fixed message counter
- Model-specific optimizations

### **3. Modern Dashboard UI** ✅  
- ChatGPT-style interface
- Model selector dropdown
- Preview modal for images
- Mobile responsive
- Conversation threading

### **4. Enhanced Zapier** ✅
- Improved webhooks (already built)
- Better event tracking
- Make.com integration (already built)

---

## 🔑 **Required Environment Variables:**

### **Add to Render:**

```bash
# Google AI (NEW - you have this key!)
GOOGLE_AI_API_KEY=AIza...your_gemini_key

# Notion (Optional - if you want Notion integration)
NOTION_CLIENT_ID=your_notion_client_id
NOTION_CLIENT_SECRET=your_notion_client_secret
NOTION_REDIRECT_URI=https://ai-team.skillsoul.store/notion/callback

# Existing (already configured)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
STRIPE_SECRET_KEY=sk_live_...
# ... etc
```

---

## 📁 **File Structure:**

```
your-project/
├── web_app_auth.py (UPDATED - main backend)
├── templates/
│   ├── dashboard.html (UPDATED - modern UI)
│   ├── automations.html (existing)
│   ├── pricing.html (existing)
│   └── ... (all other existing templates)
└── routes/
    └── notion_routes.py (NEW)
```

---

## 🚀 **Deployment Steps:**

### **Step 1: Create Routes Directory**

In your project root:
```bash
mkdir -p routes
```

### **Step 2: Add Files**

Upload these 3 files:
1. `routes/notion_routes.py` (created above)
2. `web_app_auth.py` (I'm creating now - LARGE FILE!)
3. `dashboard.html` (I'm creating now - modern UI)

### **Step 3: Add Google AI Key to Render**

1. Render Dashboard → ai-team → Environment
2. Add variable:
   ```
   GOOGLE_AI_API_KEY = AIza...your_key_here
   ```
3. **Don't save yet** - wait for all files

### **Step 4: Install Google AI Package**

Add to `requirements.txt`:
```
google-generativeai>=0.3.0
```

---

## ⚙️ **Key Changes in Backend:**

### **New Features:**

**1. Multi-Model System:**
```python
MODELS = {
    # Claude
    'claude-sonnet-4.5': {...},
    'claude-opus-4': {...},
    'claude-haiku-4.5': {...},
    
    # GPT
    'gpt-4o': {...},
    'gpt-4-turbo': {...},
    'gpt-4o-mini': {...},
    
    # Gemini
    'gemini-2.0-flash': {...},
    'gemini-1.5-pro': {...}
}
```

**2. Conversation History:**
```python
def get_conversation_history(user_id, agent, limit=20):
    """Get recent messages for context"""
    # Returns last 20 messages
    # Formats for each AI provider
```

**3. Fixed Message Counter:**
```python
# After successful chat:
cursor.execute("""
    UPDATE users
    SET messages_today = messages_today + 1
    WHERE id = ?
""", (user_id,))
```

**4. Model Routing:**
```python
def route_to_ai(model_key, system, history):
    if provider == 'anthropic':
        return call_claude(...)
    elif provider == 'openai':
        return call_gpt(...)
    elif provider == 'google':
        return call_gemini(...)
```

---

## 🎨 **Key Changes in Frontend:**

### **New UI Elements:**

**1. Model Selector:**
```html
<select id="modelSelector" class="model-select">
    <optgroup label="Claude">
        <option value="claude-sonnet-4.5" selected>Sonnet 4.5 (Fast)</option>
        <option value="claude-opus-4">Opus 4 (Best)</option>
        <option value="claude-haiku-4.5">Haiku 4.5 (Cheap)</option>
    </optgroup>
    <optgroup label="GPT">
        <option value="gpt-4o">GPT-4o (Latest)</option>
        <option value="gpt-4-turbo">GPT-4 Turbo</option>
        <option value="gpt-4o-mini">GPT-4o Mini (Cheapest)</option>
    </optgroup>
    <optgroup label="Gemini">
        <option value="gemini-2.0-flash">Gemini 2.0 (FREE)</option>
        <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
    </optgroup>
</select>
```

**2. Preview Modal:**
```html
<div id="previewModal" class="modal">
    <div class="modal-content">
        <span class="close">&times;</span>
        <img id="previewImage" />
    </div>
</div>
```

**3. ChatGPT-Style Messages:**
```css
.chat-message {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}

.message-user {
    background: #f7f7f8;
    border-radius: 12px;
}

.message-agent {
    background: white;
    border-left: 3px solid #10a37f;
}
```

---

## ✅ **Testing After Deployment:**

### **1. Conversation History:**
```
1. Send: "Hello Luna"
2. Luna responds
3. Send: "What did I just say?"
4. Luna should remember: "You said 'Hello Luna'"
```

**Expected:** ✅ Agent remembers conversation

### **2. Message Counter:**
```
1. Check counter: "25/25"
2. Send message
3. Counter should show: "24/25"
4. Refresh page
5. Still shows: "24/25"
```

**Expected:** ✅ Counter decreases and persists

### **3. Multi-Model:**
```
1. Select "GPT-4o" from dropdown
2. Send message
3. Get response from GPT-4o
4. Switch to "Gemini 2.0"
5. Send message
6. Get response from Gemini
```

**Expected:** ✅ All models work

### **4. Mobile:**
```
1. Open on phone
2. Chat interface looks good
3. Can select models
4. Can send messages
5. Messages display properly
```

**Expected:** ✅ Works on mobile

### **5. Preview Modal:**
```
1. Generate image
2. Click on image
3. Modal opens with large view
4. Can close modal
```

**Expected:** ✅ Modal works

---

## 🐛 **Troubleshooting:**

### **Issue: "Google AI not configured"**
**Fix:** Add GOOGLE_AI_API_KEY to Render environment variables

### **Issue: "Conversation not remembered"**
**Fix:** Check database has chat_history with messages

### **Issue: "Message counter stuck at 25"**
**Fix:** Clear browser cache, check database users table

### **Issue: "Model selector not visible"**
**Fix:** Hard refresh (Ctrl+Shift+R), clear cache

### **Issue: "Notion not working"**
**Fix:** Add NOTION_CLIENT_ID and NOTION_CLIENT_SECRET env vars

---

## 💰 **Cost Management:**

### **Set Default Models:**

**Free Users:**
- Default: GPT-4o Mini ($0.15/1M tokens)
- Alternative: Gemini 2.0 Flash (FREE)

**Paid Users:**
- Default: Claude Sonnet 4.5 ($3/1M tokens)
- Premium: Claude Opus 4 ($15/1M tokens)

### **Smart Routing:**
```python
# In backend, auto-select based on query:
if len(message) < 50:
    model = 'gpt-4o-mini'  # Simple questions
elif 'complex' or 'detailed':
    model = 'claude-opus-4'  # Complex tasks
else:
    model = 'claude-sonnet-4.5'  # Default
```

---

## 📊 **Database Changes:**

### **chat_history table - NEW COLUMN:**
```sql
ALTER TABLE chat_history ADD COLUMN model_used TEXT DEFAULT 'claude-sonnet-4.5';
```

This tracks which model was used for each message.

### **Migration (automatic):**
Backend will auto-add column if missing.

---

## 🎉 **Final Checklist:**

**Before Deploying:**
- [ ] Have Google AI API key
- [ ] Have Notion credentials (optional)
- [ ] Created routes/ directory
- [ ] Added google-generativeai to requirements.txt

**Files to Upload:**
- [ ] routes/notion_routes.py
- [ ] web_app_auth.py (updated)
- [ ] templates/dashboard.html (updated)

**After Deploying:**
- [ ] Add GOOGLE_AI_API_KEY to Render
- [ ] Add Notion vars (if using)
- [ ] Test conversation history
- [ ] Test message counter
- [ ] Test all 8 models
- [ ] Test on mobile
- [ ] Test preview modal

---

## 🚀 **Ready to Deploy:**

I'm now creating the actual files...

**Creating:**
1. ✅ routes/notion_routes.py (DONE)
2. ⏳ web_app_auth.py (BUILDING NOW - this is huge!)
3. ⏳ dashboard.html (BUILDING NEXT)

**Estimated time:** 10-15 more minutes for the large files.

---

Generated: November 29, 2025
Multi-Model System - Complete Deployment Guide
