"""
Interactive Demo - Talk to the AI Team
Quick and easy way to interact with your AI agents
"""

import os
from ai_team import AITeam


def print_header():
    print("\n" + "="*70)
    print("🤖 AI TEAM - Interactive Demo")
    print("="*70)


def print_agents(team):
    print("\n👥 Your AI Team:")
    for agent in team.list_agents():
        print(f"  {agent['emoji']} {agent['name']:8} - {agent['role']}")


def setup_context(team):
    """Optional: Set up business/brand context"""
    print("\n📋 Would you like to set up context? (brand voice, audience, etc.)")
    setup = input("Setup context? (y/n): ").lower()
    
    if setup == 'y':
        print("\nEnter context (press Enter to skip):")
        
        brand = input("  Brand/Company Name: ")
        if brand:
            team.set_context("brand_name", brand, "User")
        
        voice = input("  Brand Voice (e.g., professional, friendly): ")
        if voice:
            team.set_context("brand_voice", voice, "User")
        
        audience = input("  Target Audience: ")
        if audience:
            team.set_context("target_audience", audience, "User")
        
        industry = input("  Industry: ")
        if industry:
            team.set_context("industry", industry, "User")
        
        print("\n✅ Context saved!")


def interactive_mode(team):
    """Main interactive loop"""
    print("\n" + "="*70)
    print("💬 Chat with your AI Team")
    print("="*70)
    print("\nOptions:")
    print("  • Just type your request (coordinator will route automatically)")
    print("  • Type 'luna:', 'mila:', etc. to request a specific agent")
    print("  • Type 'agents' to see the team")
    print("  • Type 'context' to view/set context")
    print("  • Type 'history' to see recent work")
    print("  • Type 'clear' to clear the database")
    print("  • Type 'quit' to exit")
    
    project_id = None
    
    while True:
        print("\n" + "-"*70)
        user_input = input("\n💭 You: ").strip()
        
        if not user_input:
            continue
        
        # Handle commands
        if user_input.lower() == 'quit':
            print("\n👋 Goodbye!")
            break
        
        elif user_input.lower() == 'agents':
            print_agents(team)
            continue
        
        elif user_input.lower() == 'context':
            context = team.shared_memory.get_all_context()
            if context:
                print("\n📋 Current Context:")
                for key, value in context.items():
                    print(f"  • {key}: {value}")
            else:
                print("\n📋 No context set yet")
            
            setup = input("\nAdd more context? (y/n): ").lower()
            if setup == 'y':
                setup_context(team)
            continue
        
        elif user_input.lower() == 'history':
            recent = team.get_recent_work(limit=5)
            if recent:
                print("\n📜 Recent Team Work:")
                for work in recent:
                    print(f"\n  {work['timestamp']}")
                    print(f"  {work['agent']}: {work['content'][:200]}...")
            else:
                print("\n📜 No work history yet")
            continue
        
        elif user_input.lower() == 'clear':
            confirm = input("⚠️  Clear all data? (yes/no): ")
            if confirm.lower() == 'yes':
                os.remove("team_memory.db")
                team = AITeam(api_key=os.environ.get("ANTHROPIC_API_KEY"))
                print("✅ Database cleared!")
            continue
        
        # Check for specific agent request (e.g., "luna: analyze this")
        specific_agent = None
        for agent_key in team.agents.keys():
            if user_input.lower().startswith(f"{agent_key}:"):
                specific_agent = agent_key
                user_input = user_input[len(agent_key)+1:].strip()
                break
        
        # Ask about project ID if not set
        if project_id is None:
            use_project = input("\n🗂️  Use a project ID to maintain context? (y/n): ").lower()
            if use_project == 'y':
                project_id = input("   Project ID: ").strip()
        
        # Process the request
        print("\n⏳ Processing...")
        
        try:
            results = team.process_request(
                user_input,
                project_id=project_id,
                specific_agent=specific_agent
            )
            
            # Display results
            for agent_name, response in results.items():
                agent = team.agents[agent_name]
                print(f"\n{agent.emoji} {agent.name}:")
                print(response)
        
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("   Try again or check your API key")


def quick_demo(team):
    """Run a quick demonstration"""
    print("\n" + "="*70)
    print("🚀 Quick Demo")
    print("="*70)
    
    # Set up sample context
    print("\n📋 Setting up sample context...")
    team.set_context("brand_name", "DemoCompany", "Demo")
    team.set_context("brand_voice", "Professional yet friendly", "Demo")
    team.set_context("target_audience", "Small business owners", "Demo")
    
    # Demo request 1
    print("\n📝 Demo Request 1: Social Media Post")
    print("   Request: 'Create a LinkedIn post about productivity tips'")
    result = team.process_request(
        "Create a LinkedIn post about 3 productivity tips for entrepreneurs",
        specific_agent="mila"
    )
    print(f"\n🐿 Mila's Response:")
    print(result['mila'])
    
    # Demo request 2
    print("\n\n📝 Demo Request 2: Strategy Question")
    print("   Request: 'What metrics should we track for growth?'")
    result = team.process_request(
        "What are the top 3 metrics a SaaS company should track for growth?",
        specific_agent="luna"
    )
    print(f"\n🌙 Luna's Response:")
    print(result['luna'])
    
    input("\n\n⏎ Press Enter to continue to interactive mode...")


def main():
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n⚠️  API Key Required")
        print("\nPlease set your Anthropic API key:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print("\nOr add it to a .env file:")
        print("  ANTHROPIC_API_KEY=your-key-here")
        return
    
    print_header()
    
    # Initialize team
    print("\n⏳ Initializing AI Team...")
    team = AITeam(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    print("✅ Team ready!")
    
    print_agents(team)
    
    # Choose mode
    print("\n" + "="*70)
    print("Choose Mode:")
    print("  1. Quick Demo (see examples)")
    print("  2. Interactive Mode (chat with team)")
    print("  3. Setup Context First")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        quick_demo(team)
        interactive_mode(team)
    elif choice == "2":
        interactive_mode(team)
    elif choice == "3":
        setup_context(team)
        interactive_mode(team)
    else:
        print("\nStarting interactive mode...")
        interactive_mode(team)


if __name__ == "__main__":
    main()
