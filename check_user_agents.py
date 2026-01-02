#!/usr/bin/env python3
"""Check what global agents a user has access to"""

import sqlite3

DB_PATH = '/home/user/ai-team/ai_team.db'

def check_user_global_agents(user_id):
    """Check what global agents a user has access to"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get user info
    cursor.execute("SELECT id, email, username FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        print(f"❌ User ID {user_id} not found!")
        return

    print(f"\n👤 User: {user[1]} (ID: {user[0]}, Username: {user[2]})")
    print("=" * 80)

    # Get assigned global agents
    cursor.execute("""
        SELECT ga.id, ga.name, ga.emoji, ga.description, uga.assigned_at
        FROM global_agents ga
        INNER JOIN user_global_agents uga ON ga.id = uga.global_agent_id
        WHERE uga.user_id = ? AND ga.is_active = 1
        ORDER BY ga.name
    """, (user_id,))

    assigned_agents = cursor.fetchall()

    if assigned_agents:
        print(f"\n✅ Assigned Global Agents ({len(assigned_agents)}):")
        print("-" * 80)
        for agent in assigned_agents:
            print(f"{agent[2]} {agent[1]}")
            print(f"   {agent[3]}")
            print(f"   Assigned: {agent[4]}")
            print()
    else:
        print("\n⚠️  No global agents assigned to this user!")

    # Get all available global agents (not assigned)
    cursor.execute("""
        SELECT ga.id, ga.name, ga.emoji, ga.description
        FROM global_agents ga
        WHERE ga.is_active = 1
        AND ga.id NOT IN (
            SELECT global_agent_id FROM user_global_agents WHERE user_id = ?
        )
        ORDER BY ga.name
    """, (user_id,))

    unassigned_agents = cursor.fetchall()

    if unassigned_agents:
        print(f"\n❌ Available but NOT assigned ({len(unassigned_agents)}):")
        print("-" * 80)
        for agent in unassigned_agents:
            print(f"{agent[2]} {agent[1]}")
            print(f"   {agent[3]}")
            print()

    conn.close()

    return assigned_agents, unassigned_agents

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        user_id = int(sys.argv[1])
    else:
        # Default to admin user
        user_id = 1

    check_user_global_agents(user_id)
