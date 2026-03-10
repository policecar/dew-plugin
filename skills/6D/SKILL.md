---
name: 6D
description: 6D workflow orchestrator. Manages the six-stage development process (Discover → Design → Demonstrate → Develop → Document → Debrief), tracking state, loading artifact context, invoking stage skills, and maintaining git history at stage boundaries.
---

# 6D Workflow Orchestrator

**6D** is a structured engineering process for building software with rigor and measurability. Every stage is an interactive conversation — this orchestrator loads context and hands off to the appropriate stage skill, which runs directly in the current session.

| Stage | Plugin | Skill | Artifact |
|-------|--------|-------|----------|
| **Discover** | six-d | `/6D-discover` | `.6d/docs/01-discover.md` |
| **Design** | six-d | `/6D-design` | `.6d/docs/02-design.md` |
| **Demonstrate** | six-d | `/6D-demonstrate` | `.6d/design-verification/DESIGN_VERIFICATION.md` |
| **Develop** | six-d | `/6D-develop` | production code in repo |
| **Document** | six-d | `/6D-document` | `docs/` Hugo site |
| **Debrief** | six-d | `/6D-debrief` | `.6d/docs/06-debrief.md` |

**Commands:**
- `/6D` — continue from the current active stage
- `/6D new` — start a new 6D project
- `/6D done` — complete the current stage: write artifact, update state, commit, then prompt for `/clear`
- `/6D pause` — snapshot conversation context to `.6d/context.md`, commit, safe to quit
- `/6D resume` — restore context from `.6d/context.md` and re-enter the active stage
- `/6D status` — show current state without entering a stage
- `/6D back <stage>` — backtrack to an earlier stage
- `/6D-<stage-name>` — jump to a named stage (6D-discover / 6D-design / 6D-demonstrate / 6D-develop / 6D-document / 6D-debrief)

**Command presentation**: When showing any command to the user, always use the short form without the `six-d:` namespace prefix (e.g., `/6D done`, NEVER(!) `/six-d:6D done`). The namespace prefix is an internal Claude Code routing detail and must not be shown to users.

---

## Current Save State

!`cat .6d/state.md 2>/dev/null || echo "6D_STATUS: none — no active project found"`

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

2. Run `mkdir -p .6d/docs` to create the artifact directory.

3. Write `.6d/state.md` using the State File Format at the bottom of this file.

4. If in a git repo, commit the state file:
   - Message: `6D(init): begin 6D for <project-name>`

5. Set active stage to `discover` and enter the stage (Step 3).

---

### Step 3 — Enter Stage

Read the `Active Stage` from the save state. Load context for the stage (read any prerequisite artifacts). Then invoke the appropriate stage skill using the Skill tool.

**Context loading per stage:**

- **discover**: No prior artifacts. If revisit, read `.6d/docs/01-discover.md` and summarize what changed.
- **design**: Read `.6d/docs/01-discover.md` and present its contents to establish context before invoking the skill.
- **demonstrate**: Read `.6d/docs/02-design.md` and present its contents before invoking the skill.
- **develop**: Read `.6d/docs/02-design.md` and `.6d/design-verification/DESIGN_VERIFICATION.md` and present both before invoking the skill.
- **document**: Read `.6d/docs/01-discover.md`, `.6d/docs/02-design.md`, and `.6d/design-verification/DESIGN_VERIFICATION.md` and present all three before invoking the skill.
- **debrief**: Read `.6d/state.md` (full contents including backtrack log) and present it before invoking the skill.

**After loading context**, briefly tell the user:
- Which stage we are entering
- What context was loaded
- That you are now invoking the stage skill

Then invoke the stage skill via the Skill tool:
- discover → `Skill("six-d:6D-discover")`
- design → `Skill("six-d:6D-design")`
- demonstrate → `Skill("six-d:6D-demonstrate")`
- develop → `Skill("six-d:6D-develop")`
- document → `Skill("six-d:6D-document")`
- debrief → `Skill("six-d:6D-debrief")`

**If this is a revisit** (backtrack log is non-empty for this stage), prepend a brief summary of why we are back here before invoking the skill, so the stage skill has the backtrack context.

---

### Step 4 — Complete Stage (triggered by `/6D done`)

When the user invokes `/6D done`:

