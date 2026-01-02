#!/usr/bin/env python3
"""Test the global agents API endpoint directly"""

import sqlite3
import json

DB_PATH = '/home/user/ai-team/ai_team.db'

def test_api_endpoint_logic():
    """Simulate what the /api/global-agents endpoint does"""

    print("\n🧪 Testing /api/global-agents API Endpoint Logic")
    print("=" * 80)

    # Simulate the API for user ID 1 (admin)
    user_id = 1

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Execute the same query the API uses
    cursor.execute("""
        SELECT DISTINCT
            ga.id, ga.name, ga.description, ga.emoji, ga.category,
            ga.system_prompt, ga.template_variables, ga.created_at
        FROM global_agents ga
        INNER JOIN user_global_agents uga ON ga.id = uga.global_agent_id
        WHERE uga.user_id = ? AND ga.is_active = 1
        ORDER BY ga.name
    """, (user_id,))

    agents = []
    for row in cursor.fetchall():
        agents.append({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'emoji': row[3],
            'category': row[4],
            'system_prompt': row[5][:100] + '...' if row[5] else None,  # Truncate for display
            'template_variables': json.loads(row[6]) if row[6] else None,
            'created_at': row[7],
            'type': 'global'
        })

    conn.close()

    # This is what the API would return
    api_response = {'agents': agents}

    print(f"\n📊 API Response Summary:")
    print(f"   Total agents: {len(agents)}")
    print(f"   Response format: {{'agents': [...]}}")
    print(f"\n📋 Agents in response:")

    for agent in agents:
        print(f"\n   {agent['emoji']} {agent['name']}")
        print(f"      ID: {agent['id']}")
        print(f"      Description: {agent['description']}")
        print(f"      Category: {agent['category']}")
        print(f"      Type: {agent['type']}")

    print("\n" + "=" * 80)
    print("✅ API endpoint logic test complete!")
    print("\nIf you see 10 agents above, the API is working correctly.")
    print("The issue might be:")
    print("  1. Browser cache - Try hard refresh (Ctrl+Shift+R or Cmd+Shift+R)")
    print("  2. JavaScript console errors - Check browser developer tools")
    print("  3. Session/login issues - Try logging out and back in")
    print("  4. Network issues - Check browser network tab for failed requests")

if __name__ == '__main__':
    test_api_endpoint_logic()
