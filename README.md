# claude-codebase-agent

A standalone Python tool built on the **Claude Agent SDK** that explores unfamiliar codebases and implements features from high-level natural-language requirements. Point it at any Git repository, ask a question or describe a feature, and the agent handles discovery, planning, implementation, and verification — with a mandatory human checkpoint before any file is modified.

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

You'll be prompted for a target repo path, then shown a 3-option menu.

---

## Three Modes

### 1) Ask a question

Single-shot read-only lookup. The agent Greps for the most specific anchor first, reads only the files it needs, and returns precise file + line references.

```
choice> 1
question> where is the JWT token validation logic?
```

### 2) Adaptive investigation

Open-ended goal explored across four passes: map structure → identify high-impact subsystems → build a numbered plan → execute adaptively.

```
choice> 2
investigation goal> understand how background job processing works
```

Returns four structured sections: **Structure Map**, **High-Impact Areas**, **Plan**, **Report**.

### 3) Implement a feature

Full plan → confirm → write → verify pipeline. The agent investigates the codebase, produces a concrete plan, **pauses for your approval**, then implements and runs tests until they pass.

```
choice> 3
feature requirement> add a pet weight field (kg, decimal) to the pet entity,
                     owner list view, and add/edit form
```

---

## Worked Example

```bash
git clone https://github.com/spring-projects/spring-petclinic /tmp/petclinic
python -m claude_codebase_agent
```

```
Target repo path> /tmp/petclinic

choice> 1
question> where is the owner service?
→ src/main/java/.../owner/OwnerRepository.java:34

choice> 3
feature requirement> add a pet weight field (kg, decimal) to the pet entity and owner's pet list view
Verify command [leave blank to auto-detect]>
# auto-detected: mvn -q test

STEP 1/4  Discovering the codebase (read-only) …
STEP 2/4  Building implementation plan …

[plan printed — review it]

Proceed with implementation? [y/N] y

STEP 4/4  Implementing …

DIFF SUMMARY
 src/main/java/.../Pet.java            |  8 +++
 src/main/resources/db/h2/schema.sql   |  1 +
 src/main/resources/templates/pets/... |  4 ++
 3 files changed, 13 insertions(+)

To undo everything: git -C /tmp/petclinic checkout . && git clean -fd
```

---

## Safety

- Always target a **git repo** so changes are revertible.
- Review the plan carefully before typing `y` at the confirm prompt.
- Inspect the diff after: `git -C <target_dir> diff`
- Undo everything: `git -C <target_dir> checkout . && git clean -fd`

The builder agent is constrained by its system prompt never to modify files outside the `target_dir` you supply.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | Anthropic API key — set in `.env` |
| `VERIFY_CMD` | No | Override the auto-detected build/test command |

See [docs/configuration.md](docs/configuration.md) for the full list of options.

---

## Documentation

| Document | Description |
|---|---|
| [docs/running.md](docs/running.md) | Setup, starting the agent, running tests, troubleshooting |
| [docs/user-guide.md](docs/user-guide.md) | Mode-by-mode walkthrough with example sessions and tips |
| [docs/architecture.md](docs/architecture.md) | Module responsibilities, data flow, design decisions |
| [docs/api-reference.md](docs/api-reference.md) | Full API reference for programmatic use |
| [docs/configuration.md](docs/configuration.md) | Env vars, verify command detection, MCP setup, SDK options |

---

## Running Tests

```bash
pytest
# 5 smoke tests — import-only, no API calls, ~0.2s
```

---

## Optional: MCP Server Integration

```bash
cp .mcp.json.example .mcp.json
# Edit .mcp.json to add GitHub, Jira, or other MCP servers
```

See [docs/configuration.md](docs/configuration.md#mcp-server-integration-optional) for details.
