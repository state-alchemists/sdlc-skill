import os
import sys

from zrb import CmdTask, Group, cli
from zrb.builtin.git import git_commit

_DIR = os.path.dirname(__file__)
_PYTHON = sys.executable


# SKILL =======================================================================

skill_group = cli.add_group(
    Group(name="skill", description="🧩 Skill maintenance")
)

# Regenerate every bundled copy (the validator + shared templates) from the
# single source under scripts/. The installer copies skill dirs verbatim and
# never runs this tooling, so the bundled copies must be committed — this task
# keeps them from drifting.
sync_skills = skill_group.add_task(
    CmdTask(
        name="sync-skills",
        description="Copy scripts/ + shared templates into the skills that need them",
        cwd=_DIR,
        cmd=f"{_PYTHON} scripts/sync_skills.py",
    ),
    alias="sync",
)

# CI / pre-push guard: fail (exit 1) if any bundled copy has drifted from its
# source. Does not write anything.
check_skills = skill_group.add_task(
    CmdTask(
        name="check-skills-sync",
        description="Verify bundled scripts/templates are in sync (no writes)",
        cwd=_DIR,
        cmd=f"{_PYTHON} scripts/sync_skills.py --check",
    ),
    alias="check",
)

# Validator self-test against the bundled fixtures, plus eval-case lint.
test_skills = skill_group.add_task(
    CmdTask(
        name="test-skills",
        description="Lint eval cases and smoke-test the validator",
        cwd=_DIR,
        cmd=f"{_PYTHON} evals/run.py",
    ),
    alias="test",
)

# Never commit drifted copies: sync runs before any commit.
sync_skills >> git_commit
