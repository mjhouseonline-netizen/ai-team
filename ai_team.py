"""
AI Team System - A collaborative AI agent framework with shared memory
Featuring: Luna, Mila, Sage, Ember, Sol, Nova, and Theo
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from anthropic import Anthropic


class SharedMemory:
    """Central memory system that all agents can read from and write to"""
    
    def __init__(self, db_path: str = "team_memory.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the shared memory database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                assigned_to TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                result TEXT
            )
        """)
        
        # Agent outputs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                task_id INTEGER,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id)
            )
        """)
        
        # Context/notes table - shared knowledge base
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                created_by TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Conversations table - for context continuity
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT,
                agent_name TEXT,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_task(self, description: str, assigned_to: Optional[str] = None) -> int:
        """Add a new task to the shared memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (description, assigned_to) VALUES (?, ?)",
            (description, assigned_to)
        )
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id
    
    def update_task(self, task_id: int, status: str, result: Optional[str] = None):
        """Update task status and result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if result:
            cursor.execute(
                "UPDATE tasks SET status = ?, result = ?, completed_at = ? WHERE id = ?",
                (status, result, datetime.now(), task_id)
            )
        else:
            cursor.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (status, task_id)
            )
        conn.commit()
        conn.close()
    
    def add_output(self, agent_name: str, content: str, task_id: Optional[int] = None, 
                   metadata: Optional[Dict] = None):
        """Store agent output in shared memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agent_outputs (agent_name, task_id, content, metadata) VALUES (?, ?, ?, ?)",
            (agent_name, task_id, content, json.dumps(metadata) if metadata else None)
        )
        conn.commit()
        conn.close()
    
    def set_context(self, key: str, value: str, created_by: str):
        """Store or update context information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO context (key, value, created_by, updated_at) VALUES (?, ?, ?, ?)",
            (key, value, created_by, datetime.now())
        )
        conn.commit()
        conn.close()
    
    def get_context(self, key: str) -> Optional[str]:
        """Retrieve context information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM context WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def get_all_context(self) -> Dict[str, str]:
        """Get all context as a dictionary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM context")
        results = cursor.fetchall()
        conn.close()
        return {key: value for key, value in results}
    
    def add_conversation(self, message: str, agent_name: str, project_id: Optional[str] = None):
        """Add a conversation message for context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (project_id, agent_name, message) VALUES (?, ?, ?)",
            (project_id, agent_name, message)
        )
        conn.commit()
        conn.close()
    
    def get_recent_conversations(self, limit: int = 10, project_id: Optional[str] = None) -> List[Dict]:
        """Get recent conversation history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if project_id:
            cursor.execute(
                "SELECT agent_name, message, created_at FROM conversations WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                (project_id, limit)
            )
        else:
            cursor.execute(
                "SELECT agent_name, message, created_at FROM conversations ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        results = cursor.fetchall()
        conn.close()
        return [{"agent": r[0], "message": r[1], "timestamp": r[2]} for r in reversed(results)]
    
    def get_agent_outputs(self, agent_name: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """Get recent outputs from a specific agent or all agents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if agent_name:
            cursor.execute(
                "SELECT agent_name, content, created_at FROM agent_outputs WHERE agent_name = ? ORDER BY created_at DESC LIMIT ?",
                (agent_name, limit)
            )
        else:
            cursor.execute(
                "SELECT agent_name, content, created_at FROM agent_outputs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        results = cursor.fetchall()
        conn.close()
        return [{"agent": r[0], "content": r[1], "timestamp": r[2]} for r in results]


class Agent:
    """Base agent class with shared memory access"""
    
    def __init__(self, name: str, emoji: str, role: str, personality: str, 
                 shared_memory: SharedMemory, api_key: str):
        self.name = name
        self.emoji = emoji
        self.role = role
        self.personality = personality
        self.shared_memory = shared_memory
        self.client = Anthropic(api_key=api_key)
    
    def get_system_prompt(self) -> str:
        """Generate the system prompt for this agent"""
        context = self.shared_memory.get_all_context()
        recent_outputs = self.shared_memory.get_agent_outputs(limit=3)
        
        context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()]) if context else "None yet"
        recent_work = "\n".join([f"- {o['agent']}: {o['content'][:100]}..." for o in recent_outputs]) if recent_outputs else "None yet"
        
        return f"""You are {self.emoji} {self.name}, an AI agent specialized in {self.role}.

Your personality: {self.personality}

You work as part of a collaborative AI team with shared memory. Your teammates are:
- 🌙 Luna (Strategy & Analytics)
- 🐿 Mila (Social Media & Trends)
- 🐇 Sage (Editor & Quality Control)
- 🦊 Ember (Creative Content)
- 🐻 Sol (Project Management)
- 🦉 Nova (Research & Insights)
- 🦫 Theo (Technical & Automation)

SHARED CONTEXT:
{context_str}

RECENT TEAM ACTIVITY:
{recent_work}

When responding:
1. Stay in character with your personality
2. Focus on your area of expertise
3. Reference shared context when relevant
4. Be collaborative - acknowledge when another agent's skills would be helpful
5. Be concise but thorough
6. Add relevant information to shared memory when appropriate

Your goal is to excel at your specialty while contributing to the team's collective success."""
    
    def process(self, request: str, project_id: Optional[str] = None) -> str:
        """Process a request using Claude API"""
        system_prompt = self.get_system_prompt()
        
        # Get conversation history for context
        recent_convos = self.shared_memory.get_recent_conversations(limit=5, project_id=project_id)
        
        messages = []
        for convo in recent_convos:
            messages.append({
                "role": "user" if convo["agent"] == "User" else "assistant",
                "content": f"[{convo['agent']}]: {convo['message']}"
            })
        
        messages.append({
            "role": "user",
            "content": request
        })
        
        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            system=system_prompt,
            messages=messages
        )
        
        result = response.content[0].text
        
        # Store in shared memory
        self.shared_memory.add_output(self.name, result, metadata={"project_id": project_id})
        self.shared_memory.add_conversation(request, "User", project_id)
        self.shared_memory.add_conversation(result, self.name, project_id)
        
        return result


