#!/usr/bin/env python3
"""Update username to match email and verify user"""

import sqlite3

DB_PATH = '/home/user/ai-team/ai_team.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n🔍 Current User Information:")
print("=" * 80)

cursor.execute("SELECT id, email, username FROM users WHERE id = 1")
user = cursor.fetchone()

print(f"User ID: {user[0]}")
print(f"Email: {user[1]}")
print(f"Current Username: {user[2]}")
print()

# Ask if user wants to update username to match
print("The username is currently 'bubbles' but you're trying to login as 'bubblesfox'")
print()
response = input("Would you like to update the username to 'bubblesfox'? (yes/no): ")

if response.lower() == 'yes':
    cursor.execute("UPDATE users SET username = ? WHERE id = 1", ("bubblesfox",))
    conn.commit()
    print("\n✅ Username updated to 'bubblesfox'")
    print("\nNow please:")
    print("1. Log out from your dashboard")
    print("2. Log back in with:")
    print("   - Email: bubblesfox@gmail.com")
    print("   - OR Username: bubblesfox")
    print("3. Your global agents should appear!")
else:
    print("\n⚠️  Username not updated. You should login with:")
    print(f"   - Email: {user[1]}")
    print(f"   - OR Username: {user[2]}")
    print("\nNOTE: You can login with EITHER email or username")

# Check global agents assignment
cursor.execute("SELECT COUNT(*) FROM user_global_agents WHERE user_id = 1")
count = cursor.fetchone()[0]
print(f"\n✅ User has {count} global agents assigned and waiting!")

conn.close()
