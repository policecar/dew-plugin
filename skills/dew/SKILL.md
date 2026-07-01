---
name: dew
description: dew workflow orchestrator. Manages the full six-stage process (Discover → Design → Demonstrate → Develop → Document → Debrief) and the fast three-stage process (Plan → Build → Verify), tracking state, loading artifact context, invoking stage skills, and maintaining git history at stage boundaries.
---

# dew Workflow Orchestrator

**dew** is a structured engineering process for building software with rigor and measurability. Every stage is an interactive conversation — this orchestrator loads context and hands off to the appropriate stage skill, which runs directly in the current session.

*Full workflow (6 stages):*

| Stage | Plugin | Skill | Artifact |
|-------|--------|-------|----------|
| **Discover** | dew | `/dew-discover` | `.dew/docs/01-discover.md` |
| **Design** | dew | `/dew-design` | `.dew/docs/02-design.md` |
| **Demonstrate** | dew | `/dew-demonstrate` | `.dew/design-verification/DESIGN_VERIFICATION.md` |
| **Develop** | dew | `/dew-develop` | production code in repo |
| **Document** | dew | `/dew-document` | `docs/` Hugo site |
| **Debrief** | dew | `/dew-debrief` | `.dew/docs/06-debrief.md` |

*Fast workflow (3 stages):*

| Stage | Plugin | Skill | Artifact |
|-------|--------|-------|----------|
| **Plan** | dew | `/dew-fast` | `.dew/docs/fast-plan.md` |
| **Build** | dew | `/dew-fast` | production code in repo |
| **Verify** | dew | `/dew-fast` | `.dew/docs/fast-debrief.md` |

**Commands:**
- `/dew` — continue from the current active stage
- `/dew new` — start a new dew project
- `/dew done` — complete the current stage: write artifact, update state, commit, then prompt for `/clear`
- `/dew pause` — snapshot conversation context to `.dew/context.md`, commit, safe to quit
- `/dew resume` — restore context from `.dew/context.md` and re-enter the active stage
- `/dew status` — show current state without entering a stage
- `/dew back <stage>` — backtrack to an earlier stage
- `/dew-<stage-name>` — jump to a named stage (dew-discover / dew-design / dew-demonstrate / dew-develop / dew-document / dew-debrief / dew-fast)

**Shared conduct**: All dew skills follow the rules in `${CLAUDE_PLUGIN_ROOT}/skills/shared/conduct.md`. In particular: when showing any command to the user, always use the short form without the `dew:` namespace prefix (e.g., `/dew done`, never `/dew:dew done`) — the prefix is an internal routing detail.

---

## Current Save State

!`cat .dew/state.md 2>/dev/null || echo "dew_STATUS: none — no active project found"`

## Current Repository Status

!`git status --short 2>/dev/null || echo "(not a git repository — commits will be skipped)"`

## Commit Mode

!`grep -qE '^(\*\*/)?/?\.dew(/\*{0,2})?/?$' .gitignore 2>/dev/null && echo "COMMIT_MODE: skip — .dew is gitignored (artifacts are ephemeral)" || git rev-parse --git-dir >/dev/null 2>&1 && echo "COMMIT_MODE: enabled — .dew artifacts will be committed at stage boundaries" || echo "COMMIT_MODE: skip — not a git repository"`

## Worktree Policy

dew work should not land directly on the repository's default branch. This policy is enforced during Initialize (Step 2), where you offer the user one of three options:

- **Worktree** (recommended for larger cycles): create it at `<repo>/.worktrees/<project-name>` on a new branch `dew/<project-name>` via `git worktree add .worktrees/<project-name> -b dew/<project-name>`. **Caveat you must state explicitly**: `.dew/` state lives inside the checkout it was created in, so the user must run Claude Code from within the worktree directory for `/dew` to find the project state. After creating the worktree, tell the user to restart Claude inside it and re-run `/dew new`, then stop.
- **Feature branch** in the current checkout: `git checkout -b dew/<project-name>`, then continue initialization here.
- **Stay on the current branch**: only if the user explicitly chooses this. Record the choice in the state file's Notes.

Before any dew commit, check the current branch. If it is the default branch (main/master) and the user has not explicitly opted to commit there, ask before committing.

---

## Instructions

Arguments provided: `$ARGUMENTS`

### Step 1 — Determine Action

