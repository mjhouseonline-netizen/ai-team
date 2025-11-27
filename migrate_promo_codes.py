"""
Promo Codes Database Migration Script
Run this in Render Shell to fix the promo_codes table
"""

import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'ai_team_platform.db')

def migrate_promo_codes_table():
    """Migrate promo_codes table to add missing columns"""
    
    print("🔧 Starting promo codes database migration...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if promo_codes table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='promo_codes'
        """)
        
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("📦 Creating promo_codes table...")
            cursor.execute("""
                CREATE TABLE promo_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    tier TEXT NOT NULL,
                    max_uses INTEGER DEFAULT 1,
                    times_used INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            print("✅ Created promo_codes table")
        else:
            print("✅ promo_codes table exists")
            
            # Check existing columns
            cursor.execute("PRAGMA table_info(promo_codes)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            print(f"📋 Existing columns: {existing_columns}")
            
            # Add missing columns
            if 'times_used' not in existing_columns:
                print("➕ Adding times_used column...")
                cursor.execute("ALTER TABLE promo_codes ADD COLUMN times_used INTEGER DEFAULT 0")
                # Update existing rows
                cursor.execute("UPDATE promo_codes SET times_used = 0 WHERE times_used IS NULL")
                print("✅ Added times_used column")
            else:
                print("✅ times_used column exists")
            
            if 'is_active' not in existing_columns:
                print("➕ Adding is_active column...")
                cursor.execute("ALTER TABLE promo_codes ADD COLUMN is_active BOOLEAN DEFAULT 1")
                # Update existing rows
                cursor.execute("UPDATE promo_codes SET is_active = 1 WHERE is_active IS NULL")
                print("✅ Added is_active column")
            else:
                print("✅ is_active column exists")
            
            if 'max_uses' not in existing_columns:
                print("➕ Adding max_uses column...")
                cursor.execute("ALTER TABLE promo_codes ADD COLUMN max_uses INTEGER DEFAULT 1")
                cursor.execute("UPDATE promo_codes SET max_uses = 1 WHERE max_uses IS NULL")
                print("✅ Added max_uses column")
            else:
                print("✅ max_uses column exists")
            
            if 'expires_at' not in existing_columns:
                print("➕ Adding expires_at column...")
                cursor.execute("ALTER TABLE promo_codes ADD COLUMN expires_at TIMESTAMP")
                print("✅ Added expires_at column")
            else:
                print("✅ expires_at column exists")
        
        # Check if promo_code_usage table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='promo_code_usage'
        """)
        
        usage_table_exists = cursor.fetchone()
        
        if not usage_table_exists:
            print("📦 Creating promo_code_usage table...")
            cursor.execute("""
                CREATE TABLE promo_code_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    promo_code_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (promo_code_id) REFERENCES promo_codes (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(promo_code_id, user_id)
                )
            """)
            print("✅ Created promo_code_usage table")
        else:
            print("✅ promo_code_usage table exists")
        
        # Commit changes
        conn.commit()
        
        # Verify final schema
        cursor.execute("PRAGMA table_info(promo_codes)")
        final_columns = [col[1] for col in cursor.fetchall()]
        print(f"\n📋 Final promo_codes schema: {final_columns}")
        
        # Count existing codes
        cursor.execute("SELECT COUNT(*) FROM promo_codes")
        code_count = cursor.fetchone()[0]
        print(f"📊 Existing promo codes: {code_count}")
        
        conn.close()
        
        print("\n✅ Migration completed successfully!")
        print("\n🎯 Next steps:")
        print("1. Restart your web server")
        print("2. Go to /promo-codes page")
        print("3. Try generating codes again")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🎫 Promo Codes Database Migration")
    print("=" * 60)
    print()
    
    success = migrate_promo_codes_table()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ MIGRATION SUCCESSFUL")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ MIGRATION FAILED")
        print("=" * 60)
