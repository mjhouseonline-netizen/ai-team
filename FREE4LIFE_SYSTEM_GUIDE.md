# 🎟️ FREE4LIFE SINGLE-USE + MULTI-USE PROMO SYSTEM

## ✅ **WHAT YOU HAVE NOW:**

Your promo code system supports **TWO TYPES** of codes:

### **1. SINGLE-USE CODES (10 Free4Life Codes)**
```
Code: FREE4LIFE-A1B2
Type: Single-use only
Plan: Pro ($30/month)
Uses: Can only be used ONCE
After Use: Code becomes inactive automatically
```

### **2. MULTI-USE CODES (All Other Codes)**
```
Code: WELCOME2024
Type: Multi-use
Plan: Starter or Pro  
Uses: Up to max_uses (e.g., 100)
After Use: Stays active until max_uses reached
```

---

## 🚀 **DEPLOYMENT (3 Steps):**

### **Step 1: Upload Updated Backend**
```bash
web_app_auth_UPDATED.py → /web_app_auth.py
```

**What Changed:**
- ✅ Added `single_use` column to promo_codes table
- ✅ Updated validation logic for single-use codes
- ✅ Auto-deactivates single-use codes after redemption
- ✅ Multi-use codes work as before

### **Step 2: Run Code Generator**
```bash
python generate_free4life_codes.py
```

**What Happens:**
- ✅ Adds single_use column (if needed)
- ✅ Generates 10 unique FREE4LIFE codes
- ✅ Saves codes to database
- ✅ Creates codes_free4life.txt file

### **Step 3: Share the 10 Codes**
Give one code to each special user!

---

## 🎯 **HOW IT WORKS:**

### **FREE4LIFE Codes (Single-Use):**

```
1. Admin runs: python generate_free4life_codes.py
   └─> Generates: FREE4LIFE-X7Y9

2. Admin gives code to User A
   └─> User A goes to /pricing

3. User A enters: FREE4LIFE-X7Y9
   └─> System validates ✅
   
4. User A clicks "Subscribe"
   └─> Gets Pro plan FREE
   └─> Code becomes INACTIVE ❌
   
5. User B tries same code: FREE4LIFE-X7Y9
   └─> System says: "Code already used" ❌
```

### **Regular Codes (Multi-Use):**

```
1. Admin creates: WELCOME2024 (max_uses=100)
   └─> Type: Multi-use

2. User A uses code
   └─> Uses: 1/100 ✅
   └─> Code stays ACTIVE

3. User B uses code
   └─> Uses: 2/100 ✅
   └─> Code stays ACTIVE

...

100. User 100 uses code
   └─> Uses: 100/100 ✅
   └─> Code becomes INACTIVE

101. User 101 tries code
   └─> "Max uses reached" ❌
```

---

## 📊 **DATABASE STRUCTURE:**

### **promo_codes Table:**
```sql
CREATE TABLE promo_codes (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,           -- "FREE4LIFE-A1B2"
    tier TEXT NOT NULL,                   -- "Pro" or "Starter"
    max_uses INTEGER DEFAULT 1,           -- 1 for single-use, 100 for multi
    times_used INTEGER DEFAULT 0,         -- Usage counter
    single_use BOOLEAN DEFAULT 0,         -- 1 = single-use, 0 = multi-use
    is_active BOOLEAN DEFAULT 1,          -- Active status
    created_at TIMESTAMP,
    expires_at TIMESTAMP
)
```

### **Example Records:**

**Single-Use Code:**
```
id: 1
code: FREE4LIFE-X7Y9
tier: Pro
max_uses: 1
times_used: 0
single_use: 1  ← Single-use flag!
is_active: 1
```

**Multi-Use Code:**
```
id: 2
code: WELCOME2024
tier: Pro
max_uses: 100
times_used: 23
single_use: 0  ← Multi-use flag!
is_active: 1
```

---

## 🔧 **CODE GENERATOR SCRIPT:**

### **generate_free4life_codes.py**

Located at: `/mnt/user-data/outputs/generate_free4life_codes.py`

**What It Does:**
1. Checks if single_use column exists
2. Adds it if missing
3. Generates 10 unique codes
4. Saves to database with single_use=1
5. Creates codes_free4life.txt file

**Run It:**
```bash
python generate_free4life_codes.py
```

**Output:**
```
🚀 FREE4LIFE Code Generator
============================================================
✅ Column already exists
Generating 10 FREE4LIFE codes...
✅ Generated: FREE4LIFE-A1B2
✅ Generated: FREE4LIFE-C3D4
✅ Generated: FREE4LIFE-E5F6
✅ Generated: FREE4LIFE-G7H8
✅ Generated: FREE4LIFE-I9J0
✅ Generated: FREE4LIFE-K1L2
✅ Generated: FREE4LIFE-M3N4
✅ Generated: FREE4LIFE-O5P6
✅ Generated: FREE4LIFE-Q7R8
✅ Generated: FREE4LIFE-S9T0

============================================================
🎉 10 SINGLE-USE FREE4LIFE CODES GENERATED!
============================================================

CODES:
------------------------------------------------------------
 1. FREE4LIFE-A1B2
 2. FREE4LIFE-C3D4
 3. FREE4LIFE-E5F6
 4. FREE4LIFE-G7H8
 5. FREE4LIFE-I9J0
 6. FREE4LIFE-K1L2
 7. FREE4LIFE-M3N4
 8. FREE4LIFE-O5P6
 9. FREE4LIFE-Q7R8
10. FREE4LIFE-S9T0
------------------------------------------------------------

✅ SUCCESS! 10 codes generated and saved to database
💾 CODES SAVED TO: codes_free4life.txt
```

