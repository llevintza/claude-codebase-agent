# PR Merge Order Report

All 7 PRs are stacked — each branch targets the one before it — so they must be merged in sequence (1 → 7). Merging out of order will produce conflicts or incorrect diffs.

---

## PR Table

| # | Branch | PR URL | Description | Depends on |
|---|---|---|---|---|
| 1 | `feat/scaffold` | https://github.com/llevintza/claude-codebase-agent/pull/1 | All config/static files + package skeleton (`__init__.py`, `__main__.py`, `tests/__init__.py`, `.claude/settings.json`) | `main` |
| 2 | `feat/prompts` | https://github.com/llevintza/claude-codebase-agent/pull/2 | `prompts.py` — `EXPLORER_PROMPT` + `BUILDER_PROMPT` | PR 1 |
| 3 | `feat/session` | https://github.com/llevintza/claude-codebase-agent/pull/3 | `session.py` — `run_session()` SDK wrapper with `cwd` and `permission_mode` | PR 2 |
| 4 | `feat/explorer` | https://github.com/llevintza/claude-codebase-agent/pull/4 | `explorer.py` — `discover()` + `adaptive_investigation()`, read-only | PR 3 |
| 5 | `feat/builder` | https://github.com/llevintza/claude-codebase-agent/pull/5 | `builder.py` — `implement_feature()` with plan→confirm→write→verify | PR 4 |
| 6 | `feat/cli` | https://github.com/llevintza/claude-codebase-agent/pull/6 | `cli.py` + `__main__.py` — interactive REPL | PR 5 |
| 7 | `feat/docs` | https://github.com/llevintza/claude-codebase-agent/pull/7 | `README.md` + `tests/test_smoke.py` | PR 6 |

---

## Merge Sequence and Rationale

**PR 1 first** — all other modules import from the `claude_codebase_agent` package. The scaffold creates the package directory structure and `pyproject.toml`. Nothing else can be installed without it.

**PR 2 second** — `prompts.py` defines `EXPLORER_PROMPT` and `BUILDER_PROMPT`. Both `session.py` (PR 3 indirectly) and `explorer.py` / `builder.py` import from `prompts`. It has no imports from this project, so it can go right after the scaffold.

**PR 3 third** — `session.py` imports only from the standard library and `claude_agent_sdk`. It's the foundation that `explorer.py` and `builder.py` both depend on.

**PR 4 fourth** — `explorer.py` imports `EXPLORER_PROMPT` (PR 2) and `run_session` (PR 3). Both must be merged before PR 4.

**PR 5 fifth** — `builder.py` imports from `explorer.py` (PR 4), `prompts.py` (PR 2), and `session.py` (PR 3). All three must be present.

**PR 6 sixth** — `cli.py` lazily imports `discover`, `adaptive_investigation` (PR 4), and `implement_feature` (PR 5). Both must be merged first.

**PR 7 last** — `test_smoke.py` imports from every module (PRs 2–6). The README documents the complete tool. Both belong at the end.

---

## Why Stacked?

Each branch targets the previous branch (not `main`), so each PR's diff shows **only the changes introduced by that PR** — no noise from earlier PRs bleeding into the diff. If merged out of order:

- Merging PR 2 before PR 1: the `src/claude_codebase_agent/` package directory doesn't exist in `main`, causing a conflict or incorrect tree.
- Merging PR 4 before PR 3: `from claude_codebase_agent.session import run_session` would fail at install/test time since `session.py` isn't on `main` yet.
- Merging any PR before its parent: GitHub will include the parent branch's unmerged commits in the diff, making the PR diff noisy and review harder.

Stacked PRs are a deliberate choice: each reviewer sees only the focused change for that layer of the stack.

---

## Post-Merge Checklist

After all 7 PRs are merged into `main` in order:

```bash
# 1. Pull the updated main
git checkout main && git pull origin main

# 2. Reinstall (picks up all new modules)
pip install -e ".[dev]"

# 3. Run smoke tests — must be 5/5 green
pytest
# Expected: 5 passed in ~0.2s

# 4. Confirm the CLI launches
python -m claude_codebase_agent
# Expected: prompts for target repo path, then shows the 3-option menu

# 5. Sanity-check the entry point script
claude-codebase-agent
# Expected: same as above
```

All steps must pass before the release is considered complete.
