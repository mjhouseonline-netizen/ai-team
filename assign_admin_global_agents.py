#!/usr/bin/env python3
"""Assign all admin global agents to a specific user"""

import sqlite3
import sys

DB_PATH = '/home/user/ai-team/ai_team.db'

def get_user_info():
    """Display all users for selection"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, email, username FROM users ORDER BY id")
    users = cursor.fetchall()

    print("\n📋 Available Users:")
    print("-" * 60)
    for user in users:
        print(f"ID: {user[0]:3d} | Email: {user[1]:30s} | Username: {user[2]}")
    print("-" * 60)

    conn.close()
    return users

def get_global_agents():
    """Get all global agents"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, description, emoji, category, created_by
        FROM global_agents
        WHERE is_active = 1
        ORDER BY id
    """)
    agents = cursor.fetchall()

    print("\n🤖 Global Agents Available:")
    print("-" * 80)
    for agent in agents:
        print(f"ID: {agent[0]:3d} | {agent[3]} {agent[1]:25s} | Created by user: {agent[5]}")
        print(f"     {agent[2]}")
    print("-" * 80)

    conn.close()
    return agents

def assign_all_global_agents_to_user(user_id):
    """Assign all global agents to a specific user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all active global agents
    cursor.execute("SELECT id, name FROM global_agents WHERE is_active = 1")
    agents = cursor.fetchall()

    assigned = 0
    skipped = 0

    print(f"\n🔄 Assigning global agents to user ID {user_id}...")

    for agent_id, agent_name in agents:
        try:
            cursor.execute("""
                INSERT INTO user_global_agents (user_id, global_agent_id, assigned_by, assigned_at)
                VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            """, (user_id, agent_id))
            print(f"  ✅ Assigned: {agent_name}")
            assigned += 1
        except sqlite3.IntegrityError:
            print(f"  ⏭️  Already assigned: {agent_name}")
            skipped += 1

    conn.commit()
    conn.close()

    print(f"\n📊 Summary:")
    print(f"   Newly assigned: {assigned}")
    print(f"   Already had access: {skipped}")
    print(f"   Total global agents: {assigned + skipped}")

    return assigned, skipped

if __name__ == '__main__':
    print("🚀 Global Agents Assignment Tool")
    print("=" * 80)

    # Show all users
    users = get_user_info()

    # Show all global agents
    agents = get_global_agents()

    if not agents:
        print("\n⚠️  No global agents found in the database!")
        sys.exit(1)

    # Get user ID to assign to
    print("\n" + "=" * 80)
    user_input = input("Enter the USER ID to assign all global agents to (or 'all' for all users): ")

    if user_input.lower() == 'all':
        print("\n🔄 Assigning to ALL users...")
        for user in users:
            user_id = user[0]
            print(f"\nProcessing user: {user[1]} (ID: {user_id})")
            assign_all_global_agents_to_user(user_id)
    else:
        try:
            user_id = int(user_input)
            assign_all_global_agents_to_user(user_id)
        except ValueError:
            print("❌ Invalid user ID!")
            sys.exit(1)

    print("\n✅ Complete! Refresh your browser to see the updated global agents.")
