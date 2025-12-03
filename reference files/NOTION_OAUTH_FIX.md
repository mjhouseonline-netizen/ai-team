# 🔧 NOTION OAUTH FIX GUIDE

## **ISSUE: Notion Connection Not Working**

Support: ai-team@skillsoul.store

---

## **COMMON PROBLEMS & SOLUTIONS:**

### **Problem 1: "Invalid Client ID"**

**Cause:** Client ID doesn't match Notion integration

**Fix:**
1. Go to https://www.notion.so/my-integrations
2. Find your AI Team integration
3. Copy the **OAuth client ID** (starts with "oauth2_client_")
4. Update in your environment variables:
```bash
NOTION_CLIENT_ID=oauth2_client_YOUR_ACTUAL_ID
```

---

### **Problem 2: "Redirect URI Mismatch"**

**Cause:** Callback URL not whitelisted in Notion

**Fix:**
1. Go to https://www.notion.so/my-integrations
2. Click your AI Team integration
3. Scroll to "Redirect URIs"
4. Add BOTH of these:
```
https://ai-team.skillsoul.store/notion-callback
http://localhost:5000/notion-callback (for testing)
```
5. Click "Save"

---

### **Problem 3: "Invalid Redirect URI"**

**Cause:** Callback route not configured correctly

**Fix in web_app_auth.py:**
```python
@app.route('/notion-oauth')
@login_required
def notion_oauth():
    client_id = os.getenv('NOTION_CLIENT_ID')
    redirect_uri = 'https://ai-team.skillsoul.store/notion-callback'  # Must match Notion settings
    
    # Notion OAuth URL
    auth_url = f"https://api.notion.com/v1/oauth/authorize?client_id={client_id}&response_type=code&owner=user&redirect_uri={redirect_uri}"
    
    return redirect(auth_url)

@app.route('/notion-callback')
@login_required
def notion_callback():
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        flash(f'Notion authorization failed: {error}', 'error')
        return redirect('/dashboard')
    
    if not code:
        flash('No authorization code received', 'error')
        return redirect('/dashboard')
    
    # Exchange code for access token
    client_id = os.getenv('NOTION_CLIENT_ID')
    client_secret = os.getenv('NOTION_CLIENT_SECRET')
    redirect_uri = 'https://ai-team.skillsoul.store/notion-callback'
    
    token_url = 'https://api.notion.com/v1/oauth/token'
    
    # Notion requires Basic Auth with base64 encoded credentials
    import base64
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri
    }
    
    try:
        response = requests.post(token_url, headers=headers, json=data)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get('access_token')
        workspace_id = token_data.get('workspace_id')
        
        # Store in database
        cursor = get_db().cursor()
        cursor.execute('''
            UPDATE users 
            SET notion_token = ?,
                notion_workspace_id = ?
            WHERE id = ?
        ''', (access_token, workspace_id, current_user.id))
        get_db().commit()
        
        flash('Notion connected successfully!', 'success')
        
    except requests.exceptions.RequestException as e:
        flash(f'Failed to connect Notion: {str(e)}', 'error')
    
    return redirect('/dashboard')
```

---

### **Problem 4: "Missing Environment Variables"**

**Check your .env file:**
```bash
# Notion OAuth
NOTION_CLIENT_ID=oauth2_client_YOUR_ID_HERE
NOTION_CLIENT_SECRET=secret_YOUR_SECRET_HERE
NOTION_REDIRECT_URI=https://ai-team.skillsoul.store/notion-callback
```

**On Render:**
1. Go to your Render dashboard
2. Click your web service
3. Go to "Environment" tab
4. Add these environment variables:
   - `NOTION_CLIENT_ID` = oauth2_client_...
   - `NOTION_CLIENT_SECRET` = secret_...
   - `NOTION_REDIRECT_URI` = https://ai-team.skillsoul.store/notion-callback
5. Click "Save Changes"
6. Wait for redeploy

---

### **Problem 5: Database Schema Missing**

**Add Notion columns to users table:**

