# 🎯 QUICK FIX - Exact Lines to Change

## 📍 LOCATION: Line 1241-1280 in web_app_auth.py

---

## ❌ CURRENT CODE (WRONG):

```python
@app.route('/api/user-stats')
@login_required
def get_user_stats():
    """Get current user's usage statistics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
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
        tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
        
        # Reset counter if it's a new day
        if last_reset:
            last_reset_date = datetime.fromisoformat(last_reset).date()
            today = datetime.utcnow().date()
            
            if last_reset_date < today:
                messages_today = 0
        
        return jsonify({
            'messages_today': messages_today,
            'messages_limit': tier_info['messages_per_day'],  # ❌ WRONG NAME
            'tier': tier,
            'tier_name': tier_info['name']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## ✅ NEW CODE (CORRECT):

```python
@app.route('/api/user-stats')
@login_required
def get_user_stats():
    """Get current user's usage statistics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
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
        tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
        daily_limit = tier_info['messages_per_day']  # ✅ STORE IN VARIABLE
        
        # Reset counter if it's a new day
        if last_reset:
            last_reset_date = datetime.fromisoformat(last_reset).date()
            today = datetime.utcnow().date()
            
            if last_reset_date < today:
                messages_today = 0
        
        # ✅ CALCULATE REMAINING MESSAGES
        if daily_limit == -1 or daily_limit == 999999:
            messages_remaining = -1  # Unlimited
        else:
            messages_remaining = max(0, daily_limit - messages_today)
        
        return jsonify({
            'subscription_tier': tier,              # ✅ ADDED
            'messages_today': messages_today,
            'daily_limit': daily_limit,             # ✅ FIXED NAME
            'messages_remaining': messages_remaining,  # ✅ ADDED
            'tier_name': tier_info['name']
        }), 200
        
    except Exception as e:
        print(f"Error getting user stats: {str(e)}")  # ✅ ADDED LOGGING
        return jsonify({'error': str(e)}), 500
```

---

## 🔄 WHAT CHANGED:

### Line ~1262:
```python
# OLD:
tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])

# NEW:
tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
daily_limit = tier_info['messages_per_day']  # ← ADDED THIS LINE
```

### Lines ~1270-1276:
```python
# OLD:
return jsonify({
    'messages_today': messages_today,
    'messages_limit': tier_info['messages_per_day'],
    'tier': tier,
    'tier_name': tier_info['name']
}), 200

# NEW:
# Calculate remaining messages
if daily_limit == -1 or daily_limit == 999999:
    messages_remaining = -1
else:
    messages_remaining = max(0, daily_limit - messages_today)

return jsonify({
    'subscription_tier': tier,           # ← ADDED
    'messages_today': messages_today,
    'daily_limit': daily_limit,          # ← CHANGED NAME
    'messages_remaining': messages_remaining,  # ← ADDED
    'tier_name': tier_info['name']
}), 200
```

### Line ~1280:
```python
# OLD:
except Exception as e:
    return jsonify({'error': str(e)}), 500

# NEW:
except Exception as e:
    print(f"Error getting user stats: {str(e)}")  # ← ADDED LOGGING
    return jsonify({'error': str(e)}), 500
```

---

## 📦 EASIEST WAY:

### Option 1: Use the Fixed File
```bash
# Download web_app_auth_FIXED.py
# Replace your current file
cp web_app_auth_FIXED.py web_app_auth.py
```

### Option 2: Manual Edit
1. Open your `web_app_auth.py`
2. Go to line 1241
3. Select from line 1241 to line 1280
4. Delete it
5. Paste the "NEW CODE" from above
6. Save

---

## 🚀 THEN DEPLOY:

```bash
git add web_app_auth.py
git commit -m "Fix user-stats API response fields"
git push origin main
```

---

## ✅ VERIFICATION:

After deploying, visit:
```
https://ai-team-q84h.onrender.com/api/user-stats
```

You should see:
```json
{
  "subscription_tier": "starter",
  "messages_today": 0,
  "daily_limit": 100,
  "messages_remaining": 100,
  "tier_name": "Starter"
}
```

**If you see this, it's FIXED!** ✅

---

## 🎯 BOTTOM LINE:

**Change 3 things in the return statement:**
1. `'messages_limit'` → `'daily_limit'`
2. Add `'subscription_tier': tier`
3. Add `'messages_remaining': messages_remaining`

**That's it!** 🎉
