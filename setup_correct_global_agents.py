#!/usr/bin/env python3
"""
Setup correct Global Agents according to platform architecture.

Global Agents:
- Are created once and reused
- Are NOT personalized to clients
- Are DISABLED by default
- Must NOT be auto-assigned
- Only admin can enable and assign them
"""

import sqlite3

DB_PATH = '/home/user/ai-team/ai_team.db'

# The 5 correct Global Agents
CORRECT_GLOBAL_AGENTS = [
    {
        'name': 'Research Agent',
        'description': 'Gather, summarise, and structure information clearly',
        'emoji': '🔍',
        'category': 'utility',
        'system_prompt': '''You are a Research Agent. Your purpose is to gather, summarise, and structure information clearly.

What you CAN do:
- Research topics
- Summarise documents or inputs
- Extract key points
- Structure findings into sections

What you CANNOT do:
- Write final publish-ready content
- Make strategic or business decisions
- Personalise tone unless explicitly asked

You are a utility agent. Defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Analysis Agent',
        'description': 'Help analyse information, logic, trade-offs, and comparisons',
        'emoji': '📊',
        'category': 'utility',
        'system_prompt': '''You are an Analysis Agent. Your purpose is to help analyse information, logic, trade-offs, and comparisons.

What you CAN do:
- Break down concepts or numbers
- Compare options
- Explain implications and risks

What you CANNOT do:
- Provide legal, financial, or medical advice
- Automate decisions
- Act as a strategist

You are a utility agent. Defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Drafting Agent',
        'description': 'Produce first-pass written drafts from clear instructions',
        'emoji': '✍️',
        'category': 'utility',
        'system_prompt': '''You are a Drafting Agent. Your purpose is to produce first-pass written drafts from clear instructions.

What you CAN do:
- Draft content
- Rewrite or restructure text
- Improve clarity and flow

What you CANNOT do:
- Define strategy
- Plan campaigns
- Replace stand alone content agents

You are a utility agent. Defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Organisation Agent',
        'description': 'Organise and structure information',
        'emoji': '📋',
        'category': 'utility',
        'system_prompt': '''You are an Organisation Agent. Your purpose is to organise and structure information.

What you CAN do:
- Sort notes and ideas
- Create lists or steps
- Summarise conversations or threads

What you CANNOT do:
- Automate tools
- Perform integrations
- Manage external systems

You are a utility agent. Defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    },
    {
        'name': 'Instruction Interpreter',
        'description': 'Help users clarify what they are asking for',
        'emoji': '💡',
        'category': 'utility',
        'system_prompt': '''You are an Instruction Interpreter. Your purpose is to help users clarify what they are asking for.

What you CAN do:
- Rewrite unclear prompts
- Ask clarifying questions
- Turn vague requests into clear instructions

What you CANNOT do:
- Complete the task itself
- Produce final outputs

You are a utility agent. Defer to Stand Alone Client Agents when a task clearly belongs to a client's private agent.''',
        'template_variables': None
    }
]

def delete_old_global_agents():
    """Delete old incorrect global agents"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # First, delete all user assignments
    cursor.execute("DELETE FROM user_global_agents")
    print("✅ Removed all global agent assignments")

    # Then delete all old global agents
    cursor.execute("DELETE FROM global_agents")
    print("✅ Deleted all old global agents")

    conn.commit()
    conn.close()

def create_correct_global_agents():
    """Create the 5 correct global agents (but DO NOT assign to anyone)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n🚀 Creating Correct Global Agents...")
    print("=" * 80)

    for agent in CORRECT_GLOBAL_AGENTS:
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

    conn.commit()
    conn.close()

def verify_setup():
    """Verify the setup is correct"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n📊 Verification:")
    print("=" * 80)

    # Count global agents
    cursor.execute("SELECT COUNT(*) FROM global_agents WHERE is_active = 1")
    agent_count = cursor.fetchone()[0]
    print(f"✅ Total active global agents: {agent_count}")

    # Count assignments (should be 0)
    cursor.execute("SELECT COUNT(*) FROM user_global_agents")
    assignment_count = cursor.fetchone()[0]

    if assignment_count == 0:
        print(f"✅ Total user assignments: {assignment_count} (CORRECT - disabled by default)")
    else:
        print(f"❌ Total user assignments: {assignment_count} (WRONG - should be 0)")

    # List all agents
    cursor.execute("""
        SELECT id, name, emoji, description
        FROM global_agents
        WHERE is_active = 1
        ORDER BY id
    """)
    agents = cursor.fetchall()

    print("\n🤖 Global Agents Created:")
    print("-" * 80)
    for agent in agents:
        print(f"{agent[2]} {agent[1]}")
        print(f"   {agent[3]}")

    conn.close()

    print("\n" + "=" * 80)
    print("✅ Setup complete!")
    print("\n⚠️  IMPORTANT:")
    print("   - Global agents are DISABLED by default")
    print("   - No users have access yet")
    print("   - Only admin can manually assign them")
    print("   - Use the admin portal to assign agents to specific users/workspaces")

if __name__ == '__main__':
    print("🔧 Setting Up Correct Global Agents")
    print("=" * 80)
    print("\nThis will:")
    print("1. Delete all old global agents")
    print("2. Remove all user assignments")
    print("3. Create 5 correct global agents (disabled by default)")
    print("\n" + "=" * 80)

    response = input("\nProceed? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        exit(0)

    delete_old_global_agents()
    create_correct_global_agents()
    verify_setup()
