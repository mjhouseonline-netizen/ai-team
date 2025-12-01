#!/usr/bin/env python3
"""
Generate 10 Single-Use Free4Life Promo Codes

This script:
1. Adds 'single_use' column to promo_codes table
2. Generates 10 unique FREE4LIFE codes
3. Each code can only be used once
4. Gives Pro plan for free permanently
"""

import sqlite3
import random
import string

DB_PATH = 'database.db'

def generate_code():
    """Generate a unique code like FREE4LIFE-A1B2"""
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"FREE4LIFE-{suffix}"

def setup_database():
    """Add single_use column if it doesn't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(promo_codes)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'single_use' not in columns:
        print("Adding 'single_use' column to promo_codes table...")
        cursor.execute("""
            ALTER TABLE promo_codes 
            ADD COLUMN single_use INTEGER DEFAULT 0
        """)
        conn.commit()
        print("✅ Column added!")
    else:
        print("✅ Column already exists")
    
    conn.close()

def generate_free4life_codes():
    """Generate 10 unique FREE4LIFE codes"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    codes = []
    attempts = 0
    max_attempts = 100
    
    print("\nGenerating 10 FREE4LIFE codes...")
    
    while len(codes) < 10 and attempts < max_attempts:
        attempts += 1
        code = generate_code()
        
        try:
            # Insert code with single_use=1
            cursor.execute("""
                INSERT INTO promo_codes (
                    code, 
                    tier, 
                    max_uses, 
                    times_used, 
                    is_active,
                    single_use,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (code, 'Pro', 1, 0, 1, 1))
            
            codes.append(code)
            print(f"✅ Generated: {code}")
            
        except sqlite3.IntegrityError:
            # Code already exists, try again
            continue
    
    conn.commit()
    conn.close()
    
    return codes

def display_codes(codes):
    """Display generated codes in a nice format"""
    print("\n" + "="*60)
    print("🎉 10 SINGLE-USE FREE4LIFE CODES GENERATED!")
    print("="*60)
    print("\nThese codes:")
    print("• Give Pro plan ($30/month) for FREE")
    print("• Can only be used ONCE (single-use)")
    print("• After use, code becomes inactive")
    print("• User keeps Pro plan forever\n")
    
    print("CODES:")
    print("-" * 60)
    for i, code in enumerate(codes, 1):
        print(f"{i:2d}. {code}")
    print("-" * 60)
    
    print("\n📋 HOW TO SHARE THESE CODES:")
    print("1. Give one code to each special user")
    print("2. User goes to /pricing")
    print("3. User enters code")
    print("4. User gets Pro plan for FREE")
    print("5. Code becomes inactive (can't be reused)")
    
    print("\n💾 CODES SAVED TO: codes_free4life.txt")
    
    # Save to file
    with open('codes_free4life.txt', 'w') as f:
        f.write("FREE4LIFE SINGLE-USE PROMO CODES\n")
        f.write("="*60 + "\n\n")
        f.write("Plan: Pro ($30/month) for FREE\n")
        f.write("Type: Single-Use Only\n")
        f.write("Generated: Now\n\n")
        f.write("CODES:\n")
        f.write("-"*60 + "\n")
        for i, code in enumerate(codes, 1):
            f.write(f"{i:2d}. {code}\n")
        f.write("-"*60 + "\n")

if __name__ == "__main__":
    print("🚀 FREE4LIFE Code Generator")
    print("="*60)
    
    # Step 1: Update database schema
    setup_database()
    
    # Step 2: Generate codes
    codes = generate_free4life_codes()
    
    # Step 3: Display results
    if len(codes) == 10:
        display_codes(codes)
        print("\n✅ SUCCESS! 10 codes generated and saved to database")
    else:
        print(f"\n❌ ERROR: Only generated {len(codes)}/10 codes")
        print("Try running the script again")
