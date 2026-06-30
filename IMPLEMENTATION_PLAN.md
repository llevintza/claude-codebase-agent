# Implementation Plan — claude-codebase-agent

> This document is the authoritative spec for implementing the project. Execute it top-to-bottom. Each section maps to one PR. Read CLAUDE.md first for environment setup and conventions.

---

## Step 0 — Prerequisites (do before any branching)

```bash
# 1. Create the GitHub repo (if not already done)
gh repo create llevintza/claude-codebase-agent --public \
  --description "A Claude Agent SDK tool that explores unfamiliar codebases and implements features from high-level requirements"

# 2. Add remote and push main
cd /Users/llevintza/wrk/claude-codebase-agent
git remote add origin git@github.com:llevintza/claude-codebase-agent.git
git push -u origin main

# 3. Set up the venv (direnv hook is already in ~/.zshrc — open a new shell or source it)
direnv allow
pip install -e ".[dev]"

# 4. Introspect ClaudeAgentOptions field names BEFORE writing any code
python3.12 -c "
import dataclasses, claude_agent_sdk as sdk
for f in dataclasses.fields(sdk.ClaudeAgentOptions):
    print(f.name, '=', repr(f.default))
"
# Save this output — use the actual field names in session.py
```

---

## PR 1 — feat/scaffold

**Branch:** `feat/scaffold` (from `main`)
**Commit:** `feat(scaffold): add project config and package skeleton`

### Files to create

**`.claude/settings.json`**
```json
{
  "permissions": {
    "allow": [
      "Bash(git status)",
      "Bash(git diff*)",
      "Bash(git log*)",
      "Bash(git add*)",
      "Bash(git commit*)",
      "Bash(git push*)",
      "Bash(git checkout*)",
      "Bash(git branch*)",
      "Bash(python*)",
      "Bash(pip*)",
      "Bash(pytest*)",
      "Bash(direnv*)",
      "Bash(gh*)"
    ],
    "deny": []
  }
}
```

**`src/claude_codebase_agent/__init__.py`** — empty file (just `# claude-codebase-agent`)

**`src/claude_codebase_agent/__main__.py`** — placeholder:
```python
from claude_codebase_agent.cli import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
```

**`tests/__init__.py`** — empty file

