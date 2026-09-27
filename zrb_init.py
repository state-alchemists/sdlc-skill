import os

from zrb import CmdTask, Group, cli

_DIR = os.path.dirname(__file__)


# SKILL =======================================================================

skill_group = cli.add_group(Group(name="skill", description="🧩 Skill maintenance"))

test_skills = skill_group.add_task(
    CmdTask(
        name="test-skills",
        description="Run every check CI runs (bin/test.sh)",
        cwd=_DIR,
        cmd="bin/test.sh",
    ),
    alias="test",
)

# INSTALL =====================================================================

install_skills = skill_group.add_task(
    CmdTask(
        name="install-skills",
        description="Install the sdlc-* skills into detected AI coding tools",
        cwd=_DIR,
        cmd="bin/install.sh",
    ),
    alias="install",
)
