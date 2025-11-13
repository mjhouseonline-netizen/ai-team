# create_notion_table.py
# Run this ONCE to create the Notion integrations table

import sqlite3
import os

def create_notion_integration_table():
    """Create the notion_integrations table in the users database"""
    
    # Path to your users database
    db_path = 'users.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Error: {db_path} not found!")
        print("Make sure you're running this from your ai-team folder")
        return
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create notion_integrations table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS notion_integrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        access_token TEXT NOT NULL,
        workspace_id TEXT,
        workspace_name TEXT,
        workspace_icon TEXT,
        bot_id TEXT,
        connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_synced TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """
    
    try:
        cursor.execute(create_table_sql)
        conn.commit()
        print("✅ SUCCESS! notion_integrations table created!")
        print()
        
        # Verify table was created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notion_integrations';")
        result = cursor.fetchone()
        
        if result:
            print("✅ Table verified in database!")
            print()
            print("Next steps:")
            print("1. Edit ai_team.py to register the Notion blueprint")
            print("2. Edit notion_routes.py to fix imports")
            print("3. Edit notion_api.py to fix imports")
            print("4. Deploy to Render!")
        else:
            print("⚠️  Warning: Table creation reported success but couldn't verify")
            
    except sqlite3.Error as e:
        print(f"❌ Error creating table: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("="*60)
    print("NOTION INTEGRATION - DATABASE TABLE CREATOR")
    print("="*60)
    print()
    create_notion_integration_table()
