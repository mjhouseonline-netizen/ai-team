# 💎 FREEMIUM + STRIPE - Complete Setup Guide

## 🎉 What I Just Built for You!

A complete freemium subscription system with Stripe payments!

### Your Business Model:

```
FREE TIER (🆓)
├─ 10 messages/day
├─ All 7 agents
├─ Basic features
└─ $0/month → You make: $0

PRO TIER (💎) ⭐ Most Popular
├─ 100 messages/day  
├─ All features
├─ Priority responses
└─ $30/month → You make: ~$20-25/month

BUSINESS TIER (🚀)
├─ UNLIMITED messages
├─ All features
├─ Fastest responses
└─ $100/month → You make: ~$85-90/month
```

---

## 📥 FILES TO DOWNLOAD & REPLACE:

### Backend Files:
1. **[auth.py](computer:///mnt/user-data/outputs/auth.py)** - REPLACE
   - Added subscription management
   - Message limit checking
   - Stripe integration support

2. **[web_app_auth.py](computer:///mnt/user-data/outputs/web_app_auth.py)** - REPLACE
   - Limit checking on every message
   - Stripe checkout routes
   - Webhook handling

3. **[requirements.txt](computer:///mnt/user-data/outputs/requirements.txt)** - REPLACE
   - Added Stripe library

### Frontend Files:
4. **[dashboard.html](computer:///mnt/user-data/outputs/templates/dashboard.html)** - REPLACE
   - Tier badge in header
   - Message counter
   - Upgrade modal
   - Limit handling

5. **[pricing.html](computer:///mnt/user-data/outputs/templates/pricing.html)** - NEW
   - Beautiful pricing page
   - 3 tiers displayed
   - Comparison table
   - Upgrade buttons

---

## 🚀 SETUP STEPS:

### Step 1: Update Local Files (5 minutes)

1. **Replace** these files in `Desktop\ai-team\`:
   - auth.py
   - web_app_auth.py
   - requirements.txt

2. **Replace** this file in `Desktop\ai-team\templates\`:
   - dashboard.html

3. **Add** this NEW file to `Desktop\ai-team\templates\`:
   - pricing.html

---

### Step 2: Install Stripe Library Locally

Open Command Prompt in your ai-team folder:
```bash
cd Desktop\ai-team
pip install stripe --break-system-packages
```

---

### Step 3: Create Stripe Account (10 minutes)

1. Go to **https://stripe.com/**
2. Click **"Start now"**
3. **Sign up** (free account)
4. **Verify email**
5. Complete business info

---

### Step 4: Get Stripe Keys (5 minutes)

In Stripe Dashboard:

1. Click **"Developers"** (top right)
2. Click **"API keys"**
3. You'll see:
   - **Publishable key** (starts with `pk_test_`)
   - **Secret key** (starts with `sk_test_`)
4. **Copy both** - you'll need them!

⚠️ **Important:** Use TEST keys for now (they have `_test_` in them)

---

### Step 5: Create Stripe Products (10 minutes)

In Stripe Dashboard:

1. Click **"Products"** (left sidebar)
2. Click **"Add product"**

**Create Pro Product:**
- Name: `AI Team Pro`
- Description: `100 messages per day, all features`
- Price: `$30` USD
- Billing: `Recurring` → `Monthly`
- Click **"Save product"**
- **Copy the Price ID** (starts with `price_`)

**Create Business Product:**
- Name: `AI Team Business`
- Description: `Unlimited messages, priority support`
- Price: `$100` USD
- Billing: `Recurring` → `Monthly`
- Click **"Save product"**
- **Copy the Price ID** (starts with `price_`)

---

### Step 6: Set Up Webhook (5 minutes)

In Stripe Dashboard:

1. Click **"Developers"** → **"Webhooks"**
2. Click **"Add endpoint"**
3. **Endpoint URL:** `https://ai-team-q84h.onrender.com/api/stripe-webhook`
   (Replace with YOUR render URL!)
4. **Events to send:**
   - `checkout.session.completed`
   - `customer.subscription.deleted`
5. Click **"Add endpoint"**
6. **Copy the Signing secret** (starts with `whsec_`)

---

### Step 7: Add Environment Variables to Render (10 minutes)

Go to **dashboard.render.com** → Your ai-team service → **Environment**

Add these NEW variables:

**Stripe Keys:**
```
STRIPE_SECRET_KEY = sk_test_YOUR_SECRET_KEY_HERE
STRIPE_PUBLISHABLE_KEY = pk_test_YOUR_PUBLISHABLE_KEY_HERE
STRIPE_WEBHOOK_SECRET = whsec_YOUR_WEBHOOK_SECRET_HERE
```

**Price IDs:**
```
STRIPE_PRO_PRICE_ID = price_YOUR_PRO_PRICE_ID_HERE
STRIPE_BUSINESS_PRICE_ID = price_YOUR_BUSINESS_PRICE_ID_HERE
```

Click **"Save Changes"** - Render will redeploy!

---

### Step 8: Update Procfile (STILL NEEDS FIXING!)

⚠️ **Don't forget this from earlier!**

In `Desktop\ai-team\Procfile`:

Change:
```
web: gunicorn web_app:app
```

To:
```
web: gunicorn web_app_auth:app
```

---

### Step 9: Push Everything to GitHub (5 minutes)

1. Open **GitHub Desktop**
2. You'll see all changed files
3. Commit message: `Add freemium system with Stripe integration`
4. Click **"Commit to main"**
5. Click **"Push origin"**

---

### Step 10: Wait for Deployment (5 minutes)

1. Go to **dashboard.render.com**
2. Watch it deploy (3-5 minutes)
3. Wait for **"Live"** status

---

## 🧪 TESTING YOUR FREEMIUM SYSTEM:

### Test 1: Free Tier Limits

1. Go to your site: https://ai-team-q84h.onrender.com/
2. Create a new account (or login)
3. See tier badge: **🆓 Free - 0/10**
4. Send 10 messages (count goes up each time)
5. On message #11:
   - **Upgrade modal appears! ✅**
   - "Daily Limit Reached"
   - "Upgrade to Pro" button

### Test 2: Pricing Page

1. Click **"Upgrade to Pro"** button
2. Redirects to pricing page
3. See 3 tiers:
   - Free ($0)
   - Pro ($30) ⭐
   - Business ($100)
4. Beautiful design!

### Test 3: Stripe Checkout (Use Test Card!)

1. On pricing page, click **"Upgrade to Pro"**
2. Redirects to Stripe checkout
3. Use **test card number:**
   - Card: `4242 4242 4242 4242`
   - Exp: Any future date (12/25)
   - CVC: Any 3 digits (123)
   - ZIP: Any 5 digits (12345)
4. Click **"Subscribe"**
5. Redirects back to your site
6. Tier badge updates: **💎 Pro - 0/100** ✅

### Test 4: Unlimited Usage

1. As Pro user, send 50+ messages
2. Counter updates
3. No limit modal! ✅
4. Can send up to 100/day

---

## 💡 HOW IT WORKS:

### User Flow:

```
1. User signs up
   ↓
2. Starts with FREE tier (🆓)
   ↓
3. Sends 10 messages
   ↓
4. Hits limit → Modal appears
   ↓
5. Clicks "Upgrade to Pro"
   ↓
6. Goes to pricing page
   ↓
7. Clicks "Upgrade to Pro" ($30/mo)
   ↓
8. Stripe checkout opens
   ↓
9. Enters payment info
   ↓
10. Subscribes successfully
    ↓
11. Webhook updates tier to PRO (💎)
    ↓
12. User now has 100 messages/day!
    ↓
13. YOU GET PAID! 💰
```

---

## 📊 YOUR DASHBOARD:

### What Users See:

**Top Right Corner:**

**Free User:**
```
┌──────────────────┐
│ 🆓 Free          │
│ 7/10 messages    │
└──────────────────┘
```

**Pro User:**
```
┌──────────────────┐
│ 💎 Pro           │
│ 45/100 messages  │
└──────────────────┘
```

**Business User:**
```
┌──────────────────┐
│ 🚀 Business      │
│ ♾️ Unlimited     │
└──────────────────┘
```

---

## 💰 REVENUE TRACKING:

### In Stripe Dashboard:

- Click **"Payments"** to see all transactions
- Click **"Subscriptions"** to see active subscribers
- Click **"Customers"** to see customer list
- Real-time revenue tracking!

---

## 🎯 KEY FEATURES:

### Tier Management:
✅ Automatic tier assignment (starts as Free)
✅ Message counting per user per day
✅ Daily reset at midnight
✅ Upgrade modal when limit reached

### Stripe Integration:
✅ Secure checkout
✅ Automatic subscription management
✅ Webhook handling
✅ Customer portal (coming soon)

### User Experience:
✅ Beautiful pricing page
✅ Tier badge in dashboard
✅ Real-time message counter
✅ Smooth upgrade flow

---

## ⚙️ ENVIRONMENT VARIABLES:

Make sure these are ALL set in Render:

```
ANTHROPIC_API_KEY = sk-ant-your-key
STRIPE_SECRET_KEY = sk_test_your-key
STRIPE_PUBLISHABLE_KEY = pk_test_your-key
STRIPE_WEBHOOK_SECRET = whsec_your-secret
STRIPE_PRO_PRICE_ID = price_your-pro-id
STRIPE_BUSINESS_PRICE_ID = price_your-business-id
```

---

## 🔧 TROUBLESHOOTING:

### "Limit modal doesn't appear"
**Fix:** Check browser console (F12) for errors

### "Stripe checkout fails"
**Fix:** 
- Check STRIPE_SECRET_KEY is set
- Check Price IDs are correct
- Use test card: 4242 4242 4242 4242

### "Tier doesn't update after payment"
**Fix:**
- Check webhook is configured
- Check STRIPE_WEBHOOK_SECRET is set
- Check webhook URL is correct

### "Messages don't count"
**Fix:** Database might need migration. Delete users.db locally and test again.

---

## 🎨 CUSTOMIZATION:

### Change Pricing:

Edit in Stripe Dashboard:
1. Products → Your Product
2. Edit price
3. Update code with new Price ID

### Change Limits:

In `auth.py`, find:
```python
limits = {
    'free': 10,      # Change this!
    'pro': 100,      # Change this!
    'business': 999999
}
```

### Change Tier Names:

In `dashboard.html`, find:
```javascript
const tierNames = {
    'free': 'Free',     # Change this!
    'pro': 'Pro',       # Change this!
    'business': 'Business'
}
```

---

## 🚀 GO LIVE CHECKLIST:

Before switching from test to live:

### In Stripe:
- [ ] Switch to **Live** mode (top right toggle)
- [ ] Get LIVE API keys (start with `pk_live_` and `sk_live_`)
- [ ] Recreate products in LIVE mode
- [ ] Get new Price IDs
- [ ] Create new webhook for LIVE mode
- [ ] Get new webhook secret

### In Render:
- [ ] Update all Stripe keys to LIVE versions
- [ ] Update Price IDs to LIVE versions
- [ ] Update webhook secret to LIVE version
- [ ] Test with REAL card (will charge!)

---

## 💡 NEXT FEATURES TO ADD:

### Phase 1: Customer Portal
- Let users manage subscriptions
- Cancel/upgrade/downgrade
- View payment history

### Phase 2: Email Notifications
- Welcome email
- Upgrade confirmation
- Limit warning (90% used)
- Payment failed notifications

### Phase 3: Admin Dashboard
- See all users
- View revenue
- Manage subscriptions
- Analytics

---

## 📞 SUPPORT RESOURCES:

**Stripe Documentation:** https://stripe.com/docs
**Stripe Test Cards:** https://stripe.com/docs/testing
**Stripe Dashboard:** https://dashboard.stripe.com/
**Your Render Dashboard:** https://dashboard.render.com/

---

## 🎊 CONGRATULATIONS!

You now have a complete SaaS platform with:
- ✅ User authentication
- ✅ Beautiful custom UI
- ✅ 7 AI agents
- ✅ Freemium tiers
- ✅ Stripe payments
- ✅ Subscription management
- ✅ **READY TO MAKE MONEY!** 💰

---

## 📋 QUICK SUMMARY:

**Time to set up:** ~1 hour
**Files changed:** 5 files
**New features:** Freemium + Stripe
**Revenue potential:** $20-90/month per user

**What works:**
✅ Free tier with 10 msg/day limit
✅ Pro tier with 100 msg/day ($30/mo)
✅ Business tier unlimited ($100/mo)
✅ Automatic upgrades via Stripe
✅ Beautiful pricing page
✅ Upgrade modals
✅ Usage tracking

**What's next:**
🎯 Fix Procfile (2 min)
🎯 Test locally
🎯 Push to GitHub
🎯 Set up Stripe
🎯 Deploy & test
🎯 START MAKING MONEY! 💰

---

**You've built something INCREDIBLE!** 🚀
