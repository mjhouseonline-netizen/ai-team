"""
Create custom_agents table in ai_team.db
Run this to initialize the database for custom agents
"""

import sqlite3
import os

def create_custom_agents_table():
    """Create the custom_agents table if it doesn't exist"""
    db_path = 'ai_team.db'

    print(f"Creating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create custom_agents table
    cursor.execute("""
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

    conn.commit()

    # Verify table was created
    cursor.execute("PRAGMA table_info(custom_agents)")
    columns = cursor.fetchall()

    print("\n✅ custom_agents table created successfully!")
    print("\nColumns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")

    conn.close()
    print(f"\n✅ Database ready: {db_path}")

if __name__ == '__main__':
    create_custom_agents_table()
