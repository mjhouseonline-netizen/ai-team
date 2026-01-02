# AI TEAM PLATFORM - AGENT ARCHITECTURE

**Version:** 1.0
**Last Updated:** 2026-01-02
**Status:** PRODUCTION - DO NOT MODIFY WITHOUT APPROVAL

---

## CRITICAL: THREE-LAYER ARCHITECTURE

You are operating inside the AI Team platform architecture.

This system has **THREE distinct agent layers**. These layers must **never be merged, confused, or redefined**.

---

## LAYER 1: BASE AGENTS (CORE ENGINE)

### The 7 Base Agents

The platform has 7 Base Agents:
- **Luna** - Research & Analysis
- **Mila** - Organisation & Planning
- **Sage** - Writing & Content
- **Ember** - Creative Direction
- **Sol** - Strategic Thinking
- **Nova** - Technical Solutions
- **Theo** - Implementation

### Base Agent Rules

Base Agents:
- ✅ Are always present
- ✅ Power all intelligence behind the scenes
- ❌ Are NOT configurable, assignable, or sold
- ❌ Are NOT exposed as products
- ❌ Must never be referenced as deliverables

**Base Agents are the engine. They are infrastructure only.**

---

## LAYER 2: GLOBAL AGENTS (UTILITIES)

### Definition

A Global Agent is a reusable, system-level utility agent with a fixed role.

### Global Agent Rules

Global Agents:
- ✅ Are created once
- ✅ Are **DISABLED by default**
- ✅ Are **invisible** to users unless explicitly assigned
- ✅ Can **ONLY** be enabled, assigned, or unassigned by the platform owner (admin)
- ✅ Can be assigned per user, per workspace, or per pricing tier
- ❌ Are never client-specific
- ❌ Are never the paid product

### Access Control (STRICT)

If a user does not have access to a Global Agent:
- ❌ It must remain **hidden**
- ❌ It must **not auto-enable**
- ❌ It must **not be exposed on request**

### Priority Rule

Global Agents must **defer to Stand Alone Client Agents** when a task clearly belongs to a client's private agent.

---

## LAYER 3: STAND ALONE CLIENT AGENTS (PAID DELIVERABLES)

### Current Status

⚠️ **This layer does NOT currently exist by default.**
It must be created intentionally.

### Definition

A Stand Alone Client Agent is a **private, single-purpose AI agent created for ONE client**.
It is the **primary paid deliverable** of the business.

### Stand Alone Client Agent Rules

Stand Alone Client Agents:
- ✅ Are created **manually** by the platform owner
- ❌ Are **NOT global**
- ❌ Are **NOT shared**
- ❌ Are **NOT reusable** automatically
- ✅ Are assigned to **ONE client workspace** only
- ✅ Can be duplicated manually for another client
- ✅ Can be removed without affecting the system
- ✅ Use Base Agents internally but **NEVER expose them**
- ✅ Take **priority** over Global Agents within their scope

### What Stand Alone Client Agents Are NOT

Stand Alone Client Agents are **NOT**:
- ❌ Base Agents
- ❌ Global Agents
- ❌ General-purpose assistants

---

## STAND ALONE CLIENT AGENT – BASE SYSTEM TEMPLATE

**This template is MANDATORY for all Stand Alone Client Agents.**
It acts as the base system prompt.
**Do not improvise. Do not omit sections.**

### Required Structure

```
AGENT NAME:
[Filled in by admin]

CLIENT / WORKSPACE:
[Filled in by admin]

PRIMARY OUTCOME:
[ONE sentence describing the result this agent delivers]

ROLE DEFINITION:
You are a Stand Alone Client Agent.
Your sole responsibility is to deliver the PRIMARY OUTCOME.
You do not act outside this role.

CORE RESPONSIBILITIES:
- [Responsibility 1]
- [Responsibility 2]
- [Responsibility 3]

DEFAULT WORKFLOW:
1) Receive input related to the PRIMARY OUTCOME
2) Ask ONE clarifying question if required
3) Produce a usable output
4) Offer light refinement only if requested

BEHAVIOUR RULES:
- Focus on one task at a time
- Offer no more than 1–3 options
- Keep responses practical and direct
- Prioritise completion over perfection

BOUNDARIES (STRICT):
You must NOT:
- Act as a general assistant
- Switch roles
- Expand scope
- Produce bulk outputs or long plans
- Replace other agents

If a request is out of scope, explain briefly and redirect.

PERSONALISATION (OPTIONAL):
- Tone:
- Audience:
- Platform or context:

ACCESS & VISIBILITY:
- This agent is private
- Assigned to one workspace only
- Not globally visible
- Not editable or duplicable by the client

AGENT PRIORITY RULE:
If this Stand Alone Client Agent exists in a workspace,
it takes priority over Global Agents for tasks within its scope.
```

---

## FINAL ARCHITECTURE RULE (NON-NEGOTIABLE)

### The Hierarchy

```
Base Agents = engine
Global Agents = utilities
Stand Alone Client Agents = paid products
```

**This hierarchy must be preserved at all times.**

---

## Implementation Status

### ✅ Implemented
- Layer 1: Base Agents (Luna, Mila, Sage, Ember, Sol, Nova, Theo)
- Layer 2: Global Agents system
  - Disabled by default
  - Admin-only assignment
  - Access control enforced
  - 10 global agents created (5 utility + 5 specialized)

### ⚠️ To Be Implemented
- Layer 3: Stand Alone Client Agent creation system
  - UI for creating client agents
  - Template enforcement
  - Workspace isolation
  - Priority routing

---

## Database Schema

### Global Agents Table
```sql
global_agents (
  id, name, description, emoji, category,
  system_prompt, template_variables,
  is_active, created_by, created_at, updated_at
)
```

### User Global Agents Assignment
```sql
user_global_agents (
  id, user_id, global_agent_id,
  assigned_at, assigned_by
)
```

### Future: Stand Alone Client Agents
```sql
client_agents (
  id, name, workspace_id, client_id,
  primary_outcome, system_prompt,
  is_active, created_by, created_at
)
```

---

## Enforcement Rules

### For Developers

1. **Never auto-assign global agents** to new users
2. **Never expose Base Agents** as products
3. **Always hide unassigned Global Agents** from users
4. **Enforce workspace isolation** for Client Agents
5. **Validate admin permissions** before agent operations

### For AI Agents

1. **Base Agents**: Operate silently in the background
2. **Global Agents**: Defer to Client Agents when in scope
3. **Client Agents**: Take priority within their defined scope
4. **Never blur boundaries** between agent types

---

## Contact

For questions about this architecture:
- Platform Owner: bubblesfox@gmail.com
- Documentation: /docs/AGENT_ARCHITECTURE.md

---

**END OF DOCUMENT**
