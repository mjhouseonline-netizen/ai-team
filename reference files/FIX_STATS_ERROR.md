# 🔧 FIX FOR STATS LOADING ERROR

## 🚨 THE PROBLEM:

Console error:
```
Error loading stats: SyntaxError: Failed to execute 'close' on 'ReadableStreamDefaultController': 
Unexpected token '<', "<!DOCTYPE "... is not valid JSON
```

**Cause:** The `/api/user-stats` endpoint doesn't exist in your backend.

**Impact:** 
- Stats show "Loading..." forever on profile page
- Console errors (annoying but not breaking)
- Everything else works fine

---

## ✅ SOLUTION 1: ADD THE MISSING ENDPOINT (RECOMMENDED)

### Step 1: Open your `web_app_auth.py`

### Step 2: Find a Good Location

Look for your API routes section. Add this **after your chat routes** and **before your promo code section**.

Good places to add it:
```python
# After this line:
@app.route('/api/chat', methods=['POST'])
def api_chat():
    # ... chat code ...

# ADD THE NEW ENDPOINT HERE ↓

@app.route('/api/user-stats')
@login_required
def api_user_stats():
    # ... new code ...
```

### Step 3: Copy This Entire Function

```python
@app.route('/api/user-stats')
@login_required
def api_user_stats():
    """Get current user's usage statistics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get user's current stats
        cursor.execute("""
            SELECT subscription_tier, messages_today, last_message_reset
            FROM users
            WHERE id = ?
        """, (current_user.id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'User not found'}), 404
        
        tier, messages_today, last_reset = result
        
        # Get tier info
        tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
        daily_limit = tier_info['messages_per_day']
        
        # Reset counter if it's a new day
        if last_reset:
            from datetime import datetime
            last_reset_date = datetime.fromisoformat(last_reset).date()
            today = datetime.utcnow().date()
            
            if last_reset_date < today:
                messages_today = 0
        
        return jsonify({
            'subscription_tier': tier,
            'messages_today': messages_today,
            'daily_limit': daily_limit,
            'messages_remaining': daily_limit - messages_today if daily_limit != -1 else -1
        }), 200
        
    except Exception as e:
        print(f"Error getting user stats: {str(e)}")
        return jsonify({'error': str(e)}), 500
```

### Step 4: Deploy

```bash
git add web_app_auth.py
git commit -m "Add user stats API endpoint"
git push origin main
```

### Step 5: Test

1. Wait for deployment
2. Visit your profile page
3. Check console - error should be gone!
4. Stats should load correctly

---

## ✅ SOLUTION 2: QUICK FIX (TEMPORARY)

If you don't want to update the backend right now, modify the profile page JavaScript:

### In profile_green_theme.html:

**Replace this:**
```javascript
async function loadStats() {
    try {
        const response = await fetch('/api/user-stats');
        const data = await response.json();
        
        document.getElementById('messages-today').textContent = data.messages_today || 0;
        // ... rest of code
    } catch (error) {
        console.error('Error loading stats:', error);
        // Shows "-" on error
    }
}
```

**With this:**
```javascript
async function loadStats() {
    try {
        const response = await fetch('/api/user-stats');
        
        // Check if response is OK
        if (!response.ok) {
            throw new Error('Stats endpoint not available');
        }
        
        const data = await response.json();
        
        document.getElementById('messages-today').textContent = data.messages_today || 0;
        document.getElementById('daily-limit').textContent = data.daily_limit === 999999 ? 'Unlimited' : data.daily_limit;
        
        if (data.daily_limit === 999999) {
            document.getElementById('messages-remaining').textContent = 'Unlimited';
        } else {
            const remaining = data.daily_limit - data.messages_today;
            document.getElementById('messages-remaining').textContent = Math.max(0, remaining);
        }
    } catch (error) {
        // Silently fail - just show placeholders
        console.log('Stats not available yet');
        document.getElementById('messages-today').textContent = '—';
        document.getElementById('daily-limit').textContent = '—';
        document.getElementById('messages-remaining').textContent = '—';
    }
}
```

**This will:**
- Stop the console errors
- Show "—" instead of "Loading..." if endpoint is missing
- Work fine once you add the endpoint

---

## 🎯 RECOMMENDED APPROACH:

### Do This:

1. **Add the endpoint to web_app_auth.py** (Solution 1)
2. **Deploy it**
3. **Stats will load correctly**

This is the proper fix and takes only 5 minutes!

---

## 📋 WHERE TO ADD IT IN WEB_APP_AUTH.PY:

### Look for this structure:

```python
# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    # ... existing code ...

# ADD YOUR NEW ENDPOINT HERE ↓
@app.route('/api/user-stats')
@login_required
def api_user_stats():
    # ... new code from above ...

# ============================================
# PROMO CODES (existing section below)
# ============================================
```

---

## 🧪 TESTING THE FIX:

### After adding the endpoint:

**Test 1: Check endpoint directly**
```
Visit: https://ai-team-q84h.onrender.com/api/user-stats
Should return JSON like:
{
  "subscription_tier": "starter",
  "messages_today": 0,
  "daily_limit": 100,
  "messages_remaining": 100
}
```

**Test 2: Check profile page**
```
Visit: https://ai-team-q84h.onrender.com/profile
Stats should load (not show "Loading..." or "—")
Console should have no errors
```

---

## ⚠️ IF YOU SEE OTHER ERRORS:

### Check for SUBSCRIPTION_TIERS constant

The endpoint uses `SUBSCRIPTION_TIERS` which should be defined in your code like:

```python
SUBSCRIPTION_TIERS = {
    'free': {
        'name': 'Free',
        'messages_per_day': 25,
        'features': ['Access to all 7 AI agents', 'File upload']
    },
    'freeforlife': {
        'name': 'Free For Life',
        'messages_per_day': 999999,
        'features': ['Unlimited messages', 'All features']
    },
    'starter': {
        'name': 'Starter',
        'messages_per_day': 100,
        'features': ['100 messages/day', 'All features']
    },
    'pro': {
        'name': 'Pro',
        'messages_per_day': 500,
        'features': ['500 messages/day', 'All features', 'API access']
    }
}
```

If this is missing, you'll need to add it near the top of your file (after imports).

---

## 🎯 SUMMARY:

**Current Situation:**
- ❌ Stats showing "Loading..." forever
- ❌ Console errors
- ✅ Everything else works

**After Fix:**
- ✅ Stats load correctly
- ✅ No console errors
- ✅ Shows real usage data
- ✅ Updates dynamically

**Time to Fix:** 5 minutes
**Difficulty:** Easy (copy-paste one function)

---

## 💡 NEED HELP?

If you're not sure where to add it or run into issues:

1. Send me your current web_app_auth.py
2. I'll show you exactly where to add it
3. Or I'll give you the complete updated file

---

**This is an easy fix - just add one API endpoint and deploy!** 🚀

The error isn't breaking anything critical, but it's good to fix it so your stats display works properly! 😊
