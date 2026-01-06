#!/usr/bin/env python3
"""
Database Restore Script
Safely restore databases from backup
"""

import os
import shutil
import sqlite3
from datetime import datetime

BACKUP_DIR = 'auto_backups'
DB_FILES = ['ai_team.db', 'users.db', 'ai_team_platform.db']

def list_backups():
    """List all available backups with details"""
    if not os.path.exists(BACKUP_DIR):
        print("❌ No backups directory found")
        return []

    backups = []
    for item in os.listdir(BACKUP_DIR):
        item_path = os.path.join(BACKUP_DIR, item)
        if os.path.isdir(item_path) and item.startswith('backup_'):
            timestamp = os.path.getmtime(item_path)
            backups.append((item, item_path, timestamp))

    # Sort by modification time (newest first)
    backups.sort(key=lambda x: x[2], reverse=True)

    print("\n📦 Available Backups:\n")
    for i, (name, path, timestamp) in enumerate(backups, 1):
        dt = datetime.fromtimestamp(timestamp)
        print(f"{i}. {name}")
        print(f"   Created: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

        # Check what's in the backup
        for db_file in DB_FILES:
            backup_file = os.path.join(path, db_file)
            if os.path.exists(backup_file):
                size = os.path.getsize(backup_file)
                print(f"   - {db_file}: {size:,} bytes")
        print()

    return backups

def verify_backup(backup_path):
    """Verify backup contains valid data"""
    print(f"\n🔍 Verifying backup: {backup_path}")

    db_file = os.path.join(backup_path, 'ai_team.db')
    if not os.path.exists(db_file):
        print("❌ Backup does not contain ai_team.db")
        return False

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Check users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        # Check global agents
        cursor.execute("SELECT COUNT(*) FROM global_agents")
        agent_count = cursor.fetchone()[0]

        conn.close()

        print(f"✅ Backup contains:")
        print(f"   - {user_count} user(s)")
        print(f"   - {agent_count} global agent(s)")

        return True

    except Exception as e:
        print(f"❌ Error verifying backup: {e}")
        return False

def create_safety_backup():
    """Create a safety backup of current database before restore"""
    safety_dir = 'safety_backups'
    os.makedirs(safety_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safety_path = os.path.join(safety_dir, f'pre_restore_{timestamp}')
    os.makedirs(safety_path, exist_ok=True)

    print(f"\n🔒 Creating safety backup before restore: {safety_path}")

    for db_file in DB_FILES:
        if os.path.exists(db_file):
            backup_file = os.path.join(safety_path, db_file)
            shutil.copy2(db_file, backup_file)
            print(f"   ✅ Backed up {db_file}")

    return safety_path

def restore_backup(backup_path):
    """Restore database from backup"""
    print(f"\n🔄 Restoring from: {backup_path}")

    # Verify backup first
    if not verify_backup(backup_path):
        print("\n❌ Backup verification failed. Aborting restore.")
        return False

    # Create safety backup
    safety_backup = create_safety_backup()

    # Confirm with user
    print("\n⚠️  WARNING: This will replace your current database!")
    print(f"   A safety backup has been created at: {safety_backup}")
    response = input("\nType 'RESTORE' to confirm: ")

    if response != 'RESTORE':
        print("❌ Restore cancelled")
        return False

    # Perform restore
    print("\n📥 Restoring databases...")

    for db_file in DB_FILES:
        backup_file = os.path.join(backup_path, db_file)
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, db_file)
            print(f"   ✅ Restored {db_file}")

    print("\n✅ Restore complete!")
    print(f"   Original database saved at: {safety_backup}")

    return True

if __name__ == '__main__':
    import sys

    print("=" * 60)
    print("DATABASE RESTORE TOOL")
    print("=" * 60)

    backups = list_backups()

    if not backups:
        print("❌ No backups found")
        sys.exit(1)

    if len(sys.argv) > 1:
        # Restore specific backup by number
        try:
            backup_num = int(sys.argv[1])
            if 1 <= backup_num <= len(backups):
                backup_path = backups[backup_num - 1][1]
                restore_backup(backup_path)
            else:
                print(f"❌ Invalid backup number. Choose 1-{len(backups)}")
        except ValueError:
            print("❌ Invalid backup number")
    else:
        print("Usage:")
        print("  python3 restore_backup.py <backup_number>")
        print("\nExample:")
        print("  python3 restore_backup.py 1  # Restore the most recent backup")