---

## 💡 **EXAMPLE SCENARIOS:**

### **Scenario 1: VIP Launch (Single-Use)**
```
You want to give 10 special users FREE Pro access

Admin:
1. Runs: python generate_free4life_codes.py
2. Gets 10 codes
3. Sends one code to each VIP

VIP Users:
1. Receive unique code: FREE4LIFE-X7Y9
2. Go to /pricing
3. Enter code
4. Get Pro for FREE
5. Code becomes inactive (can't be shared)

Result: ✅ Exactly 10 VIPs get free Pro
```

### **Scenario 2: Launch Campaign (Multi-Use)**
```
You want first 100 users to get Pro free

Admin:
1. Goes to /promo-codes
2. Creates: LAUNCH2024
3. Plan: Pro
4. Max Uses: 100
5. Shares publicly

Users:
1. See code on Twitter/email
2. Go to /pricing
3. Enter LAUNCH2024
4. Get Pro for FREE
5. Code stays active for others

Result: ✅ First 100 users get free Pro, then code stops
```

### **Scenario 3: Mix of Both**
```
Admin has:
• 10 FREE4LIFE codes (single-use for VIPs)
• LAUNCH2024 (multi-use for 100 users)
• PARTNER50 (multi-use for 50 partner users)

Different users get different codes based on source:
• VIPs: Get unique FREE4LIFE code
• Launch: Get LAUNCH2024 code
• Partners: Get PARTNER50 code

All codes tracked separately!
```

---

## 🎨 **ADMIN PANEL VIEW:**

### **After Creating Codes:**

```
PROMO CODES DASHBOARD
────────────────────────────────────────────

FREE4LIFE-X7Y9
Plan: Pro  Uses: 1/1  Status: ❌ Inactive
Type: Single-Use ⚡

FREE4LIFE-A1B2
Plan: Pro  Uses: 0/1  Status: ✅ Active
Type: Single-Use ⚡

WELCOME2024
Plan: Pro  Uses: 23/100  Status: ✅ Active
Type: Multi-Use 🔁

LAUNCH2024
Plan: Pro  Uses: 100/100  Status: ❌ Inactive
Type: Multi-Use 🔁
```

---

## 📝 **USER EXPERIENCE:**

### **User with Single-Use Code:**

```
1. User visits: /pricing
2. Sees: 🎟️ Have a Promo Code?
3. Enters: FREE4LIFE-X7Y9
4. Clicks: Apply Code
5. Sees: ✅ Success! Pro plan FREE!
6. Price: $30 → FREE
7. Clicks: Select Pro
8. Gets: Pro plan activated!

User tries to share code with friend:
Friend enters: FREE4LIFE-X7Y9
System: ❌ "This promo code has already been used"
```

### **User with Multi-Use Code:**

```
1. User A visits: /pricing
2. Enters: WELCOME2024
3. Gets: Pro plan FREE! (Uses: 1/100)

User A tells friend:
2. Friend visits: /pricing
3. Enters: WELCOME2024
4. Gets: Pro plan FREE! (Uses: 2/100)

Both codes work! ✅
```

---

## 🔐 **SECURITY & TRACKING:**

### **What's Tracked:**
```
✅ Which user used which code
✅ When they used it
✅ How many times each code was used
✅ Which codes are still active
✅ Single-use vs multi-use status
```

### **What's Prevented:**
```
❌ Users can't use same code twice
❌ Single-use codes can't be reused
❌ Multi-use codes stop after max_uses
❌ Inactive codes can't be used
```

---

## 🐛 **TROUBLESHOOTING:**

### **"Column single_use doesn't exist"**
```bash
# Run the generator script - it adds the column
python generate_free4life_codes.py
```

### **"Code already exists"**
```
# Generator creates unique codes
# If you see this, just run script again
# It will generate new unique codes
```

### **"Can't generate 10 codes"**
```
# Check database connection
# Make sure DB_PATH is correct in script
# Default: database.db
```

---

## 📋 **DEPLOYMENT CHECKLIST:**

Before Deploy:
- [ ] Download web_app_auth_UPDATED.py
- [ ] Download generate_free4life_codes.py

Deploy:
- [ ] Upload web_app_auth_UPDATED.py as /web_app_auth.py
- [ ] Deploy to Render (git push)
- [ ] Wait for deployment

After Deploy:
- [ ] SSH into server OR run locally with DB connection
- [ ] Run: python generate_free4life_codes.py
- [ ] Save the 10 codes from codes_free4life.txt
- [ ] Distribute codes to VIP users

Test:
- [ ] Go to /pricing
- [ ] Enter one FREE4LIFE code
- [ ] Should work and get Pro
- [ ] Try same code again
- [ ] Should say "already used"
- [ ] Create regular multi-use code in admin
- [ ] Test multi-use code with 2 different users
- [ ] Both should work

---

## ✅ **SUMMARY:**

**What You Have:**
- ✅ 10 single-use FREE4LIFE codes
- ✅ Unlimited multi-use codes (as before)
- ✅ Both systems work together
- ✅ Full tracking and security

**Files Updated:**
- ✅ web_app_auth_UPDATED.py (backend)
- ✅ generate_free4life_codes.py (generator)

**Deploy Time:**
- ⏱️ 5 minutes

**User Experience:**
- ✅ Seamless - users don't see any difference
- ✅ Just enter code and get free plan
- ✅ Single-use codes can't be shared

---

**READY TO DEPLOY!** 🚀

Run the generator after deploying the backend to get your 10 codes!
