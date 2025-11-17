# 💳 STRIPE INTEGRATION CODE - Add to web_app_auth.py

## 📦 STEP 1: Add Import at the Top

```python
import stripe
import os
from datetime import datetime
```

---

## ⚙️ STEP 2: Add Stripe Configuration (after app config, before routes)

```python
# ============================================
# STRIPE CONFIGURATION
# ============================================
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
STRIPE_STARTER_PRICE_ID = os.environ.get('STRIPE_STARTER_PRICE_ID')
STRIPE_PRO_PRICE_ID = os.environ.get('STRIPE_PRO_PRICE_ID')
```

---

## 🎨 STEP 3: Add Pricing Page Route

```python
@app.route('/pricing')
@login_required
def pricing():
    """Display pricing page with Stripe checkout"""
    return render_template('pricing.html',
                         current_plan=current_user.subscription_tier,
                         starter_price_id=STRIPE_STARTER_PRICE_ID,
                         pro_price_id=STRIPE_PRO_PRICE_ID)
```

---

## 💳 STEP 4: Add Stripe Checkout Session Route

```python
@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create Stripe checkout session for subscription"""
    try:
        price_id = request.form.get('price_id')
        
        # Determine plan details based on price_id
        if price_id == STRIPE_STARTER_PRICE_ID:
            plan_name = 'starter'
        elif price_id == STRIPE_PRO_PRICE_ID:
            plan_name = 'pro'
        else:
            return jsonify({'error': 'Invalid price ID'}), 400
        
        # Create or retrieve Stripe customer
        if current_user.stripe_customer_id:
            customer_id = current_user.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={'user_id': current_user.id}
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()
            customer_id = customer.id
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.host_url + 'success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url + 'cancel',
            metadata={
                'user_id': current_user.id,
                'plan': plan_name
            }
        )
        
        return redirect(checkout_session.url)
        
    except Exception as e:
        print(f"Error creating checkout session: {str(e)}")
        flash('Error creating checkout session. Please try again.', 'error')
        return redirect(url_for('pricing'))
```

---

## ✅ STEP 5: Add Success Page Route

```python
@app.route('/success')
@login_required
def success():
    """Payment success page"""
    session_id = request.args.get('session_id')
    
    try:
        # Retrieve session details
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Get plan details
        plan_name = session.metadata.get('plan', 'unknown')
        
        # Get daily limit based on plan
        limits = {
            'starter': 100,
            'pro': 500
        }
        daily_limit = limits.get(plan_name, 100)
        
        return render_template('success.html',
                             plan_name=plan_name.capitalize(),
                             daily_limit=daily_limit)
    except Exception as e:
        print(f"Error retrieving session: {str(e)}")
        return render_template('success.html',
                             plan_name='Unknown',
                             daily_limit=100)
```

---

## ❌ STEP 6: Add Cancel Page Route

```python
@app.route('/cancel')
@login_required
def cancel():
    """Payment cancelled page"""
    return render_template('cancel.html')
```

---

## 🔔 STEP 7: Add Webhook Handler (CRITICAL!)

```python
@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session_completed(session)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_invoice_payment_succeeded(invoice)
    
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_invoice_payment_failed(invoice)
    
    return jsonify({'status': 'success'})


def handle_checkout_session_completed(session):
    """Handle completed checkout session"""
    try:
        user_id = session['metadata']['user_id']
        plan = session['metadata']['plan']
        customer_id = session['customer']
        subscription_id = session['subscription']
        
        user = User.query.get(user_id)
        if user:
            user.stripe_customer_id = customer_id
            user.stripe_subscription_id = subscription_id
            user.subscription_tier = plan
            
            # Set message limits
            if plan == 'starter':
                user.daily_message_limit = 100
            elif plan == 'pro':
                user.daily_message_limit = 500
            
            db.session.commit()
            print(f"✅ User {user.email} upgraded to {plan}")
        
    except Exception as e:
        print(f"Error handling checkout session: {str(e)}")


def handle_subscription_updated(subscription):
    """Handle subscription updates"""
    try:
        customer_id = subscription['customer']
        status = subscription['status']
        
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            if status == 'active':
                # Subscription is active
                print(f"✅ Subscription active for {user.email}")
            elif status == 'canceled':
                # Subscription cancelled
                user.subscription_tier = 'free'
                user.daily_message_limit = 25
                user.stripe_subscription_id = None
                db.session.commit()
                print(f"❌ Subscription cancelled for {user.email}")
    
    except Exception as e:
        print(f"Error handling subscription update: {str(e)}")


def handle_subscription_deleted(subscription):
    """Handle subscription deletion"""
    try:
        customer_id = subscription['customer']
        
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            user.subscription_tier = 'free'
            user.daily_message_limit = 25
            user.stripe_subscription_id = None
            db.session.commit()
            print(f"🗑️ Subscription deleted for {user.email}")
    
    except Exception as e:
        print(f"Error handling subscription deletion: {str(e)}")


def handle_invoice_payment_succeeded(invoice):
    """Handle successful payment"""
    try:
        customer_id = invoice['customer']
        amount_paid = invoice['amount_paid'] / 100  # Convert from cents
        
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            print(f"💰 Payment of ${amount_paid} succeeded for {user.email}")
    
    except Exception as e:
        print(f"Error handling payment success: {str(e)}")


def handle_invoice_payment_failed(invoice):
    """Handle failed payment"""
    try:
        customer_id = invoice['customer']
        
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            print(f"⚠️ Payment failed for {user.email}")
            # You might want to send an email notification here
    
    except Exception as e:
        print(f"Error handling payment failure: {str(e)}")
```

---

## 📝 STEP 8: Update requirements.txt

Add this line to your `requirements.txt`:

```
stripe==7.4.0
```

---

## 🔄 STEP 9: Update Database Schema (if needed)

Your User model should already have these fields, but verify:

```python
class User(UserMixin, db.Model):
    # ... existing fields ...
    
    # Stripe fields (should already exist)
    stripe_customer_id = db.Column(db.String(100), unique=True, nullable=True)
    stripe_subscription_id = db.Column(db.String(100), unique=True, nullable=True)
    subscription_tier = db.Column(db.String(20), default='free')
    daily_message_limit = db.Column(db.Integer, default=25)
```

---

## ✅ INTEGRATION CHECKLIST:

- [ ] Added imports at top of file
- [ ] Added Stripe configuration section
- [ ] Added `/pricing` route
- [ ] Added `/create-checkout-session` route
- [ ] Added `/success` route
- [ ] Added `/cancel` route
- [ ] Added `/webhook` route and helper functions
- [ ] Updated `requirements.txt`
- [ ] Copied HTML files to `templates/` folder
- [ ] Set environment variables in Render
- [ ] Tested in test mode

---

## 🧪 TESTING STEPS:

1. Deploy with test mode keys
2. Visit `/pricing`
3. Click "Select Starter"
4. Use test card: 4242 4242 4242 4242
5. Complete checkout
6. Verify redirect to success page
7. Check database - user should be upgraded
8. Check Stripe dashboard - subscription should exist

---

## 🎉 YOU'RE DONE!

After adding all this code and deploying, you'll have:

✅ Working payment system
✅ Automatic subscription management
✅ Webhook event handling
✅ Beautiful pricing page
✅ Success/cancel pages
✅ Database updates

**Now you can start making money!** 💰

---

## 📧 Questions?

- Check the STRIPE_SETUP_GUIDE.md for account setup
- Test everything in test mode first
- Use Stripe Dashboard to monitor payments
- Webhook logs help debug issues

**You've got this!** 🚀
