#!/usr/bin/env python3
"""List all users in the database"""

import sqlite3

DB_PATH = '/home/user/ai-team/ai_team.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT id, email, username, created_at
    FROM users
    ORDER BY id
""")

users = cursor.fetchall()

print("\n📋 All Users in Database:")
print("=" * 90)
print(f"{'ID':>4} | {'Email':40} | {'Username':20} | Created")
print("-" * 90)

for user in users:
    print(f"{user[0]:>4} | {user[1]:40} | {user[2]:20} | {user[3]}")

print("-" * 100)
print(f"Total users: {len(users)}")

conn.close()
