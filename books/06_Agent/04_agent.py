#!/usr/bin/env python3
"""04_agent.py - 在 03_agent.py 基础上增加 MCP 工具。

本节只新增一件事：MCP。

- 保留 03 的 bash、Skill、history 和 agent loop；
- 新增 connect_mcp(name) 工具，用来连接一个 mock MCP server；
- 连接后，把 MCP server 暴露的工具加入工具池；
- MCP 工具统一命名为 mcp__{server}__{tool}。

这里的 MCP server 是教学用 mock，不需要真正启动外部服务。
"""

import json
import os
import re
import subprocess
from pathlib import Path

try:
    import readline

    readline.parse_and_bind("set bind-tty-special-chars off")  # 避免终端特殊控制字符干扰输入。
    readline.parse_and_bind("set input-meta on")  # 允许读取非 ASCII 输入，例如中文。
    readline.parse_and_bind("set output-meta on")  # 允许终端正常显示非 ASCII 字符。
    readline.parse_and_bind("set convert-meta off")  # 不把高位字符转换成转义序列。
except (ImportError, ValueError):
    pass

from anthropic import Anthropic
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
SKILLS_DIR = ROOT / "skills"
HISTORY_PATH = ROOT / "04_history.json"

load_dotenv(ROOT / ".env", override=True)
load_dotenv(override=True)

if not os.getenv("ANTHROPIC_AUTH_TOKEN"):
    raise RuntimeError(".env 中设置 ANTHROPIC_AUTH_TOKEN")
if not os.getenv("MODEL_ID"):
    raise RuntimeError(".env 中设置 MODEL_ID")

client = Anthropic(
    auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN"),
    base_url=os.getenv("ANTHROPIC_BASE_URL"),
)
MODEL = os.environ["MODEL_ID"]


def parse_skill_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse a small YAML-like frontmatter block without adding dependencies."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, parts[2].strip()


def scan_skills() -> dict[str, dict[str, str]]:
    """Return skill registry: name -> description/content."""
    registry = {}
    if not SKILLS_DIR.exists():
        return registry
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        content = skill_file.read_text(encoding="utf-8")
        meta, body = parse_skill_frontmatter(content)
        name = meta.get("name", skill_dir.name)
        description = meta.get("description")
        if not description:
            description = body.splitlines()[0].lstrip("#").strip() if body else name
        registry[name] = {
            "name": name,
            "description": description,
            "content": content,
        }
    return registry


SKILL_REGISTRY = scan_skills()


def list_skills() -> str:
    if not SKILL_REGISTRY:
        return "(no skills found)"
    return "\n".join(
        f"- {skill['name']}: {skill['description']}"
        for skill in SKILL_REGISTRY.values()
    )


def load_skill(name: str) -> str:
    skill = SKILL_REGISTRY.get(name)
    if not skill:
        available = ", ".join(SKILL_REGISTRY) or "none"
        return f"Skill not found: {name}. Available skills: {available}"
    return skill["content"]


# ---- MCP system: only the new part compared with 03_agent.py ----

class MCPClient:
    """Teaching mock: discover and call tools from one MCP server."""

    def __init__(self, name: str):
        self.name = name
        self.tools: list[dict] = []
        self._handlers = {}

    def register(self, tool_defs: list[dict], handlers: dict) -> None:
        self.tools = tool_defs
        self._handlers = handlers

    def call_tool(self, tool_name: str, args: dict) -> str:
        handler = self._handlers.get(tool_name)
        if not handler:
            return f"MCP error: unknown tool '{tool_name}'"
        try:
            return handler(**args)
        except Exception as e:
            return f"MCP error: {e}"


mcp_clients: dict[str, MCPClient] = {}
_DISALLOWED_CHARS = re.compile(r"[^a-zA-Z0-9_-]")


def normalize_mcp_name(name: str) -> str:
    """Replace non [a-zA-Z0-9_-] characters with underscore."""
    return _DISALLOWED_CHARS.sub("_", name)