```sql
-- Check if columns exist
PRAGMA table_info(users);

-- Add columns if missing
ALTER TABLE users ADD COLUMN notion_token TEXT;
ALTER TABLE users ADD COLUMN notion_workspace_id TEXT;
```

**Or in Python (auto-migration):**
```python
def init_db():
    db = get_db()
    cursor = db.cursor()
    
    # Check if notion columns exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'notion_token' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN notion_token TEXT')
    
    if 'notion_workspace_id' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN notion_workspace_id TEXT')
    
    db.commit()
```

---

## **COMPLETE CHECKLIST:**

### **In Notion (notion.so):**
- [ ] Integration created
- [ ] Client ID copied
- [ ] Client Secret copied
- [ ] Redirect URI added: https://ai-team.skillsoul.store/notion-callback
- [ ] Integration has correct capabilities (read/write pages)

### **In Your Code:**
- [ ] Routes exist: /notion-oauth and /notion-callback
- [ ] Redirect URI matches exactly
- [ ] Basic Auth implemented correctly
- [ ] Access token stored in database
- [ ] Database has notion_token and notion_workspace_id columns

### **In Environment:**
- [ ] NOTION_CLIENT_ID set
- [ ] NOTION_CLIENT_SECRET set
- [ ] NOTION_REDIRECT_URI set (if used)
- [ ] Variables deployed to Render
- [ ] Service redeployed

---

## **TESTING STEPS:**

1. **Click "Connect Notion" button**
   - Should redirect to Notion
   - Should show permission screen

2. **Grant permission**
   - Select workspace
   - Click "Allow access"

3. **Callback**
   - Should redirect back to your site
   - Should show success message
   - Should store token in database

4. **Verify in Database:**
```sql
SELECT id, email, notion_token, notion_workspace_id 
FROM users 
WHERE id = YOUR_USER_ID;
```

---

## **DEBUGGING:**

### **Enable Debug Logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/notion-callback')
@login_required
def notion_callback():
    code = request.args.get('code')
    error = request.args.get('error')
    
    print(f"DEBUG: Code received: {code[:10]}..." if code else "No code")
    print(f"DEBUG: Error: {error}" if error else "No error")
    
    # ... rest of code
    
    print(f"DEBUG: Response status: {response.status_code}")
    print(f"DEBUG: Response body: {response.text}")
```

### **Common Error Messages:**

**"invalid_client"**
→ Client ID or Secret is wrong. Check Notion integration settings.

**"invalid_grant"**
→ Authorization code expired or already used. User needs to reconnect.

**"unauthorized_client"**
→ Redirect URI doesn't match. Check Notion integration settings.

**"access_denied"**
→ User clicked "Cancel" on Notion permission screen.

---

## **QUICK FIX SCRIPT:**

Create `fix_notion.py`:
```python
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

# Add missing columns
db = sqlite3.connect('database.db')
cursor = db.cursor()

try:
    cursor.execute('ALTER TABLE users ADD COLUMN notion_token TEXT')
    print("✅ Added notion_token column")
except:
    print("⚠️  notion_token column already exists")

try:
    cursor.execute('ALTER TABLE users ADD COLUMN notion_workspace_id TEXT')
    print("✅ Added notion_workspace_id column")
except:
    print("⚠️  notion_workspace_id column already exists")

db.commit()
db.close()

# Check environment variables
required_vars = ['NOTION_CLIENT_ID', 'NOTION_CLIENT_SECRET']
for var in required_vars:
    if os.getenv(var):
        print(f"✅ {var} is set")
    else:
        print(f"❌ {var} is MISSING!")

print("\n📝 Reminder: Update these in Render environment too!")
```

Run: `python fix_notion.py`

---

## **STILL NOT WORKING?**

Contact support: **ai-team@skillsoul.store**

Include:
- Error message (if any)
- Screenshot of Notion integration settings
- What happens when you click "Connect Notion"
- Browser console errors (F12 → Console)

We'll help you fix it! 🚀
