---
name: dew
description: dew workflow orchestrator. Manages the full six-stage process (Discover → Design → Demonstrate → Develop → Document → Debrief) and the fast three-stage process (Plan → Build → Verify), tracking state, loading artifact context, invoking stage skills, and maintaining git history at stage boundaries.
---

# dew Workflow Orchestrator

**dew** is a structured engineering process for building software with rigor and measurability. Every stage is an interactive conversation — this orchestrator loads context and hands off to the appropriate stage skill, which runs directly in the current session.

The work splits cleanly in two. **Mechanics** — state transitions, artifact-existence checks, cycle archiving, git commits, the branch guard — are executed by the plugin's `scripts/dew.py`; never perform them by hand or edit state files directly. **Judgment** — asking the user questions, loading and presenting context, synthesizing pause snapshots, invoking stage skills — is yours.

*Full workflow (6 stages):*

| Stage | Skill | Artifact |
|-------|-------|----------|
| **Discover** | `/dew-discover` | `.dew/docs/01-discover.md` |
| **Design** | `/dew-design` | `.dew/docs/02-design.md` |
| **Demonstrate** | `/dew-demonstrate` | `.dew/design-verification/DESIGN_VERIFICATION.md` |
| **Develop** | `/dew-develop` | production code in repo |
| **Document** | `/dew-document` | `docs/` Hugo site |
| **Debrief** | `/dew-debrief` | `.dew/docs/06-debrief.md` |

*Fast workflow (3 stages):*

| Stage | Skill | Artifact |
|-------|-------|----------|
| **Plan** | `/dew-fast` | `.dew/docs/fast-plan.md` |
| **Build** | `/dew-fast` | production code in repo |
| **Verify** | `/dew-fast` | `.dew/docs/fast-debrief.md` |

**Commands:**
- `/dew` — continue from the current active stage
- `/dew new` — start a new dew project
- `/dew done` — complete the current stage: verify artifact, advance, commit, prompt for `/clear`
- `/dew pause` — snapshot conversation context to `.dew/context.md`, commit, safe to quit
- `/dew resume` — restore context from `.dew/context.md` and re-enter the active stage
- `/dew status` — show current state without entering a stage
- `/dew back <stage>` — backtrack to an earlier stage
- `/dew-<stage-name>` — jump to a named stage (dew-discover / dew-design / dew-demonstrate / dew-develop / dew-document / dew-debrief / dew-fast)

**Shared conduct**: All dew skills follow the rules in `${CLAUDE_PLUGIN_ROOT}/skills/shared/conduct.md`. In particular: when showing any command to the user, always use the short form without the `dew:` namespace prefix (e.g., `/dew done`, never `/dew:dew done`) — the prefix is an internal routing detail.

---

## The Mechanics Script

All mechanical operations go through `scripts/dew.py` at this plugin's root, run with `python3` from the project's working directory. Locate it once per session: use `"$CLAUDE_PLUGIN_ROOT/scripts/dew.py"` if that variable resolves; otherwise derive the plugin root from this skill file's own path (this file lives at `<plugin-root>/skills/dew/SKILL.md`).

| Command | Does |
|---------|------|
| `init --name <slug> --workflow full\|fast --type new-project\|major-feature\|revisit-fix --branch-mode worktree\|branch\|stay` | archive any previous cycle, set up branch/worktree, create fresh state, initial commit |
| `enter` | mark the active stage entered (status, visits, dates); prints a JSON brief |
| `done` | verify the stage artifact exists, complete + advance the stage, commit |
| `back <stage> --reason "..."` | backtrack: record reason, mark intermediate stages needs-revisit, commit |
| `jump <stage>` | set the active stage without a backtrack reason (forward moves, revisits) |
| `pause` | commit an already-written `.dew/context.md` snapshot |
| `consume-context` | delete the snapshot after resuming (deletion is committed at the next boundary) |
| `status` | human-readable status report |
| `state` | machine-readable state + brief as JSON |

