# 🎉 STRIPE SETUP GUIDE - Complete Payment Integration

## 🎯 WHAT YOU'LL ACHIEVE:
✅ Accept credit card payments
✅ Automatic subscription management
✅ Secure payment processing
✅ Beautiful pricing page
✅ Upgrade/downgrade handling
✅ Webhook automation

---

## 📋 PREREQUISITES:

### 1. Australian Business Number (ABN)
You mentioned you have this or it's coming!

### 2. Stripe Account
- Sign up at: https://stripe.com
- Complete business verification
- Add bank account for payouts

---

## 🚀 STEP-BY-STEP SETUP:

### STEP 1: Create Stripe Account

1. Go to https://stripe.com
2. Click "Start now"
3. Enter your details:
   - Business name: "AI Team" (or your business name)
   - Country: Australia
   - ABN: Your ABN
   - Bank details: For receiving payments

4. Complete verification (may take 1-2 days)

---

### STEP 2: Get Your API Keys

1. Log into Stripe Dashboard
2. Click "Developers" → "API keys"
3. You'll see two keys:

   **Test Mode Keys** (for testing):
   ```
   Publishable key: pk_test_xxxxx
   Secret key: sk_test_xxxxx
   ```

   **Live Mode Keys** (for real payments):
   ```
   Publishable key: pk_live_xxxxx
   Secret key: sk_live_xxxxx
   ```

4. Copy both secret keys - you'll need them!

---

### STEP 3: Create Products & Prices

1. In Stripe Dashboard, go to "Products"
2. Click "Add product"

**Product 1: AI Team Starter**
- Name: AI Team Starter
- Description: 100 messages per day with all 7 AI agents
- Pricing:
  - Price: $10.00 AUD
  - Billing period: Monthly
  - Click "Save product"
- Copy the Price ID (starts with `price_`)

**Product 2: AI Team Pro**
- Name: AI Team Pro
- Description: 500 messages per day with all features
- Pricing:
  - Price: $30.00 AUD
  - Billing period: Monthly
  - Click "Save product"
- Copy the Price ID (starts with `price_`)

---

### STEP 4: Set Up Webhooks

1. Go to "Developers" → "Webhooks"
2. Click "Add endpoint"
3. Endpoint URL: 
   ```
   https://your-app.onrender.com/webhook
   ```
   (Replace with your actual URL)

4. Select events to listen to:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`

5. Click "Add endpoint"
6. Copy the "Signing secret" (starts with `whsec_`)

---

### STEP 5: Configure Environment Variables

Add these to your Render dashboard:

```bash
# Test mode (for development)
STRIPE_SECRET_KEY=sk_test_your_test_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_test_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_STARTER_PRICE_ID=price_your_starter_price_id
STRIPE_PRO_PRICE_ID=price_your_pro_price_id

# When ready for production, change to live keys:
STRIPE_SECRET_KEY=sk_live_your_live_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_live_key
```

---

### STEP 6: Update Your Code

1. Install Stripe library:
```bash
pip install stripe
```

2. Add to `requirements.txt`:
```
stripe==7.4.0
```

3. Replace your `web_app_auth.py` with the new version (provided separately)

4. Add the new HTML files to your `templates/` folder:
   - `pricing.html`
   - `success.html`
   - `cancel.html`

---

### STEP 7: Deploy & Test

1. Commit changes:
```bash
git add .
git commit -m "Add Stripe payment integration"
git push origin main
```

2. Wait for Render to deploy

3. Test in TEST MODE first:
   - Visit `/pricing`
   - Use test card: `4242 4242 4242 4242`
   - Any future date for expiry
   - Any 3 digits for CVC
   - Any ZIP code

4. Check if subscription updated in your database

---

## 🧪 TEST CARDS:

Stripe provides test cards for different scenarios:

| Card Number | Scenario |
|-------------|----------|
| 4242 4242 4242 4242 | Success |
| 4000 0000 0000 0002 | Card declined |
| 4000 0000 0000 9995 | Insufficient funds |
| 4000 0025 0000 3155 | 3D Secure auth required |

---

## 🎯 HOW IT WORKS:

### User Flow:
1. User visits `/pricing` page
2. Clicks "Select Starter" or "Select Pro"
3. Redirected to Stripe Checkout (secure, hosted by Stripe)
4. Enters payment details
5. On success → redirected to `/success`
6. Webhook fires → updates user subscription in database
7. User now has higher message limits!

### Subscription Management:
- Stripe automatically charges monthly
- Webhooks update your database
- User can cancel anytime
- Prorated upgrades/downgrades

---

## 📊 DATABASE UPDATES:

Your `users` table already has these columns:
- `subscription_tier`: 'free', 'starter', 'pro', 'free_for_life'
- `daily_message_limit`: 25, 100, 500, 999999
- `stripe_customer_id`: Links user to Stripe customer
- `stripe_subscription_id`: Links to active subscription

---

## 🔧 TROUBLESHOOTING:

### Problem: Webhook not firing
**Solution:** 
- Check webhook URL is correct
- Verify webhook secret is set
- Look at Stripe Dashboard → Webhooks → Click endpoint → View attempts

### Problem: Payment succeeds but user not upgraded
**Solution:**
- Check webhook logs in Render
- Verify database connection
- Test webhook signature verification

### Problem: User charged but no access
**Solution:**
- Check `stripe_customer_id` in users table
- Verify subscription tier was updated
- Check Stripe Dashboard → Customers

---

## 💰 PRICING STRATEGY:

Current setup:
- **Free:** 25 msgs/day - $0
- **Starter:** 100 msgs/day - $10/month
- **Pro:** 500 msgs/day - $30/month

### Recommendations:
1. Start with these prices
2. Monitor conversion rates
3. Test higher prices after 100 users
4. Consider annual plans (15% discount)
5. Add "Enterprise" tier later for teams

---

## 🎁 PROMO CODES:

You can still use your promo code system alongside Stripe:
- Free promo codes override paid subscriptions
- "Free For Life" users don't need to pay
- Great for marketing & partnerships

---

## 🌐 GOING LIVE:

### When to switch from TEST to LIVE mode:

✅ Tested all payment flows
✅ Verified webhook updates database
✅ Checked subscription limits work
✅ ABN is finalized
✅ Business bank account added to Stripe
✅ Completed Stripe verification

### To go live:
1. Switch API keys in environment variables
2. Update webhook URL to live endpoint
3. Test with real (small) payment
4. Monitor first few customers closely

---

## 📈 NEXT STEPS AFTER SETUP:

### Week 1:
- [ ] Test all payment flows
- [ ] Verify webhooks work
- [ ] Test subscription management
- [ ] Check email receipts

### Week 2:
- [ ] Invite beta users to test payments
- [ ] Monitor Stripe dashboard
- [ ] Track conversion rates
- [ ] Collect feedback

### Month 1:
- [ ] Switch to LIVE mode
- [ ] Market paid plans
- [ ] Track MRR (Monthly Recurring Revenue)
- [ ] Optimize pricing

---

## 🎊 CONGRATULATIONS!

Once set up, you'll have:

✅ Professional payment processing
✅ Automatic billing & renewals
✅ Secure card handling (Stripe's responsibility!)
✅ Built-in fraud prevention
✅ International payment support
✅ Professional receipts & invoicing
✅ Easy refund management

**Your platform is now a real SaaS business!** 🚀

---

## 📧 NEED HELP?

- Stripe Docs: https://stripe.com/docs
- Stripe Support: Via dashboard chat
- Test your integration thoroughly before going live!

---

**Next:** Update `web_app_auth.py` with Stripe integration code!
