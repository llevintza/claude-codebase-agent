"""Write-capable feature builder — plan → confirm → write → verify."""
from __future__ import annotations
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
