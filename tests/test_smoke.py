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