| Condition | Action |
|-----------|--------|
| State is "none" **or** ARGUMENTS contains `new` | → **Initialize** a new project (Step 2) |
| ARGUMENTS is `done` | → **Complete** the current stage (Step 4) |
| ARGUMENTS is `pause` | → **Pause** the current stage (Pause Protocol) |
| ARGUMENTS is `resume` | → **Resume** from a paused stage (Resume Protocol) |
| ARGUMENTS is `status` | → **Report** current state and stop |
| ARGUMENTS starts with `back` | → **Backtrack** to the specified stage |
| ARGUMENTS matches a stage name | → **Jump** to that stage |
| State exists, ARGUMENTS is empty | → **Enter** the current active stage (Step 3) |

---

### Step 2 — Initialize (new project only)

1. Ask the user:
   - "What are we building? Give it a short slug-friendly name (e.g., `retina-pipeline`, `auth-system`)."
   - "Is this a **new project**, a **major new feature** in an existing codebase, or a **revisit/fix** of something in progress?"
   - "**Full workflow** (6 stages: Discover → Design → Demonstrate → Develop → Document → Debrief) or **Fast workflow** (3 stages: Plan → Build → Verify)? The fast workflow suits well-scoped tasks where the requirements and approach are fairly clear. The full workflow suits larger or more complex projects where thorough exploration and empirical validation are worth the investment."

2. **Branch / worktree setup** (see Worktree Policy above): offer worktree, feature branch, or stay-put. Act on the user's choice. If a worktree was created, instruct the user to restart Claude inside it and stop here — the remaining steps run in the worktree session.

3. **Archive previous cycle** (if `.dew/state.md` exists):
   - Read `.dew/state.md` to get the previous project name (from the `Project:` field).
   - Generate archive name: `YYMMDD-<previous-project-name>` (e.g., `260511-retina-pipeline`).
   - Move current cycle files into the archive: `mkdir -p .dew/YYMMDD-<name> && mv .dew/docs .dew/state.md .dew/context.md .dew/graph.json .dew/design-verification .dew/YYMMDD-<name>/ 2>/dev/null`
   - This preserves prior work in `.dew/` while starting fresh.

4. Run `mkdir -p .dew/docs` to create the artifact directory.

5. Write `.dew/state.md` using the appropriate State File Format at the bottom of this file (full or fast).

6. **Commit** (if COMMIT_MODE is enabled):
   - Message: `dew(init): begin dew for <project-name>`

7. Set active stage to `discover` (full workflow) or `plan` (fast workflow) and enter the stage (Step 3).

---

### Step 3 — Enter Stage

Read the `Active Stage` from the save state. Load context for the stage (read any prerequisite artifacts). Then invoke the appropriate stage skill using the Skill tool.

**If entering via an explicit stage argument (jump)**: when the requested stage differs from the state file's `Active Stage`, update the state file first — set `Active Stage` to the target, set its Stage Log status to `in-progress`, and increment its visit count — so state matches reality. (To return to an *earlier* stage, prefer the Backtrack Protocol so the reason is recorded.)

**Context loading per stage:**

*Full workflow:*
- **discover**: No prior artifacts. If revisit, read `.dew/docs/01-discover.md` and summarize what changed.
- **design**: Read `.dew/docs/01-discover.md` and present its contents to establish context before invoking the skill.
- **demonstrate**: Read `.dew/docs/02-design.md` and present its contents before invoking the skill.
- **develop**: Read `.dew/docs/02-design.md` and `.dew/design-verification/DESIGN_VERIFICATION.md` and present both before invoking the skill.
- **document**: Read `.dew/docs/01-discover.md`, `.dew/docs/02-design.md`, and `.dew/design-verification/DESIGN_VERIFICATION.md` and present all three before invoking the skill.
- **debrief**: Read `.dew/state.md` (full contents including backtrack log) and present it before invoking the skill.

*Fast workflow:*
- **plan**: No prior artifacts. If revisit, read `.dew/docs/fast-plan.md` and summarize what changed.
- **build**: Read `.dew/docs/fast-plan.md` and present its contents before invoking the skill.
- **verify**: Read `.dew/docs/fast-plan.md` and present its contents before invoking the skill.

Also attempt to surface a brief project graph summary after loading artifacts, following the availability probe in `${CLAUDE_PLUGIN_ROOT}/skills/shared/dag-integration.md`: probe, then `dag_load(".dew/graph.json")` followed by `dag_status`. On success, include the summary (what's done, what's pending across all stage namespaces) so the user and the stage skill have an instant orientation on overall progress. On tool-unavailable failure, silently skip the graph summary.

**After loading context**, briefly tell the user:
- Which stage we are entering
- What context was loaded
- That you are now invoking the stage skill