1. **Write the stage artifact** by synthesizing the conversation:
   - discover → write `.6d/docs/01-discover.md`
   - design → write `.6d/docs/02-design.md`
   - demonstrate → finalize `.6d/design-verification/DESIGN_VERIFICATION.md` (test programs were written during the stage)
   - develop → no additional artifact; code is already in the repo
   - document → finalize the Hugo site files
   - debrief → write `.6d/docs/06-debrief.md`

2. **Update `.6d/state.md`**:
   - Mark the completed stage with today's date
   - Advance `Active Stage` to the next stage (or `complete` if debrief is done)
   - Mark the artifact as complete in the Artifacts table

3. **Git commit** (if in a git repo):
   - Stage `.6d/state.md` and any new/changed files in `.6d/docs/` or `.6d/design-verification/`
   - Message: `6D(<stage>): complete <stage-name> for <project-name>`
   - Example: `6D(discover): complete discovery for retina-pipeline`
   - Do **not** push unless explicitly asked

4. **Show a summary** and prompt for context reset:
   - What artifact was written
   - What stage is next and what it will focus on
   - Flag anything from the conversation that might warrant backtracking before proceeding
   - Then say: **"Run `/clear` and then `/6D` to begin the next stage with a clean context."**

---

### Backtrack Protocol

When the user invokes `/6D back <stage>`:

1. Ask for the reason if not provided: "What did you find that requires going back to [stage]?"

2. Update `.6d/state.md`:
   - Add an entry to the Backtrack Log
   - Set `Active Stage` to the target stage
   - Mark all intermediate stages as `needs-revisit`

3. Commit the state update:
   - Message: `6D(backtrack): return to <stage> — <brief reason>`

4. Enter the stage (Step 3) with the backtrack context loaded.

---

### Pause Protocol

When the user invokes `/6D pause`:

1. **Synthesize the conversation** into `.6d/context.md` with the following structure:

```markdown
# 6D Context Snapshot

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
   - Stage `.6d/context.md`
   - Message: `6D(pause): <stage> for <project-name>`

3. **Tell the user**: "Context saved to `.6d/context.md`. It's safe to quit. Run `/6D resume` in a new session to pick up where we left off."

---

### Resume Protocol

When the user invokes `/6D resume`:

1. **Check for `.6d/context.md`**. If it does not exist, tell the user: "No paused context found. Run `/6D` to enter the current stage fresh." Then stop.

2. **Read `.6d/context.md`** and present its contents to the user as a recap: "Here's where we left off:" followed by the snapshot.

3. **Load the normal stage context** (same as Step 3 — read prerequisite artifacts for the active stage).

4. **Invoke the stage skill**, prepending the context snapshot so the skill has full awareness of prior progress.

5. **Delete `.6d/context.md`** after the stage skill is successfully invoked (the context is now live in the conversation). Do **not** commit the deletion — it will be cleaned up by the next `/6D done` or `/6D pause` commit.

---

### Status Report

When `/6D status` is invoked:

```
6D: <project-name> (<type>)
─────────────────────────────────────────
  [✓] Discover      completed <date>
  [✓] Design        completed <date>
  [→] Demonstrate   in progress
  [ ] Develop       pending
  [ ] Document      pending
  [ ] Debrief       pending

Backtracks:  0
Artifacts:
  .6d/docs/01-discover.md               ✓
  .6d/docs/02-design.md                 ✓
  .6d/design-verification/DESIGN_VERIFICATION.md   in progress
```

Then stop — do not invoke any stage skill.

---

## State File Format

`.6d/state.md`:

```markdown
# 6D Save State

## Project
- **Name**: <project-name>
- **Type**: new-project | major-feature | revisit-fix
- **Started**: <ISO date>
- **Last Updated**: <ISO date>

## Active Stage
**Stage**: discover | design | demonstrate | develop | document | debrief | complete
**Status**: in-progress | complete

## Artifacts
| Artifact | Path | Status |
|----------|------|--------|
| Discover | .6d/docs/01-discover.md | pending |
| Design (IDD) | .6d/docs/02-design.md | pending |
| Demonstrate | .6d/design-verification/DESIGN_VERIFICATION.md | pending |
| Develop | (codebase) | pending |
| Document | docs/ | pending |
| Debrief | .6d/docs/06-debrief.md | pending |

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
