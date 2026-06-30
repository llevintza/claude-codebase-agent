# API Reference

All public functions are async coroutines unless noted otherwise.

---

## `session.run_session`

```python
async def run_session(
    prompt: str,
    *,
    cwd: str | None = None,
    allowed_tools: list[str],
    system_prompt: str,
    permission_mode: str = "default",
    mcp_servers: dict | None = None,
    session_id: str | None = None,
) -> tuple[str, str | None]
```

Single chokepoint for all Claude Agent SDK calls. Streams assistant text to stdout in real time.

### Parameters

| Name | Type | Required | Description |
|---|---|---|---|
| `prompt` | `str` | Yes | The user message sent to the agent |
| `cwd` | `str \| None` | No | Working directory for the agent subprocess. Defaults to the Python process's cwd if omitted. |
| `allowed_tools` | `list[str]` | Yes | Tool names the agent may use (e.g. `["Grep", "Glob", "Read"]`) |
| `system_prompt` | `str` | Yes | System prompt string — use `EXPLORER_PROMPT` or `BUILDER_PROMPT` |
| `permission_mode` | `str` | No | `"default"` (read-only) or `"acceptEdits"` (allows file writes). Default: `"default"` |
| `mcp_servers` | `dict \| None` | No | MCP server config passed to `ClaudeAgentOptions`. Default: `{}` |
| `session_id` | `str \| None` | No | Resume a previous session by ID. Passed as `resume` to the SDK. |

### Returns

`tuple[str, str | None]` — `(final_text, session_id)`

- `final_text`: the agent's final answer extracted from `ResultMessage`. Empty string if the agent produced no result text.
- `session_id`: captured from `SystemMessage` during the stream, or `None` if not provided by the SDK.

### Side effects

Prints assistant text blocks to stdout as they arrive.

### Example

```python
from claude_codebase_agent.session import run_session
from claude_codebase_agent.prompts import EXPLORER_PROMPT

answer, sid = await run_session(
    "Where is the database connection pool configured?",
    cwd="/path/to/myapp",
    allowed_tools=["Grep", "Glob", "Read"],
    system_prompt=EXPLORER_PROMPT,
)
print(f"Session: {sid}")
```

---

## `explorer.discover`

```python
async def discover(question: str, cwd: str) -> tuple[str, str | None]
```

Single-shot read-only question answered against a codebase. Wraps `run_session` with `EXPLORER_TOOLS` and `EXPLORER_PROMPT`.

### Parameters

| Name | Type | Description |
|---|---|---|
| `question` | `str` | A specific question about the target codebase |
| `cwd` | `str` | Absolute path to the target repository |

### Returns

`tuple[str, str | None]` — same as `run_session`: `(answer_text, session_id)`.

### Example

```python
from claude_codebase_agent.explorer import discover

answer, _ = await discover(
    "Where is the JWT token validation logic?",
    cwd="/path/to/backend",
)
```

---

## `explorer.adaptive_investigation`

```python
async def adaptive_investigation(goal: str, cwd: str) -> dict
```

Open-ended codebase investigation across four sequential agent turns. Each turn's output is injected as context into the next prompt.

### Parameters

| Name | Type | Description |
|---|---|---|
| `goal` | `str` | High-level investigation goal (e.g. "understand how authentication works") |
| `cwd` | `str` | Absolute path to the target repository |

### Returns

`dict` with four string keys:

| Key | Content |
|---|---|
| `structure_map` | Terse summary of the repo's top-level layout, entry points, architecture style, and build tooling |
| `high_impact_areas` | 3-5 subsystems most relevant to the goal, each with a one-sentence rationale |
| `plan` | Numbered investigation subtasks (5-8 items) ordered by dependency |
| `report` | Full investigation report: Findings, Open Questions, Suggested Next Actions |

### Example

```python
from claude_codebase_agent.explorer import adaptive_investigation

result = await adaptive_investigation(
    "understand how the payment processing pipeline works",
    cwd="/path/to/ecommerce-app",
)

print(result["structure_map"])
print(result["report"])
```

