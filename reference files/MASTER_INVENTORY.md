# 📋 MASTER INVENTORY - AI TEAM PLATFORM

**Last Updated:** December 2, 2024  
**Platform:** ai-team.skillsoul.store  
**Tech Stack:** Flask + Python + SQLite + Render

---

## 🎯 **CURRENT STATE SUMMARY:**

### **What You Have Deployed:**
- ✅ AI Team Platform with 8 AI models
- ✅ 7 core agents (Luna, Mila, Sage, Ember, Sol, Nova, Theo)
- ✅ Voice input/output, image generation, file upload
- ✅ Website builder (Nova/Theo generate HTML files)
- ✅ Custom agent creator
- ✅ Subscription system (Free/$10/$30)
- ✅ Stripe payment integration
- ✅ Promo code system
- ✅ Admin portal
- ✅ Notion OAuth integration
- ✅ Google Drive integration (optional)

### **What Needs Deploying (From This Session):**
1. **dashboard_ULTIMATE_FIXED.html** → `/templates/dashboard.html` (CRITICAL - Mobile fix!)
2. **pricing_UPDATED.html** → `/templates/pricing.html` (Promo code redemption)
3. **promo_codes_UPDATED.html** → `/templates/promo_codes.html` (Correct plan names)
4. **web_app_auth_UPDATED.py** → `/web_app_auth.py` (Backend with single-use codes)
5. **generate_free4life_codes.py** → Run to create 10 VIP codes

---

## 🗂️ **FILE STRUCTURE:**

### **✅ CORRECT FILES (Deploy These):**

#### **1. Dashboard - ULTIMATE Version**
```
File: dashboard_ULTIMATE_FIXED.html
Location: /mnt/user-data/outputs/
Deploy to: /templates/dashboard.html
Size: 1,180 lines / 38KB

Features:
✅ Modern ChatGPT-style layout
✅ Dark sidebar (280px, #1a1a1a)
✅ Clean white main area
✅ Mobile input fix (sticky at bottom)
✅ Combined buttons dropdown (➕ Options)
✅ Floating preview window
✅ All 7 agents with avatars
✅ Model selector (8 models)
✅ Voice, image, file upload
✅ Custom agent creator
✅ Prompt builder
✅ Professional green theme (#10a37f)

Layout:
┌────────┬────────────────┐
│Sidebar │ Main Chat Area │
│(dark)  │ (white/clean)  │
│Agents  │ Messages       │
│Tools   │ Input (sticky) │
└────────┴────────────────┘

Mobile: Sidebar hidden, toggle button, sticky input ✅
```

#### **2. Pricing Page**
```
File: pricing_UPDATED.html
Location: /mnt/user-data/outputs/
Deploy to: /templates/pricing.html
Size: ~600 lines

Features:
✅ 3 pricing tiers: Free ($0), Starter ($10), Pro ($30)
✅ Promo code input section at top
✅ Real-time code validation
✅ Price updates (shows FREE when code applied)
✅ Green gradient jungle theme
✅ FAQ section
✅ Mobile responsive
✅ Glass-morphism cards

Pricing:
- Free: $0/month, 25 messages/day
- Starter: $10/month, 100 messages/day
- Pro: $30/month, 500 messages/day

Promo Codes:
User enters code → Validates → Price shows FREE → Subscribe
```

#### **3. Promo Codes Admin**
```
File: promo_codes_UPDATED.html
Location: /mnt/user-data/outputs/
Deploy to: /templates/promo_codes.html
Size: ~400 lines

Features:
✅ Create promo codes (Starter or Pro)
✅ Set max uses
✅ Track usage (X/100)
✅ Active/Inactive status
✅ Copy code button
✅ Delete codes
✅ Correct plan names (Starter/Pro)

Admin Only: User ID 1
```

#### **4. Backend**
```
File: web_app_auth_UPDATED.py
Location: /mnt/user-data/outputs/
Deploy to: /web_app_auth.py
Size: ~3,700 lines

Features:
✅ User authentication (Flask-Login)
✅ Subscription tiers (free, starter, pro)
✅ Stripe integration (checkout, webhooks)
✅ Promo code system with single_use support
✅ Multi-use codes (e.g., 100 uses)
✅ Single-use codes (10 Free4Life codes)
✅ API endpoints for chat, models, images
✅ File upload handling
✅ Notion OAuth
✅ Admin routes
✅ Database: SQLite

New Features:
- single_use column in promo_codes table
- validate_promo_code() handles both types
- /api/check-promo-code endpoint
- /api/apply-promo-upgrade endpoint
```

