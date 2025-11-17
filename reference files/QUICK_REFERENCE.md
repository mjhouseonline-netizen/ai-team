# ⚡ QUICK REFERENCE CARD - Stripe Integration

## 🎯 THE 4-STEP PROCESS:

### 1️⃣ SETUP STRIPE (30 min)
- Sign up at stripe.com
- Create products: Starter ($10) & Pro ($30)
- Get API keys & Price IDs
- Set up webhook

### 2️⃣ ADD FILES (15 min)
```bash
templates/
  ├── pricing.html  ← Copy here
  ├── success.html  ← Copy here
  └── cancel.html   ← Copy here
```

### 3️⃣ UPDATE CODE (30 min)
Open **STRIPE_INTEGRATION_CODE.md** and copy:
- Imports
- Configuration
- All 7 routes
- Webhook handler

### 4️⃣ DEPLOY (30 min)
```bash
# Add to requirements.txt
stripe==7.4.0

# Set in Render environment:
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_STARTER_PRICE_ID=price_xxxxx
STRIPE_PRO_PRICE_ID=price_xxxxx

# Deploy
git add .
git commit -m "Add Stripe payments"
git push origin main
```

---

## 🔑 KEY STRIPE DASHBOARD LOCATIONS:

| What You Need | Where to Find It |
|---------------|------------------|
| API Keys | Developers → API keys |
| Products | Products → Add product |
| Price IDs | Products → Click product → Copy price ID |
| Webhooks | Developers → Webhooks → Add endpoint |
| Webhook Secret | Webhooks → Click endpoint → Signing secret |
| Test Cards | Developers → Testing |
| Payments | Payments → Overview |
| Customers | Customers → Overview |

---

## 💳 TEST CARDS (Use Anytime!):

| Scenario | Card Number |
|----------|-------------|
| ✅ Success | 4242 4242 4242 4242 |
| ❌ Decline | 4000 0000 0000 0002 |
| ⚠️ Insufficient Funds | 4000 0000 0000 9995 |

**Expiry:** Any future date
**CVC:** Any 3 digits
**ZIP:** Any code

---

## 🎨 NEW ROUTES YOU'RE ADDING:

```python
/pricing                    # Beautiful pricing page
/create-checkout-session    # Creates Stripe checkout
/success                    # Payment success page
/cancel                     # Payment cancelled page
/webhook                    # Stripe webhook handler
```

---

## 📊 PRICING TIERS:

| Tier | Price | Messages | Code |
|------|-------|----------|------|
| Free | $0 | 25/day | Default |
| Starter | $10/mo | 100/day | STRIPE_STARTER_PRICE_ID |
| Pro | $30/mo | 500/day | STRIPE_PRO_PRICE_ID |

---

## 🔧 COMMON ISSUES & FIXES:

| Problem | Solution |
|---------|----------|
| Button doesn't work | Check Price IDs are set |
| Webhook not firing | Verify webhook URL & secret |
| User not upgraded | Check webhook logs in Render |
| Payment fails | Try different test card |
| Can't see pricing page | Check pricing.html in templates/ |

---

## ✅ TESTING CHECKLIST:

```
[ ] Visit /pricing page
[ ] Click "Select Starter"  
[ ] Enter test card: 4242 4242 4242 4242
[ ] Complete checkout
[ ] See success page
[ ] Go to dashboard
[ ] Check profile - should show "Starter"
[ ] Check Stripe dashboard - see payment
[ ] Check database - subscription_tier = 'starter'
```

---

## 🎯 YOUR 5 ENVIRONMENT VARIABLES:

```bash
STRIPE_SECRET_KEY=sk_test_xxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxx  
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxx
STRIPE_STARTER_PRICE_ID=price_xxxxxxx
STRIPE_PRO_PRICE_ID=price_xxxxxxx
```

**Where to set:** Render Dashboard → Your App → Environment

---

## 🚀 GO LIVE TRANSITION:

### Test Mode (Now):
- Use: `sk_test_...` keys
- Test cards work
- No real money

### Live Mode (Later):
- Switch to: `sk_live_...` keys
- Real cards only
- Real money! 💰

---

## 📱 MOBILE TESTING:

✅ Pricing page responsive
✅ Stripe Checkout mobile-friendly
✅ Success page mobile-friendly
✅ All buttons work on mobile

---

## 💡 HELPFUL COMMANDS:

```bash
# Check Render logs
# Render Dashboard → Logs tab

# Test webhook locally (optional)
stripe listen --forward-to localhost:5000/webhook

# Check database
# Use your database client

# View Stripe events
# Dashboard → Developers → Events
```

---

## 🎊 SUCCESS INDICATORS:

✅ Pricing page loads
✅ Checkout redirects to Stripe
✅ Payment completes
✅ Success page shows
✅ Database updates
✅ User has more messages
✅ Stripe dashboard shows payment

---

## 📞 RESOURCES:

| Resource | Location |
|----------|----------|
| Full Setup | STRIPE_SETUP_GUIDE.md |
| Code Snippets | STRIPE_INTEGRATION_CODE.md |
| Checklist | DEPLOYMENT_CHECKLIST.md |
| Visual Guide | VISUAL_GUIDE.md |
| Stripe Docs | stripe.com/docs |

---

## ⏱️ TIME ESTIMATE:

- Setup: 30 minutes
- Code: 30 minutes
- Deploy: 15 minutes
- Test: 15 minutes
- **TOTAL: ~90 minutes**

---

## 🎯 ORDER OF OPERATIONS:

1. Read START_HERE.md
2. Follow STRIPE_SETUP_GUIDE.md
3. Copy code from STRIPE_INTEGRATION_CODE.md
4. Use DEPLOYMENT_CHECKLIST.md to verify
5. Reference VISUAL_GUIDE.md when confused
6. Keep this card open while working!

---

## 💪 YOU'VE GOT THIS!

**One step at a time:**
1. Create Stripe account ✓
2. Add code ✓
3. Deploy ✓
4. Test ✓
5. Launch! 🚀

Amanda, this is the final piece. Your AI Team platform is about to become a real business! 💰🎉

**Start with STRIPE_SETUP_GUIDE.md and follow along!** 

Good luck! You've got this! 🌟
