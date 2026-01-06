#!/usr/bin/env python3
"""
Add share codes to custom agents that don't have them yet
This ensures all custom agents are shareable
"""

import sqlite3
import secrets
import os

def get_db_path():
    """Get the database path"""
    # Check for the database in common locations
    possible_paths = [
        'ai_team.db',
        'instance/ai_team.db',
        '/home/user/ai-team/ai_team.db'
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return 'ai_team.db'  # Default

def fix_missing_share_codes():
    """Add share codes to custom agents that don't have them"""
    db_path = get_db_path()
    print(f"📂 Using database: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if share_code column exists
        cursor.execute("PRAGMA table_info(custom_agents)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'share_code' not in columns:
            print("⚠️ share_code column doesn't exist yet. It will be created when the first agent is created.")
            conn.close()
            return

        # Find agents without share codes
        cursor.execute("""
            SELECT id, name, user_id
            FROM custom_agents
            WHERE share_code IS NULL OR share_code = ''
        """)

        agents_without_codes = cursor.fetchall()

        if not agents_without_codes:
            print("✅ All custom agents already have share codes!")
            conn.close()
            return

        print(f"🔍 Found {len(agents_without_codes)} agents without share codes")

        # Generate share codes for each agent
        updated = 0
        for agent_id, name, user_id in agents_without_codes:
            # Generate unique share code
            share_code = secrets.token_urlsafe(12)

            # Ensure it's unique
            while True:
                cursor.execute("SELECT id FROM custom_agents WHERE share_code = ?", (share_code,))
                if not cursor.fetchone():
                    break
                share_code = secrets.token_urlsafe(12)

            # Update the agent
            cursor.execute("""
                UPDATE custom_agents
                SET share_code = ?, is_public = 1
                WHERE id = ?
            """, (share_code, agent_id))

            print(f"   ✅ Added share code to '{name}' (ID: {agent_id}, User: {user_id})")
            updated += 1

        conn.commit()
        conn.close()

        print(f"\n🎉 Successfully added share codes to {updated} custom agents!")
        print(f"   All custom agents are now shareable!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("🔧 Fixing missing share codes for custom agents...\n")
    fix_missing_share_codes()