Also stage and commit the existing files already on disk:
- `.gitignore`, `.envrc`, `.env.example`, `.mcp.json.example`, `LICENSE`, `pyproject.toml`, `CLAUDE.md`, `IMPLEMENTATION_PLAN.md`
- Remove `.gitkeep` from main before branching (or just leave it — it's harmless)

### PR description
> Adds the complete project scaffold: package metadata (pyproject.toml with hatchling, console-script entry point, dev extras), direnv integration (.envrc with `layout python python3.12`), environment template (.env.example), MCP server template (.mcp.json.example), MIT license, project memory (CLAUDE.md), and the empty package skeleton under src/.

---

## PR 2 — feat/prompts

**Branch:** `feat/prompts` (from `feat/scaffold`)
**Commit:** `feat(prompts): add explorer and builder system prompts`

### File to create: `src/claude_codebase_agent/prompts.py`

**EXPLORER_PROMPT** — key rules to encode:
- ALWAYS start with Grep. Pick the most specific anchor from the user's question (function name, class, error string, import path) and Grep for it before reading anything.
- Use Glob only for file-path patterns (e.g., `**/*.java`, `**/config*.yml`), never for content search.
- Read sparingly — only files that Grep/Glob pointed you at. Follow imports to the next layer. Do not preemptively read siblings.
- Stop when you have enough to answer. Cite specific files and line ranges.
- If the question is ambiguous, ask a clarifying question rather than reading broadly.
- For the adaptive investigation flow: map structure → identify high-impact areas → build a numbered plan → execute adaptively (may add/skip subtasks based on findings).

**BUILDER_PROMPT** — key rules to encode:
- This is the IMPLEMENTATION phase. You have been given a concrete change plan that the user has already approved.
- Follow the target repo's existing conventions and style exactly — naming, indentation, file layout, test patterns.
- Make MINIMAL targeted changes. Do not refactor code unrelated to the requirement.
- After editing, run the verify command. If it fails, diagnose and fix before reporting done.
- Cite every file you changed in the final summary.
- NEVER edit files outside the target directory you were given.
- If the verify command is not provided, auto-detect: look for `pom.xml` → `mvn -q test`; `build.gradle` → `./gradlew test`; `package.json` → `npm test`; `go.mod` → `go test ./...`; `pytest.ini` / `pyproject.toml` with `[tool.pytest]` → `python -m pytest`.

---

## PR 3 — feat/session

**Branch:** `feat/session` (from `feat/prompts`)
**Commit:** `feat(session): add SDK wrapper with cwd and permission_mode support`

### File to create: `src/claude_codebase_agent/session.py`

```python
"""Single chokepoint for all Claude Agent SDK calls."""
from __future__ import annotations
import asyncio
from claude_agent_sdk import ClaudeAgentOptions, query, AssistantMessage, SystemMessage, ResultMessage

async def run_session(
    prompt: str,
    *,
    cwd: str | None = None,
    allowed_tools: list[str],
    system_prompt: str,
    permission_mode: str = "default",
    mcp_servers: dict | None = None,
    session_id: str | None = None,
) -> tuple[str, str | None]:
    """Run one agent turn, streaming output. Returns (final_text, session_id)."""
    # Build options — use ACTUAL field names from Step 0 introspection
    opts_kwargs = dict(
        system_prompt=system_prompt,
        allowed_tools=allowed_tools,
        mcp_servers=mcp_servers or {},
    )
    # Add optional fields only if the SDK supports them
    # (confirmed by the introspection in Step 0)
    if cwd is not None:
        opts_kwargs["cwd"] = cwd
    if permission_mode != "default":
        opts_kwargs["permission_mode"] = permission_mode
    if session_id is not None:
        opts_kwargs["resume"] = session_id

    options = ClaudeAgentOptions(**opts_kwargs)

    final_text = ""
    captured_session_id: str | None = None

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, SystemMessage):
            data = getattr(message, "data", {}) or {}
            sid = data.get("session_id") or getattr(message, "session_id", None)
            if sid:
                captured_session_id = sid
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                text = getattr(block, "text", None)
                if text:
                    print(text, end="", flush=True)
        elif isinstance(message, ResultMessage):
            final_text = (
                getattr(message, "result", None)
                or getattr(message, "text", "")
                or ""
            )

    if final_text:
        print()
    return final_text, captured_session_id
```

> **Important:** After the introspection in Step 0, if `cwd` or `permission_mode` are not valid `ClaudeAgentOptions` fields, remove those kwargs and add a comment explaining the fallback (e.g., `os.chdir(cwd)` before the call, or note that permission_mode isn't supported in this SDK version).

---

## PR 4 — feat/explorer

**Branch:** `feat/explorer` (from `feat/session`)
**Commit:** `feat(explorer): add read-only discover and adaptive_investigation`

### File to create: `src/claude_codebase_agent/explorer.py`

```python
"""Read-only codebase discovery — Grep-first, incremental."""
from __future__ import annotations
from claude_codebase_agent.prompts import EXPLORER_PROMPT
from claude_codebase_agent.session import run_session

EXPLORER_TOOLS = ["Grep", "Glob", "Read"]


async def discover(question: str, cwd: str) -> tuple[str, str | None]:
    """Single-shot question against a codebase. Returns (answer, session_id)."""
    return await run_session(
        question,
        cwd=cwd,
        allowed_tools=EXPLORER_TOOLS,
        system_prompt=EXPLORER_PROMPT,
    )


async def adaptive_investigation(goal: str, cwd: str) -> dict:
    """4-step open-ended codebase investigation.

    Step 1 — Map: summarize top-level structure, entry points, architecture.
    Step 2 — High-impact: which 3-5 subsystems matter most for the goal and why.
    Step 3 — Plan: ordered numbered investigation subtasks (5-8 items).
    Step 4 — Execute: run the plan adaptively (may add/skip subtasks).

    Returns dict with keys: structure_map, high_impact_areas, plan, report.
    """
    structure_map, _ = await run_session(
        "Summarize this project's layout for someone new to the repo. "
        "Cover: top-level directories and their roles, the main entry point(s), "
        "the dominant architectural style, and the build/test tooling. "
        "Be terse — this is a map, not a tour.",
        cwd=cwd,
        allowed_tools=EXPLORER_TOOLS,
        system_prompt=EXPLORER_PROMPT,
    )

    high_impact_areas, _ = await run_session(
        f"Below is a structure map of the project. Given the goal:\n  GOAL: {goal}\n\n"
        "List the 3-5 subsystems most relevant to that goal and, for each, one sentence "
        "on why it matters. Use only the structure map and minimal Grep.\n\n"
        f"STRUCTURE MAP:\n{structure_map}",
        cwd=cwd,
        allowed_tools=EXPLORER_TOOLS,
        system_prompt=EXPLORER_PROMPT,
    )

    plan, _ = await run_session(
        "Given the goal and high-impact areas below, produce a numbered investigation "
        "plan (5-8 subtasks) ordered by dependency: earlier subtasks produce info that "
        "later subtasks need. Keep each subtask to one sentence.\n\n"
        f"GOAL: {goal}\n\nHIGH-IMPACT AREAS:\n{high_impact_areas}",
        cwd=cwd,
        allowed_tools=EXPLORER_TOOLS,
        system_prompt=EXPLORER_PROMPT,
    )

    report, _ = await run_session(
        "Execute the investigation plan below to satisfy the goal. As you work, you MAY "
        "add subtasks if a finding opens a relevant thread, and you MAY skip subtasks "
        "that turn out to be irrelevant — note any deviation in the final report. "
        "Use Grep first, Read sparingly. End with a structured report: "
        "Findings, Open Questions, Suggested Next Actions.\n\n"
        f"GOAL: {goal}\n\nPLAN:\n{plan}",
        cwd=cwd,
        allowed_tools=EXPLORER_TOOLS,
        system_prompt=EXPLORER_PROMPT,
    )

    return {
        "structure_map": structure_map,
        "high_impact_areas": high_impact_areas,
        "plan": plan,
        "report": report,
    }
```

---

## PR 5 — feat/builder

**Branch:** `feat/builder` (from `feat/explorer`)
**Commit:** `feat(builder): add plan→confirm→write→verify feature builder`

### File to create: `src/claude_codebase_agent/builder.py`

```python
"""Write-capable feature builder — plan → confirm → write → verify."""
from __future__ import annotations
import asyncio
import os
import subprocess
from claude_codebase_agent.prompts import EXPLORER_PROMPT, BUILDER_PROMPT
from claude_codebase_agent.session import run_session
from claude_codebase_agent.explorer import EXPLORER_TOOLS, adaptive_investigation

BUILDER_TOOLS = ["Grep", "Glob", "Read", "Write", "Edit", "Bash"]

_DETECT_RULES = [
    ("pom.xml", "mvn -q test"),
    ("build.gradle", "./gradlew test"),
    ("build.gradle.kts", "./gradlew test"),
    ("package.json", "npm test"),
    ("go.mod", "go test ./..."),
    ("Makefile", "make test"),
    ("pytest.ini", "python -m pytest"),
    ("setup.cfg", "python -m pytest"),
    ("pyproject.toml", "python -m pytest"),
]


def _detect_verify_cmd(target_dir: str) -> str | None:
    for filename, cmd in _DETECT_RULES:
        if os.path.exists(os.path.join(target_dir, filename)):
            return cmd
    return None


async def implement_feature(
    requirement: str,
    target_dir: str,
    verify_cmd: str | None = None,
) -> None:
    """Discover → plan → confirm → implement → verify against the target repo."""
    target_dir = os.path.abspath(target_dir)

    # ── Step 1: Discover ──────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("STEP 1/4  Discovering the codebase (read-only) …")
    print(f"{'─'*60}\n")
    investigation = await adaptive_investigation(requirement, cwd=target_dir)

    # ── Step 2: Build implementation plan (read-only) ─────────────────────────
    print(f"\n{'─'*60}")
    print("STEP 2/4  Building implementation plan …")
    print(f"{'─'*60}\n")

    if verify_cmd is None:
        verify_cmd = _detect_verify_cmd(target_dir) or ""

    plan_prompt = (
        "You have just investigated a codebase with the following findings:\n\n"
        f"STRUCTURE MAP:\n{investigation['structure_map']}\n\n"
        f"HIGH-IMPACT AREAS:\n{investigation['high_impact_areas']}\n\n"
        f"INVESTIGATION REPORT:\n{investigation['report']}\n\n"
        "Now produce a CONCRETE IMPLEMENTATION PLAN for the following requirement:\n"
        f"  REQUIREMENT: {requirement}\n\n"
        "The plan must list:\n"
        "1. Every file to create or modify (with the exact path)\n"
        "2. What change to make in each file (function signature, class, etc.)\n"
        "3. What tests to add or modify\n"
        f"4. The verify command that will be run: {verify_cmd or '(none specified — auto-detect)'}\n\n"
        "Be specific enough that another agent can execute this plan without asking questions."
    )
    plan_text, _ = await run_session(
        plan_prompt,
        cwd=target_dir,
        allowed_tools=EXPLORER_TOOLS,
        system_prompt=EXPLORER_PROMPT,
    )

    # ── Step 3: Human confirm gate ────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("STEP 3/4  Review the plan above.")
    print(f"{'─'*60}")
    answer = input("Proceed with implementation? [y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        print("Aborted — no files were changed.")
        return

    # ── Step 4: Implement ─────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("STEP 4/4  Implementing …")
    print(f"{'─'*60}\n")

    impl_prompt = (
        f"REQUIREMENT: {requirement}\n\n"
        f"APPROVED IMPLEMENTATION PLAN:\n{plan_text}\n\n"
        f"VERIFY COMMAND: {verify_cmd or '(none — skip verification step)'}\n\n"
        "Execute the plan now. Follow the repo's existing conventions exactly. "
        "Make minimal targeted changes. After all edits, run the verify command "
        "and iterate until it passes. Finish with a summary of every file changed."
    )
    _, _ = await run_session(
        impl_prompt,
        cwd=target_dir,
        allowed_tools=BUILDER_TOOLS,
        system_prompt=BUILDER_PROMPT,
        permission_mode="acceptEdits",
        mcp_servers={},
    )

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("DIFF SUMMARY")
    print(f"{'─'*60}")
    result = subprocess.run(
        ["git", "-C", target_dir, "diff", "--stat"],
        capture_output=True, text=True,
    )
    print(result.stdout or "(no git diff — target dir may not be a git repo)")
    untracked = subprocess.run(
        ["git", "-C", target_dir, "status", "--short"],
        capture_output=True, text=True,
    )
    if untracked.stdout:
        print(untracked.stdout)
    print(f"{'─'*60}")
    print("Review changes above. Run 'git diff' in the target repo for the full patch.")
    print("To undo everything: git -C <target_dir> checkout . && git clean -fd")
```

---

## PR 6 — feat/cli

**Branch:** `feat/cli` (from `feat/builder`)
**Commit:** `feat(cli): add interactive REPL with menu and target-dir prompt`

### Files to create/update

**`src/claude_codebase_agent/cli.py`**

```python
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
```

**`src/claude_codebase_agent/__main__.py`** (update from placeholder)
```python
import asyncio
from claude_codebase_agent.cli import main

if __name__ == "__main__":
    asyncio.run(main())
```

---

## PR 7 — feat/docs

**Branch:** `feat/docs` (from `feat/cli`)
**Commit:** `docs: add README, setup guide, and smoke tests`

### Files to create

**`tests/test_smoke.py`** — import-only, no API calls:
```python
"""Smoke tests — verify imports and structure only. No API calls."""
import asyncio
import inspect


def test_session_exports():
    from claude_codebase_agent.session import run_session
    assert asyncio.iscoroutinefunction(run_session)
    sig = inspect.signature(run_session)
    assert "cwd" in sig.parameters
    assert "allowed_tools" in sig.parameters
    assert "permission_mode" in sig.parameters


def test_explorer_exports():
    from claude_codebase_agent.explorer import discover, adaptive_investigation, EXPLORER_TOOLS
    assert asyncio.iscoroutinefunction(discover)
    assert asyncio.iscoroutinefunction(adaptive_investigation)
    assert "Grep" in EXPLORER_TOOLS
    assert "Write" not in EXPLORER_TOOLS


def test_builder_exports():
    from claude_codebase_agent.builder import implement_feature, BUILDER_TOOLS
    assert asyncio.iscoroutinefunction(implement_feature)
    assert "Write" in BUILDER_TOOLS
    assert "Edit" in BUILDER_TOOLS
    assert "Bash" in BUILDER_TOOLS


def test_cli_exports():
    from claude_codebase_agent.cli import main
    assert asyncio.iscoroutinefunction(main)


def test_prompts_exports():
    from claude_codebase_agent.prompts import EXPLORER_PROMPT, BUILDER_PROMPT
    assert "Grep" in EXPLORER_PROMPT
    assert "Read" in EXPLORER_PROMPT
    assert isinstance(BUILDER_PROMPT, str)
    assert len(BUILDER_PROMPT) > 100
```

**`README.md`** — full setup and usage guide. Include:
- What it does (one paragraph — discover + build)
- Prerequisites (Python 3.12, direnv, Anthropic API key)
- Setup steps (clone → `direnv allow` → `pip install -e ".[dev]"` → copy `.env.example`)
- Quick start (run `python -m claude_codebase_agent`, point at any repo)
- Three modes explained with examples (ask, investigate, build)
- Full worked example: clone `https://github.com/spring-projects/spring-petclinic`, run the agent, ask "where is the owner service?", then build a feature like "add a pet weight field to the owner's pet list"
- Safety section: always use git repos, `git diff` to review, `git checkout .` to revert
- Optional MCP setup (copy `.mcp.json.example` → `.mcp.json`, fill tokens)
- Link to Anthropic console for API key

---

## Merge-Order Report

After all 7 PRs are open, write `docs/pr-merge-order.md`. Commit it directly to `main` or as an 8th small branch — your call.

The report must contain:
- A table with PR number, branch name, PR URL, brief description, and dependency
- The merge sequence (1 → 7) with the rationale for each ordering constraint
- A "why stacked?" explanation: each branch targets the previous so the PR diff shows only its own changes; merging out of order will produce conflicts or incorrect diffs
- A post-merge checklist: after all merges, run `pip install -e ".[dev]"` + `pytest` + `python -m claude_codebase_agent` to confirm the full stack works

---

## Summary of Execution Order

```
Step 0:  gh repo create + push main + direnv allow + pip install + introspect SDK
PR 1:    feat/scaffold  →  gh pr create --base main
PR 2:    feat/prompts   →  gh pr create --base feat/scaffold
PR 3:    feat/session   →  gh pr create --base feat/prompts
PR 4:    feat/explorer  →  gh pr create --base feat/session
PR 5:    feat/builder   →  gh pr create --base feat/explorer
PR 6:    feat/cli       →  gh pr create --base feat/builder
PR 7:    feat/docs      →  gh pr create --base feat/cli
Report:  docs/pr-merge-order.md  →  commit to main (or separate branch)
```
