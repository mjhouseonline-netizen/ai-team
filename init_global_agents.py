#!/usr/bin/env python3
"""Initialize global agents tables and assign default agents to users"""

import sqlite3
import os

DB_PATH = '/home/user/ai-team/ai_team.db'

# Default global agents
DEFAULT_GLOBAL_AGENTS = [
    {
        'name': 'Code Review Assistant',
        'description': 'Expert code reviewer for all programming languages',
        'emoji': '👨‍💻',
        'category': 'development',
        'system_prompt': '''You are an expert code reviewer with deep knowledge of software engineering best practices, design patterns, and security. Review code thoroughly for:
- Logic errors and bugs
- Security vulnerabilities
- Performance issues
- Code style and readability
- Best practices
Provide constructive, actionable feedback.''',
        'template_variables': None
    },
    {
        'name': 'Meeting Notes Taker',
        'description': 'Organize meeting discussions into structured notes',
        'emoji': '📝',
        'category': 'productivity',
        'system_prompt': '''You are a professional meeting notes assistant. Transform meeting transcripts or discussions into well-organized notes with:
- Key discussion points
- Action items with owners
- Decisions made
- Follow-up questions
Format output with clear sections: Summary, Action Items, Decisions, Next Steps.''',
        'template_variables': None
    }
]

def init_global_agents_tables():
    """Create global_agents tables if they don't exist"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create global_agents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS global_agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                emoji TEXT DEFAULT '🤖',
                category TEXT DEFAULT 'general',
                system_prompt TEXT NOT NULL,
                template_variables TEXT DEFAULT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        """)

        # Create user_global_agents junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_global_agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                global_agent_id INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (global_agent_id) REFERENCES global_agents (id),
                FOREIGN KEY (assigned_by) REFERENCES users (id),
                UNIQUE(user_id, global_agent_id)
            )
        """)

        conn.commit()
        conn.close()
        print("✅ Global agents tables created")
        return True

    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False

def create_default_global_agents():
    """Create default global agents"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for agent in DEFAULT_GLOBAL_AGENTS:
            # Check if agent already exists
            cursor.execute("SELECT id FROM global_agents WHERE name = ?", (agent['name'],))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO global_agents (
                        name, description, emoji, category, system_prompt,
                        template_variables, created_by, is_active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP)
                """, (
                    agent['name'],
                    agent['description'],
                    agent['emoji'],
                    agent['category'],
                    agent['system_prompt'],
                    agent['template_variables']
                ))
                print(f"✅ Created global agent: {agent['name']}")

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error creating default agents: {str(e)}")
        return False

def assign_agents_to_all_users():
    """Assign all global agents to all users"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get all users
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()

        # Get all global agents
        cursor.execute("SELECT id FROM global_agents WHERE is_active = 1")
        agents = cursor.fetchall()

        assigned_count = 0
        for user in users:
            user_id = user[0]
            for agent in agents:
                agent_id = agent[0]
                try:
                    cursor.execute("""
                        INSERT INTO user_global_agents (user_id, global_agent_id, assigned_by, assigned_at)
                        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                    """, (user_id, agent_id))
                    assigned_count += 1
                except sqlite3.IntegrityError:
                    # Already assigned, skip
                    pass

        conn.commit()
        conn.close()
        print(f"✅ Assigned {assigned_count} global agents to users")
        return True

    except Exception as e:
        print(f"❌ Error assigning agents: {str(e)}")
        return False

if __name__ == '__main__':
    print("🚀 Initializing global agents system...")
    print(f"📂 Database: {DB_PATH}\n")

    # Step 1: Create tables
    if not init_global_agents_tables():
        print("Failed to create tables")
        exit(1)

    # Step 2: Create default agents
    if not create_default_global_agents():
        print("Failed to create default agents")
        exit(1)

    # Step 3: Assign to all users
    if not assign_agents_to_all_users():
        print("Failed to assign agents to users")
        exit(1)

    # Verify
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM global_agents")
    agent_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM user_global_agents")
    assignment_count = cursor.fetchone()[0]
    conn.close()

    print(f"\n📊 Summary:")
    print(f"   Total global agents: {agent_count}")
    print(f"   Total assignments: {assignment_count}")
    print(f"\n✅ Setup complete! Refresh your browser to see the global agents.")