#### **5. Free4Life Code Generator**
```
File: generate_free4life_codes.py
Location: /mnt/user-data/outputs/
Run after deploying backend

What it does:
✅ Adds single_use column (if needed)
✅ Generates 10 unique codes (FREE4LIFE-XXXX)
✅ Each code: single-use only, Pro plan, FREE
✅ Saves to database
✅ Creates codes_free4life.txt file

Usage:
python generate_free4life_codes.py

Output:
FREE4LIFE-A1B2
FREE4LIFE-C3D4
...10 codes total
```

---

## ❌ **DEPRECATED FILES (Don't Use):**

### **Old Dashboard Versions:**
```
❌ dashboard.html (3,756 lines - OLD layout)
   - Character grid at top
   - Stats bar
   - Jungle green everywhere
   - DO NOT DEPLOY

❌ dashboard_MOBILE_FIXED.html (3,777 lines)
   - OLD layout + mobile fix
   - DO NOT DEPLOY

❌ dashboard_COMBINED_BUTTONS.html (3,919 lines)
   - OLD layout + mobile fix + combined buttons
   - DO NOT DEPLOY

❌ dashboard_COMPLETE_MODERN.html
❌ dashboard_MODERN_CLEAN.html
❌ dashboard_UPDATED.html
   - Various iterations, all deprecated
   - DO NOT DEPLOY
```

**Why deprecated?** These have the OLD layout. You switched to the ULTIMATE ChatGPT-style design, so these are obsolete.

---

## 📦 **OTHER IMPORTANT FILES:**

### **Admin Dashboard**
```
File: admin_dashboard_UNIFIED.html
Deploy to: /templates/admin_dashboard.html
Features: Analytics, user stats, revenue tracking
Status: Should already be deployed
```

### **Automations/Integrations**
```
File: automations_UNIFIED.html
Deploy to: /templates/automations.html
Features: API keys, Zapier, Make.com, webhooks
Status: Should already be deployed
```

### **JavaScript**
```
File: dashboard_ultimate.js
Location: /static/
Features: All dashboard functionality
Status: Needs to match ULTIMATE dashboard
```

---

## 🎨 **DESIGN SYSTEMS:**

### **ULTIMATE Dashboard (Current/Correct)**
```css
Colors:
--primary: #10a37f (teal green)
--primary-hover: #0d8c6f
--sidebar-bg: #1a1a1a (dark gray)
--bg-main: #ffffff (white)
--bg-secondary: #f9fafb (light gray)
--text-primary: #374151 (dark gray)
--text-secondary: #6b7280 (medium gray)

Layout:
- Sidebar: 280px, dark (#1a1a1a)
- Main: Flexible width, white
- Font: -apple-system, BlinkMacSystemFont, 'Segoe UI'
- Modern, clean, minimalist
- ChatGPT-inspired
```

### **Pricing/Promo Pages (Green Jungle)**
```css
Colors:
- Background: linear-gradient(135deg, #1a4d2e, #2d5016)
- Primary green: #90EE90
- Gold: #FFD700
- Glass cards: rgba(255, 255, 255, 0.1)

Layout:
- Full-width gradient background
- Glass-morphism cards
- Green/gold color scheme
- Jungle/rainforest theme
```

**Note:** Dashboard = Modern/professional, Pricing = Jungle/playful

---

## 🗄️ **DATABASE STRUCTURE:**

### **Users Table**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE,
    password_hash TEXT,
    subscription_tier TEXT,  -- 'free', 'starter', 'pro'
    promo_code_used TEXT,    -- Which code user redeemed
    messages_today INTEGER,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    created_at TIMESTAMP
)
```

### **Promo Codes Table**
```sql
CREATE TABLE promo_codes (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    tier TEXT NOT NULL,          -- 'Starter' or 'Pro'
    max_uses INTEGER DEFAULT 1,
    times_used INTEGER DEFAULT 0,
    single_use BOOLEAN DEFAULT 0, -- NEW! 0=multi-use, 1=single-use
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP,
    expires_at TIMESTAMP
)
```

### **Messages Table**
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    agent TEXT,
    model TEXT,
    content TEXT,
    role TEXT,
    timestamp TIMESTAMP
)
```

