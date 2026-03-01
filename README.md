# 6D — A Structured Engineering Workflow for Claude Code

**6D** is a Claude Code plugin implementing a rigorous, six-stage software development process. Each stage is an interactive conversation with a specialized AI assistant, producing a concrete artifact that feeds the next stage. The workflow enforces engineering discipline: explicit assumptions, measurable goals, empirical validation before implementation, and structured retrospectives.

```
Discover → Design → Demonstrate → Develop → Document → Debrief
```

---

## The Six Stages

| # | Stage | What Happens | Artifact |
|---|-------|-------------|----------|
| 1 | **Discover** | Deep problem domain exploration. Surfaces assumptions, defines measurable success criteria, maps constraints and stakeholders. No implementation talk. | `docs/6D/01-discover.md` |
| 2 | **Design** | Hardware-aware implementation design. Data layouts, compute kernels, module structure — driven by the hardware's capabilities, not the problem's semantics. | `docs/6D/02-design.md` |
| 3 | **Demonstrate** | Empirical validation of critical design assumptions. Minimal isolated test programs, measured against theoretical hardware limits. Failures caught here, not in production. | `design-verification/DESIGN_VERIFICATION.md` |
| 4 | **Develop** | Production code implementation. Structure defined and agreed before a single line is written. Incremental validation throughout. | (codebase) |
| 5 | **Document** | Developer-facing Hugo documentation site. Synthesizes all upstream artifacts into architecture docs, design decisions, internals, and codebase map. | `docs/` Hugo site |
| 6 | **Debrief** | Structured retrospective. Root-cause analysis of what worked and what didn't, with findings written back into the skill configurations for the next cycle. | `docs/6D/06-debrief.md` |

---

## Installation

### Requirements

- [Claude Code](https://github.com/anthropics/claude-code) CLI v1.0.33 or later

### Install from GitHub

```
/plugin marketplace add jkerdels/6D-plugin
/plugin install six-d@jkerdels

restart claude
```

### Test locally (without installing)

```bash
claude --plugin-dir ./path/to/6D-plugin
```

---

## Usage

All commands can be prefixed with the namespace `/six-d:`, but the search in claude code omits this.

### Start a new project

```
/6D new
```

The orchestrator asks for a project name and type, creates the state file, and drops you into the **Discover** stage.

### Continue from where you left off

```
/6D
```

### Check current status

```
/6D status
```

### Complete the current stage and advance

```
/6D done
```

Writes the stage artifact, commits it to git, and prompts you to `/clear` before the next stage (each stage runs with a clean context window).

### Jump directly to a stage

```
/6D-discover
/6D-design
/6D-demonstrate
/6D-develop
/6D-document
/6D-debrief
```

### Backtrack to an earlier stage

```
/6D back design
```

Records the reason in the state file and reloads that stage's context.

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
  plugin.json       — plugin manifest (name, version, description)
skills/
  proc/             — orchestrator: state, context loading, stage transitions
  discover/         — domain exploration and planning
  design/           — hardware-aware implementation design
  demonstrate/      — empirical design validation
  develop/          — production code implementation
  document/         — Hugo documentation site generator
  debrief/          — retrospective facilitator
README.md
```

---

## State File

The workflow maintains `.claude/6D-state.md` in your project repository, tracking:
- Current active stage and status
- Artifact completion status
- Stage log with visit counts and dates
- Backtrack log with reasons

This file is committed to git at each stage transition, giving you a full audit trail of the development cycle.

---

## License

MIT
