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

**Command presentation**: When showing any command to the user, always use the short form without the `dew:` namespace prefix (e.g., `/dew done`, NEVER(!) `/dew:dew done`). The namespace prefix is an internal Claude Code routing detail and must not be shown to users.

---

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

2. Run `mkdir -p .dew/docs` to create the artifact directory.

3. Write `.dew/state.md` using the appropriate State File Format at the bottom of this file (full or fast).

4. If in a git repo, commit the state file:
   - Message: `dew(init): begin dew for <project-name>`

5. Set active stage to `discover` (full workflow) or `plan` (fast workflow) and enter the stage (Step 3).

---

### Step 3 — Enter Stage

Read the `Active Stage` from the save state. Load context for the stage (read any prerequisite artifacts). Then invoke the appropriate stage skill using the Skill tool.

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

If the `mcp__dependency-graph__dag_status` tool is available, also call `dag_status` after loading artifacts to show a brief project graph summary (what's done, what's pending across all stage namespaces). This gives the user and the stage skill an instant orientation on overall progress.

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

1. **Write the stage artifact** by synthesizing the conversation:

   *Full workflow:*
   - discover → write `.dew/docs/01-discover.md`
   - design → write `.dew/docs/02-design.md` and `.dew/metacog/quality-requirements.md` (create `.dew/metacog/` if needed)
   - demonstrate → finalize `.dew/design-verification/DESIGN_VERIFICATION.md` (test programs were written during the stage)
   - develop → no additional artifact; code is already in the repo
   - document → finalize the Hugo site files
   - debrief → write `.dew/docs/06-debrief.md`

   *Fast workflow:*
   - plan → write `.dew/docs/fast-plan.md`
   - build → no additional artifact; code is already in the repo
   - verify → write `.dew/docs/fast-debrief.md`

2. **Update `.dew/state.md`**:
   - Mark the completed stage with today's date
   - Advance `Active Stage` to the next stage:
     - Full workflow: discover→design→demonstrate→develop→document→debrief→complete
     - Fast workflow: plan→build→verify→complete
   - Mark the artifact as complete in the Artifacts table

3. **Git commit** (if in a git repo):
   - Stage `.dew/state.md`, `.dew/graph.json` (if it exists), and any new/changed files in `.dew/docs/`, `.dew/metacog/`, or `.dew/design-verification/`
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
   - Mark all intermediate stages as `needs-revisit`

3. Commit the state update:
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

2. **Git commit** (if in a git repo):
   - Stage `.dew/context.md` and `.dew/graph.json` (if it exists)
   - Message: `dew(pause): <stage> for <project-name>`

3. **Tell the user**: "Context saved to `.dew/context.md`. It's safe to quit. Run `/dew resume` in a new session to pick up where we left off."

---

### Resume Protocol

When the user invokes `/dew resume`:

1. **Check for `.dew/context.md`**. If it does not exist, tell the user: "No paused context found. Run `/dew` to enter the current stage fresh." Then stop.

2. **Read `.dew/context.md`** and present its contents to the user as a recap: "Here's where we left off:" followed by the snapshot.

3. **Reload the graph** (if `mcp__dependency-graph__dag_status` is available): call `dag_load(".dew/graph.json")` followed by `dag_save(".dew/graph.json", auto_save=true)` to restore and re-enable auto-save. Then call `dag_status` and include a brief graph summary in the recap — which nodes are done, which are in-progress, what is next.

4. **Load the normal stage context** (same as Step 3 — read prerequisite artifacts for the active stage).

5. **Invoke the stage skill**, prepending both the context snapshot and the graph status so the skill has full awareness of prior progress. The stage skill's own DAG Integration section will then take over, using `dag_next` to resume from the correct point.

6. **Delete `.dew/context.md`** after the stage skill is successfully invoked (the context is now live in the conversation). Do **not** commit the deletion — it will be cleaned up by the next `/dew done` or `/dew pause` commit.

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
| Stage | Started | Completed | Visits | Notes |
|-------|---------|-----------|--------|-------|
| discover | — | — | 0 | |
| design | — | — | 0 | |
| demonstrate | — | — | 0 | |
| develop | — | — | 0 | |
| document | — | — | 0 | |
| debrief | — | — | 0 | |

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
| Stage | Started | Completed | Visits | Notes |
|-------|---------|-----------|--------|-------|
| plan | — | — | 0 | |
| build | — | — | 0 | |
| verify | — | — | 0 | |

## Backtrack Log
<!-- Format: | <date> | from: <stage> → to: <stage> | reason: <why> | resolved: yes/no | -->
(none yet)
```
