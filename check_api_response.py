#!/usr/bin/env python3
"""Check what the API would actually return for different scenarios"""

import sqlite3
import json

DB_PATH = '/home/user/ai-team/ai_team.db'

def check_api_for_all_users():
    """Check what the API would return for each user"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n🔍 Checking API Response for All Users")
    print("=" * 80)

    # Get all users
    cursor.execute("SELECT id, email, username FROM users ORDER BY id")
    users = cursor.fetchall()

    for user in users:
        user_id = user[0]
        user_email = user[1]
        user_username = user[2]

        print(f"\n👤 User: {user_email} (ID: {user_id}, Username: {user_username})")
        print("-" * 80)

        # Simulate the API query for this user
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
                'type': 'global'
            })

        # This is what /api/global-agents would return
        api_response = {'agents': agents}

        if agents:
            print(f"   ✅ API would return {len(agents)} agents:")
            for agent in agents:
                print(f"      {agent['emoji']} {agent['name']}")
        else:
            print(f"   ❌ API would return 0 agents (empty array)")
            print(f"      Response: {json.dumps(api_response)}")

    conn.close()

    print("\n" + "=" * 80)

def check_login_required_decorator():
    """Check if there might be issues with @login_required"""

    print("\n🔐 Login/Session Troubleshooting:")
    print("=" * 80)
    print("""
If the API returns an empty array for the admin user, possible causes:

1. Session Issue:
   - You might not be logged in properly
   - Session might have expired
   - Flask session might not be persisting current_user.id

2. Authentication Issue:
   - @login_required might be failing
   - current_user.id might be None or different from 1

3. Browser Issue:
   - Cookies disabled
   - CORS issue
   - Session cookie not being sent

SOLUTION:
1. Check browser Network tab for /api/global-agents request
2. Look at the Response tab - what does it show?
   - If it shows {"agents": []}, there's a session issue
   - If it shows an error, there's an auth issue
   - If it redirects to /login, you're not logged in

3. Check if the request has cookies:
   - In Network tab, click on /api/global-agents request
   - Go to Headers tab
   - Look for "Cookie" in Request Headers
   - Should have session cookie

4. Try:
   - Log out completely
   - Clear all cookies for the site
   - Log back in with bubblesfox@gmail.com
   - Hard refresh the page
""")

if __name__ == '__main__':
    check_api_for_all_users()
    check_login_required_decorator()