def _mock_server_docs() -> MCPClient:
    server = MCPClient("docs")
    server.register(
        tool_defs=[
            {
                "name": "search",
                "description": "Search documentation. (readOnly)",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
            {
                "name": "get_version",
                "description": "Get documentation API version. (readOnly)",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
        ],
        handlers={
            "search": lambda query: f"[docs] Found 3 results for '{query}'",
            "get_version": lambda: "[docs] API v2.1.0",
        },
    )
    return server


def _mock_server_deploy() -> MCPClient:
    server = MCPClient("deploy")
    server.register(
        tool_defs=[
            {
                "name": "status",
                "description": "Check deployment status. (readOnly)",
                "inputSchema": {
                    "type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"],
                },
            }
        ],
        handlers={
            "status": lambda service: f"[deploy] {service}: running",
        },
    )
    return server


MOCK_SERVERS = {
    "docs": _mock_server_docs,
    "deploy": _mock_server_deploy,
}


def connect_mcp(name: str) -> str:
    if name in mcp_clients:
        return f"MCP server '{name}' already connected"
    factory = MOCK_SERVERS.get(name)
    if not factory:
        available = ", ".join(MOCK_SERVERS)
        return f"Unknown MCP server '{name}'. Available: {available}"
    mcp_client = factory()
    mcp_clients[name] = mcp_client
    tool_names = [tool["name"] for tool in mcp_client.tools]
    print(f"\033[35m[mcp] connected: {name} -> {tool_names}\033[0m")
    return (
        f"Connected to MCP server '{name}'. "
        f"Discovered {len(tool_names)} tools: {', '.join(tool_names)}"
    )


def list_mcp_servers() -> str:
    if not mcp_clients:
        return "(no MCP servers connected)"
    lines = []
    for name, mcp_client in mcp_clients.items():
        tool_names = ", ".join(tool["name"] for tool in mcp_client.tools)
        lines.append(f"- {name}: {tool_names}")
    return "\n".join(lines)


def build_system() -> str:
    return (
        f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. "
        "Act, don't explain.\n\n"
        "Skills available:\n"
        f"{list_skills()}\n\n"
        "Use load_skill(name) to load full skill instructions when a task matches a skill.\n\n"
        "MCP:\n"
        "- Use connect_mcp(name) to connect a mock MCP server.\n"
        "- Available mock servers: docs, deploy.\n"
        "- After connection, MCP tools appear as mcp__{server}__{tool}.\n"
        "Connected MCP servers:\n"
        f"{list_mcp_servers()}"
    )


BUILTIN_TOOLS = [
    {
        "name": "bash",
        "description": "Run a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "load_skill",
        "description": "Load full instructions for a skill by name.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "connect_mcp",
        "description": "Connect to a mock MCP server (docs, deploy) and discover tools.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
]


def save_history(history: list) -> None:
    HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=os.getcwd(),
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"


def assemble_tool_pool() -> tuple[list[dict], dict]:
    """Return builtin tools plus tools discovered from connected MCP servers."""
    tools = list(BUILTIN_TOOLS)
    handlers = {
        "bash": run_bash,
        "load_skill": load_skill,
        "connect_mcp": connect_mcp,
    }
    for server_name, mcp_client in mcp_clients.items():
        safe_server = normalize_mcp_name(server_name)
        for tool_def in mcp_client.tools:
            safe_tool = normalize_mcp_name(tool_def["name"])
            prefixed_name = f"mcp__{safe_server}__{safe_tool}"
            tools.append(
                {
                    "name": prefixed_name,
                    "description": tool_def.get("description", ""),
                    "input_schema": tool_def.get("inputSchema", {}),
                }
            )
            handlers[prefixed_name] = (
                lambda c=mcp_client, t=tool_def["name"], **kw: c.call_tool(t, kw)
            )
    return tools, handlers


def run_tool(block, handlers: dict) -> str:
    print(f"\033[33m> {block.name} {block.input}\033[0m")
    handler = handlers.get(block.name)
    if not handler:
        return f"Error: Unknown tool {block.name}"
    return handler(**block.input)


def agent_loop(messages: list):
    while True:
        tools, handlers = assemble_tool_pool()
        response = client.messages.create(
            model=MODEL,
            system=build_system(),
            messages=messages,
            tools=tools,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_tool(block, handlers)
                print(str(output)[:200])
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    }
                )
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    print("s04: MCP Tools")
    print(f"Skills directory: {SKILLS_DIR}")
    print(f"Available skills:\n{list_skills()}\n")
    print("Mock MCP servers: docs, deploy\n")

    history = []
    try:
        while True:
            try:
                query = input("\033[36ms04 >> \033[0m")
            except (EOFError, KeyboardInterrupt):
                break
            if query.strip().lower() in ("q", "exit", ""):
                break
            history.append({"role": "user", "content": query})
            agent_loop(history)
            save_history(history)
            response_content = history[-1]["content"]
            if isinstance(response_content, list):
                for block in response_content:
                    if hasattr(block, "text"):
                        print(block.text)
            print()
    finally:
        save_history(history)
        print(f"History saved to {HISTORY_PATH}")