Then invoke the stage skill via the Skill tool:

*Full workflow:*
- discover → `Skill("dew:dew-discover")`
- design → `Skill("dew:dew-design")`
- demonstrate → `Skill("dew:dew-demonstrate")`
- develop → `Skill("dew:dew-develop")`
- document → `Skill("dew:dew-document")`
- debrief → `Skill("dew:dew-debrief")`

*Fast workflow:*
- plan → `Skill("dew:dew-fast")`
- build → `Skill("dew:dew-fast")`
- verify → `Skill("dew:dew-fast")`

**If this is a revisit** (backtrack log is non-empty for this stage), prepend a brief summary of why we are back here before invoking the skill, so the stage skill has the backtrack context.

---

### Step 4 — Complete Stage (triggered by `/dew done`)

When the user invokes `/dew done`:

1. **Verify the stage artifact exists** — the stage skill writes its own artifact at the stage's conclusion; `/dew done` does not synthesize one:

   *Full workflow:*
   - discover → `.dew/docs/01-discover.md`
   - design → `.dew/docs/02-design.md`
   - demonstrate → `.dew/design-verification/DESIGN_VERIFICATION.md` (plus test programs written during the stage)
   - develop → no artifact file; the code in the repo is the artifact
   - document → the Hugo site files under `docs/`
   - debrief → `.dew/docs/06-debrief.md`

   *Fast workflow:*
   - plan → `.dew/docs/fast-plan.md`
   - build → no artifact file; the code in the repo is the artifact
   - verify → `.dew/docs/fast-debrief.md`

   If the expected artifact file is missing or clearly incomplete, do **not** reconstruct it from memory — tell the user the stage skill has not written its artifact yet, and offer to return to the stage conversation to finish it. Only if the stage conversation happened in the current session and its conclusions are fully present in context may you write the artifact now, and say explicitly that you are doing so.

2. **Update `.dew/state.md`**:
   - Set the completed stage's Stage Log status to `complete` with today's date
   - Advance `Active Stage` to the next stage:
     - Full workflow: discover→design→demonstrate→develop→document→debrief→complete
     - Fast workflow: plan→build→verify→complete
   - Mark the artifact as complete in the Artifacts table

3. **Commit** (if COMMIT_MODE is enabled):
   - Stage `.dew/state.md`, `.dew/graph.json` (if it exists), any new/changed files in `.dew/docs/` or `.dew/design-verification/`, and any pending deletion of `.dew/context.md` (left by a `/dew resume` — check `git status`)
   - Message: `dew(<stage>): complete <stage-name> for <project-name>`
   - Example: `dew(discover): complete discovery for retina-pipeline`
   - Do **not** push unless explicitly asked

4. **Show a summary** and prompt for context reset:
   - What artifact was written
   - What stage is next and what it will focus on
   - Flag anything from the conversation that might warrant backtracking before proceeding
   - Then say: **"Run `/clear` and then `/dew` to begin the next stage with a clean context."**

---

### Backtrack Protocol

When the user invokes `/dew back <stage>`:

1. Ask for the reason if not provided: "What did you find that requires going back to [stage]?"

2. Update `.dew/state.md`:
   - Add an entry to the Backtrack Log
   - Set `Active Stage` to the target stage
   - Set the target stage's Stage Log status to `in-progress` and mark all intermediate stages (between the target and where we came from) as `needs-revisit` in the Stage Log's Status column

3. **Commit** (if COMMIT_MODE is enabled):
   - Message: `dew(backtrack): return to <stage> — <brief reason>`

4. Enter the stage (Step 3) with the backtrack context loaded.

---

### Pause Protocol

When the user invokes `/dew pause`:

1. **Synthesize the conversation** into `.dew/context.md` with the following structure:

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

2. **Commit** (if COMMIT_MODE is enabled):
   - Stage `.dew/context.md` and `.dew/graph.json` (if it exists)
   - Message: `dew(pause): <stage> for <project-name>`

3. **Tell the user**: "Context saved to `.dew/context.md`. It's safe to quit. Run `/dew resume` in a new session to pick up where we left off."

---

### Resume Protocol

When the user invokes `/dew resume`:

1. **Check for `.dew/context.md`**. If it does not exist, tell the user: "No paused context found. Run `/dew` to enter the current stage fresh." Then stop.

2. **Read `.dew/context.md`** and present its contents to the user as a recap: "Here's where we left off:" followed by the snapshot.

