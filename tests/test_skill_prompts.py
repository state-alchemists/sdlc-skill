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
        case_adopt_is_the_last_command_of_the_legacy_journey,
        case_writing_skills_read_the_annotation_reference,
        case_templates_ask_for_a_date_not_a_date_format,
        case_shipped_config_is_valid_json,
        case_annotation_covers_every_hazard_that_broke_a_file,
        case_review_asks_for_independence_confirmation,
        case_review_caps_verdict_without_fresh_context,
        case_review_handoffs_reference_the_rule,
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


def case_adopt_is_the_last_command_of_the_legacy_journey():
    """A legacy project needs `/sdlc-init` then `/sdlc-adopt`, and must not be
    sent back to `/sdlc-init` a third time.

    `/sdlc-init` cannot finish setup on a legacy layout -- writing
    `.sdlc/docs/product.md` beside the project's own `docs/product.md` would
    create a parallel tree -- so it installs scaffolding and stops. The obvious
    fix was a second `/sdlc-init` afterwards, which is what the docs said, and
    it was wrong: it sent the user back to a skill whose legacy branch stops
    again for the same reason. `/sdlc-adopt` relocates the documents, and once
    they are under `.sdlc/` the parallel-tree objection is gone, so adopt is
    where setup finishes.

    Three things have to stay true together, and drifting any one of them
    restores the three-command journey silently.
    """
    init_text = read_text(get_skill_path("sdlc-init"))
    adopt_text = read_text(get_skill_path("sdlc-adopt"))

    # 1. init's action block no longer lists a second init.
    #    Assert on the block itself, not the whole file: the file legitimately
    #    says "do not tell the user to re-run /sdlc-init", and a substring check
    #    cannot tell a prohibition from an instruction.
    blocks = re.findall(r"```\n(Next, in a fresh session:.*?)\n```", init_text, re.S)
    assert blocks, "sdlc-init's legacy path carries no action block"
    for block in blocks:
        assert "/sdlc-init" not in block, (
            "sdlc-init's action block sends the user back to /sdlc-init, so "
            "setup needs three commands instead of two"
        )
    # 2. init still refuses to write steering documents on the legacy path,
    #    and the reason is on the branch that acts on it. Checking the phrase
    #    anywhere in the file is too weak: "parallel tree" also appears in the
    #    transition message, so deleting the reason from the branch still left
    #    the case green.
    branch = [
        line
        for line in init_text.splitlines()
        if line.lstrip().startswith("- **Legacy layout confirmed**")
    ]
    assert len(branch) == 1, "sdlc-init's legacy branch is missing or duplicated"
    assert "parallel tree" in branch[0], (
        "sdlc-init's legacy branch stopped explaining why it writes no steering "
        "documents; without that the early stop looks like a bug to fix"
    )
    # 3. adopt completes setup rather than only filling a structure.
    completion_markers = "Mode A tail"
    assert completion_markers in adopt_text, (
        "sdlc-adopt no longer carries the setup-completion step, so a legacy "
        "project ends up adopted with no rules.md"
    )
    assert (
        ".sdlc/rules.md" in adopt_text
    ), "sdlc-adopt never mentions the constitution it is supposed to derive"
    # 4. No document may still claim adopt only fills a structure. The phrase
    #    "fills a structure; it does not create one" survived the mode that
    #    creates five documents, and it was repeated in README.md -- a model
    #    reading top-down meets the contradiction before the correction.
    for label, text in (
        ("sdlc-adopt", adopt_text),
        ("README.md", read_text("README.md")),
    ):
        assert "fills a structure" not in text and "does not create one" not in text, (
            "%s still says /sdlc-adopt only fills a structure, contradicting the "
            "setup it now completes" % label
        )
    # 5. adopt's frontmatter description is its public contract -- it is what a
    #    runtime shows when choosing a skill -- so it has to mention the
    #    terminal step too.
    frontmatter = adopt_text.split("---")[1]
    assert "rules.md" in frontmatter, (
        "sdlc-adopt's description omits completing setup, so the skill looks "
        "like a relocation tool"
    )
    # 6. The setup steps live in exactly one file. Restating /sdlc-init's
    #    Phase 3b-5 body inside sdlc-adopt is how the two copies start, and the
    #    copy that goes stale is whichever one the model reads second. Adopt may
    #    *name* what it defers to -- it names the phases and the sentinel -- but
    #    it must not reproduce the instruction bodies themselves.
    assert (
        "Phase 3b" in adopt_text and "Phase 5" in adopt_text
    ), "sdlc-adopt's setup tail no longer names the /sdlc-init phases it runs"
    restated = [
        "Templates come from `.sdlc/templates/`",
        "Read the template, fill its `{{placeholders}}`",
        "Re-read the freshly written steering documents first",
        "Rules describe what must **always** be true and **never** happen",
    ]
    found = [s for s in restated if s in adopt_text.split("## Mode B")[0]]
    assert not found, (
        "sdlc-adopt restates /sdlc-init's setup instructions (%s) instead of deferring to that skill"
        % found
    )
    # 7. /sdlc-init stops only where the parallel-tree hazard is live. A project
    #    already under .sdlc/ has no hazard, and sending it to /sdlc-adopt makes
    #    it run a relocation with nothing to relocate.
    init_branches = init_text.split("### Phase 2")[0]
    assert "already under `.sdlc/`" in init_branches, (
        "sdlc-init has no branch for a project whose artifacts are already at "
        "the canonical paths, so such a project is stopped and sent to "
        "/sdlc-adopt for a relocation it does not need"
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


def case_review_asks_for_independence_confirmation():
    """A review verdict inherits the independence of the session that ran it.

    `/sdlc-review` is Tier-3: nothing pauses to ask whether the review is the
    same session that wrote the code. The fix is a mandatory question at the
    start of the review — an APPROVE from a session that created what it is
    reviewing is a self-declared pass. The gate must survive as a question, so
    the assertion is on the question and the contamination sources it names.
    """
    text = read_text(get_skill_path("sdlc-review"))
    assert "independence gate" in text, (
        "sdlc-review no longer runs an independence gate before reviewing"
    )
    assert "this session" in text, (
        "sdlc-review's independence gate does not ask about this session"
    )
    for source in ("/sdlc-implement", "/sdlc-quickfix", "Mode C"):
        assert source in text, (
            "sdlc-review's independence gate omits a contamination source: %s"
            % source
        )


def case_review_caps_verdict_without_fresh_context():
    """A contaminated review may criticise but must not approve.

    The validator-fallback path already caps the verdict — "an APPROVE with no
    deterministic pass is a false pass" — and a review that ran in the
    implementing session is the same shape of false pass. The cap has to be a
    rule in the skill and visible on the artifact it produces, or the verdict
    is a self-declared APPROVE again.
    """
    review_text = read_text(get_skill_path("sdlc-review"))
    assert "cap the verdict at COMMENT" in review_text, (
        "sdlc-review no longer caps an in-session verdict at COMMENT"
    )
    report_template = read_text(
        os.path.join(TEMPLATES_DIRECTORY, "review-report.md")
    )
    assert "## Review Context" in report_template, (
        "the review report template does not record the context the verdict "
        "depends on"
    )
    conventions = read_text(os.path.join(ASSETS_DIRECTORY, "CONVENTIONS.md"))
    assert re.search(r"^## Review independence", conventions, re.M), (
        "CONVENTIONS.md no longer defines the review-independence rule, so "
        "the skills can drift a copy each"
    )


def case_review_handoffs_reference_the_rule():
    """Every skill that hands the user to `/sdlc-review` states the fresh
    session is for independence — and points at the rule, not a copy of it.

    sdlc-implement's action block and sdlc-quickfix's inline review are the two
    places a user actually learns the discipline. If the consequence (verdict
    capped) is left to the review itself, the fresh-session note reads as
    etiquette, which is exactly the drift this rule exists to prevent. The
    assertion is on the shared `Review independence` anchor so the rule lives
    in one file and the references cannot fork."""
    for skill_name in ("sdlc-implement", "sdlc-quickfix"):
        text = read_text(get_skill_path(skill_name))
        assert "Review independence" in text, (
            "%s hands off to the review without referencing the independence "
            "rule, so a user learns the fresh-session cost only from the report"
            % skill_name
        )


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
