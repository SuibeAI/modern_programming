#!/usr/bin/env python3
"""03_agent.py - 在 02_agent.py 基础上增加 Skill 加载。

本节只新增一件事：Skill。

- 启动时扫描 books/06_Agent/skills/*/SKILL.md；
- 把 skill 名称和简短说明放入 SYSTEM prompt；
- 当模型需要完整说明时，调用 load_skill(name) 读取完整内容。

除此之外，Agent 循环、bash 工具和 history 保存逻辑都保持和 02_agent.py 基本一致。
"""

import json
import os
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
HISTORY_PATH = ROOT / "03_history.json"

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


def build_system() -> str:
    return (
        f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. "
        "Act, don't explain.\n\n"
        "Skills available:\n"
        f"{list_skills()}\n\n"
        "Use load_skill(name) to load full skill instructions when a task matches a skill."
    )


SYSTEM = build_system()

TOOLS = [
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


def run_tool(block) -> str:
    if block.name == "bash":
        print(f"\033[33m$ {block.input['command']}\033[0m")
        return run_bash(block.input["command"])
    if block.name == "load_skill":
        print(f"\033[33mload_skill({block.input['name']})\033[0m")
        return load_skill(block.input["name"])
    return f"Error: Unknown tool {block.name}"


def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_tool(block)
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
    print("s03: Skill Loading")
    print(f"Skills directory: {SKILLS_DIR}")
    print(f"Available skills:\n{list_skills()}\n")

    history = []
    try:
        while True:
            try:
                query = input("\033[36ms03 >> \033[0m")
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
