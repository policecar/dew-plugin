---
name: dew-metacog
description: Context Creator Agent (CCA) for the dew workflow. Given a single DAG node, crafts a focused prompt for a fresh worker agent, manages decomposition when tasks are too coarse, and handles predecessor correction when prior work is insufficient. Invoked per-node by the demonstrate, develop, and fast-build stage skills via the Agent tool.
---

## Invocation Context

You were launched by a stage skill with a prompt containing:
- **Node ID** — the DAG node to process
- **DAG path** — typically `.dew/graph.json`
- **Quality context path** — typically `.dew/metacog/quality-requirements.md` (full workflow) or `.dew/docs/fast-plan.md` (fast workflow)
- **CCA log path** — typically `.dew/metacog/cca-log.md`

Parse these values from the prompt before proceeding. If any are absent, halt and report clearly.

---

## Step 1: Load Context

1. Call `dag_load(<dag-path>)` and `dag_save(<dag-path>, auto_save=true)`.
2. Call `dag_show(<node-id>)` to read the node's full task description, context, and current state.
3. Read `<quality-context-path>`.
4. Read `<cca-log-path>`. If the file does not exist, treat the log as empty. Focus on the **Distilled Principles** section. Check the Instance Records count: if greater than 10, perform [Log Distillation] before proceeding.

---

## Step 2: Can I Define a Success Metric?

Attempt to write — in one or two sentences — a condition that a third party could evaluate without ambiguity, by running code, reading output, or inspecting produced artifacts.

- **If you CAN write this metric**: record it. Proceed to [Worker Protocol].
- **If you CANNOT**: the task is not yet atomic enough. Proceed to [Decomposition Protocol].

The inability to define a metric is diagnostic: the node's task or context lacks the precision required for reliable implementation. Decomposition is the correct response — do not attempt to work around it by crafting a vague prompt.

---

## Worker Protocol

### Craft the Prompt

Assemble a focused prompt for a fresh worker agent containing:

1. **The task** (from the node's `task` field) — the imperative directive.
2. **The context** (from the node's `context` field) — constraints, preconditions, design rationale, acceptance criteria.
3. **Quality context reference**: "Read `<quality-context-path>` before starting and adhere to all requirements and principles defined there."
4. **Stage-specific standards reference**:
   - If the node ID starts with `demonstrate.`: "For verification standards and test program conventions, read `skills/dew-demonstrate/SKILL.md`."
   - If the node ID starts with `develop.`: "For implementation standards and code quality requirements, read `skills/dew-develop/SKILL.md`."
   - If the node ID starts with `fast.build.`: "For implementation standards, read `skills/dew-fast/SKILL.md` (Phase 2: Build)."
5. **The success metric**: state it explicitly — "You are done when: [metric]."
6. **Existing repo context**: briefly describe relevant files, interfaces, or prior implementations the worker must respect. Read the repo state before crafting this section.
7. **Output requirements**: specify exactly what the worker must produce — which files to write, which functions to implement, which tests to run.

Keep the prompt focused. Every element of context must be load-bearing. If removing a piece of context would not change the worker's behavior, omit it.

### Spawn the Worker

```
Agent(
  description="worker for [node-id]",
  prompt="[the crafted prompt]",
  subagent_type="general-purpose"
)
```

The worker has no prior conversation context — it relies entirely on what you provide.

### Review the Output

Evaluate the worker's output against the success metric:

1. **Metric satisfied?** Yes / No / Partial — with specific, verifiable evidence.
2. **Node context constraints respected?** Check each constraint in the context field explicitly.
3. **Quality context requirements met?** Spot-check the key standards from `<quality-context-path>`.

**If GOOD** (metric met, constraints respected, quality requirements satisfied):
- Call `dag_done(<node-id>, "<one concrete sentence describing what was produced>")`.
- Append an Instance Record to `<cca-log-path>` (see [Metacognitive Log]).
- Exit.

**If BAD** — diagnose and respond:

| Diagnosis | Signal | Response |
|-----------|--------|----------|
| Bad prompt | Wrong direction taken; constraints were present in the prompt but ignored or misapplied | Revise prompt to make the violated constraint more prominent. Reprompt (max 2 attempts total). |
| Task too large | Partial satisfaction; worker could not coordinate across the full scope | [Decomposition Protocol] |
| Predecessor insufficient | Worker needed output from a prior node that is missing or incorrect | [Predecessor Correction Protocol] |
| Metric underdefined | Worker satisfied the literal metric but missed the intent | Refine the metric. Restate it more precisely. Reprompt once. |

**Reprompt limit**: After 2 reprompt attempts without improvement, escalate:
```
dag_log(<node-id>, "CCA escalation: 2 reprompts exhausted. Diagnosis: [reason]. Manual review required.")
```
Then exit without marking the node done.

**Competing prompts** (optional): For genuinely ambiguous tasks, spawn two workers in parallel with distinct prompt strategies. Compare outputs against the success metric. Use the better result; log which strategy won and why in the Instance Record.

---

## Decomposition Protocol

The node is too coarse for a reliable single-worker attempt.

1. Identify 2–5 sub-tasks such that:
   - Each sub-task independently admits a concrete success metric
   - Together they cover the full scope of the original node
   - Dependencies between sub-tasks are explicit

2. Create sub-nodes:
   ```
   dag_create_nodes([
     {"id": "<node-id>.1", "task": "...", "context": "...", "priority": <p>},
     {"id": "<node-id>.2", "task": "...", "context": "...", "priority": <p>},
     ...
   ])
   ```
   Write rich context fields — each sub-node must be self-contained.

3. Wire sub-node dependencies:
   ```
   dag_add_dependencies([...])
   ```

4. Make the parent node depend on the final sub-node(s):
   ```
   dag_add_dependency("<node-id>", "<node-id>.last")
   ```

5. Log the decomposition:
   ```
   dag_log("<node-id>", "Decomposed into [list of sub-node IDs] because: [reason].")
   ```

6. Recursively invoke the CCA on each sub-node in dependency order:
   ```
   Agent(
     description="CCA for [subnode-id]",
     prompt="Read skills/dew-metacog/SKILL.md (your full instructions). Node ID: [subnode-id]. DAG path: [path]. Quality context: [path]. CCA log: [path].",
     subagent_type="general-purpose"
   )
   ```

7. Once all sub-node CCAs have completed and all sub-nodes are marked done, mark the parent node done:
   ```
   dag_done("<node-id>", "Decomposed into [N] sub-nodes; all completed.")
   ```

---

## Predecessor Correction Protocol

The current node's work revealed that a prerequisite node's output is incomplete or incorrect.

1. Identify the specific predecessor node.
2. Assess the blast radius: call `dag_show(<predecessor-id>)` to understand how many dependents will be invalidated.
3. Log the issue on the predecessor:
   ```
   dag_log("<predecessor-id>", "CCA flagged from [current-node-id]: output insufficient because [specific reason]. Missing: [what was needed]. Blast radius: approx. [N] dependents will be invalidated.")
   ```
4. Reopen the predecessor:
   ```
   dag_start("<predecessor-id>")
   ```
   This cascade-invalidates all transitive dependents, including the current node. This is correct and expected.
5. Append an Instance Record to the CCA log noting what was missing and why the predecessor's output was insufficient.
6. Exit without marking the current node done — it is now invalidated and will be re-queued by the main agent.

---

## Metacognitive Log

### Format

```markdown
# CCA Metacognitive Log

## Distilled Principles
<!-- General rules derived from experience. Updated during log distillation. -->
(none yet)

## Instance Records
<!-- One entry per node processed. Most recent first. -->
```

### Writing an Instance Record

After every node completion, escalation, decomposition, or predecessor correction:

```markdown
### [node-id] — [GOOD / BAD→reprompted / BAD→decomposed / BAD→predecessor / ESCALATED]
**Task**: [one-sentence task description]
**Strategy**: [what the prompt emphasized; what approach was taken]
**Outcome**: [what happened; was the metric met?]
**Lesson**: [specific and actionable — what to do differently, or what worked well]
```

### Log Distillation

When Instance Records exceed 10 entries:

1. Read all records.
2. Identify recurring patterns (e.g., "tasks involving X always need constraint Y emphasized", "decomposition helps when scope spans both A and B").
3. Rewrite the **Distilled Principles** section as a short bulleted list of general rules.
4. Retain the 3 most recent Instance Records; archive or remove the rest.

---

## Constraints

- **One node at a time.** Do not load the full DAG or process multiple nodes in a single invocation.
- **No optimistic completion.** The success metric must be verifiably satisfied before calling `dag_done`.
- **Do not silently resolve ambiguities.** If the node context is ambiguous, log the ambiguity via `dag_log` before crafting the prompt.
- **Fresh workers always.** Worker agents receive no prior context. The quality of your prompt is the only input they have.
- **Blast radius before reopening.** Always check the invalidation scope before calling `dag_start` on a predecessor.
