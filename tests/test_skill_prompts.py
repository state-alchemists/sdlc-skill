#!/usr/bin/env python3
"""Static invariants over the skill prompts.

The prompts are the product, and CI could not see them: it compiled the Python,
ran the validator tests, and linted the eval case structure, none of which look
at a SKILL.md. Every invariant here is one that actually regressed.

This does not test behaviour. It tests the properties the behaviour depends on,
which is the part a parser can hold onto. Run it directly:

    python3 tests/test_skill_prompts.py

Exit 0 means every case passed; a failed assertion names the case.
"""

import os
import re
import sys

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIRECTORY = os.path.join(REPOSITORY_ROOT, "skills")
ASSETS_DIRECTORY = os.path.join(SKILLS_DIRECTORY, "sdlc-init", "assets")
TEMPLATES_DIRECTORY = os.path.join(ASSETS_DIRECTORY, "templates")

# The three skills that write or edit code, and therefore emit headers.
WRITING_SKILL_NAMES = ("sdlc-implement", "sdlc-quickfix", "sdlc-adopt")

# A bare `src/` or `tests/` outside a fenced example is a layout assumption.
# Fenced blocks are illustrations; `.sdlc/...` paths are this tool's own.
LAYOUT_PATH_PATTERN = re.compile(r"(?<![\w./`])(?:src|tests)/")
CODE_FENCE_PATTERN = re.compile(r"^\s*```")
LEGACY_BLOCK_PATTERN = re.compile(
    r"<!-- legacy-detection:start -->.*?<!-- legacy-detection:end -->", re.S
)


def main():
    """Run every case, printing one line each, and return an exit code."""
    cases = [
        case_no_skill_hardcodes_the_source_or_test_layout,
        case_implement_forbids_editing_the_spec,
        case_no_skill_still_says_generated_from_spec,
        case_legacy_detection_rule_is_identical_everywhere,
        case_every_skill_reads_the_conventions,
        case_every_transition_is_an_action_block,
        case_writing_skills_read_the_annotation_reference,
        case_templates_ask_for_a_date_not_a_date_format,
        case_shipped_config_is_valid_json,
        case_annotation_covers_every_hazard_that_broke_a_file,
    ]
    failures = []
    for case in cases:
        try:
            case()
            print("PASS  %s" % case.__name__)
        except Exception as error:  # a crash is a failed case, not a lost run
            failures.append((case.__name__, error))
            print("FAIL  %s — %s: %s" % (case.__name__, type(error).__name__, error))

    print("\n%d case(s), %d failed" % (len(cases), len(failures)))
    return 1 if failures else 0


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------
def case_no_skill_hardcodes_the_source_or_test_layout():
    """`src/` + `tests/` is the greenfield default, not every project's layout.

    Thirteen sites across five files assumed it, while the validator itself was
    layout-agnostic the whole time. A fenced block is an illustration and an
    explicit `<!-- layout-ok -->` marks a deliberate mention.
    """
    offenders = []
    for skill_name, path in get_skill_paths():
        for line_number, line in get_unfenced_lines(read_text(path)):
            if "<!-- layout-ok -->" in line:
                continue
            if LAYOUT_PATH_PATTERN.search(line):
                offenders.append(
                    "%s:%d" % (os.path.relpath(path, REPOSITORY_ROOT), line_number)
                )
    assert not offenders, (
        "a skill hardcodes src/ or tests/ instead of reading the project's "
        "layout: %s" % ", ".join(offenders)
    )


def case_implement_forbids_editing_the_spec():
    """The cheapest way to clear a trace-code error is to delete the requirement.

    sdlc-quickfix has always said so; sdlc-implement did not, while telling the
    model to treat validator errors as failures to fix, with a retry loop.
    """
    text = read_text(get_skill_path("sdlc-implement"))
    assert re.search(
        r"Do NOT modify[^\n]{0,120}\.sdlc", text
    ), "sdlc-implement does not forbid the sub-agent from editing the spec"
    assert (
        "git diff --name-only -- .sdlc/" in text
    ), "sdlc-implement does not verify the spec was left alone"


def case_no_skill_still_says_generated_from_spec():
    """One token everywhere. `SPEC:` is a prefix of the old one, so a grep
    written for it already matches both; the reverse is impossible."""
    offenders = [
        os.path.relpath(path, REPOSITORY_ROOT)
        for _, path in get_skill_paths()
        if "GENERATED FROM SPEC" in read_text(path)
    ]
    assert (
        not offenders
    ), "these files still use the retired header token: %s" % ", ".join(offenders)


def case_every_transition_is_an_action_block():
    """A skill that is stateless between sessions has exactly one place to tell
    the user what comes next: its transition message.

    The failure this guards is drift back to prose. "run /sdlc-spec <feature>
    (e.g. `User Auth` -> slug `user-auth`)" asks the user to apply the kebab-case
    rule correctly, by hand, at the moment of highest friction — when the skill
    already resolved the slug and could have printed it. So: no skill may ship a
    placeholder in its transition, and every skill must point at the shared
    convention that defines the block's shape.
    """
    handoff_reference = "Session handoff"
    assert handoff_reference in read_text(
        os.path.join(ASSETS_DIRECTORY, "CONVENTIONS.md")
    ), "CONVENTIONS.md no longer defines the session handoff block"

    offenders = []
    for skill_name, path in get_skill_paths():
        text = read_text(path)
        if handoff_reference not in text:
            offenders.append("%s never references the handoff convention" % skill_name)
            continue
        # `<slug>` is legitimate as an instruction to the model; it is not
        # legitimate as something the user is told to paste.
        if "To continue:" in text:
            offenders.append(
                "%s still ships a prose 'To continue:' transition" % skill_name
            )
    assert not offenders, "; ".join(offenders)


