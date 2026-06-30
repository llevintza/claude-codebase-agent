# Configuration

## Environment Variables

Set these in `.env` (copy `.env.example` to get started) or export them in your shell. The CLI loads `.env` automatically at startup via `python-dotenv`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | — | API key for the Anthropic API. Get one at [console.anthropic.com](https://console.anthropic.com). |
| `VERIFY_CMD` | No | `""` | Override the auto-detected build/test command for the Builder. When set, the CLI skips the verify command prompt and uses this value directly. |

### `.env` example

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...

# Optional: override the auto-detected verify command
# VERIFY_CMD=mvn -q test
```

---

## Verify Command Auto-Detection

When `VERIFY_CMD` is not set and no command is supplied interactively, `builder.implement_feature` scans the target repo's root directory for these files (first match wins):

| Marker file | Command run |
|---|---|
| `pom.xml` | `mvn -q test` |
| `build.gradle` | `./gradlew test` |
| `build.gradle.kts` | `./gradlew test` |
| `package.json` | `npm test` |
| `go.mod` | `go test ./...` |
| `Makefile` | `make test` |
| `pytest.ini` | `python -m pytest` |
| `setup.cfg` | `python -m pytest` |
| `pyproject.toml` | `python -m pytest` |

If no marker is found, verification is skipped and noted in the implementation summary.

**Priority order for setting the verify command** (highest to lowest):

1. `VERIFY_CMD` environment variable
2. Value typed at the interactive prompt in the CLI
3. `verify_cmd` argument passed to `implement_feature()` directly
4. Auto-detection from marker files
5. No verification (skipped)

---

## Claude Code Permissions (`.claude/settings.json`)

`.claude/settings.json` controls which `Bash` commands Claude Code (the agent) may run without prompting when this tool is used inside a Claude Code session.

Current allowlist:

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

This file governs the **development environment** for this project, not the target repo. The Builder agent's access to the target repo is controlled by `BUILDER_TOOLS` and `permission_mode="acceptEdits"` in `session.py`.

---

## MCP Server Integration (Optional)

MCP (Model Context Protocol) servers provide the agent with additional tools — for example, access to GitHub issues, Jira tickets, or internal documentation.

### Setup

```bash
cp .mcp.json.example .mcp.json
```

Edit `.mcp.json` and add your server configurations. Example:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/target"]
    }
  }
}
```

MCP servers are passed to `ClaudeAgentOptions.mcp_servers` in `run_session`. The default is an empty dict — MCP is opt-in.

`.mcp.json` is git-ignored and should never be committed (it contains tokens).

---

## Python Environment

The project uses `direnv` + `python3.12` to manage its virtualenv.

```bash
# First time
direnv allow          # creates .direnv/python-3.12/ venv
pip install -e ".[dev]"

# After pulling changes that add dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run the tool
python -m claude_codebase_agent
# or:
claude-codebase-agent
```

The `layout python python3.12` line in `.envrc` creates the venv automatically when you enter the project directory (if direnv is hooked into your shell).

---

## Changing Model or Agent Options

`run_session` in `session.py` passes all options through `ClaudeAgentOptions`. To override the model or set additional SDK options, edit `run_session` directly or extend the function signature.

Available `ClaudeAgentOptions` fields (confirmed via introspection on `claude-agent-sdk==0.2.110`):

```
tools, allowed_tools, system_prompt, mcp_servers, strict_mcp_config,
permission_mode, continue_conversation, resume, session_id, max_turns,
max_budget_usd, disallowed_tools, model, fallback_model, betas,
permission_prompt_tool_name, cwd, cli_path, settings, add_dirs, env,
extra_args, max_buffer_size, debug_stderr, stderr, can_use_tool, hooks,
user, include_partial_messages, include_hook_events, fork_session, agents,
setting_sources, skills, sandbox, plugins, max_thinking_tokens, thinking,
effort, output_format, enable_file_checkpointing, session_store,
session_store_flush, load_timeout_ms, task_budget
```

Common overrides:

```python
# Use a specific model
opts_kwargs["model"] = "claude-opus-4-8"

# Cap cost
opts_kwargs["max_budget_usd"] = 1.00

# Limit turns
opts_kwargs["max_turns"] = 10
```
