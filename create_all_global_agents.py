#!/usr/bin/env python3
"""Create all 5 global agents and assign to admin"""

import sqlite3
import json

DB_PATH = '/home/user/ai-team/ai_team.db'

# All 5 global agents
ALL_GLOBAL_AGENTS = [
    # Original 3 from web_app_auth.py
    {
        'name': 'Content Helper',
        'description': 'Social media content creation and optimization',
        'emoji': '✍️',
        'category': 'productivity',
        'system_prompt': '''You are a Content Helper specialized in social media content creation.

Your capabilities:
1. Transform messy ideas into polished posts
2. Shorten content while maintaining tone and voice
3. Generate content ideas through strategic questions

When users share messy ideas, clean them up into engaging posts.
When asked to shorten content, preserve the original tone.
When users don't know what to post, ask 3-5 targeted questions about:
- Their target audience
- Recent business updates
- Pain points they solve
- Success stories or testimonials

Always match the user's brand voice and keep responses actionable.''',
        'template_variables': json.dumps({
            'business_name': {'type': 'text', 'description': 'Your business or brand name', 'default': ''},
            'tone': {'type': 'select', 'options': ['Professional', 'Casual', 'Friendly', 'Authoritative'], 'default': 'Professional'},
            'audience': {'type': 'text', 'description': 'Your target audience', 'default': ''}
        })
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

Always ask for context if needed: recipient, purpose, desired tone.''',
        'template_variables': json.dumps({
            'signature': {'type': 'text', 'description': 'Your email signature', 'default': ''},
            'tone': {'type': 'select', 'options': ['Formal', 'Professional', 'Friendly', 'Casual'], 'default': 'Professional'}
        })
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

Format output with clear sections: Summary, Action Items, Decisions, Next Steps.''',
        'template_variables': None
    },
    # Additional 2 agents you like
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
        'emoji': '📋',
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

def create_all_agents():
    """Create all 5 global agents"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    created = []
    existing = []

    for agent in ALL_GLOBAL_AGENTS:
        # Check if agent exists
        cursor.execute("SELECT id FROM global_agents WHERE name = ?", (agent['name'],))
        result = cursor.fetchone()

        if not result:
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
            created.append(agent['name'])
            print(f"✅ Created: {agent['emoji']} {agent['name']}")
        else:
            existing.append(agent['name'])
            print(f"⏭️  Already exists: {agent['emoji']} {agent['name']}")

    conn.commit()
    conn.close()

    return created, existing

def assign_all_to_admin():
    """Assign all global agents to admin (user ID 1)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all active global agents
    cursor.execute("SELECT id, name, emoji FROM global_agents WHERE is_active = 1")
    agents = cursor.fetchall()

    assigned = []
    already_had = []

    print(f"\n🔄 Assigning all global agents to admin...")

    for agent_id, agent_name, emoji in agents:
        try:
            cursor.execute("""
                INSERT INTO user_global_agents (user_id, global_agent_id, assigned_by, assigned_at)
                VALUES (1, ?, 1, CURRENT_TIMESTAMP)
            """, (agent_id,))
            assigned.append(agent_name)
            print(f"  ✅ Assigned: {emoji} {agent_name}")
        except sqlite3.IntegrityError:
            already_had.append(agent_name)
            print(f"  ⏭️  Already had: {emoji} {agent_name}")

    conn.commit()
    conn.close()

    return assigned, already_had

if __name__ == '__main__':
    print("🚀 Creating All Global Agents")
    print("=" * 80)

    created, existing = create_all_agents()

    print(f"\n📊 Agent Creation Summary:")
    print(f"   Newly created: {len(created)}")
    print(f"   Already existed: {len(existing)}")
    print(f"   Total agents: {len(created) + len(existing)}")

    assigned, already_had = assign_all_to_admin()

    print(f"\n📊 Assignment Summary for admin:")
    print(f"   Newly assigned: {len(assigned)}")
    print(f"   Already had access: {len(already_had)}")
    print(f"   Total global agents: {len(assigned) + len(already_had)}")

    print("\n✅ Complete! Refresh your browser to see all 5 global agents.")