Contract notes:
- `.dew/state.json` is canonical and script-owned; `.dew/state.md` is a rendered view for humans and git diffs. **Never edit either by hand.**
- Structured output arrives on stdout; progress notes (commits made/skipped) on stderr. Exit codes: 2 usage, 3 precondition failed, 4 git refused/failed.
- The script detects commit mode itself (not a git repo, or `.dew` gitignored → commits silently skipped) and enforces the branch guard: no dew commits on the default branch unless the user chose `--branch-mode stay` (or you pass `--allow-default-branch` after asking them).
- When the script refuses something, relay its message and resolve with the user — do not work around it by hand.

## Current Save State

!`cat .dew/state.md 2>/dev/null || echo "dew_STATUS: none — no active project found"`

## Current Repository Status

!`git status --short 2>/dev/null || echo "(not a git repository — commits will be skipped)"`

---

## Instructions

Arguments provided: `$ARGUMENTS`

### Step 1 — Determine Action

| Condition | Action |
|-----------|--------|
| State is "none" **or** ARGUMENTS contains `new` | → **Initialize** (Step 2) |
| ARGUMENTS is `done` | → **Complete** the current stage (Step 4) |
| ARGUMENTS is `pause` | → **Pause Protocol** |
| ARGUMENTS is `resume` | → **Resume Protocol** |
| ARGUMENTS is `status` | → run `status`, show its output verbatim, and stop |
| ARGUMENTS starts with `back` | → **Backtrack Protocol** |
| ARGUMENTS matches a stage name | → run `jump <stage>`, then enter it (Step 3, skipping `enter`) |
| State exists, ARGUMENTS is empty | → **Enter** the current active stage (Step 3) |

---

### Step 2 — Initialize (new project only)

