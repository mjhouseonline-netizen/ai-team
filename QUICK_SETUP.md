# ⚡ QUICK SETUP - 5 MINUTES

## Step 1: Download (2 min)
1. [integrations.py](computer:///mnt/user-data/outputs/integrations.py) → `Desktop\ai-team\`
2. [integrations.html](computer:///mnt/user-data/outputs/integrations.html) → `Desktop\ai-team\templates\`
3. [dashboard_simple.html](computer:///mnt/user-data/outputs/dashboard_simple.html) → Rename to `dashboard.html`, replace in `templates\`
4. [integration_routes.py](computer:///mnt/user-data/outputs/integration_routes.py) → Reference only

## Step 2: Update Files (2 min)

**requirements.txt** - Add these lines:
```
openai==1.54.0
requests==2.31.0
```

**web_app_auth.py** - Add at top:
```python
from integrations import integrations_manager
```

**web_app_auth.py** - Copy ALL routes from integration_routes.py before the `if __name__` line

## Step 3: Test (1 min)
```bash
pip install openai requests --break-system-packages
```
Run `START_BUSINESS_FIXED.bat`
Visit dashboard → Click "🔌 Integrations"

---

## After Setup:

### Get API Keys:
- **Claude:** console.anthropic.com
- **OpenAI:** platform.openai.com  
- **Facebook:** developers.facebook.com
- **Instagram:** developers.facebook.com

### Use Features:
- **🎨 Generate Image** - Create AI images
- **📱 Post to Social** - Post to Facebook/Instagram
- **🔌 Integrations** - Manage connections

---

## Files Structure:
```
ai-team/
├── integrations.py          ← NEW
├── web_app_auth.py          ← UPDATED
├── requirements.txt         ← UPDATED
└── templates/
    ├── dashboard.html       ← REPLACED
    └── integrations.html    ← NEW
```

---

**Done! 🎉 Your AI Team can now connect to Claude, ChatGPT, DALL-E, Facebook, and Instagram!**

See [INTEGRATIONS_SETUP_GUIDE.md](computer:///mnt/user-data/outputs/INTEGRATIONS_SETUP_GUIDE.md) for detailed docs.
