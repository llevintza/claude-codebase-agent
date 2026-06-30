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
    opts_kwargs: dict = dict(
        system_prompt=system_prompt,
        allowed_tools=allowed_tools,
        mcp_servers=mcp_servers or {},
    )
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
