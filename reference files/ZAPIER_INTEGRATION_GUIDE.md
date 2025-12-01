# 🔗 ZAPIER INTEGRATION - COMPLETE GUIDE

## ✅ **Already Built!**

Your Zapier integration is ALREADY working! The webhook system was built in the previous Make.com integration.

---

## 🎯 **What You Have:**

### **1. Webhook System** ✅
- Automatic event triggering
- Real-time notifications
- Custom webhook URLs
- Event filtering

### **2. API Endpoints** ✅
- `/api/chat` - Send messages to AI agents
- `/api/generate-image` - Create AI images
- `/api/agents` - List available agents
- `/api/usage` - Check quota

### **3. Webhook Management** ✅
- Add webhooks via UI
- Toggle active/inactive
- Delete webhooks
- View webhook history

---

## 🚀 **How to Use Zapier:**

### **Method 1: Webhooks (Receive Events)**

**Setup:**
1. **In Zapier:**
   - Create new Zap
   - Choose trigger: **"Webhooks by Zapier"**
   - Select: **"Catch Hook"**
   - Copy the webhook URL

2. **In AI Team:**
   - Go to: https://ai-team.skillsoul.store/automations
   - Scroll to "Webhook Management"
   - Click "Add Webhook"
   - Paste Zapier webhook URL
   - Select event: `message.completed`
   - Save

3. **Test:**
   - Send a message in AI Team
   - Zapier receives the webhook
   - You can see the data!

**Webhook Payload:**
```json
{
  "event": "message.completed",
  "agent": "Luna",
  "message": "Analyze this data",
  "response": "Based on the analysis...",
  "timestamp": "2025-11-29T12:00:00Z",
  "user_id": 1,
  "model_used": "claude-sonnet-4.5"
}
```

---

### **Method 2: API Calls (Send to AI Team)**

**Setup:**
1. **In Zapier:**
   - Choose action: **"Webhooks by Zapier"**
   - Select: **"POST"**
   - URL: `https://ai-team.skillsoul.store/api/chat`
   
2. **Configure:**
   - **Method:** POST
   - **Headers:**
     ```
     Authorization: Bearer YOUR_API_KEY
     Content-Type: application/json
     ```
   - **Data:**
     ```json
     {
       "agent": "Luna",
       "message": "Your message here",
       "model": "claude-sonnet-4.5"
     }
     ```

3. **Test:**
   - Trigger the Zap
   - AI Team processes the request
   - Response comes back to Zapier

---

## 📊 **Example Zaps:**

### **Zap 1: Email → AI Analysis → Spreadsheet**

```
Trigger: Gmail - New Email
  ↓
Action: Webhooks - POST to AI Team
  URL: https://ai-team.skillsoul.store/api/chat
  Body: {
    "agent": "Luna",
    "message": "Analyze this email: {{body}}",
    "model": "claude-sonnet-4.5"
  }
  ↓
Action: Google Sheets - Add Row
  Columns:
    - Subject: {{subject}}
    - Analysis: {{response}}
    - Date: {{timestamp}}
```

---

### **Zap 2: Form → AI Summary → Slack**

```
Trigger: Typeform - New Response
  ↓
Action: Webhooks - POST to AI Team
  URL: https://ai-team.skillsoul.store/api/chat
  Body: {
    "agent": "Sage",
    "message": "Summarize this form: {{answers}}",
    "model": "gpt-4o"
  }
  ↓
Action: Slack - Send Message
  Channel: #submissions
  Message: New form response:
           {{response}}
```

---

### **Zap 3: Calendar Event → AI Agenda → Notion**

```
Trigger: Google Calendar - New Event
  ↓
Action: Webhooks - POST to AI Team
  URL: https://ai-team.skillsoul.store/api/chat
  Body: {
    "agent": "Theo",
    "message": "Create meeting agenda for: {{event_title}}",
    "model": "claude-opus-4"
  }
  ↓
Action: Notion - Create Page
  Title: {{event_title}} - Agenda
  Content: {{response}}
```

---

### **Zap 4: AI Team → Multiple Actions**

**Using Webhooks (Event-Driven):**

```
Trigger: Webhooks - Catch Hook (AI Team webhook)
  ↓
Filter: Only if event = "message.completed"
  ↓
Paths:
  Path A: If agent = "Luna"
    → Save to Database
  
  Path B: If agent = "Sage"
    → Post to WordPress
  
  Path C: If agent = "Ember"
    → Send to Design Team (Email)
```

---

## 🔑 **Getting Your API Key:**

