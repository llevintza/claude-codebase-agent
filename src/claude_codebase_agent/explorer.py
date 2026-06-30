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