### Notes

- Uses four independent `run_session` calls — no SDK-level session is shared between turns.
- All four turns are strictly read-only (`EXPLORER_TOOLS`).
- The plan step produces 5-8 subtasks. The execute step may add or skip subtasks based on findings; deviations are noted in the report.

---

## `builder.implement_feature`

```python
async def implement_feature(
    requirement: str,
    target_dir: str,
    verify_cmd: str | None = None,
) -> None
```

Full plan → confirm → implement → verify pipeline. Blocks on a `[y/N]` prompt before making any file changes.

### Parameters

| Name | Type | Description |
|---|---|---|
| `requirement` | `str` | High-level feature description (e.g. "add a pet weight field to the pet entity and owner view") |
| `target_dir` | `str` | Path to the target repository. Resolved to absolute via `os.path.abspath`. |
| `verify_cmd` | `str \| None` | Command to run after implementation (e.g. `"mvn -q test"`, `"npm test"`). Auto-detected if `None`. |

### Returns

`None`. All output (plan, progress, diff summary) is written to stdout.

### Verify command auto-detection

If `verify_cmd` is `None`, the function scans `target_dir` for these marker files (first match wins):

| Marker | Command |
|---|---|
| `pom.xml` | `mvn -q test` |
| `build.gradle` / `build.gradle.kts` | `./gradlew test` |
| `package.json` | `npm test` |
| `go.mod` | `go test ./...` |
| `Makefile` | `make test` |
| `pytest.ini` / `setup.cfg` / `pyproject.toml` | `python -m pytest` |

If no marker is found, verification is skipped and noted in the summary.

### Human gate

After printing the plan, the function calls `input("Proceed with implementation? [y/N] ")`. Anything other than `y` or `yes` aborts — no files are changed.

### Example

```python
from claude_codebase_agent.builder import implement_feature

await implement_feature(
    requirement="add a rate-limit header to all API responses",
    target_dir="/path/to/api-server",
    verify_cmd="go test ./...",
)
```

### Notes

- The discovery and planning steps use `EXPLORER_TOOLS` (read-only).
- The implementation step uses `BUILDER_TOOLS` with `permission_mode="acceptEdits"`.
- After implementation, prints `git diff --stat` and `git status --short` from `target_dir`.
- Prints undo instructions: `git -C <target_dir> checkout . && git clean -fd`

---

## `cli.main`

```python
async def main() -> None
```

Entry point for the interactive REPL. Called by `python -m claude_codebase_agent` and the `claude-codebase-agent` console script.

### Behaviour

1. Loads `.env` via `python-dotenv`
2. Warns if `ANTHROPIC_API_KEY` is not set
3. Prompts for a `target_dir` (loops until a valid directory is entered; warns for non-git dirs)
4. Runs the menu loop until `q`, `quit`, `exit`, or EOF/Ctrl-C

### Menu options

| Choice | Handler | Calls |
|---|---|---|
| `1` | `_menu_ask` | `explorer.discover` |
| `2` | `_menu_investigate` | `explorer.adaptive_investigation` |
| `3` | `_menu_build` | `builder.implement_feature` |
| `q` / `quit` / `exit` | — | exits |

---

## Constants

### `explorer.EXPLORER_TOOLS`

```python
EXPLORER_TOOLS = ["Grep", "Glob", "Read"]
```

Read-only tool allowlist used by all Explorer sessions and by the planning step of `implement_feature`.

### `builder.BUILDER_TOOLS`

```python
BUILDER_TOOLS = ["Grep", "Glob", "Read", "Write", "Edit", "Bash"]
```

Full tool allowlist used by the implementation step of `implement_feature`.

### `prompts.EXPLORER_PROMPT`

System prompt string enforcing Grep-first read-only discovery. See `src/claude_codebase_agent/prompts.py` for the full text.

### `prompts.BUILDER_PROMPT`

System prompt string enforcing convention-following minimal edits, verify-until-pass, and no-files-outside-target-dir. See `src/claude_codebase_agent/prompts.py` for the full text.
