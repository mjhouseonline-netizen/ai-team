# 🚨 COST MONITORING & ALERT SYSTEM - IMPLEMENTATION GUIDE

## 📋 What This Does:

1. ✅ Tracks cost of every message in real-time
2. ✅ Sends alerts when users exceed thresholds
3. ✅ Automatically blocks expensive models when costs spike
4. ✅ Provides admin dashboard to monitor all users
5. ✅ Calculates profit margins and revenue
6. ✅ Resets blocks daily so users can try again

---

## 🎯 Cost Thresholds (Auto-configured):

### **Starter ($19/month)**
- ⚠️ Warning at $1/day
- 🚨 Block expensive models at $2/day
- 🔴 Monthly max: $19

### **Pro ($49/month)**
- ⚠️ Warning at $3/day
- 🚨 Block expensive models at $5/day
- 🔴 Monthly max: $49

### **Enterprise ($99/month)**
- ⚠️ Warning at $5/day
- 🚨 Block expensive models at $10/day
- 🔴 Monthly max: $99

**When blocked, users can still use:**
- ✅ Gemini (FREE)
- ✅ GPT-4o Mini (cheap)
- ✅ Haiku (cheap)

**Blocked from:**
- ❌ Claude Opus 4
- ❌ GPT-4 Turbo

---

## 📦 FILES PROVIDED:

1. **cost_monitoring_system.py** - Complete backend code
2. **admin_usage.html** - Dashboard template
3. **IMPLEMENTATION_GUIDE.md** - This file

---

## 🚀 STEP-BY-STEP DEPLOYMENT:

### **STEP 1: Add Code to Backend**

Open your `web_app_auth.py` file and add the cost monitoring code:

```bash
# Option A: Copy the entire cost_monitoring_system.py content
# and paste it into your web_app_auth.py AFTER your imports

# Option B: Import it as a module (cleaner)
# Save cost_monitoring_system.py in your project folder
# Then add to web_app_auth.py:
from cost_monitoring_system import *
```

---

### **STEP 2: Setup Database**

Run this ONCE to create the cost tracking tables:

```python
# In your Python console or add to your init code:
from cost_monitoring_system import setup_cost_tracking
setup_cost_tracking()
```

Or add this to your `web_app_auth.py` at the bottom:

```python
if __name__ == '__main__':
    setup_cost_tracking()  # Creates tables if they don't exist
    app.run(debug=True)
```

---

### **STEP 3: Modify Your Chat Endpoint**

Find your `/api/chat` route in `web_app_auth.py` and add these lines:

**BEFORE processing the message:**

```python
@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    message = data.get('message', '')
    agent = data.get('agent', 'luna')
    model_key = data.get('model', 'gemini-2.0-flash')
    
    # ✅ ADD THIS: Check if expensive models are blocked
    if is_expensive_model_blocked(current_user.id):
        if model_key in EXPENSIVE_MODELS:
            return jsonify({
                'error': 'Expensive models temporarily blocked due to high usage today. Try Gemini or GPT-4o Mini!',
                'blocked': True,
                'allowed_models': ['gemini-2.0-flash', 'gemini-1.5-pro', 'gpt-4o-mini', 'claude-haiku-4.5']
            }), 403
    
    # ... your existing chat logic ...
    
    # Get AI response
    ai_response = route_to_model(model_key, system_prompt, history, message)
    
    # ✅ ADD THIS: Track the cost AFTER getting response
    cost = track_message_cost(current_user.id, model_key, message_count=1)
    
    return jsonify({
        'response': ai_response,
        'agent': agent,
        'model': model_key,
        'cost': f"${cost:.4f}" if cost else None  # Show user the cost
    }), 200
```

---

### **STEP 4: Add Admin Dashboard Template**

1. Create `templates/admin_usage.html` in your project
2. Copy the contents from `admin_usage.html` file I provided
3. Save it

---

### **STEP 5: Configure Email Alerts (Optional)**

Add these to your Render environment variables:

```
ADMIN_EMAIL=your-email@example.com
ALERT_EMAIL_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-gmail@gmail.com
```

**For Gmail:**
1. Go to https://myaccount.google.com/apppasswords
2. Create an "App Password" for "Mail"
3. Use that password (not your regular Gmail password)

**Skip this step if you just want console/dashboard alerts**

---

### **STEP 6: Deploy to Render**

```bash
git add .
git commit -m "Add cost monitoring and alert system"
git push
```

Render will auto-deploy in ~3 minutes.

---

### **STEP 7: Test It Works**

1. Visit: `https://ai-team.skillsoul.store/admin/usage`
2. You should see the dashboard with stats
3. Send a message using an expensive model
4. Check if cost is tracked

---

## 🧪 TESTING CHECKLIST:

### Test 1: Normal Usage
- [ ] Send message with Gemini → Should cost $0
- [ ] Send message with Sonnet → Should track ~$0.003
- [ ] Check admin dashboard shows the cost

### Test 2: Warning Alert
- [ ] Create test Pro user
- [ ] Send enough messages to cost $3.01
- [ ] Check console logs for warning alert
- [ ] Check admin dashboard shows alert

### Test 3: Expensive Model Block
- [ ] Continue sending messages until $5.01 cost
- [ ] Try to use Claude Opus
- [ ] Should get "blocked" error
- [ ] Gemini should still work