1. Ask the user (their answers become the script's flags):
   - "What are we building? Give it a short slug-friendly name (e.g., `retina-pipeline`, `auth-system`)."
   - "Is this a **new project**, a **major new feature** in an existing codebase, or a **revisit/fix** of something in progress?"
   - "**Full workflow** (6 stages: Discover → Design → Demonstrate → Develop → Document → Debrief) or **Fast workflow** (3 stages: Plan → Build → Verify)? The fast workflow suits well-scoped tasks where the requirements and approach are fairly clear. The full workflow suits larger or more complex projects where thorough exploration and empirical validation are worth the investment."
   - "Branch handling: a **worktree** at `.worktrees/<name>` (recommended for larger cycles), a **feature branch** `dew/<name>` in this checkout, or **stay** on the current branch?"

2. Run `init` with those flags. Then:
   - **worktree**: the script creates it and prints restart instructions — relay them to the user verbatim and stop; initialization completes inside the worktree session.
   - **branch / stay**: on success, proceed to Step 3.
   - If the script refuses (e.g., default-branch guard), relay its message and resolve with the user.

---

### Step 3 — Enter Stage

1. Run `enter`. Its JSON brief gives you the active stage, its expected artifact, whether this is a revisit, any `needs_revisit` stages, and recent backtracks.

2. **Load conversational context** — read and present the prerequisite artifacts for the stage:

   *Full workflow:*
   - **discover**: No prior artifacts. If a revisit, read `.dew/docs/01-discover.md` and summarize what changed.
   - **design**: Read `.dew/docs/01-discover.md` and present its contents.
   - **demonstrate**: Read `.dew/docs/02-design.md` and present its contents.
   - **develop**: Read `.dew/docs/02-design.md` and `.dew/design-verification/DESIGN_VERIFICATION.md` and present both.
   - **document**: Read `.dew/docs/01-discover.md`, `.dew/docs/02-design.md`, and `.dew/design-verification/DESIGN_VERIFICATION.md` and present all three.
   - **debrief**: Read `.dew/state.md` (full contents including backtrack log) and present it.

   *Fast workflow:*
   - **plan**: No prior artifacts. If a revisit, read `.dew/docs/fast-plan.md` and summarize what changed.
   - **build**: Read `.dew/docs/fast-plan.md` and present its contents.
   - **verify**: Read `.dew/docs/fast-plan.md` and present its contents.

3. Also attempt to surface a brief project graph summary, following the availability probe in `${CLAUDE_PLUGIN_ROOT}/skills/shared/dag-integration.md`: probe, then `dag_load(".dew/graph.json")` followed by `dag_status`. On success, include the summary (what's done, what's pending across stage namespaces). On tool-unavailable failure, silently skip.

4. Briefly tell the user which stage we are entering and what context was loaded. If the brief marked this a revisit or listed backtracks, summarize why we are back here so the stage skill has that context.

5. Invoke the stage skill via the Skill tool:
   - *Full*: discover → `Skill("dew:dew-discover")` · design → `Skill("dew:dew-design")` · demonstrate → `Skill("dew:dew-demonstrate")` · develop → `Skill("dew:dew-develop")` · document → `Skill("dew:dew-document")` · debrief → `Skill("dew:dew-debrief")`
   - *Fast*: plan / build / verify → `Skill("dew:dew-fast")`

---

### Step 4 — Complete Stage (triggered by `/dew done`)

1. Run `done`.

2. **If it fails with "stage artifact not ready"** (exit 3): the stage skill has not written its artifact — writing it is the stage skill's job, at the stage's conclusion. Tell the user and offer to return to the stage conversation to finish it. Only if the full stage conversation happened in the current session and its conclusions are fully present in context may you write the artifact now — say explicitly that you are doing so — then re-run `done`.

3. **On success**, relay the result to the user:
   - What artifact was completed and what stage is next (from the script's JSON)
   - Flag anything from the conversation that might warrant backtracking before proceeding
   - Then say: **"Run `/clear` and then `/dew` to begin the next stage with a clean context."**

---

### Backtrack Protocol (`/dew back <stage>`)

1. Ask for the reason if not provided: "What did you find that requires going back to [stage]?"
2. Run `back <stage> --reason "<the reason>"`.
3. Enter the stage (Step 3, skipping `enter` — `back` already entered it).

---

### Pause Protocol (`/dew pause`)

1. **Synthesize the conversation** into `.dew/context.md` — this is judgment work and the one file you write here:

```markdown
# dew Context Snapshot

**Stage**: <active stage>
**Date**: <ISO date>

## Where We Are
<Which phase/step within the stage we reached. Be specific: e.g., "Phase 2 of Design — we agreed on the module layout and are mid-discussion on the data structure for the event queue.">

## Decisions Made
<Bulleted list of every decision or agreement reached during this session. Each item should be concrete enough to act on without re-discussion.>

## Open Questions
<Bulleted list of unresolved questions, disagreements, or threads that were in progress when we paused.>

## Next Steps
<What should happen when work resumes — the immediate next action or question to address.>
```

2. Run `pause` (it refuses if the snapshot is missing — write it first).
3. Tell the user: "Context saved to `.dew/context.md`. It's safe to quit. Run `/dew resume` in a new session to pick up where we left off."

---

### Resume Protocol (`/dew resume`)

1. **Check for `.dew/context.md`**. If it does not exist, tell the user: "No paused context found. Run `/dew` to enter the current stage fresh." Then stop.
2. **Read `.dew/context.md`** and present its contents as a recap: "Here's where we left off:" followed by the snapshot.
3. **Reload the graph**, following the shared probe protocol (`dag_load`, then `dag_save(".dew/graph.json", auto_save=true)` to re-enable auto-save, then `dag_status`). On success include a brief graph summary in the recap; on tool-unavailable failure skip silently.
4. **Load the normal stage context** (Step 3, including `enter`).
5. **Invoke the stage skill**, prepending both the context snapshot and the graph status so the skill resumes with full awareness of prior progress.
6. Run `consume-context` — the snapshot is now live in the conversation; the script deletes it and the deletion is committed at the next stage boundary.
