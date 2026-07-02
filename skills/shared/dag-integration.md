# Shared DAG Integration Protocol

Common protocol for working with the optional `dependency-graph` MCP server. Stage skills reference this file and supply their own stage-specific node definitions; this file defines everything that is identical across stages.

## Availability Check (probe-then-act)

The `dependency-graph` MCP server's tools are deferred — they will not appear in your visible tool list even when the server is running, so you cannot detect availability by inspecting the tool list. Probe as follows:

1. Load the probe tool schema via `ToolSearch` with query `select:mcp__dependency-graph__dag_load`.
2. Attempt to call `mcp__dependency-graph__dag_load(".dew/graph.json")`.

Interpret the result:

- **Success** (graph loaded, or a file-not-found / empty-graph response from the file layer — the expected first-run case): the MCP is available. Proceed with graph tracking. Load any other `mcp__dependency-graph__dag_*` tool schemas via `ToolSearch` as you need them.
- **Tool-unavailable failure** (`ToolSearch` returns no match for the probe, or the call returns an MCP-server-unavailable error): skip graph tracking entirely for this session and proceed without it.

Note: the server must be registered in Claude Code under the name `dependency-graph` — the probe queries and this plugin's hooks match tools named `mcp__dependency-graph__*`. If it is registered under a different name, the probe will report it unavailable and the rigor hooks will not fire.

## Session Start (when available)

1. `dag_load(".dew/graph.json")` — already performed by the probe above. A missing file means an empty graph; that is expected in the first stage.
2. `dag_save(".dew/graph.json", auto_save=true)` — enable auto-save for all subsequent mutations.
3. `dag_status` — orient yourself: what exists, what is done, what is pending across stage namespaces.
4. Create the stage's own nodes and wire dependencies as specified in the invoking skill's DAG Integration section.

## Driving Work

Use `dag_next` to get the next actionable task. Work through it in the conversation, then call `dag_done(id, summary)` with a concrete summary of what was concluded — specific enough to act on later, never a vague "done". Then call `dag_next` again. Let the graph drive the order; do not advance past a node that is not yet done. Continue until `dag_next` returns no more actionable tasks for the stage.
