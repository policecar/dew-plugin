# dew — A Structured Engineering Workflow for Claude Code

**dew** is a Claude Code plugin implementing a rigorous, six-stage software development process. Each stage is an interactive conversation with a specialized AI assistant, producing a concrete artifact that feeds the next stage. The workflow enforces engineering discipline: explicit assumptions, measurable goals, empirical validation before implementation, and structured retrospectives.

```
Discover → Design → Demonstrate → Develop → Document → Debrief
```

---

## The Six Stages

| # | Stage | What Happens | Artifact |
|---|-------|-------------|----------|
| 1 | **Discover** | Deep problem domain exploration. Surfaces assumptions, defines measurable success criteria, maps constraints and stakeholders. No implementation talk. | `.dew/docs/01-discover.md` |
| 2 | **Design** | Hardware-aware implementation design. Data layouts, compute kernels, module structure — driven by the hardware's capabilities, not the problem's semantics. | `.dew/docs/02-design.md` |
| 3 | **Demonstrate** | Empirical validation of critical design assumptions. Minimal isolated test programs, measured against theoretical hardware limits. Failures caught here, not in production. | `.dew/design-verification/DESIGN_VERIFICATION.md` |
| 4 | **Develop** | Production code implementation. Structure defined and agreed before a single line is written. Incremental validation throughout. | (codebase) |
| 5 | **Document** | Developer-facing Hugo documentation site. Synthesizes all upstream artifacts into architecture docs, design decisions, internals, and codebase map. | `docs/` Hugo site |
| 6 | **Debrief** | Structured retrospective. Root-cause analysis of what worked and what didn't, with findings written back into the skill configurations for the next cycle. | `.dew/docs/06-debrief.md` |

---

## Installation

### Requirements

- [Claude Code](https://github.com/anthropics/claude-code) CLI v1.0.33 or later

### Install from GitHub

```
/plugin marketplace add jkerdels/dew-plugin
/plugin install dew@jkerdels

restart claude
```

### Test locally (without installing)

```bash
claude --plugin-dir ./path/to/dew-plugin
```

---

## Usage

All commands can be prefixed with the namespace `/dew:`, but the search in claude code omits this.

### Start a new project

```
/dew new
```

The orchestrator asks for a project name and type, creates the state file, and drops you into the **Discover** stage.

### Continue from where you left off

```
/dew
```

### Check current status

```
/dew status
```

### Complete the current stage and advance

```
/dew done
```

Writes the stage artifact, commits it to git, and prompts you to `/clear` before the next stage (each stage runs with a clean context window).

### Pause mid-stage and resume later

```
/dew pause
```

Synthesizes the conversation into a context snapshot at `.dew/context.md` and commits it. Safe to quit Claude after this.

```
/dew resume
```

Restores the context snapshot and re-enters the active stage with full awareness of prior progress.

### Jump directly to a stage

```
/dew-discover
/dew-design
/dew-demonstrate
/dew-develop
/dew-document
/dew-debrief
```

### Backtrack to an earlier stage

```
/dew back design
```

Records the reason in the state file and reloads that stage's context.

---

## Optional: Dependency Graph MCP

dew natively integrates with [dependency-graph-mcp](https://github.com/jkerdels/dependency-graph-mcp) when it is available. Each stage skill checks for the MCP at startup and activates graph tracking automatically — no configuration needed.

### What the graph adds

**Work tracking per stage**: each conversation phase becomes a graph node. `dag_next` drives the order; `dag_done` records outcomes with concrete summaries. The graph enforces that phases are completed before the next begins.

**Cross-stage handoff nodes**: stages plant seeds in the graph for downstream stages to pick up and elaborate:

| Stage creates | Picked up by |
|---------------|-------------|
| `demonstrate.<assumption>` seeds — critical assumptions needing empirical validation | Demonstrate, which expands each into a `design→implement→execute→analyze` sub-chain |
| `develop.<component>` seeds — one per implementation component | Develop, which expands each into `structure→implement→validate` |

This gives the project a single, growing dependency graph that spans the entire development cycle — from discovery assumptions through to implementation components.

**Artifact condensation**: when the graph is active, written artifacts (planning report, IDD, DVD, implementation summary, debrief) are condensed. The graph carries the reasoning trail and decision log; artifacts focus on synthesis and conclusions. Specific sections that can be shortened are called out in each stage skill.

**Retrospective evidence**: the Debrief stage reads the full project graph — node counts per stage, PASS/FAIL patterns on `demonstrate.*` nodes, invalidation cascades (signals rework), and planned-vs-actual component structure — as primary evidence for the retrospective.

### Installation

Follow the setup instructions at [dependency-graph-mcp](https://github.com/jkerdels/dependency-graph-mcp). Once the MCP server is registered in Claude Code, dew detects it automatically.

The graph is persisted at `.dew/graph.json` in your project repository and committed alongside other artifacts at each stage transition and pause.

---

## Workflow Design Principles

**Explicit assumptions.** The primary cause of project failure is implicit assumptions. Every stage is designed to surface and challenge them.

**Measure, never guess.** Goals must be quantifiable. Performance claims must be benchmarked against hardware limits. "Fast" is not a result; "23 ms at 67% of theoretical peak" is.

**Hardware drives structure.** The Design stage shapes code around what CPUs and memory hierarchies can do efficiently — not around domain semantics or class hierarchies.

**Validate before implementing.** The Demonstrate stage exists specifically to catch design flaws before they are baked into production code.

**Honest retrospectives.** The Debrief stage writes findings back into the skill configurations themselves, so the process improves with every cycle.

**Loose coupling.** Functional interfaces over OOP. Flat data structures over pointer-chasing. Templates over inheritance.

---

## Repository Structure

```
.claude-plugin/
  plugin.json            — plugin manifest (name, version, description)
skills/
  dew/                    — orchestrator: state, context loading, stage transitions
  dew-discover/           — domain exploration and planning
  dew-design/             — hardware-aware implementation design
  dew-demonstrate/        — empirical design validation
  dew-develop/            — production code implementation
  dew-document/           — Hugo documentation site generator
  dew-debrief/            — retrospective facilitator
README.md
```

---

## Project State

The workflow maintains `.dew/state.md` in your project repository, tracking:
- Current active stage and status
- Artifact completion status
- Stage log with visit counts and dates
- Backtrack log with reasons

All dew files live under `.dew/` in your project:

```
.dew/
  state.md                          — workflow state
  graph.json                        — dependency graph (if MCP is active)
  context.md                        — pause snapshot (present only when paused)
  docs/
    01-discover.md
    02-design.md
    06-debrief.md
  design-verification/
    DESIGN_VERIFICATION.md
    <test programs>
```

Every state transition is committed to git, giving you a full audit trail of the development cycle.

---

## License

MIT