1. Go to: https://ai-team.skillsoul.store/automations
2. Your API key is displayed at the top
3. Click "Copy Key"
4. Use in Zapier webhooks

**Format:**
```
Authorization: Bearer sk-ai-team-abc123xyz...
```

---

## 📋 **Available Events:**

| Event | When Triggered | Payload |
|-------|---------------|---------|
| `message.completed` | AI responds to message | agent, message, response, model_used |
| `image.generated` | AI creates image | prompt, image_url |
| `agent.response` | Any agent activity | agent, response |

---

## 🎯 **Pro Zap Ideas:**

### **Customer Support Automation:**
```
Zendesk → AI Team (Nova) → Suggest Solution → Reply to Ticket
```

### **Content Pipeline:**
```
RSS → AI Team (Sage) → Rewrite Article → WordPress → Social Media
```

### **Data Processing:**
```
Google Sheets → AI Team (Luna) → Analyze Row → Update Sheet → Slack Alert
```

### **Lead Qualification:**
```
New Lead (CRM) → AI Team (Sol) → Score Lead → Route to Sales → Notify Team
```

### **Meeting Notes:**
```
Zoom Recording → Transcribe → AI Team (Theo) → Summary → Send to Team → Save to Notion
```

---

## 🔧 **Advanced Configuration:**

### **Multi-Step with Multiple Models:**

```
Trigger: New Task in Asana
  ↓
Step 1: AI Team (Mila) - GPT-4o Mini
  → Create initial plan (fast & cheap)
  ↓
Step 2: AI Team (Sol) - Claude Opus 4
  → Strategic analysis (deep reasoning)
  ↓
Step 3: AI Team (Theo) - Claude Sonnet 4.5
  → Action items (balanced)
  ↓
Step 4: Update Asana + Notify Team
```

---

## 💰 **Cost Optimization:**

**Use cheaper models for simple tasks:**

```javascript
// In Zapier, use Formatter to select model:
if (message.length < 50) {
  model = "gpt-4o-mini";  // $0.15/1M - cheapest!
} else if (complexity == "high") {
  model = "claude-opus-4";  // $15/1M - most capable
} else {
  model = "claude-sonnet-4.5";  // $3/1M - balanced
}
```

---

## 🐛 **Troubleshooting:**

### **Issue: 401 Unauthorized**
**Solution:** Check API key in Authorization header

### **Issue: 429 Rate Limit**
**Solution:** You've hit daily message limit - upgrade plan

### **Issue: Webhook not firing**
**Solution:** 
1. Check webhook URL is correct
2. Verify event type matches
3. Check webhook is active (not paused)

### **Issue: Response not parsing**
**Solution:** Use Zapier's "Parse JSON" action after webhook

---

## 📊 **Webhook Management:**

**View all webhooks:**
```
https://ai-team.skillsoul.store/automations
→ Scroll to "Webhook Management"
```

**Each webhook shows:**
- URL
- Event type
- Status (Active/Inactive)
- Last triggered time
- Actions (Toggle/Delete)

---

## ✅ **Quick Start Checklist:**

**For Webhooks (Receiving):**
- [ ] Create Zap with Webhook trigger
- [ ] Copy webhook URL from Zapier
- [ ] Add webhook in AI Team
- [ ] Select event type
- [ ] Test by sending AI Team message
- [ ] Verify Zapier receives data

**For API Calls (Sending):**
- [ ] Get API key from AI Team
- [ ] Create Zap with Webhook action
- [ ] Configure POST to /api/chat
- [ ] Add Authorization header
- [ ] Add message body
- [ ] Test Zap
- [ ] Check response

---

## 🎉 **Example Response Formats:**

### **Chat Response:**
```json
{
  "response": "Based on my analysis, I found three key trends...",
  "agent": "Luna",
  "model_used": "claude-sonnet-4.5"
}
```

### **Image Response:**
```json
{
  "image_url": "https://image.pollinations.ai/...",
  "prompt": "A professional dashboard",
  "provider": "pollinations"
}
```

### **Error Response:**
```json
{
  "error": "Daily message limit reached",
  "limit": 25,
  "used": 25
}
```

---

## 🚀 **Ready to Automate!**

Your Zapier integration is **fully functional** right now!

**Next Steps:**
1. Go to Zapier.com
2. Create your first Zap
3. Connect to AI Team
4. Start automating!

**Need help?** Check the automations page for live examples and webhook management.

---

Generated: November 29, 2025
Zapier Integration - Complete Guide
