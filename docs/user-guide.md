# User Guide

## Choosing the Right Mode

| You want to… | Use mode |
|---|---|
| Find where a specific function, class, or config is defined | **1 — Ask a question** |
| Understand how a subsystem works before touching it | **2 — Adaptive investigation** |
| Add, change, or fix something in the codebase | **3 — Implement a feature** |

---

## Mode 1 — Ask a Question

Best for targeted, specific lookups. The agent Greps for the most relevant symbol first, then reads only the files it needs.

**Good questions:**
- "Where is the database connection pool configured?"
- "What does the `UserAuthMiddleware` class do?"
- "Which files handle the `/api/orders` route?"
- "Where is `MAX_RETRY_COUNT` defined and what's its value?"

**Less suitable for:**
- Open-ended "how does X work" questions — use Mode 2 instead
- Multi-file cross-cutting concerns — use Mode 2 instead

### Example session

```
choice> 1
question> where is JWT token validation handled?

[agent output]
JWT validation is in src/auth/middleware.py:34-78 (verify_token function).
It calls PyJWT's decode() and raises AuthError on failure. The middleware
is registered in src/app.py:21 via app.use(verify_token).
```

---

## Mode 2 — Adaptive Investigation

Best for open-ended goals where you don't know which files are relevant. The agent runs four passes: map → focus → plan → investigate.

**Good goals:**
- "Understand how background job processing works"
- "Map the data flow from an HTTP request to the database"
- "Find all places where external API calls are made and how errors are handled"
- "Understand the test architecture and coverage strategy"

### Example session

```
choice> 2
investigation goal> understand how the email notification system works

[Turn 1 — structure map]
Top-level: src/ (app code), workers/ (background jobs), templates/ (Jinja2 email templates)...

[Turn 2 — high-impact areas]
1. workers/email_worker.py — main dispatcher for all outbound email
2. src/notifications/events.py — event types that trigger notifications
...

[Turn 3 — plan]
1. Grep for EmailWorker to find the class and its send() method
2. Grep for "emit(" to find all notification trigger sites
...

[Turn 4 — report]
## Findings
- Email sending goes through workers/email_worker.py:EmailWorker.send()
- Triggered via events in src/notifications/events.py using an in-process queue
...

## Open Questions
- Is there a dead-letter queue for failed sends?

## Suggested Next Actions
- Check workers/email_worker.py:retry_policy for retry behaviour
```

### Reading the output sections

After the agent finishes, the CLI prints the four sections in order:

```
── Structure Map ──────────────────────────
[concise repo layout]

── High-Impact Areas ──────────────────────
[3-5 subsystems relevant to your goal]

── Plan ───────────────────────────────────
[numbered subtasks the agent will run]

── Report ─────────────────────────────────
[findings, open questions, suggested actions]
```

---

## Mode 3 — Implement a Feature

A four-step workflow with a mandatory human checkpoint before any file is touched.

### Step-by-step

**1. Enter your requirement**

Be as specific or high-level as you like — the agent will investigate before planning.

```
feature requirement (high-level)> add a pet weight field (kg, decimal) to the
pet entity, the owner's pet list view, and the add/edit pet form
```

**2. Optionally specify a verify command**

Leave blank to auto-detect from your repo's build files.

```
Verify command [leave blank to auto-detect]>
  (auto-detected: mvn -q test)
```

Or override:

```
Verify command [leave blank to auto-detect]> mvn -q test -pl core-module
```

**3. Wait for the investigation and plan (Steps 1 and 2)**

The agent explores the codebase (read-only) and produces a concrete plan:

```
────────────────────────────────────────────────────────────
STEP 1/4  Discovering the codebase (read-only) …
────────────────────────────────────────────────────────────
[agent maps and investigates]

────────────────────────────────────────────────────────────
STEP 2/4  Building implementation plan …
────────────────────────────────────────────────────────────

IMPLEMENTATION PLAN
===================
Files to modify:
  1. src/main/java/.../Pet.java
     - Add field: private BigDecimal weightKg
     - Add getter/setter
     - Add @Column annotation

  2. src/main/resources/db/h2/schema.sql
     - Add column: weight_kg DECIMAL(5,2)

  3. src/main/resources/templates/owners/ownerDetails.html
     - Add weight column to pet table

  ...

Verify command: mvn -q test
```

**4. Review and approve (Step 3)**

```
────────────────────────────────────────────────────────────
STEP 3/4  Review the plan above.
────────────────────────────────────────────────────────────
Proceed with implementation? [y/N]
```

Type `y` to proceed. Anything else (`n`, Enter, Ctrl-C) aborts — no files are changed.

**5. Implementation and verification (Step 4)**

```
────────────────────────────────────────────────────────────
STEP 4/4  Implementing …
────────────────────────────────────────────────────────────
[agent edits files and runs: mvn -q test]
[if tests fail, agent diagnoses and iterates]
```

**6. Review the diff**

```
────────────────────────────────────────────────────────────
DIFF SUMMARY
────────────────────────────────────────────────────────────
 src/main/java/.../Pet.java                |  12 +++
 src/main/resources/db/h2/schema.sql       |   1 +
 src/main/resources/templates/.../html     |   6 ++
 3 files changed, 19 insertions(+)

Review changes above. Run 'git diff' in the target repo for the full patch.
To undo everything: git -C /path/to/petclinic checkout . && git clean -fd
```

### If you want to abort after approving

The implementation step cannot be interrupted mid-way cleanly. Once the agent is writing files, let it finish, then review the diff and revert if needed:

```bash
# Revert all changes in the target repo
git -C /path/to/target checkout .
git -C /path/to/target clean -fd
```

### Writing effective requirements

| Less effective | More effective |
|---|---|
| "add weight to pets" | "add a `weight_kg` field (decimal, 2dp) to the Pet entity, the database schema, the owner's pet list view, and the add/edit pet form" |
| "fix the login bug" | "fix the login flow so that users with MFA enabled are redirected to the MFA step instead of getting a 403" |
| "improve performance" | "add a database index on the `orders.created_at` column to speed up the dashboard query in `OrderRepository.findRecentOrders`" |

The agent will investigate before planning regardless, but specific requirements produce more accurate plans with less ambiguity at the confirm step.

---

## Tips

**Check the plan carefully before approving.** The plan lists exact file paths and function names — verify they match what you expect before typing `y`.

**Use Mode 2 before Mode 3 for large features.** Running an adaptive investigation first gives you a clear picture of the codebase and makes it easier to write a precise requirement for Mode 3.

**Set `VERIFY_CMD` in `.env` for a project you use repeatedly.** This skips the verify command prompt and auto-detection on every run.

**The agent never touches this tool's own source files.** `BUILDER_PROMPT` explicitly forbids editing files outside the target directory. If you're worried, inspect `git status` in this project's directory after a build run — it will be clean.

**Undo is always `git checkout . && git clean -fd` in the target repo.** Do this in the target repo, not in this project's directory.
