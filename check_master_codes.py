#!/usr/bin/env python3
"""Check master promo codes status"""

import sqlite3

DB_PATH = '/home/user/ai-team/ai_team.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n🔍 MASTER CODES STATUS CHECK")
print("=" * 80)

# Check for both master codes
master_codes = ['MASTER2024', 'MASTER-UNLIMITED-AMANDA']

for code in master_codes:
    cursor.execute("""
        SELECT code, tier, max_uses, times_used, is_active, single_use,
               discount_type, discount_value, created_at, expires_at
        FROM promo_codes
        WHERE code = ?
    """, (code,))

    result = cursor.fetchone()

    print(f"\n📋 Code: {code}")
    print("-" * 80)

    if result:
        print(f"   ✅ EXISTS in database")
        print(f"   Tier: {result[1]}")
        print(f"   Max Uses: {result[2]} ({'Unlimited' if result[2] == -1 else 'Limited'})")
        print(f"   Times Used: {result[3]}")
        print(f"   Is Active: {'✅ Yes' if result[4] else '❌ No'}")
        print(f"   Single Use: {'Yes' if result[5] else 'No'}")
        print(f"   Discount Type: {result[6] if result[6] else 'None'}")
        print(f"   Discount Value: {result[7] if result[7] else 'N/A'}")
        print(f"   Created: {result[8]}")
        print(f"   Expires: {result[9] if result[9] else 'Never'}")

        # Check if code is valid
        if not result[4]:
            print(f"\n   ⚠️  WARNING: Code is INACTIVE!")
        elif result[5] and result[3] >= 1:
            print(f"\n   ⚠️  WARNING: Single-use code already used!")
        elif result[2] != -1 and result[3] >= result[2]:
            print(f"\n   ⚠️  WARNING: Code has reached max uses!")
        else:
            print(f"\n   ✅ Code is VALID and ready to use")
    else:
        print(f"   ❌ NOT FOUND in database!")
        print(f"   Code needs to be created")

# Check all promo codes
print("\n" + "=" * 80)
print("\n📊 ALL PROMO CODES:")
cursor.execute("""
    SELECT code, tier, max_uses, times_used, is_active
    FROM promo_codes
    ORDER BY created_at DESC
""")

all_codes = cursor.fetchall()
if all_codes:
    for code_data in all_codes:
        status = "✅ Active" if code_data[4] else "❌ Inactive"
        uses = f"{code_data[3]}/{code_data[2]}" if code_data[2] != -1 else f"{code_data[3]}/∞"
        print(f"   {code_data[0]:30} | {code_data[1]:15} | Uses: {uses:10} | {status}")
else:
    print("   No promo codes found in database")

conn.close()

print("\n" + "=" * 80)
print("✅ Diagnostic complete!")
