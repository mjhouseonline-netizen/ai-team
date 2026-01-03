#!/usr/bin/env python3
"""Fix master codes by creating promo_codes table and codes"""

import sqlite3

DB_PATH = '/home/user/ai-team/ai_team.db'

def init_promo_codes_table():
    """Create promo_codes table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🔧 Creating promo_codes table...")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            tier TEXT,
            max_uses INTEGER DEFAULT -1,
            times_used INTEGER DEFAULT 0,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            single_use BOOLEAN DEFAULT 0,
            discount_type TEXT,
            discount_value REAL,
            trial_days INTEGER DEFAULT 0
        )
    """)

    # Insert default MASTER2024 code if it doesn't exist
    cursor.execute("SELECT COUNT(*) FROM promo_codes WHERE code = 'MASTER2024'")
    if cursor.fetchone()[0] == 0:
        print("Creating default MASTER2024 promo code...")
        cursor.execute("""
            INSERT INTO promo_codes (code, tier, max_uses, times_used, is_active, single_use)
            VALUES ('MASTER2024', 'enterprise', -1, 0, 1, 0)
        """)
        print("✅ MASTER2024 code created (Enterprise tier, unlimited uses)")
    else:
        print("✅ MASTER2024 code already exists")

    # Insert MASTER-UNLIMITED-AMANDA code
    cursor.execute("SELECT COUNT(*) FROM promo_codes WHERE code = 'MASTER-UNLIMITED-AMANDA'")
    if cursor.fetchone()[0] == 0:
        print("Creating MASTER-UNLIMITED-AMANDA promo code...")
        cursor.execute("""
            INSERT INTO promo_codes (code, tier, max_uses, times_used, is_active, single_use)
            VALUES ('MASTER-UNLIMITED-AMANDA', 'freeforlife', 1, 0, 1, 1)
        """)
        print("✅ MASTER-UNLIMITED-AMANDA code created (Free for life, single use)")
    else:
        print("✅ MASTER-UNLIMITED-AMANDA code already exists")

    conn.commit()
    conn.close()
    print("✅ Promo codes table and master codes initialized!")

if __name__ == '__main__':
    print("\n🚀 Fixing Master Codes")
    print("=" * 80)
    init_promo_codes_table()

    # Verify
    print("\n📊 Verifying codes...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT code, tier, max_uses, is_active FROM promo_codes")
    codes = cursor.fetchall()

    for code in codes:
        status = "✅ Active" if code[3] else "❌ Inactive"
        uses = "Unlimited" if code[2] == -1 else f"Max {code[2]}"
        print(f"   {code[0]:30} | Tier: {code[1]:15} | {uses:15} | {status}")

    conn.close()

    print("\n" + "=" * 80)
    print("✅ Master codes are now working!")
    print("\nYou can now use:")
    print("  - MASTER2024 (Enterprise, unlimited uses)")
    print("  - MASTER-UNLIMITED-AMANDA (Free for life, single use)")
