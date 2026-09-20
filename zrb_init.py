import os
import sys

from zrb import CmdTask, Group, cli

_DIR = os.path.dirname(__file__)
_PYTHON = sys.executable


# SKILL =======================================================================

skill_group = cli.add_group(
    Group(name="skill", description="🧩 Skill maintenance")
)

# Lint the eval cases and byte-compile the bundled scripts. There is nothing to
# sync: the validator and the templates exist once, under
# skills/sdlc-init/assets/, and the installer copies skill directories verbatim.
test_skills = skill_group.add_task(
    CmdTask(
        name="test-skills",
        description="Compile scripts, run validator tests, lint eval cases",
        cwd=_DIR,
        cmd=" && ".join([
            f"{_PYTHON} -m py_compile"
            " skills/sdlc-init/assets/tools/sdlc-validate.py"
            " evals/run.py tests/test_sdlc_validate.py zrb_init.py",
            f"{_PYTHON} tests/test_sdlc_validate.py",
            f"{_PYTHON} evals/run.py",
        ]),
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
