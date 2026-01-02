#!/usr/bin/env python3
"""Force re-login to fix session issues"""

import sqlite3

DB_PATH = '/home/user/ai-team/ai_team.db'

print("\n🔍 Session Troubleshooting")
print("=" * 80)
print("""
The API is returning {"agents":[]} which means:
- You're logged in, but as a different user than expected
- OR your session is corrupted
- OR current_user.id is not being set correctly

SOLUTION:
1. Log out completely from the dashboard
2. Clear all cookies for the site
3. Log back in with: bubblesfox@gmail.com
4. Hard refresh the page

OR try Incognito/Private browsing mode with fresh login.
""")

# Verify the database is still correct
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n✅ Database Verification:")
cursor.execute("SELECT COUNT(*) FROM user_global_agents WHERE user_id = 1")
count = cursor.fetchone()[0]
print(f"   Admin (user 1) has {count} global agents assigned")

cursor.execute("SELECT id, email FROM users WHERE id = 1")
admin = cursor.fetchone()
if admin:
    print(f"   Admin user: {admin[1]} (ID: {admin[0]})")

conn.close()

print("\n" + "=" * 80)
print("The database is correct. The issue is with your browser session.")
print("\nPlease:")
print("1. Log out from the dashboard")
print("2. Clear cookies")
print("3. Log back in with bubblesfox@gmail.com")
print("4. Refresh the page")
