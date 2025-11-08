# 📥 EASY DOWNLOAD GUIDE - Correct File Names!

## 🎯 Download These Files (Already Named Correctly!)

### For Root Folder (`Desktop\ai-team\`)

**[integrations.py](computer:///mnt/user-data/outputs/integrations.py)**
- Download and place in: `Desktop\ai-team\integrations.py`
- ✅ Already has the correct name!

---

### For Templates Folder (`Desktop\ai-team\templates\`)

**[dashboard.html](computer:///mnt/user-data/outputs/dashboard.html)**
- Download and place in: `Desktop\ai-team\templates\dashboard.html`
- ✅ Already has the correct name!
- ⚠️ This will REPLACE your old dashboard.html

**[integrations.html](computer:///mnt/user-data/outputs/integrations.html)**
- Download and place in: `Desktop\ai-team\templates\integrations.html`
- ✅ Already has the correct name!

---

### Reference File (Copy Code From This)

**[integration_routes.py](computer:///mnt/user-data/outputs/integration_routes.py)**
- DON'T put this file anywhere
- OPEN it and COPY all the routes
- PASTE them into `web_app_auth.py`

---

## 📋 Step-by-Step Download:

### 1. Create Folders (If Needed)
Make sure these exist:
```
Desktop\ai-team\
Desktop\ai-team\templates\
```

### 2. Download Root Files
Click and save:
- **[integrations.py](computer:///mnt/user-data/outputs/integrations.py)** → Save to `Desktop\ai-team\`

### 3. Download Template Files  
Click and save:
- **[dashboard.html](computer:///mnt/user-data/outputs/dashboard.html)** → Save to `Desktop\ai-team\templates\`
- **[integrations.html](computer:///mnt/user-data/outputs/integrations.html)** → Save to `Desktop\ai-team\templates\`

### 4. Update web_app_auth.py
1. Open **[integration_routes.py](computer:///mnt/user-data/outputs/integration_routes.py)**
2. Copy EVERYTHING (all the routes)
3. Open your `Desktop\ai-team\web_app_auth.py`
4. Add this line at the top with other imports:
   ```python
   from integrations import integrations_manager
   ```
5. Paste all the routes BEFORE the `if __name__ == '__main__':` line
6. Save

### 5. Update requirements.txt
Open `Desktop\ai-team\requirements.txt` and add these lines:
```
openai==1.54.0
requests==2.31.0
```

---

## ✅ Final File Structure:

After downloading, you should have:

```
Desktop\ai-team\
├── integrations.py              ← DOWNLOADED
├── web_app_auth.py              ← EDITED (added routes)
├── requirements.txt             ← EDITED (added packages)
├── ai_team.py
├── auth.py
├── migrate_db.py
├── Procfile
├── .gitignore
├── START_BUSINESS_FIXED.bat
│
├── templates\
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html           ← DOWNLOADED (replaces old)
│   ├── integrations.html        ← DOWNLOADED (new)
│   └── pricing.html
│
└── static\
    └── images\
        ├── ember.jpg
        ├── luna.jpg
        ├── mila.jpg
        ├── nova.jpg
        ├── sage.jpg
        ├── sol.jpg
        └── theo.jpg
```

---

## 🎯 Quick Checklist:

Download these 3 files with correct names:
- [ ] integrations.py → root folder
- [ ] dashboard.html → templates folder (replaces old)
- [ ] integrations.html → templates folder (new)

Update these 2 files:
- [ ] web_app_auth.py → add import + routes
- [ ] requirements.txt → add 2 packages

---

## 🚀 Then Test:

```bash
pip install openai requests --break-system-packages
```

Run `START_BUSINESS_FIXED.bat`

You should see:
- ✅ Dashboard loads
- ✅ "🔌 Integrations" button in header
- ✅ "🎨 Generate Image" button
- ✅ "📱 Post to Social" button
- ✅ Integrations page works

---

## 📚 Need Help?

See full guides:
- **[QUICK_SETUP.md](computer:///mnt/user-data/outputs/QUICK_SETUP.md)** - 5-minute guide
- **[MASTER_INTEGRATIONS_GUIDE.md](computer:///mnt/user-data/outputs/MASTER_INTEGRATIONS_GUIDE.md)** - Complete reference

---

**Files are now named correctly for easy downloading!** 🎉

Just click, save to the right folder, and you're done! 🚀
