# Architecture

## Overview

`claude-codebase-agent` is a thin orchestration layer on top of the **Claude Agent SDK**. It manages two distinct agent personas (Explorer and Builder) and coordinates them through a structured pipeline. The tool itself never modifies its own source files — all file changes happen in an external `target_dir` supplied by the user.

```
User (CLI)
    │
    ▼
cli.py  ────────────────────────────────────────────────────
    │                                                       │
    ▼                                                       ▼
explorer.py                                            builder.py
  discover()                                        implement_feature()
  adaptive_investigation()                               │
    │                                         ┌──────────┤
    │                                         │          │
    │                            adaptive_investigation() │
    │                            (re-uses explorer)       │
    │                                         │          │
    └─────────────────┬───────────────────────┘          │
                      ▼                                   │
                 session.py                               │
               run_session()                              │
                      │                                   │
                      ▼                                   │
            Claude Agent SDK (query())  ◄─────────────────┘
                      │
                      ▼
              Claude (running in
              the target repo's cwd)
```

---

## Two Personas

The entire design is built around a strict separation of two agent modes. They share the same `run_session()` infrastructure but receive different system prompts and tool allowlists.

### Explorer

| Attribute | Value |
|---|---|
| Module | `explorer.py` |
| System prompt | `EXPLORER_PROMPT` |
| Tools | `Grep`, `Glob`, `Read` |
| `permission_mode` | `"default"` (read-only) |
| Writes files? | Never |

The Explorer answers questions and maps codebases. It always starts with `Grep` — the most targeted tool — before opening any file. It is intentionally starved of write tools so it cannot accidentally modify a target repo during discovery.

### Builder

| Attribute | Value |
|---|---|
| Module | `builder.py` |
| System prompt | `BUILDER_PROMPT` |
| Tools | `Grep`, `Glob`, `Read`, `Write`, `Edit`, `Bash` |
| `permission_mode` | `"acceptEdits"` |
| Writes files? | Yes — only in `target_dir` |

The Builder executes a pre-approved plan. It runs only after the user has seen the plan and typed `y`. It is constrained by `BUILDER_PROMPT` never to touch files outside the target directory.

---

## Module Responsibilities

### `prompts.py`

Pure data — two string constants. No imports from this project, no side effects. Changing a prompt here affects all sessions that use it.

### `session.py` — `run_session()`

Single chokepoint for every Claude Agent SDK call. Responsibilities:
- Build `ClaudeAgentOptions` from keyword arguments
- Stream `AssistantMessage` text blocks to stdout in real time
- Capture `session_id` from `SystemMessage` (for future session resumption)
- Extract `final_text` from `ResultMessage`
- Return `(final_text, session_id)`

Nothing else in the project calls `claude_agent_sdk.query` directly.

### `explorer.py`

Two public functions:

**`discover(question, cwd)`** — single session turn. Wraps `run_session` with `EXPLORER_TOOLS` and `EXPLORER_PROMPT`. Use for targeted lookups.

**`adaptive_investigation(goal, cwd)`** — four sequential session turns, each building on the previous output:

```
Turn 1: "Summarize this project's layout"
           → structure_map
Turn 2: "Given the goal and this map, which subsystems matter?"
           → high_impact_areas
Turn 3: "Given the goal and those areas, build an investigation plan"
           → plan
Turn 4: "Execute the plan"
           → report
```

Returns `{"structure_map", "high_impact_areas", "plan", "report"}`.

Each turn is an independent session — no state is shared via the SDK between turns. The output of each turn is injected as text into the next prompt.

### `builder.py` — `implement_feature()`

Orchestrates the full plan→confirm→write→verify pipeline:

```
Step 1: adaptive_investigation(requirement, cwd=target_dir)
           → investigation dict (read-only)

Step 2: run_session(plan_prompt, allowed_tools=EXPLORER_TOOLS)
           → plan_text (read-only)

Step 3: input("Proceed? [y/N]")
           → blocks until human approves or aborts

Step 4: run_session(impl_prompt, allowed_tools=BUILDER_TOOLS,
                    permission_mode="acceptEdits")
           → agent edits files and runs verify command

Report: git diff --stat + git status --short
```

Step 2 uses `EXPLORER_TOOLS` (read-only) deliberately — the plan itself is produced without making any changes.

### `cli.py` — `main()`

Interactive REPL loop. Flow:
1. Load `.env` (via `python-dotenv`)
2. Warn if `ANTHROPIC_API_KEY` is unset
3. Prompt for a `target_dir` (validates existence, warns if not a git repo)
4. Loop: display menu → dispatch to `_menu_ask`, `_menu_investigate`, or `_menu_build`

All imports from `explorer` and `builder` are deferred (inside the menu handler functions) to keep startup fast and avoid circular import issues.

---

## Data Flow — Feature Build

```
User types: "add a weight field to the pet entity"
                │
                ▼
        _menu_build(target_dir)
                │
                ▼
        implement_feature(requirement, target_dir)
                │
        ┌───────┴──────────────────────────────────────────────┐
        │  Step 1: adaptive_investigation(requirement, cwd)    │
        │    run_session × 4 (Grep/Glob/Read only)             │
        │    → {structure_map, high_impact_areas, plan, report} │
        └───────────────────────────────────────────────────────┘
                │
        ┌───────┴──────────────────────────────────────────────┐
        │  Step 2: run_session(plan_prompt, EXPLORER_TOOLS)    │
        │    Agent reads code, outputs concrete plan           │
        │    → plan_text                                       │
        └───────────────────────────────────────────────────────┘
                │
                ▼
        [plan_text printed to stdout]
        input("Proceed? [y/N]")  ← HUMAN GATE
                │
                │ "y"
                ▼
        ┌───────┴──────────────────────────────────────────────┐
        │  Step 4: run_session(impl_prompt, BUILDER_TOOLS,    │
        │          permission_mode="acceptEdits")              │
        │    Agent edits files, runs verify cmd, iterates     │
        └───────────────────────────────────────────────────────┘
                │
                ▼
        git diff --stat  (subprocess, read-only)
        → printed to stdout
```

---

## Key Design Decisions

**Why four sequential turns for `adaptive_investigation`?**
Each turn is focused and small. A single turn asking "map the repo, then list subsystems, then plan, then execute" produces lower-quality output — the model tries to do everything at once and tends to over-read or over-plan. Chaining lets each turn specialize.

**Why is the plan produced with read-only tools?**
Step 2 (plan generation) uses `EXPLORER_TOOLS`, not `BUILDER_TOOLS`. This ensures the agent cannot start making changes while formulating a plan, which would bypass the human confirm gate.

**Why `input()` instead of a callback or flag?**
The human gate is a synchronous `input()` call in `implement_feature`. This is intentional: the gate must be impossible to accidentally skip from calling code. A flag or callback could be omitted by a caller; `input()` cannot.

**Why is `cwd` passed to the SDK rather than `os.chdir()`?**
`ClaudeAgentOptions.cwd` sets the working directory for the Claude CLI subprocess, not the Python process. Using `os.chdir()` would move the Python process's working directory, which could break relative path resolution elsewhere. The SDK field keeps the scoping clean.

**Why are `explorer` and `builder` imports deferred in `cli.py`?**
`builder.py` imports from `explorer.py`. If both were top-level imports in `cli.py`, a failed import in either would crash the CLI at startup even if the user only wants to use the other mode. Deferring imports to the point of use means each mode is only loaded when actually selected.
