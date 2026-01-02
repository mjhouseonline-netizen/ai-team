#!/usr/bin/env python3
"""Assign all global agents to the admin account"""

import sqlite3

DB_PATH = '/home/user/ai-team/ai_team.db'

def assign_all_global_agents_to_admin():
    """Assign all active global agents to admin (user ID 1)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get admin user info
    cursor.execute("SELECT id, email, username FROM users WHERE id = 1")
    admin = cursor.fetchone()

    if not admin:
        print("❌ Admin user (ID 1) not found!")
        conn.close()
        return

    print(f"\n👤 Assigning to: {admin[1]} (ID: {admin[0]}, Username: {admin[2]})")
    print("=" * 80)

    # Get all active global agents
    cursor.execute("""
        SELECT id, name, emoji, category
        FROM global_agents
        WHERE is_active = 1
        ORDER BY id
    """)
    agents = cursor.fetchall()

    if not agents:
        print("❌ No global agents found!")
        conn.close()
        return

    assigned = 0
    already_had = 0

    print(f"\n🔄 Assigning {len(agents)} global agents...\n")

    for agent_id, name, emoji, category in agents:
        try:
            cursor.execute("""
                INSERT INTO user_global_agents (user_id, global_agent_id, assigned_by, assigned_at)
                VALUES (1, ?, 1, CURRENT_TIMESTAMP)
            """, (agent_id,))
            print(f"  ✅ Assigned: {emoji} {name}")
            assigned += 1
        except sqlite3.IntegrityError:
            print(f"  ⏭️  Already had: {emoji} {name}")
            already_had += 1

    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print(f"📊 Summary:")
    print(f"   Newly assigned: {assigned}")
    print(f"   Already had access: {already_had}")
    print(f"   Total global agents: {assigned + already_had}")
    print("\n✅ Complete! Refresh your browser to see all global agents.")

if __name__ == '__main__':
    print("🚀 Assigning All Global Agents to Admin")
    print("=" * 80)
    assign_all_global_agents_to_admin()
