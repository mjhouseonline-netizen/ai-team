# 🔧 DATABASE MIGRATION FIX

## The Problem:
Your database has the old structure (without subscription columns), but your code expects the new structure.

## The Solution:
Add 2 files and redeploy!

---

## STEP 1: Download These Files

1. **[migrate_db.py](computer:///mnt/user-data/outputs/migrate_db.py)** - NEW file
   - Save to: `Desktop\ai-team\migrate_db.py`

2. **[web_app_auth.py](computer:///mnt/user-data/outputs/web_app_auth.py)** - UPDATED
   - Save to: `Desktop\ai-team\web_app_auth.py` (replace old one)

---

## STEP 2: Push to GitHub

1. Open **GitHub Desktop**
2. You'll see:
   - migrate_db.py (new)
   - web_app_auth.py (modified)
3. Commit: `Add database migration for subscription columns`
4. Push origin

---

## STEP 3: Wait for Render

1. Render will auto-deploy (3-5 min)
2. Watch for "Live" status
3. Check logs - you should see:
   ```
   🔧 Checking database schema...
   ✅ Added column: subscription_tier
   ✅ Added column: stripe_customer_id
   ✅ Migration complete!
   ```

---

## STEP 4: Test Signup

1. Go to your site
2. Click "Sign up"
3. Create account
4. **Should work now!** ✅

---

## What This Does:

The `migrate_db.py` script:
- Checks if subscription columns exist
- Adds them if missing
- Runs automatically on startup
- Updates the old database structure

The updated `web_app_auth.py`:
- Runs migration on startup
- Ensures database is up-to-date
- Then starts normally

---

## After This Works:

You can test your platform fully:
- ✅ Signup/login works
- ✅ Custom agent images show
- ✅ Agents respond
- ✅ Message counter works
- ✅ Tier badge shows (🆓 Free - 0/10)

---

**This is the final fix!** 🎉
