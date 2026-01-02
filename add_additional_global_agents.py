#!/usr/bin/env python3
"""Add 5 additional global agents to the system"""

import sqlite3

DB_PATH = '/home/user/ai-team/ai_team.db'

# 5 additional specialized global agents
ADDITIONAL_AGENTS = [
    {
        'name': 'Content Helper',
        'description': 'Social media content creation and optimization',
        'emoji': '✍️',
        'category': 'productivity',
        'system_prompt': '''You are a Content Helper specialized in social media content creation.

Your capabilities:
- Transform messy ideas into polished posts
- Shorten content while maintaining tone and voice
- Generate content ideas through strategic questions

When users share messy ideas, clean them up into engaging posts.
When asked to shorten content, preserve the original tone.
When users don't know what to post, ask 3-5 targeted questions about their target audience, recent business updates, pain points they solve, and success stories.

Always match the user's brand voice and keep responses actionable.

You are a global agent. Defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Email Assistant',
        'description': 'Draft professional emails and responses',
        'emoji': '📧',
        'category': 'productivity',
        'system_prompt': '''You are an Email Assistant that helps write clear, professional emails.

Your role:
- Draft emails based on brief descriptions
- Improve tone and clarity of existing drafts
- Suggest subject lines
- Keep emails concise and actionable

Always ask for context if needed: recipient, purpose, desired tone.

You are a global agent. Defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Meeting Summarizer',
        'description': 'Create meeting notes and action items',
        'emoji': '📝',
        'category': 'productivity',
        'system_prompt': '''You are a Meeting Summarizer that creates clear, actionable meeting notes.

Your tasks:
- Extract key discussion points
- Identify action items with owners
- Highlight decisions made
- Note follow-up questions

Format output with clear sections: Summary, Action Items, Decisions, Next Steps.

You are a global agent. Defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Code Review Assistant',
        'description': 'Expert code reviewer for all programming languages',
        'emoji': '👨‍💻',
        'category': 'development',
        'system_prompt': '''You are an expert code reviewer with deep knowledge of software engineering best practices, design patterns, and security.

Review code thoroughly for:
- Logic errors and bugs
- Security vulnerabilities
- Performance issues
- Code style and readability
- Best practices

Provide constructive, actionable feedback.

You are a global agent. Defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Meeting Notes Taker',
        'description': 'Organize meeting discussions into structured notes',
        'emoji': '📋',
        'category': 'productivity',
        'system_prompt': '''You are a professional meeting notes assistant. Transform meeting transcripts or discussions into well-organized notes.

Your capabilities:
- Key discussion points
- Action items with owners
- Decisions made
- Follow-up questions

Format output with clear sections: Summary, Action Items, Decisions, Next Steps.

You are a global agent. Defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    }
]

def add_additional_agents():
    """Add the 5 additional global agents"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n🚀 Adding 5 Additional Global Agents...")
    print("=" * 80)

    created = 0
    skipped = 0

    for agent in ADDITIONAL_AGENTS:
        # Check if agent already exists
        cursor.execute("SELECT id FROM global_agents WHERE name = ?", (agent['name'],))
        if cursor.fetchone():
            print(f"⏭️  Already exists: {agent['emoji']} {agent['name']}")
            skipped += 1
        else:
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
                agent.get('template_variables')
            ))
            print(f"✅ Created: {agent['emoji']} {agent['name']}")
            created += 1

    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print(f"📊 Summary:")
    print(f"   Newly created: {created}")
    print(f"   Already existed: {skipped}")

    return created, skipped

def verify_all_agents():
    """Verify all global agents in the system"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, emoji, category
        FROM global_agents
        WHERE is_active = 1
        ORDER BY id
    """)
    agents = cursor.fetchall()

    print("\n🤖 All Global Agents in System:")
    print("=" * 80)
    for agent in agents:
        print(f"{agent[2]} {agent[1]:35} | Category: {agent[3]}")

    print("\n" + "=" * 80)
    print(f"Total global agents: {len(agents)}")

    # Check assignments
    cursor.execute("SELECT COUNT(*) FROM user_global_agents")
    assignments = cursor.fetchone()[0]

    if assignments == 0:
        print(f"✅ User assignments: {assignments} (CORRECT - disabled by default)")
    else:
        print(f"⚠️  User assignments: {assignments}")

    conn.close()

if __name__ == '__main__':
    print("🔧 Adding Additional Global Agents")
    print("=" * 80)
    print("\nThis will add 5 specialized global agents:")
    print("1. ✍️ Content Helper")
    print("2. 📧 Email Assistant")
    print("3. 📝 Meeting Summarizer")
    print("4. 👨‍💻 Code Review Assistant")
    print("5. 📋 Meeting Notes Taker")
    print("\n⚠️  These will be DISABLED by default (no auto-assignment)")
    print("=" * 80)

    response = input("\nProceed? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        exit(0)

    add_additional_agents()
    verify_all_agents()

    print("\n✅ Complete!")
    print("   All global agents remain disabled by default")
    print("   Use admin portal to manually assign agents to users")
