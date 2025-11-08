# 🔌 COMPLETE INTEGRATIONS SYSTEM GUIDE

## 🎉 What You Just Got!

Your AI Team can now connect to:
- 🤖 **Claude AI** - Advanced reasoning & coding
- 💬 **ChatGPT** - OpenAI's conversational AI
- 🎨 **DALL-E** - AI image generation
- 📘 **Facebook** - Post updates & manage page
- 📸 **Instagram** - Post photos & engage

---

## 📥 FILES TO DOWNLOAD:

### 1. Core Integration Files:
- **[integrations.py](computer:///mnt/user-data/outputs/integrations.py)** - Integration backend
- **[integrations.html](computer:///mnt/user-data/outputs/integrations.html)** - Settings page
- **[integration_routes.py](computer:///mnt/user-data/outputs/integration_routes.py)** - API routes
- **[dashboard_simple.html](computer:///mnt/user-data/outputs/dashboard_simple.html)** - Updated dashboard

### 2. Requirements:
- **[requirements_additions.txt](computer:///mnt/user-data/outputs/requirements_additions.txt)** - New dependencies

---

## 🚀 INSTALLATION STEPS:

### Step 1: Download All Files

Download all 5 files listed above.

### Step 2: Place Files

```
Desktop\ai-team\
├── integrations.py              ← NEW file (root)
├── integration_routes.py        ← Reference file
├── requirements.txt             ← UPDATE this
│
└── templates\
    ├── dashboard.html           ← REPLACE with dashboard_simple.html
    └── integrations.html        ← NEW file
```

### Step 3: Update requirements.txt

Open `requirements.txt` and add these lines:
```
openai==1.54.0
requests==2.31.0
```

Your full requirements.txt should be:
```
Flask==3.0.0
Flask-Login==0.6.3
anthropic==0.40.0
gunicorn==21.2.0
werkzeug==3.0.1
openai==1.54.0
requests==2.31.0
```

### Step 4: Add Routes to web_app_auth.py

Open `web_app_auth.py` and:

1. **Add import at top:**
```python
from integrations import integrations_manager
```

2. **Copy ALL the routes from integration_routes.py**
   - Paste them before the `if __name__ == '__main__':` line
   - All the @app.route decorators

### Step 5: Test Locally

1. Close any running servers
2. Install new packages:
   ```bash
   pip install openai requests --break-system-packages
   ```
3. Run `START_BUSINESS_FIXED.bat`
4. Visit: `http://127.0.0.1:5000`
5. Login
6. Click **"🔌 Integrations"** button

---

## 🎯 HOW TO USE:

### 1. Connect Your Services

**Go to Integrations Page:**
- Click "🔌 Integrations" in dashboard header
- You'll see 4 cards: Claude, OpenAI, Facebook, Instagram

**Get API Keys:**

**Claude AI:**
1. Go to: https://console.anthropic.com
2. Create account
3. Generate API key
4. Paste in "Anthropic API Key" field
5. Click "Connect"

**OpenAI (ChatGPT + DALL-E):**
1. Go to: https://platform.openai.com
2. Create account
3. Add billing (pay-as-you-go)
4. Generate API key
5. Paste in "OpenAI API Key" field
6. Click "Connect"

**Facebook:**
1. Go to: https://developers.facebook.com
2. Create app
3. Get Page Access Token
4. Paste in "Page Access Token" field
5. Click "Connect"

**Instagram:**
1. Go to: https://developers.facebook.com
2. Set up Instagram Business Account
3. Get Instagram Access Token
4. Paste in "Instagram Access Token" field
5. Click "Connect"

---

### 2. Use Integrations in Dashboard

Once connected, your dashboard has new powers!

**Generate Images (DALL-E):**
1. Click "🎨 Generate Image" button
2. Describe what you want: "A tropical jungle with glowing fireflies"
3. Click "Generate"
4. Image appears in chat!
5. Option to post to social media

**Post to Social Media:**
1. Click "📱 Post to Social" button
2. Select platform (Facebook or Instagram)
3. Write your message
4. Add image URL (optional for Facebook, required for Instagram)
5. Click "Post"
6. Success! 🎉

**Use Different AI Models:**
Your agents can now use:
- Your Anthropic API for Claude responses
- Your OpenAI API for ChatGPT responses
- (We'll add agent-specific model selection next!)

---

## 💡 FEATURES:

### Image Generation:
- Generate any image with AI
- Use in your projects
- Post to social media
- Download & save

### Social Media:
- Post to Facebook
- Post to Instagram
- Add images to posts
- Automated posting from AI

### Multiple AI Models:
- Claude for advanced reasoning
- ChatGPT for conversation
- Both available for your agents

---

## 🔒 SECURITY:

**Your API keys are:**
- ✅ Stored in your private database
- ✅ Never shared
- ✅ Encrypted in storage
- ✅ Only accessible to you
- ✅ Can be deleted anytime

**Rate Limits:**
- Tracked per integration
- Logged for monitoring
- Cost tracking included

---

## 📊 USAGE TRACKING:

The system tracks:
- How many times each integration used
- Tokens consumed (for AI)
- Costs (when applicable)
- Timestamps

View stats at: `/api/integrations/usage`

---

## 🎨 PRICING NOTES:

**Claude AI:**
- Pay per token to Anthropic
- ~$3 per million input tokens
- ~$15 per million output tokens

**OpenAI:**
- **ChatGPT (GPT-4):** ~$30 per million input tokens
- **DALL-E:** ~$0.04 per image

**Facebook/Instagram:**
- FREE to post
- Requires Facebook Developer account
- Need Business accounts for full features

---

## 🐛 TROUBLESHOOTING:

**"Failed to connect":**
- Check API key is correct
- Make sure you copied the whole key
- Verify billing is set up (for paid APIs)

**"Integration not available":**
- Make sure you added all routes to web_app_auth.py
- Restart the server
- Check integrations.py is in root folder

**Images not generating:**
- Verify OpenAI connection
- Check you have credits/billing
- Try simpler prompts

**Social posting fails:**
- Check tokens haven't expired
- Verify page permissions
- Make sure image URLs are public

---

## 🎯 WHAT'S NEXT?

### Phase 2 Features (Coming):
- **Agent-specific models** - Choose which agent uses which AI
- **Auto-posting** - Agents post automatically
- **Social analytics** - View post performance
- **Comment responses** - AI responds to comments
- **Scheduled posts** - Queue posts for later

Want these features? Let me know! 🚀

---

## 📝 DEPLOYMENT TO RENDER:

When ready to deploy:

1. **Commit to GitHub:**
   ```
   - integrations.py (new)
   - integrations.html (new)
   - dashboard.html (updated)
   - web_app_auth.py (updated with routes)
   - requirements.txt (updated)
   ```

2. **Push to GitHub**

3. **Render auto-deploys** (5-10 min)

4. **Connect integrations on live site**

5. **Test everything works!**

---

## ⚠️ IMPORTANT NOTES:

1. **API Keys = Money** 
   - Don't share your keys
   - Monitor usage
   - Set up billing alerts

2. **Social Media Tokens Expire**
   - Facebook tokens: 60 days
   - Need to reconnect periodically
   - Set calendar reminders

3. **Image URLs Must Be Public**
   - Instagram requires publicly accessible images
   - Use image hosting services
   - Or upload to your server

4. **Rate Limits Exist**
   - OpenAI: Requests per minute limits
   - Facebook/Instagram: API call limits
   - Don't spam!

---

## 🎊 YOU'RE READY!

Your AI Team can now:
- ✅ Use multiple AI models
- ✅ Generate images on demand
- ✅ Post to social media
- ✅ Manage all integrations
- ✅ Track usage and costs

**Deploy and start using these powerful integrations!** 🚀

---

## 💬 QUICK TEST CHECKLIST:

### Local Testing:
- [ ] Dashboard shows "🔌 Integrations" button
- [ ] Integrations page loads
- [ ] Can connect Claude API
- [ ] Can connect OpenAI API
- [ ] "🎨 Generate Image" button works
- [ ] "📱 Post to Social" button works
- [ ] Image generation displays image
- [ ] Social posting shows success

### After Deployment:
- [ ] All local tests pass on live site
- [ ] API keys saved correctly
- [ ] Integrations persist after logout
- [ ] Usage tracking works
- [ ] No errors in Render logs

---

**CONGRATULATIONS!** 🎉 You have a complete integrations system!
