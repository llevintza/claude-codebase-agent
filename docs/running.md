# Running the Agent

## First-Time Setup

```bash
# 1. Clone the repo
git clone https://github.com/llevintza/claude-codebase-agent.git
cd claude-codebase-agent

# 2. Allow direnv to create and activate the virtualenv
direnv allow

# 3. Install the package and dev dependencies
pip install -e ".[dev]"

# 4. Add your Anthropic API key
cp .env.example .env
# Open .env and set: ANTHROPIC_API_KEY=sk-ant-...
```

After setup, the venv activates automatically whenever you `cd` into the project directory (requires direnv to be hooked into your shell).

---

## Starting the Agent

```bash
# Option A — as a Python module
python -m claude_codebase_agent

# Option B — via the installed console script (after pip install -e .)
claude-codebase-agent
```

Both are equivalent. You'll see:

```
claude-codebase-agent
Modes: explore an unfamiliar repo, or build a feature in it.

Target repo path (absolute or relative)>
```

---

## Providing a Target Repo

Enter the path to any local repository when prompted. Absolute and relative paths work; `~` is expanded.

```
Target repo path> /Users/me/projects/my-api
Target repo path> ~/projects/my-api
Target repo path> ../my-api
```

If the path is not a git repo, you'll see a warning — the tool still works, but changes from the builder mode won't be easily revertible.

```
  Warning: /path/to/dir does not appear to be a git repo.
  Changes will not be easily revertible.
```

---

## Menu Options

Once a target repo is set, you see this menu on every loop:

```
Menu:
  1) Ask a question about the codebase
  2) Adaptive investigation (open-ended goal)
  3) Implement a feature (plan → confirm → write → verify)
  q) Quit
choice>
```

---

## Running Tests

```bash
# All smoke tests (import-only, no API calls, ~0.2s)
pytest

# Verbose output
pytest -v

# Single test
pytest tests/test_smoke.py::test_session_exports
```

---

## Updating Dependencies

If `pyproject.toml` changes (new dependency added):

```bash
pip install -e ".[dev]"
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'claude_codebase_agent'`**
The package isn't installed in the active venv. Run `pip install -e ".[dev]"`.

**`WARNING: ANTHROPIC_API_KEY is not set`**
Copy `.env.example` to `.env` and fill in your key.

**`Directory not found: ...`**
The path you entered doesn't exist or isn't accessible. Enter an absolute path.

**`CLINotFoundError` or similar SDK error**
The Claude CLI binary isn't found. The `claude-agent-sdk` installs a CLI wrapper — ensure the venv is active and `pip install -e ".[dev]"` completed without errors.

**Agent runs but produces no output**
Check that `ANTHROPIC_API_KEY` is valid and has credits. Try `python -c "import anthropic; print(anthropic.__version__)"` to confirm the SDK is installed.
