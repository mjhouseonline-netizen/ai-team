#!/usr/bin/env python3
"""
Automatic Database Backup Script
Backs up all databases every hour to prevent data loss
"""

import sqlite3
import os
import shutil
from datetime import datetime
import time

DB_FILES = ['ai_team.db', 'users.db', 'ai_team_platform.db']
BACKUP_DIR = 'auto_backups'
MAX_BACKUPS = 24  # Keep last 24 backups (1 day if running hourly)

def create_backup():
    """Create timestamped backup of all databases"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'backup_{timestamp}')

    os.makedirs(backup_path, exist_ok=True)

    backed_up = False
    for db_file in DB_FILES:
        if os.path.exists(db_file):
            file_size = os.path.getsize(db_file)
            backup_file = os.path.join(backup_path, db_file)
            shutil.copy2(db_file, backup_file)
            print(f"✅ Backed up {db_file} ({file_size:,} bytes) -> {backup_file}")
            backed_up = True

    if backed_up:
        print(f"✅ Backup created: {backup_path}")
        cleanup_old_backups()
    else:
        print("⚠️  No database files found to backup")
        # Remove empty backup directory
        os.rmdir(backup_path)

    return backed_up

def cleanup_old_backups():
    """Remove old backups, keeping only MAX_BACKUPS most recent"""
    if not os.path.exists(BACKUP_DIR):
        return

    backups = []
    for item in os.listdir(BACKUP_DIR):
        item_path = os.path.join(BACKUP_DIR, item)
        if os.path.isdir(item_path) and item.startswith('backup_'):
            backups.append((item_path, os.path.getmtime(item_path)))

    # Sort by modification time (newest first)
    backups.sort(key=lambda x: x[1], reverse=True)

    # Remove old backups
    for backup_path, _ in backups[MAX_BACKUPS:]:
        print(f"🗑️  Removing old backup: {backup_path}")
        shutil.rmtree(backup_path)

def verify_backup(backup_path):
    """Verify that backup databases are valid and contain data"""
    for db_file in DB_FILES:
        backup_file = os.path.join(backup_path, db_file)
        if not os.path.exists(backup_file):
            continue

        try:
            conn = sqlite3.connect(backup_file)
            cursor = conn.cursor()

            # Try to query users table
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]

            conn.close()
            print(f"  ✅ {db_file}: {user_count} users")
        except Exception as e:
            print(f"  ⚠️  {db_file}: {e}")

def run_continuous_backup(interval_seconds=3600):
    """Run backup every interval_seconds (default: 1 hour)"""
    print(f"🔄 Starting automatic backup (every {interval_seconds}s)")

    while True:
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n[{timestamp}] Creating backup...")
            create_backup()
        except Exception as e:
            print(f"❌ Backup failed: {e}")

        print(f"⏰ Next backup in {interval_seconds}s...")
        time.sleep(interval_seconds)

if __name__ == '__main__':
    import sys

    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)

    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        # Run continuous backups
        run_continuous_backup()
    else:
        # Single backup
        print("Creating single backup...")
        if create_backup():
            print("\n✅ Backup complete!")
        else:
            print("\n⚠️  No backup created")
            sys.exit(1)