### Test 4: Daily Reset
- [ ] Wait until midnight UTC (or manually reset)
- [ ] User should be unblocked
- [ ] Cost counters reset to $0

---

## 📊 HOW TO USE THE DASHBOARD:

### Access:
Visit: `https://ai-team.skillsoul.store/admin/usage`

### What You'll See:

**Top Stats:**
- Today's total cost
- This month's total cost
- Monthly revenue from subscriptions
- Profit margin %

**Active Alerts:**
- Users who exceeded thresholds
- What alert type (warning/critical/monthly)
- How much they've cost you

**Top Cost Users:**
- Who's costing you the most
- Their daily/monthly costs
- If they're blocked from expensive models
- Usage percentage vs their plan limit

**Model Usage:**
- Which models are being used most
- How much each model is costing you today

### Dashboard Auto-Refreshes:
- Every 30 seconds automatically
- Or click "🔄 Refresh Data" button

---

## 🔍 MONITORING IN ACTION:

### Example Scenario:

**Day 1 - Normal:**
```
Pro User "John" starts using your platform
- Sends 50 messages with Gemini → Cost: $0
- Sends 50 messages with Sonnet → Cost: $1.50
- Total: $1.50/day ✅ Normal, no alerts
```

**Day 2 - Warning:**
```
- John sends 200 messages with Sonnet → Cost: $6.00
- Alert triggered: "User exceeded $3/day threshold"
- You get notification in dashboard
- John can still use all models ⚠️
```

**Day 3 - Critical:**
```
- John continues heavy usage → Cost hits $10/day
- CRITICAL alert: Expensive models BLOCKED 🚨
- John tries Claude Opus → Error: "Blocked, use Gemini"
- John can still use Gemini, GPT-4o Mini, Haiku
```

**Day 4 - Reset:**
```
- Midnight UTC: Blocks automatically reset
- John's daily cost counter → $0
- John can try expensive models again
- Cycle repeats if abuse continues
```

---

## 💰 COST SAVINGS ESTIMATE:

### Before Monitoring:
```
10 Enterprise users × $180/month (Opus abuse) = -$810/month LOSS
```

### After Monitoring:
```
System blocks Opus after $10/day
Max possible loss: $10 × 10 users = $100/month
Savings: $710/month! 🎉
```

### Plus:
- ✅ Alerts help you contact abusive users
- ✅ Data shows which models to promote/restrict
- ✅ Profit margins stay healthy
- ✅ You sleep better at night 😴

---

## 🚨 TROUBLESHOOTING:

### "Database error: no such column"
**Fix:** Run `setup_cost_tracking()` to create tables

### "Admin dashboard shows 0 costs"
**Fix:** Make sure you added `track_message_cost()` to chat endpoint

### "Alerts not showing"
**Fix:** Check Render logs with `heroku logs --tail` or Render dashboard

### "Email alerts not sending"
**Fix:** 
1. Check SMTP credentials are correct
2. Gmail app password (not regular password)
3. Set `ALERT_EMAIL_ENABLED=true`

### "Users complaining about blocks"
**Fix:** 
1. Check if they really exceeded thresholds
2. Manually reset: `UPDATE users SET expensive_models_blocked = 0 WHERE id = X`
3. Adjust thresholds in `COST_THRESHOLDS` if too strict

---

## 🔧 CUSTOMIZATION:

### Change Alert Thresholds:

Edit `COST_THRESHOLDS` in the code:

```python
COST_THRESHOLDS = {
    'pro': {
        'daily_warning': 5.0,    # Change from 3.0 to 5.0
        'daily_critical': 8.0,    # Change from 5.0 to 8.0
        'monthly_max': 49.0
    }
}
```

### Add More Expensive Models to Block:

```python
EXPENSIVE_MODELS = [
    'claude-opus-4', 
    'gpt-4-turbo',
    'gpt-4o'  # Add GPT-4o to block list
]
```

### Change Which Models Cost What:

```python
MODEL_COSTS = {
    'claude-sonnet-4.5': 0.003,
    'claude-opus-4': 0.010,  # Increase if actual cost is higher
    # Add new models here
}
```

---

## 📈 NEXT STEPS:

### Week 1:
- [ ] Deploy the system
- [ ] Monitor dashboard daily
- [ ] Verify alerts are working

### Week 2:
- [ ] Analyze which users cost most
- [ ] Check if any models are more expensive than expected
- [ ] Adjust thresholds if needed

### Month 1:
- [ ] Review profit margins
- [ ] See if any users need tier upgrades
- [ ] Consider promoting cheaper models

---

## ✅ SUCCESS METRICS:

After deploying, you should see:
- ✅ Real-time cost tracking
- ✅ Alerts when users exceed limits
- ✅ Automatic blocks on expensive models
- ✅ Profit margins stay above 40%
- ✅ No surprise API bills

---

## 🎉 YOU'RE DONE!

Your AI Team now has:
- 💰 Real-time cost tracking
- 🚨 Automatic alerts
- 🛡️ Protection from abuse
- 📊 Beautiful admin dashboard
- ✅ Sustainable profit margins

**Want help deploying? Let me know!** 🚀
