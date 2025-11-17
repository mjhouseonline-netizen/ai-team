# 🚀 STRIPE DEPLOYMENT CHECKLIST

## ⚡ QUICK START (5 Steps to Launch)

### 1️⃣ Create Stripe Account
- Go to: https://stripe.com
- Sign up with business details
- Complete verification
- Add bank account

### 2️⃣ Get Your API Keys
- Dashboard → Developers → API Keys
- Copy both secret keys (test & live)
- Keep them safe!

### 3️⃣ Create Products
- Dashboard → Products → Add Product
- Create "AI Team Starter" ($10/month)
- Create "AI Team Pro" ($30/month)
- Copy both Price IDs

### 4️⃣ Set Environment Variables in Render
```bash
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_STARTER_PRICE_ID=price_xxxxx
STRIPE_PRO_PRICE_ID=price_xxxxx
```

### 5️⃣ Deploy & Test
```bash
git add .
git commit -m "Add Stripe payments"
git push origin main
```

---

## 🔑 ENVIRONMENT VARIABLES REFERENCE

### Required for Stripe:

| Variable | Where to Get It | Example | Purpose |
|----------|----------------|---------|----------|
| `STRIPE_SECRET_KEY` | Dashboard → API Keys | `sk_test_xxxxx` | Server-side API auth |
| `STRIPE_PUBLISHABLE_KEY` | Dashboard → API Keys | `pk_test_xxxxx` | Client-side (optional) |
| `STRIPE_WEBHOOK_SECRET` | Dashboard → Webhooks | `whsec_xxxxx` | Verify webhook events |
| `STRIPE_STARTER_PRICE_ID` | Products → Starter → Pricing | `price_xxxxx` | Starter plan price |
| `STRIPE_PRO_PRICE_ID` | Products → Pro → Pricing | `price_xxxxx` | Pro plan price |

### Complete Environment Variables List:

```bash
# Database
DATABASE_URL=postgresql://your_db_url

# Flask
FLASK_SECRET_KEY=your_secret_key_here

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Notion OAuth (if using)
NOTION_CLIENT_ID=your_notion_client_id
NOTION_CLIENT_SECRET=your_notion_client_secret
NOTION_REDIRECT_URI=https://your-app.onrender.com/notion/callback

# Stripe (Test Mode)
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_STARTER_PRICE_ID=price_xxxxx
STRIPE_PRO_PRICE_ID=price_xxxxx

# When going live, replace with:
# STRIPE_SECRET_KEY=sk_live_xxxxx
# STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
```

---

## 📁 FILES TO ADD

### 1. Copy to `templates/` folder:
```
templates/
  ├── pricing.html      ← New
  ├── success.html      ← New
  ├── cancel.html       ← New
  ├── dashboard.html
  ├── profile.html
  ├── settings.html
  └── ... (existing files)
```

### 2. Update existing file:
```
web_app_auth.py         ← Add Stripe code
```

### 3. Update dependencies:
```
requirements.txt        ← Add stripe==7.4.0
```

---

## ✅ PRE-DEPLOYMENT CHECKLIST

### Stripe Account Setup:
- [ ] Created Stripe account
- [ ] Completed business verification
- [ ] Added bank account
- [ ] Got API keys (test mode)
- [ ] Created "Starter" product
- [ ] Created "Pro" product
- [ ] Copied both Price IDs
- [ ] Created webhook endpoint
- [ ] Copied webhook secret

### Code Integration:
- [ ] Added imports to web_app_auth.py
- [ ] Added Stripe configuration
- [ ] Added all 7 new routes
- [ ] Added webhook handler functions
- [ ] Added stripe==7.4.0 to requirements.txt
- [ ] Copied pricing.html to templates/
- [ ] Copied success.html to templates/
- [ ] Copied cancel.html to templates/

### Environment Variables:
- [ ] Added STRIPE_SECRET_KEY
- [ ] Added STRIPE_PUBLISHABLE_KEY
- [ ] Added STRIPE_WEBHOOK_SECRET
- [ ] Added STRIPE_STARTER_PRICE_ID
- [ ] Added STRIPE_PRO_PRICE_ID

### Deployment:
- [ ] Committed all changes
- [ ] Pushed to GitHub
- [ ] Render deployed successfully
- [ ] No errors in Render logs

---

## 🧪 POST-DEPLOYMENT TESTING

### Test Flow:
1. [ ] Visit https://your-app.onrender.com/pricing
2. [ ] Click "Select Starter" button
3. [ ] Redirected to Stripe Checkout
4. [ ] Use test card: 4242 4242 4242 4242
5. [ ] Any future expiry date
6. [ ] Any 3-digit CVC
7. [ ] Complete payment
8. [ ] Redirected to success page
9. [ ] Login to dashboard
10. [ ] Profile shows "Starter" plan
11. [ ] Message limit shows 100
12. [ ] Send a test message - should work

### Verify in Stripe Dashboard:
- [ ] Go to Dashboard → Payments
- [ ] See test payment listed
- [ ] Go to Dashboard → Customers
- [ ] See new customer created
- [ ] Go to Dashboard → Subscriptions
- [ ] See active subscription

### Verify in Database:
- [ ] Check user record
- [ ] `subscription_tier` = 'starter'
- [ ] `daily_message_limit` = 100
- [ ] `stripe_customer_id` = cus_xxxxx
- [ ] `stripe_subscription_id` = sub_xxxxx

