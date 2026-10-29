import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.agent.commands import slash_command_registry
from backend.agent.loop import agent_loop
from backend.agent.tools import tool_manager
from backend.agent.permissions import permission_enforcer
from backend.agent.context import context_loader

# ANSI Colors
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

BANNER = f"""{MAGENTA}{BOLD}
 ██████╗██╗      █████╗ ██╗    ██╗    ██████╗ ██████╗ ██████╗ ███████╗
██╔════╝██║     ██╔══██╗██║    ██║   ██╔════╝██╔═══██╗██╔══██╗██╔════╝
██║     ██║     ███████║██║ █╗ ██║   ██║     ██║   ██║██║  ██║█████╗  
██║     ██║     ██╔══██║██║███╗██║   ██║     ██║   ██║██║  ██║██╔══╝  
╚██████╗███████╗██║  ██║╚███╔███╔╝   ╚██████╗╚██████╔╝██████╔╝███████╗
{CYAN}    🦞 Powered by SYNORA AI · Multi-Model Autonomous Coding Harness{RESET}
"""

async def run_repl(workspace_root: str):
    print(BANNER)
    ws_path = Path(workspace_root).resolve()
    tool_manager.set_workspace_root(str(ws_path))
    context_loader.set_workspace_root(str(ws_path))
    slash_command_registry.set_workspace_root(str(ws_path))

    # Preflight quick status
    git_res = await tool_manager.execute_git_status()
    mem_files = context_loader.discover_memory_files()

    print(f"{DIM}📁 Workspace:{RESET} {BOLD}{ws_path}{RESET}")
    print(f"{DIM}🌿 Git:{RESET}       {GREEN}{git_res.output.splitlines()[0] if git_res.output else 'Clean'}{RESET}")
    print(f"{DIM}🛡️ Security:{RESET}  {YELLOW}{permission_enforcer.mode}{RESET}")
    if mem_files:
        print(f"{DIM}🧠 Memory:{RESET}    {CYAN}{', '.join(f['file_name'] for f in mem_files)}{RESET}")
    print(f"{DIM}Type {BOLD}/help{RESET}{DIM} for slash commands or enter any coding task. Type {BOLD}/exit{RESET}{DIM} to quit.{RESET}\n")

    while True:
        try:
            prompt = input(f"{MAGENTA}{BOLD}claw{RESET} ({YELLOW}{permission_enforcer.mode}{RESET}) > ").strip()
            if not prompt:
                continue

            if prompt.lower() in ("/exit", "/quit", "exit", "quit"):
                print(f"{CYAN}Goodbye! 👋{RESET}")
                break

            # Handle slash commands
            if prompt.startswith("/"):
                res = await slash_command_registry.execute(prompt)
                if res.success:
                    print(f"{GREEN}{res.output}{RESET}\n")
                else:
                    print(f"{RED}{res.output}{RESET}\n")
                continue

            # Execute autonomous task
            print(f"{CYAN}⚡ Running Claw Agent Harness on '{prompt}'...{RESET}")
            async for raw_chunk in agent_loop.stream(task=prompt, workspace_root=str(ws_path)):
                line = raw_chunk.strip()
                if not line.startswith("data: "):
                    continue
                import json
                try:
                    event = json.loads(line[6:])
                    ev_type = event.get("event")
                    if ev_type == "thought":
                        print(f"\n{DIM}> 💭 {event.get('content')}{RESET}")
                    elif ev_type == "tool_start":
                        args_str = json.dumps(event.get('arguments', {}))
                        if len(args_str) > 100:
                            args_str = args_str[:97] + "..."
                        print(f"  {YELLOW}🛠️  Tool Call:{RESET} {BOLD}{event.get('tool')}{RESET} {DIM}{args_str}{RESET}")
                    elif ev_type == "tool_result":
                        dur = round(event.get('duration_ms', 0), 1)
                        if event.get('success'):
                            out = event.get('output', '')
                            preview = (out[:250] + "...") if len(out) > 250 else out
                            print(f"  {GREEN}✓ [{event.get('tool')} {dur}ms]{RESET} {DIM}{preview.strip()}{RESET}")
                        else:
                            print(f"  {RED}✗ [{event.get('tool')} {dur}ms]{RESET} {RED}{event.get('output')}{RESET}")
                    elif ev_type == "complete":
                        print(f"\n{BOLD}{GREEN}🎯 Complete ({round(event.get('total_time_ms', 0), 1)}ms):{RESET}")
                        print(event.get('final_response', ''))
                        print()
                except Exception:
                    pass

        except (KeyboardInterrupt, EOFError):
            print(f"\n{CYAN}Session terminated. 👋{RESET}")
            break

def main():
    parser = argparse.ArgumentParser(
        description="Claw Code CLI — Autonomous Coding Agent powered by SYNORA AI Multi-Model Platform"
    )
    parser.add_argument("command_or_task", nargs="*", help="Slash command (/doctor, /status, /diff, etc.) or prompt task to execute")
    parser.add_argument("--workspace", "-w", default=".", help="Workspace path to operate on (default: current directory)")
    parser.add_argument("--mode", "-m", choices=["autonomous", "ask", "read_only"], default=None, help="Security gate permission mode")
    parser.add_argument("--doctor", action="store_true", help="Run preflight doctor diagnostic check")
    parser.add_argument("--status", action="store_true", help="Inspect workspace and git status")
    parser.add_argument("--diff", action="store_true", help="View git diff of workspace modifications")

    args = parser.parse_args()

    if args.mode:
        permission_enforcer.set_mode(args.mode)

    ws_path = str(Path(args.workspace).resolve())

    # Preflight flags
    if args.doctor:
        asyncio.run(execute_single_slash("/doctor", ws_path))
        return
    if args.status:
        asyncio.run(execute_single_slash("/status", ws_path))
        return
    if args.diff:
        asyncio.run(execute_single_slash("/diff", ws_path))
        return

    if args.command_or_task:
        query = " ".join(args.command_or_task)
        if query in ("doctor", "status", "diff", "review", "help", "init", "tools", "compact", "cost"):
            asyncio.run(execute_single_slash("/" + query, ws_path))
        elif query.startswith("/"):
            asyncio.run(execute_single_slash(query, ws_path))
        else:
            asyncio.run(execute_single_task(query, ws_path))
    else:
        asyncio.run(run_repl(ws_path))

async def execute_single_slash(cmd: str, ws: str):
    slash_command_registry.set_workspace_root(ws)
    tool_manager.set_workspace_root(ws)
    res = await slash_command_registry.execute(cmd)
    if res.success:
        print(f"{GREEN}{res.output}{RESET}")
    else:
        print(f"{RED}{res.output}{RESET}")

async def execute_single_task(task: str, ws: str):
    res = await agent_loop.run(task=task, workspace_root=ws)
    print(f"{BOLD}{GREEN}🎯 Claw Agent Output:{RESET}\n")
    print(res.final_response)

if __name__ == "__main__":
    main()
