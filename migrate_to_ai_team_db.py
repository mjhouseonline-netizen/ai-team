"""
Migrate all data to ai_team.db as the single source of truth
This consolidates users.db and creates the proper schema
"""

import sqlite3
import os

def migrate_database():
    """Consolidate all data into ai_team.db"""

    source_db = 'users.db'
    target_db = 'ai_team.db'

    if not os.path.exists(source_db):
        print(f"⚠️  Source database {source_db} not found")
        return

    print(f"📦 Migrating from {source_db} to {target_db}")

    # Connect to both databases
    source_conn = sqlite3.connect(source_db)
    target_conn = sqlite3.connect(target_db)

    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()

    # Create users table in target if it doesn't exist
    target_cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            subscription_tier TEXT DEFAULT 'free',
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            api_key TEXT,
            google_ai_api_key TEXT,
            messages_today INTEGER DEFAULT 0,
            last_message_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create custom_agents table in target
    target_cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            emoji TEXT DEFAULT '🤖',
            personality TEXT,
            system_prompt TEXT NOT NULL,
            share_code TEXT UNIQUE,
            is_public INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Create other tables
    target_cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    target_cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            messages_sent INTEGER DEFAULT 0,
            last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    target_cursor.execute("""
        CREATE TABLE IF NOT EXISTS notion_integrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            access_token TEXT NOT NULL,
            workspace_name TEXT,
            workspace_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    target_cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    target_conn.commit()

    # Copy data from users table
    source_cursor.execute("SELECT * FROM users")
    users = source_cursor.fetchall()

    # Get column names from source
    source_cursor.execute("PRAGMA table_info(users)")
    source_columns = [col[1] for col in source_cursor.fetchall()]

    # Get column names from target
    target_cursor.execute("PRAGMA table_info(users)")
    target_columns = [col[1] for col in target_cursor.fetchall()]

    print(f"\n📋 Source columns: {source_columns}")
    print(f"📋 Target columns: {target_columns}")

    # Find common columns
    common_columns = [col for col in source_columns if col in target_columns]
    print(f"📋 Common columns: {common_columns}")

    # Copy users
    if users:
        print(f"\n👥 Copying {len(users)} users...")
        for user in users:
            # Map source data
            user_dict = dict(zip(source_columns, user))

            # Handle password_hash -> password column rename
            password = user_dict.get('password_hash') or user_dict.get('password', '')

            try:
                target_cursor.execute("""
                    INSERT OR REPLACE INTO users
                    (id, username, email, password, subscription_tier, stripe_customer_id,
                     stripe_subscription_id, api_key, messages_today, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_dict.get('id'),
                    user_dict.get('username'),
                    user_dict.get('email'),
                    password,
                    user_dict.get('subscription_tier', 'free'),
                    user_dict.get('stripe_customer_id'),
                    user_dict.get('stripe_subscription_id'),
                    user_dict.get('api_key'),
                    user_dict.get('messages_today', 0),
                    user_dict.get('created_at')
                ))
                print(f"  ✅ Copied user: {user_dict.get('email')}")
            except Exception as e:
                print(f"  ⚠️  Error copying user {user_dict.get('email', 'unknown')}: {e}")

    # Copy custom_agents if they exist in source
    try:
        source_cursor.execute("SELECT * FROM custom_agents")
        agents = source_cursor.fetchall()
        if agents:
            print(f"\n🤖 Copying {len(agents)} custom agents...")
            source_cursor.execute("PRAGMA table_info(custom_agents)")
            agent_columns = [col[1] for col in source_cursor.fetchall()]

            for agent in agents:
                agent_dict = dict(zip(agent_columns, agent))
                target_cursor.execute("""
                    INSERT OR REPLACE INTO custom_agents
                    (id, user_id, name, description, emoji, personality, system_prompt, share_code, is_public, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent_dict.get('id'),
                    agent_dict.get('user_id'),
                    agent_dict.get('name'),
                    agent_dict.get('description'),
                    agent_dict.get('emoji', '🤖'),
                    agent_dict.get('personality'),
                    agent_dict.get('system_prompt'),
                    agent_dict.get('share_code'),
                    agent_dict.get('is_public', 0),
                    agent_dict.get('created_at')
                ))
    except sqlite3.OperationalError as e:
        print(f"  ℹ️  custom_agents table not in source: {e}")

    target_conn.commit()

    # Verify migration
    target_cursor.execute("SELECT COUNT(*) FROM users")
    user_count = target_cursor.fetchone()[0]

    target_cursor.execute("SELECT COUNT(*) FROM custom_agents")
    agent_count = target_cursor.fetchone()[0]

    print(f"\n✅ Migration complete!")
    print(f"   Users: {user_count}")
    print(f"   Custom agents: {agent_count}")

    # Show sample data
    if user_count > 0:
        target_cursor.execute("SELECT id, email, subscription_tier FROM users LIMIT 1")
        sample = target_cursor.fetchone()
        print(f"\n   Sample user: ID={sample[0]}, Email={sample[1]}, Tier={sample[2]}")

    source_conn.close()
    target_conn.close()

    print(f"\n✅ {target_db} is now the primary database")

if __name__ == '__main__':
    migrate_database()