def case_legacy_detection_rule_is_identical_everywhere():
    """One rule, three copies, and drift between them is what produced a
    day-one false positive on any project with a docs/architecture.md."""
    paths = [
        get_skill_path("sdlc-init"),
        get_skill_path("sdlc-adopt"),
        os.path.join(ASSETS_DIRECTORY, "CONVENTIONS.md"),
    ]
    blocks = {}
    for path in paths:
        match = LEGACY_BLOCK_PATTERN.search(read_text(path))
        assert match, "%s carries no legacy-detection block" % os.path.relpath(
            path, REPOSITORY_ROOT
        )
        blocks[path] = match.group(0)
    assert (
        len(set(blocks.values())) == 1
    ), "the legacy-detection blocks have drifted apart: %s" % ", ".join(
        os.path.relpath(path, REPOSITORY_ROOT) for path in paths
    )


def case_every_skill_reads_the_conventions():
    """CONVENTIONS.md is the single source of truth every skill claims to read."""
    for skill_name, path in get_skill_paths():
        assert "CONVENTIONS.md" in read_text(path), (
            "%s never reads .sdlc/CONVENTIONS.md" % skill_name
        )


def case_writing_skills_read_the_annotation_reference():
    """A header above a shebang, an encoding line or an XML prolog does not
    produce an untidy file — it produces one that no longer runs."""
    for skill_name in WRITING_SKILL_NAMES:
        assert "ANNOTATION.md" in read_text(get_skill_path(skill_name)), (
            "%s writes headers but never reads .sdlc/ANNOTATION.md" % skill_name
        )


def case_templates_ask_for_a_date_not_a_date_format():
    """`{{YYYY-MM-DD}}` is satisfied by any correctly shaped string, so a model
    invents one. `{{TODAY}}` reads as a value it has to go and obtain."""
    offenders = []
    for file_name in sorted(os.listdir(TEMPLATES_DIRECTORY)):
        text = read_text(os.path.join(TEMPLATES_DIRECTORY, file_name))
        if re.search(r"\{\{YYYY-MM-DD", text):
            offenders.append(file_name)
    assert not offenders, (
        "these templates ask for a date FORMAT rather than today's date: %s"
        % ", ".join(offenders)
    )


def case_shipped_config_is_valid_json():
    """A config that does not parse is worse than no config: the validator
    reports it as an error and every layout declaration in it is lost."""
    import json

    config_path = os.path.join(ASSETS_DIRECTORY, "config.json")
    with open(config_path, encoding="utf-8") as file_handle:
        config = json.load(file_handle)
    for section in ("layout", "headings", "comments", "gate", "scan"):
        assert section in config, (
            "the shipped config.json is missing its '%s' section" % section
        )
    assert config["gate"]["enforce_tag_roles"] is True, (
        "the shipped config ships the migration ramp switched on, which would "
        "hand every new project the pre-migration gate"
    )


def case_annotation_covers_every_hazard_that_broke_a_file():
    """Each of these was reproduced against a real parser, not guessed."""
    text = read_text(os.path.join(ASSETS_DIRECTORY, "ANNOTATION.md"))
    for hazard in (
        "shebang",
        "PEP 263",
        "<?php",
        "prolog",
        "docstring",
        "generated",
        "Makefile",
    ):
        assert hazard in text, "ANNOTATION.md does not mention the %r hazard" % hazard
    assert (
        re.search(r"`\.css`|\.css", text) and "not a CSS comment" in text
    ), "ANNOTATION.md does not warn that // is not a CSS comment"


# --------------------------------------------------------------------------
# Fixture helpers
# --------------------------------------------------------------------------
def get_skill_paths():
    """Yield (skill_name, SKILL.md path) for every sdlc-* skill."""
    for skill_name in sorted(os.listdir(SKILLS_DIRECTORY)):
        path = os.path.join(SKILLS_DIRECTORY, skill_name, "SKILL.md")
        if os.path.exists(path):
            yield skill_name, path


def get_skill_path(skill_name):
    """Return one skill's SKILL.md path."""
    return os.path.join(SKILLS_DIRECTORY, skill_name, "SKILL.md")


def get_unfenced_lines(text):
    """Yield (line_number, line) for every line outside a fenced code block."""
    is_inside_fence = False
    for line_number, line in enumerate(text.splitlines(), 1):
        if CODE_FENCE_PATTERN.match(line):
            is_inside_fence = not is_inside_fence
            continue
        if not is_inside_fence:
            yield line_number, line


def read_text(path):
    """Return a file's text."""
    with open(path, encoding="utf-8") as file_handle:
        return file_handle.read()


if __name__ == "__main__":
    sys.exit(main())