class AITeam:
    """Coordinator for the AI team"""
    
    def __init__(self, api_key: str, db_path: str = "team_memory.db"):
        self.shared_memory = SharedMemory(db_path)
        self.api_key = api_key
        self.agents = self._initialize_agents()
        self.coordinator = self._create_coordinator()
    
    def _initialize_agents(self) -> Dict[str, Agent]:
        """Initialize all 7 specialized agents"""
        agents = {}
        
        agents['luna'] = Agent(
            name="Luna",
            emoji="🌙",
            role="Strategy, analytics, long-term planning, research",
            personality="Thoughtful, strategic, data-driven. Luna sees the big picture and thinks several steps ahead. She's calm and analytical, helping teams understand the 'why' behind decisions.",
            shared_memory=self.shared_memory,
            api_key=self.api_key
        )
        
        agents['mila'] = Agent(
            name="Mila",
            emoji="🐿",
            role="Social media, quick content, data collection, trend monitoring",
            personality="Energetic, quick, always plugged into what's happening now. Mila moves fast, spots trends early, and creates snappy content that resonates. She's the team's pulse on the digital world.",
            shared_memory=self.shared_memory,
            api_key=self.api_key
        )
        
        agents['sage'] = Agent(
            name="Sage",
            emoji="🐇",
            role="Editor, quality control, brand voice guardian, advisor",
            personality="Wise, discerning, detail-oriented. Sage ensures everything meets the highest standards. She's diplomatic but firm about quality, helping the team maintain consistency and excellence.",
            shared_memory=self.shared_memory,
            api_key=self.api_key
        )
        
        agents['ember'] = Agent(
            name="Ember",
            emoji="🦊",
            role="Creative content, copywriter, idea generator, campaigns",
            personality="Creative, clever, full of spark. Ember brings ideas to life with creativity and flair. She's imaginative and playful, finding unique angles and crafting compelling narratives.",
            shared_memory=self.shared_memory,
            api_key=self.api_key
        )
        
        agents['sol'] = Agent(
            name="Sol",
            emoji="🐻",
            role="Project manager, coordinator, operations, customer service",
            personality="Reliable, warm, organized. Sol keeps everything running smoothly. He's the steady presence who ensures tasks get done, deadlines are met, and everyone feels supported.",
            shared_memory=self.shared_memory,
            api_key=self.api_key
        )
        
        agents['nova'] = Agent(
            name="Nova",
            emoji="🦉",
            role="Researcher, analyst, insights, competitive intelligence",
            personality="Intelligent, curious, observant. Nova digs deep to uncover insights others miss. She's thorough in research and brilliant at connecting dots to reveal patterns and opportunities.",
            shared_memory=self.shared_memory,
            api_key=self.api_key
        )
        
        agents['theo'] = Agent(
            name="Theo",
            emoji="🦫",
            role="Technical tasks, automation, process builder, data organizer",
            personality="Systematic, hardworking, builder mindset. Theo turns chaos into order. He creates processes, builds systems, and automates workflows so the team can work more efficiently.",
            shared_memory=self.shared_memory,
            api_key=self.api_key
        )
        
        return agents
    
    def _create_coordinator(self) -> Agent:
        """Create a coordinator agent to route tasks"""
        return Agent(
            name="Coordinator",
            emoji="🎯",
            role="Task routing and team coordination",
            personality="Strategic coordinator who understands each team member's strengths and routes work efficiently.",
            shared_memory=self.shared_memory,
            api_key=self.api_key
        )
    
    def route_task(self, request: str) -> str:
        """Determine which agent(s) should handle the request"""
        routing_prompt = f"""Given this request, which agent(s) should handle it?

Request: {request}

Available agents:
- 🌙 Luna: Strategy, analytics, long-term planning, research
- 🐿 Mila: Social media, quick content, data collection, trend monitoring
- 🐇 Sage: Editor, quality control, brand voice guardian, advisor
- 🦊 Ember: Creative content, copywriter, idea generator, campaigns
- 🐻 Sol: Project manager, coordinator, operations, customer service
- 🦉 Nova: Researcher, analyst, insights, competitive intelligence
- 🦫 Theo: Technical tasks, automation, process builder, data organizer

Respond with ONLY the agent name(s) in lowercase, comma-separated if multiple needed. 
Examples: "ember" or "nova,luna" or "mila,sage"
"""
        
        messages = [{
            "role": "user",
            "content": routing_prompt
        }]
        
        response = self.coordinator.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=100,
            messages=messages
        )
        
        return response.content[0].text.strip().lower()
    
    def process_request(self, request: str, project_id: Optional[str] = None, 
                       specific_agent: Optional[str] = None) -> Dict[str, Any]:
        """Process a request through the appropriate agent(s)"""
        if specific_agent:
            agent_names = [specific_agent.lower()]
        else:
            routing = self.route_task(request)
            agent_names = [name.strip() for name in routing.split(',')]
        
        results = {}
        for agent_name in agent_names:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                print(f"\n{agent.emoji} {agent.name} is working on this...")
                result = agent.process(request, project_id)
                results[agent_name] = result
            else:
                results[agent_name] = f"Agent '{agent_name}' not found"
        
        return results
    
    def set_context(self, key: str, value: str, agent_name: str = "User"):
        """Add information to shared context"""
        self.shared_memory.set_context(key, value, agent_name)
    
    def get_context(self, key: str) -> Optional[str]:
        """Retrieve information from shared context"""
        return self.shared_memory.get_context(key)
    
    def list_agents(self) -> List[Dict[str, str]]:
        """List all available agents"""
        return [
            {
                "name": agent.name,
                "emoji": agent.emoji,
                "role": agent.role,
                "key": key
            }
            for key, agent in self.agents.items()
        ]
    
    def get_recent_work(self, limit: int = 10) -> List[Dict]:
        """Get recent work from all agents"""
        return self.shared_memory.get_agent_outputs(limit=limit)


# Example usage
if __name__ == "__main__":
    # Initialize team (you'll need to set your API key)
    API_KEY = os.environ.get("ANTHROPIC_API_KEY", "your-api-key-here")
    team = AITeam(api_key=API_KEY)
    
    print("🎯 AI Team initialized!")
    print("\nTeam members:")
    for agent_info in team.list_agents():
        print(f"  {agent_info['emoji']} {agent_info['name']}: {agent_info['role']}")
    
    # Set some context
    team.set_context("brand_voice", "Professional yet friendly, innovative, customer-focused")
    team.set_context("target_audience", "Small business owners and content creators")
    
    # Example requests
    print("\n" + "="*60)
    print("Example 1: Automatic routing")
    print("="*60)
    
    result = team.process_request(
        "Create a social media post about our new AI team feature",
        project_id="demo_project"
    )
    
    for agent_name, response in result.items():
        print(f"\n{agent_name.upper()}:")
        print(response)
    
    print("\n" + "="*60)
    print("Example 2: Specific agent")
    print("="*60)
    
    result = team.process_request(
        "What are the top 3 AI trends for businesses in 2025?",
        specific_agent="luna"
    )
    
    for agent_name, response in result.items():
        print(f"\n{agent_name.upper()}:")
        print(response)