---

## 🔐 **ADMIN ACCESS:**

**Admin User:** User ID 1 (first user registered)

**Admin Routes:**
- `/admin` - Dashboard with analytics
- `/promo-codes` - Promo code management
- `/api/admin/*` - Admin API endpoints

**How Admin Links Appear:**
```javascript
// In sidebar, admin links only show for user ID 1
fetch('/api/user-info')
  .then(res => res.json())
  .then(data => {
    if (data.user_id === 1) {
      // Show admin links
    }
  });
```

---

## 💳 **SUBSCRIPTION SYSTEM:**

### **Tiers:**
```
Free:
- $0/month
- 25 messages/day
- All 7 agents
- File upload, chat history, Notion integration

Starter:
- $10/month
- 100 messages/day
- All Free features
- Priority support
- Stripe Price ID: price_xxx

Pro:
- $30/month
- 500 messages/day
- All Starter features
- API access
- Automation/webhooks
- Early access to new features
- Stripe Price ID: price_yyy
```

### **Stripe Integration:**
```
Routes:
- /pricing → Shows pricing page
- /create-checkout-session → Creates Stripe session
- /stripe-webhook → Handles subscription events
- /cancel-subscription → Cancels subscription

Events Handled:
- checkout.session.completed
- customer.subscription.updated
- customer.subscription.deleted
- invoice.payment_succeeded
- invoice.payment_failed
```

### **Promo Code Flow:**
```
User Journey:
1. Visit /pricing
2. See promo input at top
3. Enter code (e.g., WELCOME2024)
4. Click "Apply Code"
5. Frontend: POST /api/check-promo-code
6. Backend validates: exists, active, has uses
7. Frontend updates price: $10 → FREE
8. User clicks "Select Starter"
9. Frontend: POST /api/apply-promo-upgrade
10. Backend: Updates user tier, increments usage
11. User gets Starter plan for free
12. Multi-use: Code stays active
    Single-use: Code deactivates
```

---

## 🤖 **AI MODELS:**

### **8 Models Available:**
```
1. Claude Sonnet 4.5 (claude-sonnet-4-20250514)
2. Claude Opus 4 (claude-opus-4-20250514)
3. Claude Haiku 4.5 (claude-haiku-4-5-20251001)
4. GPT-4o (gpt-4o)
5. GPT-4 Turbo (gpt-4-turbo)
6. GPT-4o Mini (gpt-4o-mini)
7. Gemini 2.0 Flash FREE (gemini-2.0-flash)
8. Gemini 1.5 Pro (gemini-1.5-pro)
```

### **7 Core Agents:**
```
Luna 🌙 - Research Analyst
- Default agent
- Model: Claude Sonnet 4.5
- Role: Research, analysis, general tasks

Mila 📋 - Task Manager
- Model: GPT-4o
- Role: Task management, organization

Sage 🧙 - Wise Advisor
- Model: Claude Opus 4
- Role: Strategy, wisdom, advice

Ember 🔥 - Creative Dynamo
- Model: GPT-4 Turbo
- Role: Creative writing, brainstorming

Sol ☀️ - Data Analyst
- Model: Claude Haiku 4.5
- Role: Data analysis, numbers

Nova ⭐ - Code Expert & Website Builder
- Model: Claude Sonnet 4.5
- Role: Coding, website generation

Theo 💼 - Business Strategist & Website Builder
- Model: GPT-4o
- Role: Business, strategy, websites
```

---

## 🌐 **KEY FEATURES:**

### **Website Builder**
```
How it works:
1. User asks Nova or Theo to create a website
2. Agent generates complete HTML file
3. File includes CSS/JS in single file
4. User downloads HTML file
5. User can open in browser or upload to hosting

Example prompts:
"Create a landing page for my coffee shop"
"Build a portfolio website for a photographer"
"Make a restaurant menu website"
```

### **Voice Input/Output**
```
Input:
- Click 🎤 button
- Speak into microphone
- Speech transcribed to text
- Appears in input field

Output:
- Agent responses read aloud
- Voice settings: Speed, pitch, volume
- Multiple voice options
```

### **Image Generation**
```
How it works:
1. Click 🎨 button
2. Describe image you want
3. Uses DALL-E 3 (OpenAI)
4. Image appears in chat
5. Download or preview in floating window

FREE for all users!
```

