# ⚡ AUTOMATIONS - QUICK DEPLOY

## 🤖 NEW: Full Automation System with API Keys!

---

## 📥 DOWNLOAD (3 FILES):

**Backend:**
1. [web_app_auth.py](computer:///mnt/user-data/outputs/web_app_auth.py) → Project root

**Templates:**
2. [dashboard.html](computer:///mnt/user-data/outputs/dashboard.html) → templates/
3. [automations.html](computer:///mnt/user-data/outputs/automations.html) → templates/ (NEW!)

---

## 🚀 DEPLOY:

```bash
git add .
git commit -m "Add automation system with API keys"
git push origin main
```

---

## ✅ AFTER DEPLOY:

### 1. Visit Automations:
**https://ai-team-q84h.onrender.com/automations**

### 2. Create API Key:
- Click "Create New API Key"
- Name it (e.g., "Test Key")
- Copy the key (sk-...)

### 3. Test It:
```bash
curl -X POST https://ai-team-q84h.onrender.com/api/automate/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY_HERE" \
  -d '{"message": "Hello!", "agent": "Luna"}'
```

### 4. Get Response:
```json
{
  "success": true,
  "response": "Hello! How can I help you?",
  "agent": "Luna"
}
```

---

## 🎯 WHAT YOU GET:

✅ **API Key Management** - Create/delete keys with UI
✅ **Automation Endpoint** - POST to /api/automate/chat
✅ **Complete Docs** - Examples, guides, reference
✅ **7 Agents via API** - All agents accessible
✅ **Rate Limiting** - Tied to subscription tier
✅ **Usage Tracking** - Last used timestamps

---

## 💡 USE CASES:

**Zapier:**
- Trigger AI from 5,000+ apps
- Automate workflows
- Build custom zaps

**Scheduled Jobs:**
- Daily reports with Luna
- Morning briefings
- Automated analysis

**Slack Bot:**
- Team AI assistant
- Custom commands
- Instant answers

**Custom Apps:**
- Integrate into your software
- Build AI features
- Scale effortlessly

---

## 📚 FULL GUIDE:

[Complete Automation Guide](computer:///mnt/user-data/outputs/AUTOMATIONS_GUIDE.md)

---

**Just 3 files to deploy - then automate everything!** 🚀✨
