# 🚀 Automation System - Quick Start Guide

## ⚡ **Test It in 5 Minutes!**

### **Step 1: Deploy** (2 minutes)

Upload these 2 files:

```
automations.html → /templates/automations.html
web_app_auth.py → /web_app_auth.py (root)
```

Then deploy:
```bash
git add templates/automations.html web_app_auth.py
git commit -m "Add automation system"
git push origin main
```

Wait for Render to deploy (~5 min)

---

### **Step 2: Get Your API Key** (30 seconds)

1. Visit: `https://ai-team.skillsoul.store/automations`
2. Your API key is displayed automatically!
3. Click **"📋 Copy Key"**

---

### **Step 3: Test the API** (1 minute)

Open terminal and run:

```bash
curl -X POST https://ai-team.skillsoul.store/api/chat \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "Luna",
    "message": "Hello! Can you analyze some data?",
    "context": {}
  }'
```

**Replace `YOUR_API_KEY_HERE` with your actual key!**

---

### **Expected Response:**

```json
{
  "success": true,
  "agent": "Luna",
  "message": "Hello! Can you analyze some data?",
  "response": "Hello! I'd be happy to help you analyze data...",
  "timestamp": "2025-11-29T12:00:00Z",
  "remaining_quota": 24
}
```

---

## 🎉 **It Works!**

Now you can:
- ✅ Use the API in your code
- ✅ Build automations with Zapier/Make.com
- ✅ Integrate with external services
- ✅ Create custom workflows

---

## 📚 **More Examples:**

### **Python:**
```python
import requests

api_key = "YOUR_API_KEY"
response = requests.post(
    "https://ai-team.skillsoul.store/api/chat",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"agent": "Sage", "message": "Write a tweet about AI"}
)
print(response.json()['response'])
```

### **JavaScript:**
```javascript
const response = await fetch('https://ai-team.skillsoul.store/api/chat', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    agent: 'Nova',
    message: 'Help me debug this code'
  })
});
const data = await response.json();
console.log(data.response);
```

---

## 🔍 **Check Usage:**

```bash
curl -X GET https://ai-team.skillsoul.store/api/usage \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Response:
```json
{
  "success": true,
  "subscription_tier": "free",
  "daily_limit": 25,
  "used_today": 1,
  "remaining_today": 24,
  "total_api_requests": 1,
  "api_requests_today": 1
}
```

---

## ✅ **All Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Chat with agents |
| `/api/generate-image` | POST | Create AI images |
| `/api/agents` | GET | List all agents |
| `/api/usage` | GET | Check quota |

---

## 🎯 **That's It!**

You now have:
- ✅ Full REST API
- ✅ API key management
- ✅ Usage tracking
- ✅ Code examples
- ✅ Integration ready

**Start building!** 🚀

---

Generated: November 29, 2025
Automation Quick Start Guide
