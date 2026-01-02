#!/usr/bin/env python3
"""Diagnose why global agents aren't showing in dashboard"""

import sqlite3

DB_PATH = '/home/user/ai-team/ai_team.db'

def diagnose_global_agents_issue():
    """Check all aspects of global agent setup for user ID 1"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n🔍 DIAGNOSTIC: Global Agents Dashboard Issue")
    print("=" * 80)

    # 1. Check user exists
    print("\n1️⃣ Checking admin user...")
    cursor.execute("SELECT id, email, username FROM users WHERE id = 1")
    user = cursor.fetchone()
    if user:
        print(f"   ✅ Admin user found: {user[1]} (ID: {user[0]})")
    else:
        print("   ❌ Admin user NOT found!")
        return

    # 2. Check global agents exist
    print("\n2️⃣ Checking global agents table...")
    cursor.execute("SELECT COUNT(*) FROM global_agents WHERE is_active = 1")
    agent_count = cursor.fetchone()[0]
    print(f"   ✅ Active global agents: {agent_count}")

    # 3. Check user_global_agents assignments
    print("\n3️⃣ Checking user_global_agents assignments for admin...")
    cursor.execute("""
        SELECT COUNT(*) FROM user_global_agents WHERE user_id = 1
    """)
    assignment_count = cursor.fetchone()[0]
    print(f"   ✅ Assignments to admin: {assignment_count}")

    # 4. Test the exact query used by the API
    print("\n4️⃣ Testing API query (simulating /api/global-agents)...")
    cursor.execute("""
        SELECT DISTINCT
            ga.id, ga.name, ga.description, ga.emoji, ga.category,
            ga.system_prompt, ga.template_variables, ga.created_at
        FROM global_agents ga
        INNER JOIN user_global_agents uga ON ga.id = uga.global_agent_id
        WHERE uga.user_id = ? AND ga.is_active = 1
        ORDER BY ga.name
    """, (1,))

    results = cursor.fetchall()
    print(f"   Query returned: {len(results)} agents")

    if results:
        print("\n   📋 Agents returned by API query:")
        for row in results:
            print(f"      {row[3]} {row[1]} (ID: {row[0]})")
    else:
        print("   ❌ API query returned NO agents!")

    # 5. Check for JOIN issues
    print("\n5️⃣ Checking for JOIN issues...")
    cursor.execute("""
        SELECT ga.id, ga.name, uga.user_id, uga.global_agent_id
        FROM global_agents ga
        LEFT JOIN user_global_agents uga ON ga.id = uga.global_agent_id AND uga.user_id = 1
        WHERE ga.is_active = 1
        ORDER BY ga.id
    """)

    join_results = cursor.fetchall()
    print(f"   Total active global agents: {len(join_results)}")

    assigned = sum(1 for row in join_results if row[2] is not None)
    unassigned = len(join_results) - assigned

    print(f"   Assigned to admin: {assigned}")
    print(f"   NOT assigned to admin: {unassigned}")

    if unassigned > 0:
        print(f"\n   ⚠️  Unassigned agents:")
        for row in join_results:
            if row[2] is None:
                print(f"      Global agent ID {row[0]}: {row[1]}")

    # 6. Check raw user_global_agents data
    print("\n6️⃣ Raw user_global_agents data for admin...")
    cursor.execute("""
        SELECT id, user_id, global_agent_id, assigned_at, assigned_by
        FROM user_global_agents
        WHERE user_id = 1
        ORDER BY global_agent_id
    """)

    assignments = cursor.fetchall()
    if assignments:
        print(f"   Found {len(assignments)} assignment records:")
        for assign in assignments:
            print(f"      Assignment ID {assign[0]}: user_id={assign[1]}, global_agent_id={assign[2]}, assigned_at={assign[3]}")
    else:
        print("   ❌ NO assignment records found!")

    # 7. Check for duplicate assignments
    print("\n7️⃣ Checking for duplicate assignments...")
    cursor.execute("""
        SELECT global_agent_id, COUNT(*) as count
        FROM user_global_agents
        WHERE user_id = 1
        GROUP BY global_agent_id
        HAVING COUNT(*) > 1
    """)

    duplicates = cursor.fetchall()
    if duplicates:
        print(f"   ⚠️  Found {len(duplicates)} duplicate assignments:")
        for dup in duplicates:
            print(f"      Global agent ID {dup[0]} assigned {dup[1]} times")
    else:
        print("   ✅ No duplicates found")

    conn.close()

    print("\n" + "=" * 80)
    print("🔍 Diagnostic complete!")

if __name__ == '__main__':
    diagnose_global_agents_issue()
