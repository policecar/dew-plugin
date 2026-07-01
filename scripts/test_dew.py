#!/usr/bin/env python3
"""End-to-end self-test for scripts/dew.py, run in throwaway git repos.

Exercises: init (branch + stay modes), enter, artifact-gated done, the full
fast cycle, pause/consume-context (including the snapshot-deletion commit),
backtrack with needs-revisit marking, the default-branch guard, and cycle
archiving on re-init.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "dew.py"


def run(args, cwd, expect=0):
    p = subprocess.run([sys.executable, str(SCRIPT), *args],
                       cwd=cwd, capture_output=True, text=True)
    assert p.returncode == expect, (
        f"dew.py {args} -> rc={p.returncode} (expected {expect})\n"
        f"stdout: {p.stdout}\nstderr: {p.stderr}")
    return p.stdout


def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


def make_repo(tmp):
    sh(["git", "init", "-q", "-b", "main"], tmp)
    sh(["git", "config", "user.email", "test@test"], tmp)
    sh(["git", "config", "user.name", "test"], tmp)
    (Path(tmp) / "README.md").write_text("x\n")
    sh(["git", "add", "."], tmp)
    sh(["git", "commit", "-qm", "root"], tmp)


def test_fast_cycle(tmp):
    make_repo(tmp)
    run(["init", "--name", "demo", "--workflow", "fast", "--type", "new-project",
         "--branch-mode", "branch"], tmp)
    assert sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], tmp).strip() == "dew/demo"

    brief = json.loads(run(["enter"], tmp))
    assert brief["active_stage"] == "plan" and brief["revisit"] is False

    run(["done"], tmp, expect=3)  # plan artifact missing -> refuse
    (Path(tmp) / ".dew/docs/fast-plan.md").write_text("# plan\n")
    out = json.loads(run(["done"], tmp))
    assert out["completed"] == "plan" and out["next_stage"] == "build"

    json.loads(run(["enter"], tmp))
    out = json.loads(run(["done"], tmp))  # build has no artifact file
    assert out["next_stage"] == "verify"

    json.loads(run(["enter"], tmp))
    run(["pause"], tmp, expect=3)  # snapshot not written yet -> refuse
    (Path(tmp) / ".dew/context.md").write_text("# snapshot\n")
    run(["pause"], tmp)
    run(["consume-context"], tmp)
    assert not (Path(tmp) / ".dew/context.md").exists()

    (Path(tmp) / ".dew/docs/fast-debrief.md").write_text("# debrief\n")
    out = json.loads(run(["done"], tmp))
    assert out["next_stage"] == "complete"

    show = sh(["git", "show", "--name-status", "--format=", "HEAD"], tmp)
    assert "D\t.dew/context.md" in show, f"snapshot deletion not committed:\n{show}"

    state = json.loads((Path(tmp) / ".dew/state.json").read_text())
    assert state["active_stage"] == "complete"
    assert "do not edit by hand" in (Path(tmp) / ".dew/state.md").read_text()
    run(["done"], tmp, expect=3)  # already complete
    run(["status"], tmp)


def test_backtrack_guard_archive(tmp):
    make_repo(tmp)
    # stay mode: committing on main is explicitly allowed
    run(["init", "--name", "big", "--workflow", "full", "--type", "major-feature",
         "--branch-mode", "stay"], tmp)
    json.loads(run(["enter"], tmp))
    (Path(tmp) / ".dew/docs/01-discover.md").write_text("# d\n")
    run(["done"], tmp)
    json.loads(run(["enter"], tmp))
    (Path(tmp) / ".dew/docs/02-design.md").write_text("# d\n")
    run(["done"], tmp)

    run(["back", "develop", "--reason", "x"], tmp, expect=2)  # forward -> refuse
    brief = json.loads(run(["back", "discover", "--reason", "missed a stakeholder"], tmp))
    assert brief["active_stage"] == "discover" and brief["revisit"] is True
    state = json.loads((Path(tmp) / ".dew/state.json").read_text())
    assert state["stages"]["design"]["status"] == "needs-revisit"
    assert state["backtracks"][0]["reason"] == "missed a stakeholder"

    brief = json.loads(run(["jump", "design"], tmp))
    assert brief["active_stage"] == "design"

    # re-init archives the previous cycle
    run(["init", "--name", "next", "--workflow", "fast", "--type", "new-project",
         "--branch-mode", "stay"], tmp)
    archives = [p for p in (Path(tmp) / ".dew").iterdir()
                if p.is_dir() and p.name[0].isdigit()]
    assert archives and (archives[0] / "state.json").exists()
    state = json.loads((Path(tmp) / ".dew/state.json").read_text())
    assert state["project"]["name"] == "next" and state["active_stage"] == "plan"


def test_default_branch_guard(tmp):
    make_repo(tmp)
    # branch-mode branch, but force back onto main before committing
    run(["init", "--name", "guard", "--workflow", "fast", "--type", "new-project",
         "--branch-mode", "branch"], tmp)
    json.loads(run(["enter"], tmp))
    (Path(tmp) / ".dew/docs/fast-plan.md").write_text("# plan\n")
    sh(["git", "add", "-A"], tmp)
    sh(["git", "commit", "-qm", "wip"], tmp)
    sh(["git", "checkout", "-q", "main"], tmp)
    sh(["git", "merge", "-q", "dew/guard"], tmp)
    run(["done"], tmp, expect=4)  # on main without stay mode -> refuse
    out = json.loads(run(["done", "--allow-default-branch"], tmp))
    assert out["completed"] == "plan"


def main():
    tests = (test_fast_cycle, test_backtrack_guard_archive, test_default_branch_guard)
    for test in tests:
        tmp = tempfile.mkdtemp(prefix="dewtest-")
        try:
            test(tmp)
            print(f"PASS {test.__name__}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"all {len(tests)} tests passed")


if __name__ == "__main__":
    main()
