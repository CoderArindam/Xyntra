# KAIO AI Agentic Assistant Subsystem

This module implements the **agentic AI assistant** for KAIO. It enables natural language interaction with Kanban workspaces, allowing users to query, update, create, and manage boards, lists, tasks, and users.

---

## Architectural Flow & Setup

The AI subsystem follows an orchestrator-agent pattern with structured planning and tool execution:

```
User Query
    │
    ▼
Chat Service (SSE Stream)
    │
    ▼
Composer (Context & State Compiler)
    │
    ▼
Intent Router (Clarify vs. Plan vs. Chat)
    ├── Chat / Fast Actions (Direct execution)
    └── Plan (Orchestration Loop)
          │
          ├── 1. Planner (Generates tool plan)
          ├── 2. Validator (Checks plan safety/integrity)
          ├── 3. Executor ◄──► Tools (Execute workspace actions)
          └── 4. State Machine (Track and execute step updates)
```

### Subsystem Configuration
The AI subsystem relies on `pydantic-settings` to isolate its configuration bounds ([settings.py](file:///d:/kanban-project/backend/app/ai/config/settings.py)).
* **LLM Providers**: Capable of dynamically routing to multiple providers: OpenAI, Anthropic, Gemini, Azure OpenAI, and Puter via configurable environment variables.
* **Constraints**: Hard limits are enforced at the module layer (max tokens, generation temperature, execution timeout defaults of 60 seconds, and retry constraints).

---

## Directory & Component Breakdown

### 1. Orchestration Layer (`app/ai/orchestration/`)
Manages the loop of planning, validation, execution, and user feedback.
* **[intent_router.py](file:///d:/kanban-project/backend/app/ai/orchestration/intent_router.py)**: Classifies user messages to decide if they need direct execution (Fast Actions), general conversation, or a multi-step execution plan.
* **[planner.py](file:///d:/kanban-project/backend/app/ai/orchestration/planner.py)**: Compiles active workspace details and prompts the LLM to generate a sequence of step-by-step tool invocations.
* **[executor.py](file:///d:/kanban-project/backend/app/ai/orchestration/executor.py)**: Executes each step in the plan sequentially. Safely handles tool execution, handles error states, and aggregates execution results.
* **[composer.py](file:///d:/kanban-project/backend/app/ai/orchestration/composer.py)**: Assembles the LLM system prompts, combining user settings, global rules, chat histories, active screen contexts, and available tool descriptions.
* **[validator.py](file:///d:/kanban-project/backend/app/ai/orchestration/validator.py)**: Audits plan steps to ensure they respect access control, security limits, and valid input formats.
* **[clarification_router.py](file:///d:/kanban-project/backend/app/ai/orchestration/clarification_router.py)**: Prompts the user with interactive questions if parameters are ambiguous or missing.
* **[state_machine.py](file:///d:/kanban-project/backend/app/ai/orchestration/state_machine.py)**: Tracks execution stages (Planning, Executing, WaitingForFeedback, Completed, Failed).

### 2. Agents (`app/ai/agents/`)
* **[workspace_assistant.py](file:///d:/kanban-project/backend/app/ai/agents/workspace_assistant.py)**: The main assistant agent class that combines system prompts, orchestrators, and tool registrations to resolve task/board management requests.

### 3. Tool Capabilities (`app/ai/tools/`)
Functions exposed to the AI model that map natural language operations to database changes or UI controls.
* **[domain_tools.py](file:///d:/kanban-project/backend/app/ai/tools/domain_tools.py)**: Core actions like `create_task`, `move_task`, `update_task_details`, `assign_user`, or `invite_member`.
* **[workspace_tools.py](file:///d:/kanban-project/backend/app/ai/tools/workspace_tools.py)**: Read operations such as searching tasks, querying boards, lists, and auditing board logs.
* **[appearance_tools.py](file:///d:/kanban-project/backend/app/ai/tools/appearance_tools.py)**: Enables the agent to request UI updates, like switching theme, opening specific cards, or changing display settings.
* **[fuzzy.py](file:///d:/kanban-project/backend/app/ai/tools/fuzzy.py)**: Utility to match search terms with actual database records (e.g. board titles, user names) using soft text matching.

### 4. Providers & Gateway (`app/ai/providers/`, `app/ai/gateway/`)
Handles the interface to external large language model APIs.
* **[ai_gateway.py](file:///d:/kanban-project/backend/app/ai/gateway/ai_gateway.py)**: Standardizes requests to LLM APIs (e.g., Gemini or Vertex AI). It encapsulates retry-backoff algorithms, rate limiting bounds, network timeouts, and token budgeting mechanics.

### 5. Services (`app/ai/services/`)
* **[chat_service.py](file:///d:/kanban-project/backend/app/ai/services/chat_service.py)**: Manages ongoing chat sessions, histories, and database logs for conversations. It is responsible for streaming responses to the frontend utilizing Server-Sent Events (SSE) payloads.

### 6. Dynamic Prompts (`app/ai/prompts/`)
* Contains versioned Markdown files that define agent guidelines, router instructions, planning schemas, and system templates. These are resolved dynamically at runtime by a centralized registry.
