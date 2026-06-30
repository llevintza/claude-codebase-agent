# claude-codebase-agent — Project Context for Claude Code

> **Onboarding note for a new Claude session:** This file was written by the planning session that designed this project. Read it fully before doing anything. Everything you need to continue the implementation is here and in `IMPLEMENTATION_PLAN.md`.

---

## What This Project Is

A standalone, self-contained Python tool built on the **Claude Agent SDK** that:
1. **Explores** an unfamiliar codebase using Grep-first incremental discovery (read-only)
2. **Implements features** in that codebase from high-level natural-language requirements, following a **plan → confirm → write → verify** workflow (write-capable, with a human checkpoint before any file changes)

The user points this tool at any external repo, describes a feature, and the tool handles discovery, planning, implementation, and verification — without touching its own source files.

---

## Current State When This Session Starts

**Git:** initialized on `main`, one commit (`chore: initialize repository`).

**GitHub remote:** NOT yet created. You must create it first:
```bash
gh repo create llevintza/claude-codebase-agent --public \
  --description "A Claude Agent SDK tool that explores unfamiliar codebases and implements features from high-level requirements"
cd /Users/llevintza/wrk/claude-codebase-agent
git remote add origin git@github.com:llevintza/claude-codebase-agent.git
git push -u origin main
```

**Files already on disk (not yet committed to a branch):**
- `.gitignore`, `.envrc`, `.env.example`, `.mcp.json.example`, `LICENSE`, `pyproject.toml`
- `src/claude_codebase_agent/` (empty dir), `tests/` (empty dir), `.claude/` (empty dir)
- `.gitkeep` (placeholder in initial commit)

**Environment:**
- `direnv` installed (`/opt/homebrew/bin/direnv`), hook added to `~/.zshrc`
- `python3.12` installed (`/opt/homebrew/bin/python3.12`)
- `claude-agent-sdk` is NOT yet installed (install via the venv in `.envrc`)
- `ANTHROPIC_API_KEY` is NOT set — user needs to copy `.env.example` → `.env` and fill it

---

## Two Personas — Never Mix Them

| Persona | Module | Tools | permission_mode | Operates on |
|---|---|---|---|---|
| **Explorer** | `explorer.py` | Grep, Glob, Read | default (read-only) | target repo via `cwd` |
| **Builder** | `builder.py` | Grep, Glob, Read, Write, Edit, Bash | acceptEdits | target repo via `cwd` |

The builder **never** touches this repo's own `src/` files. It always receives an external `target_dir` from the user.

---

## The Plan → Confirm → Write Rule

The builder MUST follow this sequence without exception:
1. **Discover** — `adaptive_investigation(goal, cwd=target_dir)` — read-only
2. **Plan** — emit a concrete change plan (files, functions, tests, verify command) — read-only
3. **Confirm** — `input("Proceed with implementation? [y/N] ")` — **STOP until user types `y`**
4. **Implement** — `run_session(..., permission_mode="acceptEdits")` — edits files, runs verify
5. **Report** — `git -C <target_dir> diff --stat` — summarize what changed

---

## Branch and PR Strategy

**7 stacked feature branches, each targeting the previous branch** (not main), so each PR shows only its own clean diff. Must be merged in order 1→7.

| PR | Branch | Targets | Content |
|---|---|---|---|
| 1 | `feat/scaffold` | `main` | All config/static files + package skeleton |
| 2 | `feat/prompts` | `feat/scaffold` | `prompts.py` — EXPLORER_PROMPT + BUILDER_PROMPT |
| 3 | `feat/session` | `feat/prompts` | `session.py` — SDK wrapper (run_session) |
| 4 | `feat/explorer` | `feat/session` | `explorer.py` — discover() + adaptive_investigation() |
| 5 | `feat/builder` | `feat/explorer` | `builder.py` — implement_feature() |
| 6 | `feat/cli` | `feat/builder` | `cli.py` + `__main__.py` — interactive REPL |
| 7 | `feat/docs` | `feat/cli` | `README.md` + `tests/test_smoke.py` |

After all PRs are open, write a **merge-order report** (`docs/pr-merge-order.md`) on a separate branch or directly — see IMPLEMENTATION_PLAN.md.

---

## SDK Introspection (Do This Before Writing session.py)

After creating the venv and installing deps, run this to get the exact field names — they may differ from what the plan assumes:

```bash
python3.12 -c "
import dataclasses, claude_agent_sdk as sdk
for f in dataclasses.fields(sdk.ClaudeAgentOptions):
    print(f.name, '=', repr(f.default))
"
```

The plan assumes these fields exist: `system_prompt`, `allowed_tools`, `mcp_servers`, `resume`, `permission_mode`, `cwd`. Adjust `session.py` if any name differs.

---

## How to Run (After Setup)

```bash
# One-time setup
direnv allow        # creates venv via 'layout python python3.12'
pip install -e ".[dev]"
cp .env.example .env   # fill in ANTHROPIC_API_KEY

# Run
python -m claude_codebase_agent
# or: claude-codebase-agent
```

---

## Commit Message Style

Each branch has **one focused commit** with a conventional commit message:
- `feat(scaffold): add project config and package skeleton`
- `feat(prompts): add explorer and builder system prompts`
- `feat(session): add SDK wrapper with cwd and permission_mode support`
- `feat(explorer): add read-only discover and adaptive_investigation`
- `feat(builder): add plan→confirm→write→verify feature builder`
- `feat(cli): add interactive REPL with menu and target-dir prompt`
- `docs: add README, setup guide, and smoke tests`

Every commit must end with:
```
Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>
```

---

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API auth — get at console.anthropic.com |
| `VERIFY_CMD` | No | Build/test command run after feature implementation (e.g. `mvn -q test`, `npm test`, `go test ./...`) |
