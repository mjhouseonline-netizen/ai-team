# 🎨 Make.com Integration Guide - AI Team

## 🚀 **Complete Make.com Setup**

Make.com (formerly Integromat) is now **fully integrated** with AI Team!

---

## ✅ **What's Available:**

1. **HTTP Request Module** - Call AI Team API
2. **Webhook Triggers** - Get notified when events happen
3. **Pre-built Scenarios** - Ready-to-use templates
4. **Visual Workflow Builder** - Drag & drop automation

---

## 📋 **Step-by-Step Setup:**

### **Method 1: HTTP Module (Recommended)**

**Use AI Team's REST API directly in Make.com:**

#### **Step 1: Get Your API Key**
1. Go to: `https://ai-team.skillsoul.store/automations`
2. Copy your API key

#### **Step 2: Create a Scenario in Make.com**
1. Go to [Make.com](https://www.make.com)
2. Click **"Create a new scenario"**
3. Search for **"HTTP"** module
4. Add **"Make a request"**

#### **Step 3: Configure HTTP Request**

**URL:**
```
https://ai-team.skillsoul.store/api/chat
```

**Method:**
```
POST
```

**Headers:**
```json
{
  "Authorization": "Bearer YOUR_API_KEY",
  "Content-Type": "application/json"
}
```

**Body (JSON):**
```json
{
  "agent": "Luna",
  "message": "{{1.message}}",
  "context": {}
}
```

**Parse Response:** ✅ Yes

#### **Step 4: Test & Save**
1. Click **"Run once"**
2. Check the response
3. Save your scenario

---

### **Method 2: Webhooks (For Triggers)**

**Get notified when AI Team events happen:**

#### **Step 1: Create Webhook in Make.com**
1. In Make.com, add **"Webhooks"** module
2. Choose **"Custom webhook"**
3. Click **"Add"**
4. Copy the webhook URL (looks like: `https://hook.make.com/...`)

#### **Step 2: Register Webhook with AI Team**

**Using cURL:**
```bash
curl -X POST https://ai-team.skillsoul.store/api/webhooks \
  -H "Cookie: session=YOUR_SESSION" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://hook.make.com/YOUR_WEBHOOK_ID",
    "event_type": "message.completed"
  }'
```

**Or using the Automations page:**
- Visit `/automations`
- Go to "Webhooks" section
- Add your Make.com webhook URL
- Select event type

#### **Step 3: Receive Events**

When someone uses AI Team, Make.com receives:
```json
{
  "event": "message.completed",
  "agent": "Luna",
  "message": "Analyze this data...",
  "response": "Based on the analysis...",
  "timestamp": "2025-11-29T12:00:00Z",
  "user_id": 1
}
```

---

## 🎯 **Pre-Built Scenarios:**

### **Scenario 1: Email → AI Analysis → Spreadsheet**

**Modules:**
1. **Gmail**: Watch emails
2. **AI Team HTTP**: Send to Luna for analysis
3. **Google Sheets**: Add row with analysis

**Configuration:**

**Module 1 - Gmail Trigger:**
- Watch folder: Inbox
- Filter: Subject contains "Analysis Request"

**Module 2 - AI Team HTTP:**
```json
URL: https://ai-team.skillsoul.store/api/chat
Method: POST
Headers: {
  "Authorization": "Bearer YOUR_API_KEY",
  "Content-Type": "application/json"
}
Body: {
  "agent": "Luna",
  "message": "Analyze this email: {{1.textPlain}}",
  "context": {}
}
```

**Module 3 - Google Sheets:**
- Spreadsheet: Your sheet
- Add row:
  - Email Subject: `{{1.subject}}`
  - Analysis: `{{2.response}}`
  - Timestamp: `{{2.timestamp}}`

---

### **Scenario 2: Form → AI Summary → Slack**

**Modules:**
1. **Typeform**: Watch responses
2. **AI Team HTTP**: Send to Sage for summary
3. **Slack**: Post message

**Configuration:**

**Module 1 - Typeform:**
- Watch new responses

**Module 2 - AI Team HTTP:**
```json
{
  "agent": "Sage",
  "message": "Summarize this form: {{1.answers}}",
  "context": {}
}
```

**Module 3 - Slack:**
- Channel: #form-responses
- Message: 
```
New form submitted!
Summary: {{2.response}}
```

---

### **Scenario 3: RSS → Content → Social Media**

**Modules:**
1. **RSS**: Watch feeds
2. **AI Team HTTP**: Sage summarizes
3. **AI Team HTTP**: Ember creates caption
4. **AI Team HTTP**: Generate image
5. **Twitter/LinkedIn**: Post

**Configuration:**

**Module 1 - RSS:**
- Feed URL: Your blog RSS

**Module 2 - Summarize (Sage):**
```json
{
  "agent": "Sage",
  "message": "Summarize this blog post: {{1.description}}",
  "context": {}
}
```

**Module 3 - Caption (Ember):**
```json
{
  "agent": "Ember",
  "message": "Create social media caption for: {{2.response}}",
  "context": {}
}
```

**Module 4 - Image:**
```json
URL: https://ai-team.skillsoul.store/api/generate-image
Body: {
  "prompt": "Professional image for: {{1.title}}"
}
```

**Module 5 - Social Post:**
- Text: `{{3.response}}`
- Image: `{{4.image_url}}`

---

## 📊 **Available AI Agents:**

| Agent | Use For | Example |
|-------|---------|---------|
| **Luna** | Data analysis | Analyze sales data |
| **Mila** | Planning | Create project plan |
| **Sage** | Writing | Write blog summary |
| **Ember** | Creative | Design social caption |
| **Sol** | Strategy | Business decisions |
| **Nova** | Technical | Debug code |
| **Theo** | Execution | Create action plan |

---

## 🔌 **All Available Endpoints:**

### **POST /api/chat**
```json
Request:
{
  "agent": "Luna",
  "message": "Your message",
  "context": {}
}

Response:
{
  "success": true,
  "agent": "Luna",
  "response": "AI response...",
  "timestamp": "2025-11-29T12:00:00Z",
  "remaining_quota": 24
}
```

### **POST /api/generate-image**
```json
Request:
{
  "prompt": "A professional dashboard"
}

Response:
{
  "success": true,
  "image_url": "https://...",
  "timestamp": "2025-11-29T12:00:00Z"
}
```

### **GET /api/agents**
```json
Response:
{
  "success": true,
  "agents": [...],
  "total": 7
}
```

### **GET /api/usage**
```json
Response:
{
  "success": true,
  "daily_limit": 25,
  "used_today": 5,
  "remaining_today": 20
}
```

---

## 🎬 **Example Scenarios:**

### **1. Customer Support Automation**

```
New Ticket (Zendesk)
  ↓
Nova analyzes issue
  ↓
Creates solution
  ↓
Posts to ticket
  ↓
Notifies team (Slack)
```

### **2. Content Pipeline**

```
New article idea (Airtable)
  ↓
Sage writes draft
  ↓
Ember creates visuals
  ↓
Saves to Google Docs
  ↓
Sends for review (Email)
```

### **3. Data Processing**

```
New data file (Dropbox)
  ↓
Luna analyzes data
  ↓
Creates insights
  ↓
Generates charts (Image API)
  ↓
Sends report (Email)
```

---

## 🛠️ **Advanced Features:**

### **Error Handling**

Add error handling in Make.com:
```
Set up Error Handler
  ↓
If API fails (status ≠ 200)
  ↓
Send alert to Slack
  ↓
Log to Airtable
```

### **Rate Limit Handling**

Check usage before calling:
```
Module 1: GET /api/usage
  ↓
Router: If remaining > 0
  ↓
Module 2: POST /api/chat
```

### **Batch Processing**

Process multiple items:
```
Array aggregator
  ↓
Iterator
  ↓
AI Team API (for each item)
  ↓
Collect responses
  ↓
Send summary email
```

---

## 📱 **Webhook Events:**

Available event types:
- `message.completed` - When AI responds
- `image.generated` - When image is created
- `agent.response` - Any agent response

**Webhook payload:**
```json
{
  "event": "message.completed",
  "agent": "Luna",
  "message": "User message",
  "response": "AI response",
  "timestamp": "2025-11-29T12:00:00Z",
  "user_id": 1
}
```

---

## ⚡ **Performance Tips:**

1. **Use Filters**: Only process relevant data
2. **Aggregate**: Batch requests when possible
3. **Cache**: Store repeated AI responses
4. **Schedule**: Run intensive tasks off-peak
5. **Monitor**: Check usage regularly

---

## 🔒 **Security Best Practices:**

1. **Never expose API key** in scenario names
2. **Use Make.com secrets** for storing keys
3. **Rotate keys** periodically
4. **Monitor usage** for anomalies
5. **Use webhooks** for sensitive data

---

## 📖 **Troubleshooting:**

### **Issue: 401 Unauthorized**
**Solution:** Check your API key in headers

### **Issue: 429 Rate Limit**
**Solution:** You've hit daily limit, upgrade plan

### **Issue: Webhook not triggering**
**Solution:** Check webhook URL and event type

### **Issue: Empty response**
**Solution:** Check "Parse response" is enabled

---

## 🎓 **Learning Resources:**

- Make.com Academy: [https://www.make.com/en/academy](https://www.make.com/en/academy)
- HTTP Module Guide: [Make.com HTTP](https://www.make.com/en/help/apps/built-in-apps-modules/http)
- Webhook Setup: [Make.com Webhooks](https://www.make.com/en/help/tools/webhooks)

---

## 💡 **Pro Tips:**

1. **Start Simple**: Begin with one-step scenarios
2. **Test Thoroughly**: Use "Run once" before activating
3. **Use Variables**: Store API key as Make.com variable
4. **Add Logging**: Track all API calls
5. **Set Limits**: Add execution limits for safety

---

## 🎉 **You're Ready!**

Your Make.com integration is **fully set up**!

**Next Steps:**
1. Create your first scenario
2. Test with sample data
3. Activate and monitor
4. Scale with confidence

**Need Help?** Contact support or check the full API documentation at `/automations`

---

Generated: November 29, 2025
Make.com Integration - Complete Guide