### **File Upload**
```
Supported:
- Images: .png, .jpg, .jpeg, .gif, .webp
- Documents: .pdf, .txt, .md, .csv
- Office: .doc, .docx, .xls, .xlsx, .ppt, .pptx

How it works:
1. Click 📎 button
2. Select file
3. File uploaded to server
4. Agent can analyze/discuss file
```

### **Custom Agents**
```
How it works:
1. Click "+ Create Agent" in sidebar
2. Enter name, role, instructions
3. Choose AI model
4. Agent saved to database
5. Appears in sidebar
6. Use like any other agent
```

---

## 🔌 **INTEGRATIONS:**

### **Notion OAuth**
```
Status: ✅ Working
Route: /notion-oauth
Callback: /notion-callback
Features: Access Notion workspace, read/write pages
```

### **Google Drive (Optional)**
```
Status: Available if user enables
Features: Access files, upload, download
```

### **Zapier/Make.com**
```
Status: Available for Pro users
Route: /automations
Features: API keys, webhooks
```

---

## 📱 **MOBILE OPTIMIZATIONS:**

### **Responsive Breakpoint**
```css
@media (max-width: 768px) {
    /* Mobile styles */
}
```

### **Mobile-Specific Features:**
```
✅ Sidebar hidden by default (toggle with ☰)
✅ Sticky input at bottom (never scrolls away)
✅ Dynamic chat height (fits screen)
✅ iOS zoom prevention (font-size: 16px)
✅ Larger touch targets (48px minimum)
✅ Full-width input field
✅ Compact button layout
✅ Combined options dropdown
```

### **Mobile Issues Fixed:**
```
❌ Before: Chat input off-screen, can't access
✅ After: Input sticky at bottom, always visible

❌ Before: Fixed chat height pushes input down
✅ After: Dynamic height adapts to viewport

❌ Before: Too many buttons, cramped
✅ After: Combined dropdown, cleaner
```

---

## 🚀 **DEPLOYMENT CHECKLIST:**

### **Files to Deploy NOW:**

```bash
# 1. Dashboard (CRITICAL - Mobile fix!)
dashboard_ULTIMATE_FIXED.html → /templates/dashboard.html

# 2. Pricing (Promo code redemption)
pricing_UPDATED.html → /templates/pricing.html

# 3. Promo Admin (Correct plan names)
promo_codes_UPDATED.html → /templates/promo_codes.html

# 4. Backend (Single-use codes)
web_app_auth_UPDATED.py → /web_app_auth.py

# 5. Deploy
git add templates/ web_app_auth.py
git commit -m "Deploy: Mobile fix + promo codes + single-use system"
git push origin main

# 6. After deploy, generate Free4Life codes
python generate_free4life_codes.py
```

### **Testing After Deploy:**

```
Desktop:
✅ Dashboard loads with sidebar
✅ Can switch agents
✅ Can send messages
✅ Combined options button works
✅ Dropdown shows: Upload, Voice, Images
✅ Can upload file
✅ Can use voice input
✅ Can generate image

Mobile:
✅ Dashboard loads
✅ Sidebar hidden (toggle works)
✅ Input visible at bottom
✅ Input stays when scrolling
✅ Can type message
✅ Can send message
✅ Combined button shows just "+"
✅ Dropdown works

Pricing:
✅ Shows 3 tiers
✅ Promo input at top
✅ Enter code → Validates
✅ Valid code → Price shows FREE
✅ Click Subscribe → Redirects

Admin:
✅ Go to /promo-codes
✅ Create code → Dropdown shows Starter/Pro
✅ Code appears in list
✅ Can copy code
✅ Usage tracked
```

---

## 🔧 **COMMON ISSUES:**

### **Issue: Dashboard shows old layout**
```
Problem: Deployed wrong file
Solution: Deploy dashboard_ULTIMATE_FIXED.html
Check: Look for dark sidebar on left
```

### **Issue: Mobile input not visible**
```
Problem: Old dashboard or cache
Solution: Deploy ULTIMATE_FIXED, clear cache (Ctrl+Shift+R)
Check: Input should be sticky at bottom
```

### **Issue: Promo codes show wrong plans**
```
Problem: Old promo_codes.html deployed
Solution: Deploy promo_codes_UPDATED.html
Check: Dropdown should show "Starter ($10)" and "Pro ($30)"
```

