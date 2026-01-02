#!/usr/bin/env python3
"""Update username from 'bubbles' to 'bubblesfox'"""

import sqlite3

DB_PATH = '/home/user/ai-team/ai_team.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n🔄 Updating Username...")
print("=" * 80)

# Show current
cursor.execute("SELECT id, email, username FROM users WHERE id = 1")
user = cursor.fetchone()
print(f"Current: {user[1]} | Username: '{user[2]}'")

# Update username
cursor.execute("UPDATE users SET username = ? WHERE id = 1", ("bubblesfox",))
conn.commit()

# Verify update
cursor.execute("SELECT id, email, username FROM users WHERE id = 1")
user = cursor.fetchone()
print(f"Updated: {user[1]} | Username: '{user[2]}'")

print("\n✅ Username updated successfully!")
print("\nNext steps:")
print("1. Log out from your dashboard completely")
print("2. Clear all cookies for the site")
print("3. Log back in with:")
print("   - Email: bubblesfox@gmail.com")
print("   - Password: [your password]")
print("4. Hard refresh the page (Ctrl+Shift+R)")
print("\nYour global agents should now appear!")

conn.close()
