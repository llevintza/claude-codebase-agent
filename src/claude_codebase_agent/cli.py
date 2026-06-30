"""Interactive REPL — three menu options: ask, investigate, build."""
from __future__ import annotations
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _check_api_key() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "WARNING: ANTHROPIC_API_KEY is not set.\n"
            "Copy .env.example to .env and fill in your key.\n"
        )


def _prompt_target_dir() -> str:
    while True:
        raw = input("Target repo path (absolute or relative)> ").strip()
        if not raw:
            continue
        path = Path(raw).expanduser().resolve()
        if not path.is_dir():
            print(f"  Directory not found: {path}")
            continue
        if not (path / ".git").exists():
            print(
                f"  Warning: {path} does not appear to be a git repo.\n"
                "  Changes will not be easily revertible."
            )
        return str(path)


def _prompt_verify_cmd() -> str:
    raw = os.environ.get("VERIFY_CMD", "").strip()
    if raw:
        print(f"  Using VERIFY_CMD from environment: {raw}")
        return raw
    raw = input(
        "Verify command after implementing (e.g. 'mvn -q test', 'npm test') "
        "[leave blank to auto-detect]> "
    ).strip()
    return raw or ""


def _read_line(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


async def _menu_ask(target_dir: str) -> None:
    from claude_codebase_agent.explorer import discover
    question = _read_line("question> ")
    if not question:
        return
    await discover(question, cwd=target_dir)
    print()


async def _menu_investigate(target_dir: str) -> None:
    from claude_codebase_agent.explorer import adaptive_investigation
    goal = _read_line("investigation goal> ")
    if not goal:
        return
    result = await adaptive_investigation(goal, cwd=target_dir)
    print("\n── Structure Map ──────────────────────────")
    print(result["structure_map"])
    print("\n── High-Impact Areas ──────────────────────")
    print(result["high_impact_areas"])
    print("\n── Plan ───────────────────────────────────")
    print(result["plan"])
    print("\n── Report ─────────────────────────────────")
    print(result["report"])
    print()


async def _menu_build(target_dir: str) -> None:
    from claude_codebase_agent.builder import implement_feature
    requirement = _read_line("feature requirement (high-level)> ")
    if not requirement:
        return
    verify_cmd = _prompt_verify_cmd()
    await implement_feature(requirement, target_dir, verify_cmd=verify_cmd or None)


async def main() -> None:
    _check_api_key()
    print("claude-codebase-agent")
    print("Modes: explore an unfamiliar repo, or build a feature in it.\n")

    target_dir = _prompt_target_dir()
    print(f"\nTarget: {target_dir}\n")

    while True:
        print("Menu:")
        print("  1) Ask a question about the codebase")
        print("  2) Adaptive investigation (open-ended goal)")
        print("  3) Implement a feature (plan → confirm → write → verify)")
        print("  q) Quit")
        choice = _read_line("choice> ").lower()
        if not choice or choice in {"q", "quit", "exit"}:
            break
        if choice == "1":
            await _menu_ask(target_dir)
        elif choice == "2":
            await _menu_investigate(target_dir)
        elif choice == "3":
            await _menu_build(target_dir)
        else:
            print(f"Unknown choice: {choice!r}\n")
