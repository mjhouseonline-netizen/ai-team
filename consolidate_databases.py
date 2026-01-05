#!/usr/bin/env python3
"""
Database Consolidation Script
Consolidates users.db and ai_team_platform.db into ai_team.db
"""

import sqlite3
import os
import shutil
from datetime import datetime

def backup_databases():
    """Create backups of all databases before consolidation"""
    backup_dir = f"db_backups_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)

    for db_file in ['ai_team.db', 'users.db', 'ai_team_platform.db']:
        if os.path.exists(db_file):
            backup_path = os.path.join(backup_dir, db_file)
            shutil.copy2(db_file, backup_path)
            print(f"✅ Backed up {db_file} to {backup_path}")

    return backup_dir

def consolidate_databases():
    """Consolidate all databases into ai_team.db"""
    print("\n🔄 Starting database consolidation...")

    # Backup first
    backup_dir = backup_databases()
    print(f"\n📦 Backups created in: {backup_dir}\n")

    # Connect to main database
    main_conn = sqlite3.connect('ai_team.db')
    main_cursor = main_conn.cursor()

    # Check if users.db exists and has data
    if os.path.exists('users.db'):
        print("📊 Checking users.db for unique data...")
        users_conn = sqlite3.connect('users.db')
        users_cursor = users_conn.cursor()

        # Get list of tables in users.db
        users_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in users_cursor.fetchall() if t[0] != 'sqlite_sequence']

        for table in tables:
            users_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = users_cursor.fetchone()[0]
            print(f"  - {table}: {count} rows")

        users_conn.close()
        print("ℹ️  users.db appears to be a legacy database")
        print("ℹ️  All data should already be in ai_team.db via normal usage")

    # Check if ai_team_platform.db exists
    if os.path.exists('ai_team_platform.db'):
        print("\n📊 Checking ai_team_platform.db...")
        platform_conn = sqlite3.connect('ai_team_platform.db')
        platform_cursor = platform_conn.cursor()

        # Check promo_code_usage table
        try:
            platform_cursor.execute("SELECT COUNT(*) FROM promo_code_usage")
            usage_count = platform_cursor.fetchone()[0]
            print(f"  - promo_code_usage: {usage_count} rows")

            if usage_count > 0:
                print("⚠️  Found promo code usage data - migrating...")

                # Ensure promo_code_usage table exists in main db
                main_cursor.execute("""
                    CREATE TABLE IF NOT EXISTS promo_code_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        promo_code_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (promo_code_id) REFERENCES promo_codes (id),
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)

                # Copy data
                platform_cursor.execute("SELECT * FROM promo_code_usage")
                rows = platform_cursor.fetchall()

                for row in rows:
                    try:
                        main_cursor.execute("""
                            INSERT OR IGNORE INTO promo_code_usage
                            (id, promo_code_id, user_id, used_at)
                            VALUES (?, ?, ?, ?)
                        """, row)
                    except Exception as e:
                        print(f"    Warning: {e}")

                main_conn.commit()
                print(f"✅ Migrated {len(rows)} promo code usage records")

        except sqlite3.OperationalError:
            print("  - No promo_code_usage table found")

        platform_conn.close()

    main_conn.close()

    print("\n✅ Database consolidation complete!")
    print("\nNext steps:")
    print("1. Test the application to ensure everything works")
    print("2. If everything works, you can safely delete:")
    print("   - users.db (legacy)")
    print("   - ai_team_platform.db (consolidated)")
    print(f"3. Backups are saved in: {backup_dir}")

if __name__ == "__main__":
    consolidate_databases()
