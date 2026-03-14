---
name: dew-auto
description: Autonomous dew workflow using agent teams. Interviews the user, then creates a multi-model AI team (Opus, Sonnet, Haiku) that collaboratively executes the full or fast dew cycle. Requires the experimental agent teams feature to be enabled.
---

# dew Auto Mode

Autonomous execution of the dew workflow using an agent team. You (the lead) interview the user to understand the task, then create a team of AI teammates with diverse models (Opus, Sonnet, Haiku) that collaboratively execute each dew stage — debating, challenging assumptions, and producing the same artifacts as the manual workflow.

**Entry:** `/dew auto` (full 6-stage workflow) or `/dew auto fast` (fast 3-stage workflow)

---

## Instructions

Arguments provided: `$ARGUMENTS`

### Step 1 — Check Prerequisites

Determine whether agent teams are enabled:

1. Read `~/.claude/settings.json`. Check whether the `env` object contains `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"`.
2. If not found there, also check `.claude/settings.json` and `.claude/settings.local.json` in the current project.
3. If the setting is found in **any** of these files, proceed to Step 2.
4. If **not found anywhere**:
   - Explain: "Auto mode creates a team of AI agents with different models (Opus, Sonnet, Haiku) that collaborate through the dew stages autonomously. This requires Claude Code's experimental agent teams feature, which is currently not enabled."
   - Ask: "Would you like me to enable it? I'll add the setting to `~/.claude/settings.json`."
   - If **yes**: Read `~/.claude/settings.json`, add `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` to the `env` object (create the object if it doesn't exist), write the file back. Then tell the user: "Enabled. **Please restart Claude Code** and run `/dew auto` again for the setting to take effect." Then **stop**.
   - If **no**: Suggest using the normal `/dew` or `/dew fast` workflow instead. Then **stop**.

5. Determine workflow type from arguments:
   - If ARGUMENTS contains `fast` → **fast workflow** (Plan → Build → Verify)
   - Otherwise → **full workflow** (Discover → Design → Demonstrate → Develop → Document → Debrief)

---

### Step 2 — Interview the User

This is the only interactive phase. After this, the team works autonomously.

Conduct a focused interview — aim for 5-10 exchanges, not an exhaustive requirements session. The team will do deep exploration during Discover (or Plan). Ask these questions, adapting naturally to the user's responses:

1. **What are we building?** Get a short slug-friendly name and a 1-2 sentence description.
2. **What problem does it solve?** Who needs this and why?
3. **Key requirements?** Functional (what it does) and non-functional (performance, platform, security).
4. **What does "done" look like?** Concrete acceptance criteria.
5. **Scope boundaries?** What's explicitly in scope and what's explicitly NOT.
6. **Preferences?** Tech stack, architectural patterns, conventions to follow or avoid.
7. **Codebase context?** Key files, existing infrastructure, gotchas the team should know.

After the interview, synthesize into a **Project Brief** and write it to `.dew/docs/00-brief.md`:

```markdown
# Project Brief: <project-name>

## Problem
<What problem we're solving and for whom>

## Requirements
### Functional
<What it must do>

### Non-Functional
<Performance, platform, security, etc.>

## Scope
- **In scope**: ...
- **Out of scope**: ...

## Acceptance Criteria
<Concrete, testable criteria>

## Constraints & Preferences
<Tech stack, conventions, architectural preferences>

## Codebase Context
<Key files, existing infrastructure, relevant patterns>
```

---

### Step 3 — Initialize Project

1. Run `mkdir -p .dew/docs .dew/design-verification`.

2. Write `.dew/state.md` using the standard dew state format (see the dew orchestrator's State File Format section). Set:
   - **Workflow**: `full` or `fast`
   - **Type**: as appropriate from the interview
   - **Active Stage**: `discover` (full) or `plan` (fast)
   - Add `auto mode` in the Notes column of the first stage entry in the Stage Log

3. If the dependency graph MCP is available (check for `mcp__dependency-graph__dag_create_node` tool):
   - Create a DAG with stage-level nodes wired in sequence
   - Full: `auto:discover` → `auto:design` → `auto:demonstrate` → `auto:develop` → `auto:document` → `auto:debrief`
   - Fast: `auto:plan` → `auto:build` → `auto:verify`
   - Save to `.dew/graph.json` with `auto_save=true`

4. Git commit all `.dew/` files: `dew(auto-init): begin autonomous dew for <project-name>`

5. Tell the user: "Project initialized. I'm now creating the team and starting autonomous execution. You can watch progress and message teammates directly (Shift+Down to cycle through them). I'll report back when the cycle is complete."

---

### Step 4 — Create the Team

Create an agent team with three teammates, each using a different model. Use the following prompt to create the team:

> Create an agent team for the dew development workflow on "<project-name>": <brief description>.
>
> Spawn three teammates:
>
> 1. **analyst** — Use Opus model. Deep analytical thinker. Excels at finding implicit assumptions, edge cases, architectural trade-offs, and subtle failure modes. Challenges surface-level reasoning.
>
> 2. **builder** — Use Sonnet model. Pragmatic implementer. Excels at clean code, practical architecture, and balanced trade-offs. Keeps designs buildable and grounded in reality.
>
> 3. **scout** — Use Haiku model. Fast pattern-matcher and devil's advocate. Excels at spotting over-engineering, questioning necessity, and finding simpler alternatives. Keeps the team lean.

Include the following **shared context** for all teammates in their spawn prompts:

> You are part of an autonomous dew development team building "<project-name>".
>
> **Read first:**
> - Project brief: `.dew/docs/00-brief.md`
> - Current state: `.dew/state.md`
>
> **How you work:**
> - When a stage begins, read the stage's skill file at `skills/dew-<stage>/SKILL.md` (or `skills/dew-fast/SKILL.md` for fast workflow stages). This describes the methodology you follow.
> - Role-play the stage methodology collaboratively with your teammates. One teammate drives each phase (proposes structure, drafts content), the others critique, challenge, and refine. Rotate the driver role across phases so no single perspective dominates.
> - Engage in genuine debate — the quality comes from diverse perspectives challenging each other. Do NOT just agree. Ask probing questions, surface implicit assumptions, push for precision.
> - Write stage artifacts to the standard dew paths (`.dew/docs/`, `.dew/design-verification/`) when the team reaches consensus.
> - If the dependency graph MCP is available, use it to track fine-grained work items within stages.
>
> **Engineering mindset (non-negotiable):**
> - Make assumptions explicit and test them
> - Never accept "it works" — define what "works" means and how to measure it
> - Challenge vague language: "should work", "straightforward", "simple" are not conclusions
> - Ask "what if this assumption is wrong?" for every critical decision
> - Prefer measuring over guessing
>
> **Calling a timeout:**
> If you believe the team is going in circles, stuck in a rabbit hole, over-engineering, or missing something fundamental, message the lead:
> `TIMEOUT: <specific reason why fresh eyes are needed>`
> The lead will bring in an independent reviewer with no prior context.

---

### Step 5 — Execute Stages

Loop through each stage in the chosen workflow. For each stage:

#### 5a. Stage Entry

1. Update `.dew/state.md`: set active stage, increment visit count, record start date.

2. Broadcast to all teammates:
   > **Stage: [STAGE NAME]**
   >
   > Read the methodology at `skills/dew-[stage]/SKILL.md` [or `skills/dew-fast/SKILL.md` with stage context for fast workflow].
   >
   > [If prior artifacts exist]: Read these prerequisite artifacts for context from prior stages: [list paths].
   >
   > Collaborate on this stage following the skill's methodology. Debate, challenge, refine. When the team has consensus on the stage output, one teammate writes the artifact to [expected artifact path] and messages me.

3. Create stage tasks in the shared task list derived from the stage skill's structure. Set dependencies where phases are sequential.

4. If DAG is available: create fine-grained nodes under the stage namespace, wire dependencies, mark the stage-level node as started.

#### 5b. Stage Monitoring

While teammates work:

- **Let them work.** Don't micromanage. The value comes from their autonomous collaboration.
- **Handle TIMEOUT requests**: See the Fresh Eyes Protocol below.
- **Watch for completion signals**: A teammate messages that the artifact is written and the team has consensus.
- **Handle stalls**: If no progress occurs for an extended period (no messages, no task completions), check in:
  > "Status check — what's blocking progress?"

#### 5c. Stage Completion

When a teammate signals the stage is done:

1. **Verify the artifact**: Read the stage artifact. Verify it exists and has substantive content that matches the stage's expected output format.

2. **Update `.dew/state.md`**: Mark stage complete with today's date, advance active stage.

3. **Update DAG** (if available): Mark the stage-level node as done with a summary of what was produced.

4. **Git commit**: Stage all `.dew/` changes and the artifact.
   - Message: `dew(<stage>): complete <stage-name> for <project-name> [auto]`

5. **Proceed to next stage** (repeat from 5a), unless this was the final stage.

---

### Step 6 — Completion

When all stages are done:

1. **Final review**: Read all produced artifacts. Check the project against the acceptance criteria from `.dew/docs/00-brief.md`. Note any gaps.

2. **Update `.dew/state.md`**: Set active stage to `complete`.

3. **Git commit**: `dew(auto-complete): finish autonomous dew for <project-name>`

4. **Clean up the team**: Ask all teammates to shut down, then clean up team resources.

5. **Report to the user**:
   - Summary of what was built
   - List of all artifacts with their paths
   - Key architectural decisions and their rationale (pulled from artifacts)
   - Any gaps between the brief's acceptance criteria and what was delivered
   - Suggested next steps or items requiring human review

---

## Fresh Eyes Protocol

When any teammate messages `TIMEOUT: <reason>`:

1. Acknowledge to the team (broadcast): "Timeout called by [teammate]. Pausing for fresh-eyes review."

2. Spawn a **subagent** (not a teammate — completely fresh context, no team history) with this prompt:

   > You are an independent engineering reviewer called in with fresh eyes. A development team working on "<project-name>" has called a timeout because: "<reason>"
   >
   > Read the current state:
   > - Project brief: `.dew/docs/00-brief.md`
   > - All existing artifacts in `.dew/docs/` and `.dew/design-verification/`
   > - `.dew/state.md` for progress tracking
   > - If the dependency graph MCP is available, call `dag_status` for the task graph overview
   >
   > Assess with engineering rigor:
   > 1. Is the team on track or in a rabbit hole? What specific evidence supports your assessment?
   > 2. Are there simpler approaches the team hasn't considered?
   > 3. What implicit assumptions need to be challenged?
   > 4. Is scope creeping beyond the brief?
   > 5. If you were starting from this point, what would you do differently?
   >
   > Be direct, specific, and constructive. No sugar-coating.

3. Share the reviewer's assessment with all teammates (broadcast).

4. Let the team decide how to proceed. If the reviewer recommends revisiting an earlier stage, update `.dew/state.md` using the Backtrack Protocol from the dew orchestrator (add entry to backtrack log, set active stage, mark intermediate stages as needs-revisit) and redirect the team to the appropriate stage.

---

## Context Preservation

Artifacts and state persist on disk across context compaction:
- `.dew/state.md` — always reflects current progress
- `.dew/docs/*.md` — stage artifacts accumulate as stages complete
- `.dew/graph.json` — DAG state (if using dependency graph)
- Shared task list — managed by Claude Code

If your (the lead's) context is compacted mid-execution:
1. Re-read `.dew/state.md` to determine current stage and progress
2. Re-read all existing artifacts in `.dew/docs/` and `.dew/design-verification/`
3. Check DAG status (if available)
4. Check on teammates via the shared task list and messaging
5. Resume coordinating from where things stand

**Known limitation**: There is no `PostCompact` hook that supports agent-type actions. Context recovery after compaction relies on the lead re-reading persisted state from disk. Since every stage writes artifacts and updates `.dew/state.md` before advancing, no completed work is lost — only the in-flight conversation context of the current stage may need to be re-established by teammates re-reading their prior messages and artifacts.
