# claude-codebase-agent

A standalone Python tool built on the **Claude Agent SDK** that explores unfamiliar codebases and implements features from high-level natural-language requirements. Point it at any Git repository, ask a question or describe a feature, and the agent handles discovery, planning, implementation, and verification — with a human checkpoint before any file is modified.

---

## Prerequisites

- **Python 3.12+**
- **direnv** (`brew install direnv` on macOS; add `eval "$(direnv hook zsh)"` to `~/.zshrc`)
- **Anthropic API key** — get one at [console.anthropic.com](https://console.anthropic.com)

---

## Setup

```bash
# 1. Clone
git clone https://github.com/llevintza/claude-codebase-agent.git
cd claude-codebase-agent

# 2. Activate the venv (direnv creates it automatically)
direnv allow

# 3. Install the package and dev dependencies
pip install -e ".[dev]"

# 4. Configure your API key
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

---

## Quick Start

```bash
python -m claude_codebase_agent
# or, after install:
claude-codebase-agent
```

You'll be prompted for a target repo path (absolute or relative). The agent then shows a 3-option menu.

---

## Three Modes

### 1) Ask a question

Single-shot read-only question answered with Grep-first discovery.

```
Target repo path> /path/to/spring-petclinic

Menu:
  1) Ask a question about the codebase
choice> 1
question> where is the owner service?
```

The agent Greps for `OwnerService`, follows imports, and returns file + line references without reading the whole codebase.

### 2) Adaptive investigation

Open-ended goal explored in 4 steps: map structure → identify high-impact areas → build numbered plan → execute adaptively.

```
choice> 2
investigation goal> understand how the pet clinic stores and retrieves visit history
```

Returns four structured sections: **Structure Map**, **High-Impact Areas**, **Plan**, **Report** (with Findings, Open Questions, Suggested Next Actions).

### 3) Implement a feature

Full plan → confirm → write → verify pipeline.

```
choice> 3
feature requirement (high-level)> add a pet weight field to the owner's pet list view
Verify command [leave blank to auto-detect]>
```

The agent:
1. Discovers the codebase (read-only)
2. Produces a concrete implementation plan (files, functions, tests, verify command)
3. **Pauses and asks for your approval** before making any changes
4. Implements the plan and runs the verify command until it passes
5. Prints `git diff --stat` and an undo hint

---

## Worked Example

```bash
# Clone a real Java project to use as the target
git clone https://github.com/spring-projects/spring-petclinic /tmp/petclinic

# Run the agent
python -m claude_codebase_agent
```

```
Target repo path> /tmp/petclinic

choice> 1
question> where is the owner service?
# → src/main/java/org/springframework/samples/petclinic/owner/OwnerRepository.java:34

choice> 3
feature requirement> add a pet weight field (kg, decimal) to the pet entity and owner's pet list view
Verify command [leave blank to auto-detect]>
# Agent auto-detects pom.xml → runs: mvn -q test

STEP 1/4  Discovering the codebase (read-only) …
STEP 2/4  Building implementation plan …

[plan printed here]

Proceed with implementation? [y/N] y

STEP 4/4  Implementing …
[agent edits files and runs mvn -q test]

DIFF SUMMARY
 src/main/java/.../Pet.java            |  8 +++
 src/main/resources/db/h2/schema.sql   |  1 +
 src/main/resources/templates/pets/... |  4 ++
 3 files changed, 13 insertions(+)

To undo everything: git -C /tmp/petclinic checkout . && git clean -fd
```

---

## Safety

- Always use a **git repository** as the target so changes are revertible.
- Review the implementation plan before approving at the `[y/N]` prompt.
- After the agent finishes, inspect the diff: `git -C <target_dir> diff`
- To revert all changes: `git -C <target_dir> checkout . && git clean -fd`

---

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API authentication |
| `VERIFY_CMD` | No | Override the auto-detected build/test command |

---

## Optional: MCP Server Integration

Copy `.mcp.json.example` to `.mcp.json` and fill in tokens to give the agent access to additional context servers (e.g., GitHub, Jira, Confluence):

```bash
cp .mcp.json.example .mcp.json
# Edit .mcp.json and add your server configs and tokens
```

---

## Running Tests

```bash
pytest
# All smoke tests verify imports and structure only — no API calls, no network.
```
