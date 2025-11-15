"""
Generate 10 Free For Life Promo Codes
Run this ONCE after setting up the promo code system
"""

import sqlite3
import secrets
import string

DB_PATH = 'users.db'

def generate_promo_code(length=12):
    """Generate a random promo code"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def generate_freeforlife_codes():
    """Generate 10 unique free for life promo codes"""
    
    print("🎟️  Generating 10 Free For Life Promo Codes...")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure promo_codes table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
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
    
    codes = []
    attempts = 0
    max_attempts = 50
    
    while len(codes) < 10 and attempts < max_attempts:
        code = "FREEFORLIFE-" + generate_promo_code(8)
        attempts += 1
        
        try:
            cursor.execute("""
                INSERT INTO promo_codes (code, tier, max_uses)
                VALUES (?, 'freeforlife', 1)
            """, (code,))
            codes.append(code)
            print(f"✅ {len(codes)}/10: {code}")
        except sqlite3.IntegrityError:
            # Code already exists, try again
            continue
    
    conn.commit()
    conn.close()
    
    if len(codes) == 10:
        print("\n" + "=" * 60)
        print("🎉 Successfully generated 10 Free For Life codes!")
        print("=" * 60)
        print("\n📋 ALL CODES (Copy these to a safe place):")
        print("-" * 60)
        for i, code in enumerate(codes, 1):
            print(f"{i:2d}. {code}")
        print("-" * 60)
        
        # Save to file
        with open('freeforlife_codes.txt', 'w') as f:
            f.write("AI TEAM - FREE FOR LIFE PROMO CODES\n")
            f.write("=" * 60 + "\n\n")
            f.write("These codes give UNLIMITED lifetime access!\n")
            f.write("Each code can only be used ONCE.\n\n")
            for i, code in enumerate(codes, 1):
                f.write(f"{i:2d}. {code}\n")
            f.write("\n" + "=" * 60 + "\n")
            f.write("Keep these codes secure!\n")
        
        print("\n💾 Codes also saved to: freeforlife_codes.txt")
        
    else:
        print(f"\n⚠️  Warning: Only generated {len(codes)} codes")
    
    print("\n✨ Done!")

if __name__ == '__main__':
    try:
        generate_freeforlife_codes()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("   Make sure users.db exists in the same directory")
