"""
Agent Transfer and Collaboration System

This module adds features for:
1. Agent-to-agent mentions (@agentName)
2. In-chat agent switching
3. Multi-agent collaboration in one conversation
"""

def detect_agent_mentions(message, user_id):
    """
    Detect @mentions of other agents in the message
    Returns list of mentioned agents
    """
    import re
    from web_app_auth import get_db_connection

    # Core agents
    core_agents = ['Luna', 'Mila', 'Sage', 'Ember', 'Sol', 'Nova', 'Theo']

    # Get custom and global agents for this user
    conn = get_db_connection()
    cursor = conn.cursor()

    # Custom agents
    cursor.execute("SELECT name FROM custom_agents WHERE user_id = ?", (user_id,))
    custom_agents = [row[0] for row in cursor.fetchall()]

    # Global agents
    cursor.execute("""
        SELECT ga.name FROM global_agents ga
        INNER JOIN user_global_agents uga ON ga.id = uga.global_agent_id
        WHERE uga.user_id = ? AND ga.is_active = 1
    """, (user_id,))
    global_agents = [row[0] for row in cursor.fetchall()]

    conn.close()

    all_agents = core_agents + custom_agents + global_agents

    # Find @mentions in message
    mentioned = []
    pattern = r'@(\w+)'
    matches = re.findall(pattern, message)

    for match in matches:
        # Check if it matches any agent (case insensitive)
        for agent in all_agents:
            if agent.lower() == match.lower():
                mentioned.append(agent)
                break

    return mentioned

def suggest_agent_transfer(response_text, current_agent):
    """
    Detect if an agent is suggesting to transfer to another agent
    Returns suggested agent name or None
    """
    import re

    # All possible agents
    all_agents = ['Luna', 'Mila', 'Sage', 'Ember', 'Sol', 'Nova', 'Theo']

    # Remove current agent from suggestions
    other_agents = [a for a in all_agents if a != current_agent]

    # Patterns that indicate agent transfer
    transfer_patterns = [
        r'@(\w+) (would|could|can) (help|handle|be better)',
        r'(transfer|switch|hand off) (to|you to) @?(\w+)',
        r'let me (bring|get) @?(\w+)',
        r'@(\w+) (is|would be) (perfect|better suited|ideal)',
    ]

    for pattern in transfer_patterns:
        matches = re.findall(pattern, response_text, re.IGNORECASE)
        for match in matches:
            # Extract agent name from match groups
            for group in match:
                for agent in other_agents:
                    if agent.lower() in group.lower():
                        return agent

    return None

# This would be added to web_app_auth.py
