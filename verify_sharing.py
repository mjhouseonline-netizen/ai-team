#!/usr/bin/env python3
"""
Verify that all custom agents have proper share codes and can be shared
"""

import sqlite3
import os

def get_db_path():
    """Get the database path"""
    possible_paths = [
        'ai_team.db',
        'instance/ai_team.db',
        '/home/user/ai-team/ai_team.db'
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return 'ai_team.db'

def verify_sharing():
    """Verify sharing functionality"""
    db_path = get_db_path()
    print(f"📂 Using database: {db_path}\n")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if share_code column exists
        cursor.execute("PRAGMA table_info(custom_agents)")
        columns = [col[1] for col in cursor.fetchall()]

        print("📋 Custom Agents Table Columns:")
        print(f"   {', '.join(columns)}\n")

        if 'share_code' not in columns:
            print("❌ share_code column doesn't exist!")
            print("   This column will be created when the first agent is created.\n")
            conn.close()
            return

        # Get all custom agents
        cursor.execute("""
            SELECT id, user_id, name, description, emoji, share_code, is_public
            FROM custom_agents
            ORDER BY created_at DESC
        """)

        agents = cursor.fetchall()
        conn.close()

        if not agents:
            print("ℹ️ No custom agents found in database\n")
            return

        print(f"🤖 Found {len(agents)} custom agents:\n")

        agents_with_share = 0
        agents_without_share = 0

        for agent_id, user_id, name, description, emoji, share_code, is_public in agents:
            emoji_display = emoji or '🤖'
            has_share = bool(share_code)

            if has_share:
                agents_with_share += 1
                status = "✅ SHAREABLE"
                share_url = f"http://localhost:5000/custom/{share_code}"
            else:
                agents_without_share += 1
                status = "❌ NO SHARE CODE"
                share_url = "N/A"

            print(f"{status}")
            print(f"   ID: {agent_id}")
            print(f"   Name: {emoji_display} {name}")
            print(f"   Owner: User #{user_id}")
            print(f"   Description: {description}")
            print(f"   Share Code: {share_code or 'None'}")
            print(f"   Share URL: {share_url}")
            print(f"   Public: {'Yes' if is_public else 'No'}")
            print()

        print("=" * 60)
        print(f"📊 Summary:")
        print(f"   Total agents: {len(agents)}")
        print(f"   ✅ Shareable: {agents_with_share}")
        print(f"   ❌ Not shareable: {agents_without_share}")
        print()

        if agents_without_share > 0:
            print("⚠️ Some agents are missing share codes!")
            print("   Run fix_missing_share_codes.py to fix this.")
        else:
            print("🎉 All custom agents are shareable!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("🔍 Verifying Custom Agent Sharing...\n")
    verify_sharing()