### **Issue: Single-use codes don't work**
```
Problem: Database missing single_use column
Solution: Run generate_free4life_codes.py (adds column)
Check: Run script, should see "Added single_use column"
```

### **Issue: Combined buttons not working**
```
Problem: JavaScript not loaded
Solution: Check browser console for errors
Check: Click "Options" → Dropdown should appear
```

---

## 📊 **ANALYTICS:**

### **Tracked Metrics:**
```
Users:
- Total users
- Free users
- Starter subscribers
- Pro subscribers
- New signups (today, week, month)

Messages:
- Total messages
- Messages today
- Messages per user
- Popular agents
- Popular models

Revenue:
- MRR (Monthly Recurring Revenue)
- Total revenue
- Average revenue per user
- Conversion rate (free → paid)

Promo Codes:
- Total codes created
- Active codes
- Total redemptions
- Codes by plan
```

---

## 🎯 **ROADMAP / FUTURE:**

### **Completed:**
```
✅ 8 AI models integrated
✅ 7 core agents with personalities
✅ Voice input/output
✅ Image generation (free)
✅ File upload (all types)
✅ Website builder
✅ Custom agents
✅ Subscription system
✅ Promo codes (multi-use + single-use)
✅ Admin portal
✅ Notion OAuth
✅ Modern UI (ChatGPT-style)
✅ Mobile optimization
✅ Floating preview window
```

### **Pending (This Session):**
```
⏳ Deploy mobile fixes
⏳ Deploy promo redemption page
⏳ Deploy backend with single-use codes
⏳ Generate 10 Free4Life codes
```

### **Potential Future:**
```
💡 Google Drive full integration
💡 More OAuth integrations (Slack, Trello, etc.)
💡 Team accounts (multiple users per subscription)
💡 Usage analytics dashboard for users
💡 API for external developers
💡 Mobile app (iOS/Android)
💡 More custom agent templates
💡 Agent marketplace (share custom agents)
```

---

## 📝 **QUICK REFERENCE:**

### **Important URLs:**
```
Production: https://ai-team.skillsoul.store
Pricing: https://ai-team.skillsoul.store/pricing
Admin: https://ai-team.skillsoul.store/admin
Promo Codes: https://ai-team.skillsoul.store/promo-codes
Automations: https://ai-team.skillsoul.store/automations
```

### **Important Variables:**
```python
DB_PATH = 'database.db'
UPLOAD_FOLDER = 'uploads/'
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
```

### **Important Commands:**
```bash
# Deploy
git add .
git commit -m "message"
git push origin main

# Generate promo codes
python generate_free4life_codes.py

# Check database
sqlite3 database.db "SELECT * FROM promo_codes;"
sqlite3 database.db "SELECT email, subscription_tier FROM users;"

# Clear cache
Ctrl + Shift + R (browser)
```

---

## ✅ **FINAL CHECKLIST:**

**To Deploy:**
- [ ] dashboard_ULTIMATE_FIXED.html → /templates/dashboard.html
- [ ] pricing_UPDATED.html → /templates/pricing.html
- [ ] promo_codes_UPDATED.html → /templates/promo_codes.html
- [ ] web_app_auth_UPDATED.py → /web_app_auth.py
- [ ] git push to production
- [ ] python generate_free4life_codes.py
- [ ] Test on desktop
- [ ] Test on mobile
- [ ] Test promo code redemption

**Documentation:**
- [ ] Keep this MASTER_INVENTORY.md as reference
- [ ] Update when adding new features
- [ ] Review before making changes

---

## 🎯 **REMEMBER:**

**✅ CORRECT Dashboard:** dashboard_ULTIMATE_FIXED.html  
**❌ WRONG Dashboard:** dashboard.html (old layout)

**✅ Modern Layout:** Dark sidebar + clean main area  
**❌ Old Layout:** Character grid + stats bar

**✅ File Size:** ~1,180 lines (efficient)  
**❌ File Size:** ~3,750 lines (bloated old version)

**When in doubt, look for:**
1. Dark sidebar on left (#1a1a1a)
2. Modern green (#10a37f)
3. ChatGPT-style clean design
4. "ULTIMATE AI TEAM DASHBOARD" in comments

---

**END OF MASTER INVENTORY**

This is your single source of truth. Keep it updated!
