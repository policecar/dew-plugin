#!/usr/bin/env python3
"""dew workflow mechanics.

This script owns the mechanical half of the dew workflow: state
transitions, artifact-existence checks, cycle archiving, and git commits
at stage boundaries. The conversational half — the stage dialogues and
the writing of stage artifacts — stays with the skills.

State model:
  .dew/state.json  — canonical state, written only by this script
  .dew/state.md    — human-readable view, regenerated on every mutation
                     (kept for git-diffable audit trails; never hand-edit)

Exit codes:
  0  success
  2  usage error / invalid input
  3  precondition failed (no active project, missing artifact, ...)
  4  git operation refused or failed
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

DEW = Path(".dew")
STATE_JSON = DEW / "state.json"
STATE_MD = DEW / "state.md"
CONTEXT_MD = DEW / "context.md"

SEQUENCES = {
    "full": ["discover", "design", "demonstrate", "develop", "document", "debrief"],
    "fast": ["plan", "build", "verify"],
}

# Artifact each stage must produce before `done` will advance past it.
# None: the codebase itself is the artifact. A path ending in "/" is a
# directory that must exist and be non-empty.
ARTIFACTS = {
    "discover": ".dew/docs/01-discover.md",
    "design": ".dew/docs/02-design.md",
    "demonstrate": ".dew/design-verification/DESIGN_VERIFICATION.md",
    "develop": None,
    "document": "docs/",
    "debrief": ".dew/docs/06-debrief.md",
    "plan": ".dew/docs/fast-plan.md",
    "build": None,
    "verify": ".dew/docs/fast-debrief.md",
}

PROJECT_TYPES = ("new-project", "major-feature", "revisit-fix")
BRANCH_MODES = ("worktree", "branch", "stay")


def fail(code, msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def today():
    return date.today().isoformat()


# ---------------------------------------------------------------- git helpers


def git(*args, check=True):
    p = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        fail(4, f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p


def is_git_repo():
    return subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True).returncode == 0


def dew_gitignored():
    return subprocess.run(["git", "check-ignore", "-q", str(DEW)], capture_output=True).returncode == 0


def commit_mode():
    if not is_git_repo():
        return "skip (not a git repository)"
    if dew_gitignored():
        return "skip (.dew is gitignored — artifacts are ephemeral)"
    return "enabled"


def current_branch():
    return git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def on_default_branch():
    branch = current_branch()
    p = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False)
    if p.returncode == 0:
        return branch == p.stdout.strip().split("/")[-1]
    return branch in ("main", "master")


def info(msg):
    """Progress/status notes go to stderr so stdout stays clean JSON."""
    print(msg, file=sys.stderr)


def guard_branch(state, allow_default):
    """Refuse default-branch commits BEFORE any state mutation, so a refused
    commit never leaves the state file advanced past the actual git history."""
    if commit_mode() != "enabled":
        return
    if on_default_branch() and state.get("branch_mode") != "stay" and not allow_default:
        fail(4, "refusing to commit on the default branch: dew work belongs on a "
                "dew/<project> branch or worktree. Confirm with the user, then "
                "either re-run with --allow-default-branch or move to a branch.")


def commit(state, message, extra_paths=(), allow_default=False):
    mode = commit_mode()
    if mode != "enabled":
        info(f"commit skipped: {mode}")
        return
    guard_branch(state, allow_default)
    git("add", "-A", "--", str(DEW))
    for p in extra_paths:
        if Path(p.rstrip("/")).exists():
            git("add", "-A", "--", p.rstrip("/"))
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
        info("commit skipped: nothing staged")
        return
    git("commit", "-m", message)
    info(f"committed: {message}")


# ------------------------------------------------------------------- state io


def load_state():
    if STATE_JSON.exists():
        try:
            return json.loads(STATE_JSON.read_text())
        except json.JSONDecodeError as e:
            fail(3, f"{STATE_JSON} is corrupt ({e}); restore it from git history or re-init")
    if STATE_MD.exists():
        fail(3, "found legacy .dew/state.md without .dew/state.json — this cycle "
                "predates script-managed state. Run init to start a fresh cycle "
                "(the legacy files are archived automatically).")
    fail(3, "no active dew project (.dew/state.json not found); run init")


def save_state(state):
    state["project"]["last_updated"] = today()
    DEW.mkdir(exist_ok=True)
    STATE_JSON.write_text(json.dumps(state, indent=2) + "\n")
    STATE_MD.write_text(render_md(state))


def new_state(name, workflow, ptype, branch_mode):
    return {
        "project": {"name": name, "workflow": workflow, "type": ptype,
                    "started": today(), "last_updated": today()},
        "active_stage": SEQUENCES[workflow][0],
        "active_status": "pending",
        "branch_mode": branch_mode,
        "stages": {s: {"status": "pending", "started": None, "completed": None,
                       "visits": 0, "notes": ""} for s in SEQUENCES[workflow]},
        "backtracks": [],
    }


def render_md(state):
    p = state["project"]
    seq = SEQUENCES[p["workflow"]]
    lines = [
        "# dew Save State",
        "",
        "_Rendered by scripts/dew.py — do not edit by hand; canonical state is `.dew/state.json`._",
        "",
        "## Project",
        f"- **Name**: {p['name']}",
        f"- **Workflow**: {p['workflow']}",
        f"- **Type**: {p['type']}",
        f"- **Branch mode**: {state.get('branch_mode', 'unknown')}",
        f"- **Started**: {p['started']}",
        f"- **Last Updated**: {p['last_updated']}",
        "",
        "## Active Stage",
        f"**Stage**: {state['active_stage']}",
        f"**Status**: {state['active_status']}",
        "",
        "## Stage Log",
        "<!-- Status: pending | in-progress | complete | needs-revisit -->",
        "| Stage | Status | Artifact | Started | Completed | Visits |",
        "|-------|--------|----------|---------|-----------|--------|",
    ]
    for s in seq:
        e = state["stages"][s]
        art = ARTIFACTS[s] or "(codebase)"
        lines.append(f"| {s} | {e['status']} | {art} | {e['started'] or '—'} "
                     f"| {e['completed'] or '—'} | {e['visits']} |")
    lines += ["", "## Backtrack Log"]
    if state["backtracks"]:
        lines += ["| Date | From | To | Reason |", "|------|------|----|--------|"]
        for b in state["backtracks"]:
            lines.append(f"| {b['date']} | {b['from']} | {b['to']} | {b['reason']} |")
    else:
        lines.append("(none yet)")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------- mechanics


def artifact_status(stage):
    art = ARTIFACTS[stage]
    if art is None:
        return True, "(codebase — no artifact file expected)"
    path = Path(art.rstrip("/"))
    if art.endswith("/"):
        ok = path.is_dir() and any(path.iterdir())
        return ok, f"directory {art} {'present and non-empty' if ok else 'missing or empty'}"
    ok = path.is_file() and path.stat().st_size > 0
    return ok, f"file {art} {'present' if ok else 'missing or empty'}"


def mark_entered(state, stage):
    e = state["stages"][stage]
    if e["status"] != "in-progress":
        e["status"] = "in-progress"
        e["visits"] += 1
        e["started"] = e["started"] or today()
    state["active_status"] = "in-progress"


def stage_brief(state):
    stage = state["active_stage"]
    seq = SEQUENCES[state["project"]["workflow"]]
    brief = {
        "project": state["project"]["name"],
        "workflow": state["project"]["workflow"],
        "active_stage": stage,
        "active_status": state["active_status"],
    }
    if stage != "complete":
        i = seq.index(stage)
        brief["artifact"] = ARTIFACTS[stage] or "(codebase)"
        brief["next_stage"] = seq[i + 1] if i + 1 < len(seq) else "complete"
        brief["revisit"] = state["stages"][stage]["visits"] > 1
    brief["needs_revisit"] = [s for s in seq if state["stages"][s]["status"] == "needs-revisit"]
    brief["recent_backtracks"] = state["backtracks"][-3:]
    return brief


def archive_previous():
    if not (STATE_JSON.exists() or STATE_MD.exists()):
        return None
    old_name = "previous"
    try:
        old_name = json.loads(STATE_JSON.read_text())["project"]["name"]
    except Exception:
        pass
    dest = DEW / f"{date.today().strftime('%y%m%d')}-{old_name}"
    final, i = dest, 0
    while final.exists():
        i += 1
        final = Path(f"{dest}-{i}")
    final.mkdir(parents=True)
    for item in ("docs", "state.json", "state.md", "context.md", "graph.json",
                 "design-verification"):
        src = DEW / item
        if src.exists():
            src.rename(final / item)
    return final


# ---------------------------------------------------------------- subcommands


def cmd_init(args):
    name = args.name.strip()
    if not name or any(c in name for c in " /\\"):
        fail(2, "project name must be a slug (no spaces or slashes)")
    if args.workflow not in SEQUENCES:
        fail(2, f"workflow must be one of: {', '.join(SEQUENCES)}")

    if args.branch_mode == "worktree":
        if not is_git_repo():
            fail(4, "worktree mode requires a git repository")
        wt = Path(".worktrees") / name
        git("worktree", "add", str(wt), "-b", f"dew/{name}")
        print(f"worktree created at {wt} on branch dew/{name}")
        print("NOTE: .dew state is per-checkout. Tell the user to restart Claude "
              f"Code inside {wt} and run /dew new again there; this checkout was "
              "left untouched and no state was created here.")
        return
    if args.branch_mode == "branch" and is_git_repo():
        branch = f"dew/{name}"
        if git("rev-parse", "--verify", branch, check=False).returncode == 0:
            git("checkout", branch)
            print(f"checked out existing branch {branch}")
        else:
            git("checkout", "-b", branch)
            print(f"created and checked out branch {branch}")

    archived = archive_previous()
    if archived:
        print(f"previous cycle archived to {archived}")
    (DEW / "docs").mkdir(parents=True, exist_ok=True)
    state = new_state(name, args.workflow, args.type, args.branch_mode)
    save_state(state)
    commit(state, f"dew(init): begin dew for {name}",
           allow_default=args.allow_default_branch)
    print(f"initialized {args.workflow} workflow for {name}; "
          f"first stage: {state['active_stage']} (run `enter` to begin)")


def cmd_enter(args):
    state = load_state()
    if state["active_stage"] == "complete":
        fail(3, "workflow is complete; run init to start a new cycle")
    mark_entered(state, state["active_stage"])
    save_state(state)
    print(json.dumps(stage_brief(state), indent=2))


def cmd_done(args):
    state = load_state()
    stage = state["active_stage"]
    if stage == "complete":
        fail(3, "workflow already complete")
    ok, desc = artifact_status(stage)
    if not ok:
        fail(3, f"stage artifact not ready: {desc}. The stage skill writes this "
                "artifact at the stage's conclusion — return to the stage "
                "conversation to finish it; do not reconstruct it from memory.")
    guard_branch(state, args.allow_default_branch)
    seq = SEQUENCES[state["project"]["workflow"]]
    e = state["stages"][stage]
    e["status"] = "complete"
    e["completed"] = today()
    i = seq.index(stage)
    nxt = seq[i + 1] if i + 1 < len(seq) else "complete"
    state["active_stage"] = nxt
    state["active_status"] = "complete" if nxt == "complete" else "pending"
    save_state(state)
    extra = ("docs/",) if stage == "document" else ()
    commit(state, f"dew({stage}): complete {stage} for {state['project']['name']}",
           extra_paths=extra, allow_default=args.allow_default_branch)
    out = {"completed": stage, "artifact": desc, "next_stage": nxt}
    if nxt != "complete":
        out["next_artifact"] = ARTIFACTS[nxt] or "(codebase)"
        out["reminder"] = ("Tell the user to run /clear and then /dew to begin "
                           "the next stage with a clean context.")
    else:
        out["reminder"] = "Cycle complete. Suggest /dew new for the next cycle."
    print(json.dumps(out, indent=2))


def cmd_back(args):
    state = load_state()
    seq = SEQUENCES[state["project"]["workflow"]]
    target = args.stage
    if target not in seq:
        fail(2, f"unknown stage {target!r} for this workflow ({', '.join(seq)})")
    cur = state["active_stage"]
    cur_i = len(seq) if cur == "complete" else seq.index(cur)
    if seq.index(target) >= cur_i:
        fail(2, f"{target} is not earlier than the active stage ({cur}); use jump for forward moves")
    guard_branch(state, args.allow_default_branch)
    upper = cur_i if cur == "complete" else cur_i + 1
    for s in seq[seq.index(target) + 1 : upper]:
        if state["stages"][s]["status"] in ("complete", "in-progress"):
            state["stages"][s]["status"] = "needs-revisit"
    state["active_stage"] = target
    mark_entered(state, target)
    state["backtracks"].append({"date": today(), "from": cur, "to": target,
                                "reason": args.reason})
    save_state(state)
    commit(state, f"dew(backtrack): return to {target} — {args.reason}",
           allow_default=args.allow_default_branch)
    print(json.dumps(stage_brief(state), indent=2))


def cmd_jump(args):
    state = load_state()
    seq = SEQUENCES[state["project"]["workflow"]]
    if args.stage not in seq:
        fail(2, f"unknown stage {args.stage!r} for this workflow ({', '.join(seq)})")
    state["active_stage"] = args.stage
    mark_entered(state, args.stage)
    save_state(state)
    print(json.dumps(stage_brief(state), indent=2))


def cmd_pause(args):
    state = load_state()
    if not CONTEXT_MD.exists() or CONTEXT_MD.stat().st_size == 0:
        fail(3, "write the context snapshot to .dew/context.md first (synthesizing "
                "it is the skill's job), then run pause again")
    commit(state, f"dew(pause): {state['active_stage']} for {state['project']['name']}",
           allow_default=args.allow_default_branch)
    print("paused; context snapshot committed. Safe to quit — /dew resume picks up.")


def cmd_consume_context(args):
    if CONTEXT_MD.exists():
        CONTEXT_MD.unlink()
        print("context snapshot deleted; the deletion is committed at the next "
              "stage boundary (done/backtrack/pause).")
    else:
        print("no context snapshot to consume")


def cmd_status(args):
    state = load_state()
    p = state["project"]
    seq = SEQUENCES[p["workflow"]]
    marks = {"complete": "✓", "in-progress": "→", "needs-revisit": "!", "pending": " "}
    print(f"dew: {p['name']} ({p['type']})  [{p['workflow']}]")
    print("─" * 45)
    for s in seq:
        e = state["stages"][s]
        note = f"completed {e['completed']}" if e["status"] == "complete" else e["status"]
        print(f"  [{marks.get(e['status'], ' ')}] {s:<12} {note}")
    print(f"\nBacktracks:  {len(state['backtracks'])}")
    print("Artifacts:")
    for s in seq:
        if ARTIFACTS[s] is None:
            continue
        ok, _ = artifact_status(s)
        print(f"  {ARTIFACTS[s]:<50} {'✓' if ok else '—'}")
    branch = current_branch() if is_git_repo() else "(no git)"
    print(f"\nCommit mode: {commit_mode()};  branch: {branch}")


def cmd_state(args):
    state = load_state()
    print(json.dumps({"state": state, "brief": stage_brief(state)}, indent=2))


def main():
    ap = argparse.ArgumentParser(description="dew workflow mechanics (state, artifacts, commits)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def allow(p):
        p.add_argument("--allow-default-branch", action="store_true",
                       help="permit committing on the default branch (user-confirmed)")

    p = sub.add_parser("init", help="start a new cycle (archives any previous one)")
    p.add_argument("--name", required=True, help="slug-friendly project name")
    p.add_argument("--workflow", required=True, choices=list(SEQUENCES))
    p.add_argument("--type", required=True, choices=PROJECT_TYPES)
    p.add_argument("--branch-mode", required=True, choices=BRANCH_MODES)
    allow(p)
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("enter", help="mark the active stage entered; print its brief")
    p.set_defaults(fn=cmd_enter)

    p = sub.add_parser("done", help="verify artifact, complete stage, advance, commit")
    allow(p)
    p.set_defaults(fn=cmd_done)

    p = sub.add_parser("back", help="backtrack to an earlier stage")
    p.add_argument("stage")
    p.add_argument("--reason", required=True)
    allow(p)
    p.set_defaults(fn=cmd_back)

    p = sub.add_parser("jump", help="set the active stage without a backtrack reason")
    p.add_argument("stage")
    p.set_defaults(fn=cmd_jump)

    p = sub.add_parser("pause", help="commit an already-written .dew/context.md snapshot")
    allow(p)
    p.set_defaults(fn=cmd_pause)

    p = sub.add_parser("consume-context", help="delete the snapshot after resuming")
    p.set_defaults(fn=cmd_consume_context)

    p = sub.add_parser("status", help="human-readable status report")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("state", help="machine-readable state JSON")
    p.set_defaults(fn=cmd_state)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
