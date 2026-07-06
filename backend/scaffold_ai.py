import os

base_dir = r"d:\kanban-project\backend\app\ai"
dirs = [
    "",
    "gateway",
    "providers",
    "agents",
    "context",
    "tools",
    "prompts",
    "prompts/workspace_assistant",
    "memory",
    "workflows",
    "telemetry",
    "schemas",
    "services"
]

for d in dirs:
    path = os.path.join(base_dir, d)
    os.makedirs(path, exist_ok=True)
    init_file = os.path.join(path, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            pass

print("Created AI module directories and __init__.py files.")