3. **Reload the graph**, following the availability probe and session-start protocol in `${CLAUDE_PLUGIN_ROOT}/skills/shared/dag-integration.md` (`dag_load`, re-enable auto-save via `dag_save(".dew/graph.json", auto_save=true)`, then `dag_status`). On success, include a brief graph summary in the recap — which nodes are done, which are in-progress, what is next. On tool-unavailable failure, skip this step silently.

4. **Load the normal stage context** (same as Step 3 — read prerequisite artifacts for the active stage).

5. **Invoke the stage skill**, prepending both the context snapshot and the graph status so the skill has full awareness of prior progress. The stage skill's own DAG Integration section will then take over, using `dag_next` to resume from the correct point.

6. **Delete `.dew/context.md`** after the stage skill is successfully invoked (the context is now live in the conversation). Do not make a dedicated commit for the deletion — the next `/dew done` commit stages it explicitly (see Step 4), and a `/dew pause` overwrites the file with a fresh snapshot. The deletion must end up committed either way; never leave a consumed snapshot checked in.

---

### Status Report

When `/dew status` is invoked:

*Full workflow example:*
```
dew: <project-name> (<type>)  [full]
─────────────────────────────────────────
  [✓] Discover      completed <date>
  [✓] Design        completed <date>
  [→] Demonstrate   in progress
  [ ] Develop       pending
  [ ] Document      pending
  [ ] Debrief       pending

Backtracks:  0
Artifacts:
  .dew/docs/01-discover.md               ✓
  .dew/docs/02-design.md                 ✓
  .dew/design-verification/DESIGN_VERIFICATION.md   in progress
```

*Fast workflow example:*
```
dew: <project-name> (<type>)  [fast]
─────────────────────────────────────────
  [✓] Plan          completed <date>
  [→] Build         in progress
  [ ] Verify        pending

Backtracks:  0
Artifacts:
  .dew/docs/fast-plan.md                 ✓
  (codebase)                             in progress
```

Then stop — do not invoke any stage skill.

---

## State File Format

### Full Workflow

`.dew/state.md`:

```markdown
# dew Save State

## Project
- **Name**: <project-name>
- **Workflow**: full
- **Type**: new-project | major-feature | revisit-fix
- **Started**: <ISO date>
- **Last Updated**: <ISO date>

## Active Stage
**Stage**: discover | design | demonstrate | develop | document | debrief | complete
**Status**: in-progress | complete

## Artifacts
| Artifact | Path | Status |
|----------|------|--------|
| Discover | .dew/docs/01-discover.md | pending |
| Design (IDD) | .dew/docs/02-design.md | pending |
| Demonstrate | .dew/design-verification/DESIGN_VERIFICATION.md | pending |
| Develop | (codebase) | pending |
| Document | docs/ | pending |
| Debrief | .dew/docs/06-debrief.md | pending |

## Stage Log
<!-- Status: pending | in-progress | complete | needs-revisit -->
| Stage | Status | Started | Completed | Visits | Notes |
|-------|--------|---------|-----------|--------|-------|
| discover | pending | — | — | 0 | |
| design | pending | — | — | 0 | |
| demonstrate | pending | — | — | 0 | |
| develop | pending | — | — | 0 | |
| document | pending | — | — | 0 | |
| debrief | pending | — | — | 0 | |

## Backtrack Log
<!-- Format: | <date> | from: <stage> → to: <stage> | reason: <why> | resolved: yes/no | -->
(none yet)
```

### Fast Workflow

`.dew/state.md`:

```markdown
# dew Save State

## Project
- **Name**: <project-name>
- **Workflow**: fast
- **Type**: new-project | major-feature | revisit-fix
- **Started**: <ISO date>
- **Last Updated**: <ISO date>

## Active Stage
**Stage**: plan | build | verify | complete
**Status**: in-progress | complete

## Artifacts
| Artifact | Path | Status |
|----------|------|--------|
| Plan | .dew/docs/fast-plan.md | pending |
| Build | (codebase) | pending |
| Verify | .dew/docs/fast-debrief.md | pending |

## Stage Log
<!-- Status: pending | in-progress | complete | needs-revisit -->
| Stage | Status | Started | Completed | Visits | Notes |
|-------|--------|---------|-----------|--------|-------|
| plan | pending | — | — | 0 | |
| build | pending | — | — | 0 | |
| verify | pending | — | — | 0 | |

## Backtrack Log
<!-- Format: | <date> | from: <stage> → to: <stage> | reason: <why> | resolved: yes/no | -->
(none yet)
```
