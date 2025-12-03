"""
Database Migration Script
Adds subscription columns to existing users table
"""

import sqlite3
import os

def migrate_database():
    """Add subscription columns to users table if they don't exist"""
    db_path = 'users.db'
    
    if not os.path.exists(db_path):
        print("No existing database found - will be created fresh")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    
    print(f"Existing columns: {columns}")
    
    # Add missing columns
    columns_to_add = [
        ("subscription_tier", "TEXT DEFAULT 'free'"),
        ("stripe_customer_id", "TEXT"),
        ("stripe_subscription_id", "TEXT"),
        ("messages_today", "INTEGER DEFAULT 0"),
        ("last_message_reset", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]
    
    for column_name, column_def in columns_to_add:
        if column_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_def}")
                print(f"✅ Added column: {column_name}")
            except Exception as e:
                print(f"⚠️ Could not add {column_name}: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Migration complete!")

if __name__ == '__main__':
    migrate_database()