### Test Webhook:
- [ ] Go to Stripe Dashboard → Webhooks
- [ ] Click your webhook endpoint
- [ ] See successful delivery attempts
- [ ] Check "Recent Events"
- [ ] Should see `checkout.session.completed`

---

## 🚨 TROUBLESHOOTING GUIDE

### Problem: Can't see pricing page
**Check:**
- [ ] pricing.html is in templates/ folder
- [ ] Route `/pricing` exists in code
- [ ] Deployed successfully

### Problem: Checkout button doesn't work
**Check:**
- [ ] STRIPE_STARTER_PRICE_ID is set
- [ ] STRIPE_PRO_PRICE_ID is set
- [ ] Price IDs are correct format (price_xxxxx)
- [ ] Created products in same Stripe account

### Problem: Payment succeeds but user not upgraded
**Check:**
- [ ] Webhook URL is correct
- [ ] Webhook secret is correct
- [ ] Webhook events are selected
- [ ] Check Render logs for webhook calls
- [ ] Database connection is working

### Problem: Webhook signature verification fails
**Check:**
- [ ] STRIPE_WEBHOOK_SECRET matches dashboard
- [ ] Using correct secret for test/live mode
- [ ] Webhook endpoint URL is exactly right

---

## 🎯 GOING LIVE CHECKLIST

### Before Switching to Live Mode:
- [ ] Tested all payment flows in test mode
- [ ] Verified webhooks work correctly
- [ ] Confirmed database updates work
- [ ] ABN is finalized and verified
- [ ] Business bank account connected
- [ ] Stripe account fully verified
- [ ] Read Stripe's best practices
- [ ] Set up Stripe Radar (fraud prevention)
- [ ] Enabled 3D Secure
- [ ] Set up email receipts

### To Go Live:
1. [ ] Get LIVE API keys from Stripe
2. [ ] Create webhook endpoint for LIVE mode
3. [ ] Update environment variables with LIVE keys:
   ```bash
   STRIPE_SECRET_KEY=sk_live_xxxxx
   STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
   STRIPE_WEBHOOK_SECRET=whsec_live_xxxxx
   ```
4. [ ] Deploy changes
5. [ ] Make test purchase with real card (small amount)
6. [ ] Verify everything works
7. [ ] Announce to users!

---

## 💰 PRICING RECOMMENDATIONS

### Current Setup:
| Plan | Price | Messages | Best For |
|------|-------|----------|----------|
| Free | $0 | 25/day | Trying out |
| Starter | $10 | 100/day | Regular users |
| Pro | $30 | 500/day | Power users |

### Future Options:
- **Annual plans**: 15% discount (2 months free)
- **Enterprise**: Custom pricing for teams
- **Add-ons**: Extra messages, priority support
- **Lifetime deal**: $299 one-time (limited offer)

---

## 📊 METRICS TO TRACK

### Key Metrics:
- Daily signups
- Free → Paid conversion rate
- Monthly Recurring Revenue (MRR)
- Churn rate (cancellations)
- Average Revenue Per User (ARPU)
- Lifetime Value (LTV)

### Stripe Dashboard Shows:
- Total revenue
- Active subscriptions
- Failed payments
- Refund requests
- Customer growth

---

## 🎁 MARKETING IDEAS

### Launch Promotions:
- "First 100 customers: 50% off forever"
- "Launch week: 3 months for price of 2"
- "Refer a friend: both get 1 month free"

### Promo Code + Stripe:
- Keep "Free For Life" codes for special users
- Create discount codes in Stripe for promotions
- Use both systems together strategically

---

## 📞 SUPPORT RESOURCES

### Stripe Resources:
- Docs: https://stripe.com/docs
- Dashboard: https://dashboard.stripe.com
- Status: https://status.stripe.com
- Support: Via dashboard chat

### Your Resources:
- Setup Guide: STRIPE_SETUP_GUIDE.md
- Integration Code: STRIPE_INTEGRATION_CODE.md
- This Checklist: DEPLOYMENT_CHECKLIST.md

---

## 🎉 SUCCESS CRITERIA

You'll know it's working when:

✅ Users can visit pricing page
✅ Checkout redirects to Stripe
✅ Payments process successfully
✅ Users redirected to success page
✅ Database updates with new tier
✅ Message limits increase automatically
✅ Webhooks fire correctly
✅ Users receive Stripe receipts
✅ You see revenue in Stripe dashboard

---

## 🚀 FINAL NOTES

### Remember:
- Always test in TEST mode first
- Keep test/live keys separate
- Never commit API keys to Git
- Monitor webhooks for issues
- Stripe handles PCI compliance
- You're not storing credit cards

### You've Built:
✅ Professional payment system
✅ Automatic billing
✅ Subscription management
✅ Webhook automation
✅ Beautiful UX
✅ Secure processing

**Your SaaS is now revenue-ready!** 💰

---

## 🎊 NEXT STEPS

1. **Today**: Set up Stripe account
2. **This Week**: Deploy and test thoroughly
3. **Next Week**: Go live with real payments
4. **This Month**: Get your first 10 paying customers!

**You've got everything you need. Time to launch!** 🚀

Good luck, Amanda! 🌟
