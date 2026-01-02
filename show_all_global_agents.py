#!/usr/bin/env python3
"""Show all global agents in the database"""

import sqlite3

DB_PATH = '/home/user/ai-team/ai_team.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT id, name, emoji, description, category, is_active, created_by
    FROM global_agents
    ORDER BY id
""")

agents = cursor.fetchall()

print("\n🤖 All Global Agents in Database:")
print("=" * 100)

for agent in agents:
    active_status = "✅ Active" if agent[5] else "❌ Inactive"
    print(f"\nID: {agent[0]} | {active_status}")
    print(f"Name: {agent[1]} {agent[2]}")
    print(f"Description: {agent[3]}")
    print(f"Category: {agent[4]}")
    print(f"Created by user: {agent[6]}")

print("\n" + "=" * 100)
print(f"Total global agents: {len(agents)}")

# Check which users have which agents
print("\n📊 User Assignments:")
print("-" * 100)

cursor.execute("""
    SELECT u.id, u.email, ga.name, ga.emoji
    FROM users u
    INNER JOIN user_global_agents uga ON u.id = uga.user_id
    INNER JOIN global_agents ga ON uga.global_agent_id = ga.id
    ORDER BY u.id, ga.name
""")

assignments = cursor.fetchall()

current_user = None
for assignment in assignments:
    if assignment[0] != current_user:
        current_user = assignment[0]
        print(f"\n👤 User: {assignment[1]} (ID: {assignment[0]})")
    print(f"   {assignment[3]} {assignment[2]}")

if not assignments:
    print("⚠️  No user assignments found!")

conn.close()
