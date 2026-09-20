#!/usr/bin/env python3
"""sdlc-validate.py — deterministic validator for SDLC artifacts.

Installed into a project at `.sdlc/tools/sdlc-validate.py` by `/sdlc-init`.
Run it by hand, from a skill ("validate -> fix -> repeat"), or as a CI gate.
Stdlib only; Python 3.8+.

This file is the only copy — skills install it, none of them embed it.

USAGE
    python3 sdlc-validate.py [--root DIR] [--feature SLUG] [--strict] [--json]
                             [--exclude GLOB ...]

    --root DIR     Project root to scan (default: current directory).
    --feature SLUG Restrict FINDINGS to one feature. Every spec is still parsed,
                   so another feature's tags resolve instead of reporting as
                   dangling; only that feature's tags and requirements are
                   reported on.
    --strict       Make warnings exit non-zero too.
    --json         Emit a machine-readable JSON report instead of text.
    --exclude GLOB Skip files matching this glob when scanning for tags
                   (repeatable). Fenced code blocks in Markdown are skipped
                   already, so documented examples need no exclusion.

EXIT CODES
    0  clean (no errors; warnings allowed unless --strict)
    1  warnings present and --strict
    2  errors present

ID & TRACEABILITY SCHEME (see .sdlc/CONVENTIONS.md)
    - Each spec.md declares `**Feature Key:** KEY` (uppercase, globally unique).
    - Requirement IDs are per-feature (REQ-001, NFR-001, UT-001, ...) and made
      globally unambiguous by the key.
    - The test plan lives in spec.md under `## Test Plan`. A separate
      `.sdlc/tests/<slug>/test-plan.md` is read as a legacy fallback.
    - Source headers:  IMPLEMENTS: KEY:REQ-001, KEY:NFR-002
    - Test headers:    COVERS: KEY:REQ-002, KEY:UT-005, KEY:IT-001
    - Inline tags:     @sdlc KEY:REQ-003, KEY:REQ-004
    - Legacy (unkeyed) tags such as `@sdlc REQ-003` are reported as a WARNING
      and do NOT satisfy coverage — the requirement they mean to cover still
      reports as untraced until the tag is re-keyed. Run /sdlc-adopt to re-key.

CHECKS
    1  Feature key uniqueness ........................... ERROR
    2  Traceability: code coverage (IMPLEMENTS) ......... ERROR
    3  Traceability: test coverage (COVERS) ............. ERROR
    4  Dangling tag (references a non-existent ID) ...... ERROR
    5  Unkeyed tag ...................................... WARNING
    6  Duplicate active ID within a feature ............. ERROR
    7  Recycled removed ID .............................. ERROR
    8  EARS syntax (deprecated dialect / no SHALL) ...... WARNING
    9  Test-plan coverage of spec ....................... WARNING
   10  Legacy layout detected (by content, not name) .... INFO
   11  Missing test plan ................................ WARNING
   12  Requirement cites an AC the brief does not define  ERROR
   13  Planned test id that no test file COVERS ......... WARNING
"""

import argparse
import fnmatch
import json
import os
import re
import sys

ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"

EXIT_CLEAN, EXIT_WARNINGS, EXIT_ERRORS = 0, 1, 2

# Directories and extensions never scanned for traceability tags.
SKIPPED_DIRECTORIES = {
    ".git", ".sdlc", "node_modules", "dist", "build", "__pycache__",
    ".venv", "venv", ".mypy_cache", ".pytest_cache", "target", ".next",
    "coverage", ".tox",
}
SKIPPED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".tar", ".lock",
    ".ico", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".bin", ".so",
    ".dll", ".dylib", ".class", ".jar", ".wasm", ".pyc",
}
MAX_SCANNED_BYTES = 2 * 1024 * 1024
MARKDOWN_EXTENSIONS = {".md", ".markdown"}

FEATURE_KEY_PATTERN = re.compile(r"^\*\*Feature Key:\*\*\s*([A-Z][A-Z0-9_-]*)", re.M)
# What was written on the Feature Key line, valid or not, so a malformed key
# reports as malformed instead of as missing.
FEATURE_KEY_LINE_PATTERN = re.compile(r"^\*\*Feature Key:\*\*\s*(\S+)", re.M)
FEATURE_KEY_TOKEN_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]*$")
# An ID token, optionally key-prefixed: KEY:REQ-001 or REQ-001.
TAG_TOKEN_PATTERN = re.compile(
    r"\b(?:([A-Z][A-Z0-9_-]*):)?((?:REQ|NFR|UT|IT|E2E|PBT)-\d+)\b")
# A requirement or NFR definition line in spec.md.
REQUIREMENT_LINE_PATTERN = re.compile(r"^\s*[-*|]?\s*`?((?:REQ|NFR)-\d+)`?\b(.*)$")
TEST_ID_PATTERN = re.compile(r"\b((?:UT|IT|E2E|PBT)-\d+)\b")
AC_CITATION_PATTERN = re.compile(r"\b(AC-\d+)\b")
IMPLEMENTS_PATTERN = re.compile(r"IMPLEMENTS:\s*(.+)")
COVERS_PATTERN = re.compile(r"COVERS:\s*(.+)")
INLINE_TAG_PATTERN = re.compile(r"@sdlc\s+(.+)")
TEST_PLAN_HEADING_PATTERN = re.compile(r"^#{2,3}\s+Test Plan\b", re.M)
CODE_FENCE_PATTERN = re.compile(r"^\s*(?:```|~~~)")

# EARS keywords are uppercase by convention (see CONVENTIONS.md), so these match
# case-SENSITIVELY. Otherwise the ordinary English words "as" and "unless"
# inside a canonical requirement ("IF a file is uploaded as a draft, THEN ...")
# read as the deprecated dialect. Leading-keyword patterns are anchored to the
# start of the requirement for the same reason.
SHALL_PATTERN = re.compile(r"\bSHALL\b")
LOWERCASE_SHALL_PATTERN = re.compile(r"\bshall\b")
LOWERCASE_EARS_KEYWORD_PATTERN = re.compile(r"^(when|while|where|if)\b")

DEPRECATED_EARS_PATTERNS = [
    (re.compile(r"\bALWAYS\s+SHALL\b"),
     "ALWAYS SHALL -> ubiquitous (drop ALWAYS): 'The <system> SHALL ...'"),
    (re.compile(r"^\s*WHERE\b.+\bTHEN\b"),
     "WHERE ... THEN (state-driven) -> 'WHILE ..., the <system> SHALL ...'"),
    (re.compile(r"^\s*AS\b.+\bTHEN\b"),
     "AS ... THEN -> 'IF ..., THEN ... SHALL ...'"),
    (re.compile(r"\bUNLESS\b"),
     "UNLESS -> 'IF NOT ..., THEN ... SHALL ...' (or WHERE)"),
]

# An NFR is exempt from IMPLEMENTS/COVERS by exactly one route: being listed
# under the spec's "NFRs Validated Outside Code" heading. Matching words in the
# "Validated By" cell was tried and removed -- "process", "manual" and
# "dashboard" are ordinary English, so "load test in the checkout process"
# silently exempted a load test. Declaring the exemption is cheap; guessing it
# is not.

# A requirement is retired only when its text BEGINS with REMOVED (the
# documented form is `REQ-NNN (AC-NNN): REMOVED ({date}) -- {reason}`). A
# substring test would retire any requirement that merely mentions a removed
# thing. The optional group keeps the `(AC-NNN)` citation the spec template
# prescribes -- without it, retiring a requirement the documented way left it
# active forever.
REMOVED_MARKER_PATTERN = re.compile(
    r"^[\s`:*_|()\-—]*(?:\([A-Za-z]+-\d+\)[\s`:*_|()\-—]*)?REMOVED\b")

# Legacy artifacts are recognised by CONTENT, case-sensitively, never by
# directory name: most projects have a docs/ directory and it is evidence of
# nothing, and `ARCHITECTURE.md` is a project's own document while
# `architecture.md` is the one /sdlc-init writes. A near-miss is a miss.
LEGACY_STEERING_DOCUMENT_NAMES = {
    "product.md", "tech.md", "test-strategy.md", "architecture.md"}
LEGACY_REQUIREMENT_NAMES = {"problem-brief.md", "entity-dictionary.md"}
LEGACY_SPEC_NAMES = {"spec.md", "requirements.md", "design.md"}


def main(argv=None):
    """Parse arguments, validate the project, emit the report, return an exit code."""
    parser = argparse.ArgumentParser(
        description="Validate SDLC traceability, EARS, and ID hygiene.")
    parser.add_argument("--root", default=".", help="project root (default: .)")
    parser.add_argument("--feature", default=None, help="restrict to one feature slug")
    parser.add_argument("--strict", action="store_true",
                        help="warnings exit non-zero too")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="skip files matching this glob when scanning for "
                             "tags (repeatable)")
    arguments = parser.parse_args(argv)

    root = os.path.abspath(arguments.root)
    report = validate_project(root, only_feature=arguments.feature,
                              excluded_patterns=arguments.exclude)

    if arguments.json:
        emit_json_report(report)
    else:
        emit_text_report(report)

    error_count, warning_count, _ = report.count_by_severity()
    if error_count:
        return EXIT_ERRORS
    if warning_count and arguments.strict:
        return EXIT_WARNINGS
    return EXIT_CLEAN


def validate_project(root, only_feature=None, report=None, excluded_patterns=()):
    """Run every check over the project at `root` and return the filled Report.

    `only_feature` narrows what is REPORTED, not what is parsed. Every spec is
    read, so the keys and ids of the other features stay resolvable — scoping
    the parse instead made every other feature's tags report as dangling, which
    turned a single-feature review into a wall of false errors.
    """
    report = report or Report()

    check_legacy_layout(root, report)

    spec_paths_by_slug = get_spec_paths_by_slug(root)
    if not spec_paths_by_slug:
        report.info("no-specs",
                    "No SDLC specs found (looked in .sdlc/specs/ and specs/).")
        return report
    if only_feature and only_feature not in spec_paths_by_slug:
        report.info("no-specs",
                    "No spec found for feature '%s' (looked in .sdlc/specs/ "
                    "and specs/)." % only_feature)
        return report
    reported_slugs = {only_feature} if only_feature else set(spec_paths_by_slug)

    specs_by_slug, slug_by_key = check_spec_hygiene(
        root, spec_paths_by_slug, report, reported_slugs)
    tags = collect_traceability_tags(root, excluded_patterns)
    valid_targets = get_valid_tag_targets(specs_by_slug)
    reported_keys = {
        specs_by_slug[slug]["feature_key"]
        for slug in reported_slugs if slug in specs_by_slug
    }
    if only_feature:
        # Unkeyed tags survive the filter: they belong to no feature by
        # definition, and dropping them would report the requirement they meant
        # to cover as untraced without the warning that explains why.
        tags = [tag for tag in tags
                if tag[0] is None or tag[0] in reported_keys]
    check_tag_targets(tags, valid_targets, slug_by_key, report)

    reported_specs = {
        slug: spec for slug, spec in specs_by_slug.items() if slug in reported_slugs
    }
    check_requirement_coverage(root, reported_specs, spec_paths_by_slug, tags, report)
    check_ac_citations(root, reported_specs, spec_paths_by_slug, report)
    return report


def check_legacy_layout(root, report):
    """Check 10 — report SDLC artifacts still sitting at pre-`.sdlc/` paths."""
    for label, legacy_path, canonical_path in get_legacy_artifacts(root):
        if os.path.exists(os.path.join(root, canonical_path)):
            continue
        report.info(
            "legacy-layout",
            "Legacy %s at %s — run /sdlc-adopt to consolidate under .sdlc/."
            % (label, legacy_path),
            legacy_path)


def get_legacy_artifacts(root):
    """Yield (label, legacy_path, canonical_path) per legacy artifact found.

    Matched on the exact file names /sdlc-init writes, never on the name of the
    directory holding them.
    """
    if LEGACY_STEERING_DOCUMENT_NAMES & set(get_entry_names(root, "docs")):
        yield "steering docs", "docs", os.path.join(".sdlc", "docs")

    adr_directory = os.path.join("docs", "adr")
    if any(name.startswith("ADR-") and name.endswith(".md")
           for name in get_entry_names(root, adr_directory)):
        yield "ADRs", adr_directory, os.path.join(".sdlc", "docs", "adr")

    if LEGACY_REQUIREMENT_NAMES & set(get_entry_names(root, "requirements")):
        yield "requirements", "requirements", os.path.join(".sdlc", "requirements")

    if has_slug_directory_holding(root, "specs", names=LEGACY_SPEC_NAMES):
        yield "specs", "specs", os.path.join(".sdlc", "specs")

    if has_slug_directory_holding(root, "reviews", prefix="report-"):
        yield "reviews", "reviews", os.path.join(".sdlc", "reviews")

    rules_text = read_file_text(os.path.join(root, "rules.md"))
    if rules_text and "RULE-" in rules_text:
        yield "rules", "rules.md", os.path.join(".sdlc", "rules.md")


def has_slug_directory_holding(root, base, names=None, prefix=None):
    """True when any `base/<slug>/` holds one of `names` or a `prefix`*.md file."""
    for slug in get_entry_names(root, base):
        entry_names = get_entry_names(root, os.path.join(base, slug))
        if names and names & set(entry_names):
            return True
        if prefix and any(name.startswith(prefix) and name.endswith(".md")
                          for name in entry_names):
            return True
    return False


def get_entry_names(root, relative_path):
    """Return the exact entry names in a directory, or [] when it is absent."""
    try:
        return os.listdir(os.path.join(root, relative_path))
    except OSError:
        return []


def check_spec_hygiene(root, spec_paths_by_slug, report, reported_slugs=None):
    """Checks 1, 6, 7, 8 — parse every spec and validate keys, IDs, and EARS.

    Every spec is parsed so that its key and ids stay resolvable, but a spec
    outside `reported_slugs` (the --feature scope) contributes no findings.

    Returns (specs_by_slug, slug_by_key).
    """
    specs_by_slug = {}
    slug_by_key = {}
    for slug, spec_path in spec_paths_by_slug.items():
        is_reported = reported_slugs is None or slug in reported_slugs
        spec_report = report if is_reported else Report()
        text = read_file_text(spec_path)
        location = os.path.relpath(spec_path, root)
        if text is None:
            spec_report.error("read", "Could not read spec", location)
            continue

        spec = parse_spec(text)
        feature_key = resolve_feature_key(spec, slug, location, spec_report)

        # Check 1: feature key uniqueness.
        if feature_key in slug_by_key and slug_by_key[feature_key] != slug:
            spec_report.error("key-unique",
                              "Feature Key '%s' is also used by feature '%s'."
                              % (feature_key, slug_by_key[feature_key]), location)
        else:
            slug_by_key[feature_key] = slug

        # Check 6: an ID defined active more than once.
        for requirement_id in sorted(set(spec["duplicate_ids"])):
            spec_report.error("dup-id",
                              "ID %s defined more than once (active) in %s."
                              % (requirement_id, slug), location)

        # Check 7: an ID marked REMOVED that is also still active.
        recycled_ids = spec["removed_ids"] & set(spec["active_ids"])
        for requirement_id in sorted(recycled_ids):
            spec_report.error("recycled-id",
                              "ID %s is marked REMOVED but also appears active."
                              % requirement_id, location)

        # Check 8: EARS dialect.
        check_ears_syntax(spec["requirement_texts"], location, spec_report)

        # Check 11 — must happen here, not during the coverage pass: a legacy
        # test plan's UT-/IT- ids are legitimate COVERS targets, so they have to
        # be known before tags are resolved.
        resolve_test_plan(root, slug, spec, location, spec_report)

        specs_by_slug[slug] = spec
    return specs_by_slug, slug_by_key


def resolve_feature_key(spec, slug, location, report):
    """Return the spec's Feature Key, defaulting from the slug, and report it.

    The default is only usable when it is a valid key. A slug that starts with a
    digit (`2fa` -> `2FA`) is not: the tag parser cannot read `2FA:REQ-001` as
    key-prefixed, so it reads a bare `REQ-001` instead and the feature can never
    satisfy traceability no matter what is written in the source.
    """
    if spec["feature_key"]:
        return spec["feature_key"]

    declared_token = spec["declared_feature_key_token"]
    spec["feature_key"] = slug.upper()
    if declared_token:
        report.error("feature-key",
                     "Declared Feature Key '%s' is not a valid key — a key is "
                     "[A-Z][A-Z0-9_-]* (uppercase, starting with a letter). "
                     "Tags will not resolve until it is fixed."
                     % declared_token, location)
    elif FEATURE_KEY_TOKEN_PATTERN.match(spec["feature_key"]):
        report.info("feature-key",
                    "No '**Feature Key:**' declared; defaulting to '%s'. "
                    "Declare one explicitly." % spec["feature_key"], location)
    else:
        report.error("feature-key",
                     "No '**Feature Key:**' declared, and '%s' cannot be one — "
                     "a key is [A-Z][A-Z0-9_-]* and may not start with a digit. "
                     "Declare one explicitly, e.g. '**Feature Key:** F%s'."
                     % (spec["feature_key"], spec["feature_key"]), location)
    return spec["feature_key"]


def resolve_test_plan(root, slug, spec, spec_location, report):
    """Check 11 — locate the feature's test plan and record it on the spec.

    The plan belongs in the spec's own `## Test Plan` section. A project
    migrated from the two-file layout keeps it at `.sdlc/tests/<slug>/test-plan.md`;
    that is read as a fallback so its test IDs stay valid COVERS targets.
    """
    spec["test_plan_location"] = spec_location
    if spec["test_plan_text"]:
        return

    legacy_path = find_first_existing_path(
        os.path.join(root, ".sdlc", "tests", slug, "test-plan.md"),
        os.path.join(root, "tests", slug, "test-plan.md"),
    )
    if not legacy_path:
        report.warn("missing-test-plan",
                    "Feature '%s' has no '## Test Plan' section in spec.md." % slug,
                    spec_location)
        return

    location = os.path.relpath(legacy_path, root)
    report.info("legacy-test-plan",
                "Feature '%s' keeps its test plan at %s — /sdlc-adopt folds it "
                "into spec.md." % (slug, location), location)
    spec["test_plan_text"] = read_file_text(legacy_path) or ""
    spec["test_plan_location"] = location
    spec["test_ids"] = set(TEST_ID_PATTERN.findall(spec["test_plan_text"]))


def check_ears_syntax(requirement_texts, location, report):
    """Check 8 — every requirement uses canonical EARS with an uppercase SHALL.

    Uppercase is what makes a keyword a keyword, so the SHALL test is
    case-sensitive: `the system shall charge the card` is prose, not EARS.
    """
    for requirement_id, text in sorted(requirement_texts.items()):
        deprecated_hint = get_deprecated_ears_hint(text)
        if deprecated_hint:
            report.warn("ears", "%s uses deprecated EARS dialect (%s)."
                        % (requirement_id, deprecated_hint), location)
            continue
        lowercase_keyword = LOWERCASE_EARS_KEYWORD_PATTERN.match(text)
        if lowercase_keyword:
            report.warn("ears",
                        "%s opens with lowercase '%s' — EARS keywords are "
                        "uppercase (%s)." % (requirement_id,
                                             lowercase_keyword.group(1),
                                             lowercase_keyword.group(1).upper()),
                        location)
            continue
        if SHALL_PATTERN.search(text):
            continue
        if LOWERCASE_SHALL_PATTERN.search(text):
            report.warn("ears",
                        "%s uses lowercase 'shall' — EARS keywords are uppercase."
                        % requirement_id, location)
        else:
            report.warn("ears",
                        "%s has no SHALL/EARS keyword — restate in canonical EARS."
                        % requirement_id, location)


def get_deprecated_ears_hint(text):
    """Return the migration hint for the first deprecated pattern, else None."""
    for pattern, hint in DEPRECATED_EARS_PATTERNS:
        if pattern.search(text):
            return hint
    return None


def collect_traceability_tags(root, excluded_patterns=()):
    """Walk source and test files, returning every traceability tag found.

    Each tag is (feature_key_or_None, requirement_id, kind, relative_path).
    Fenced code blocks in Markdown are skipped: a README or AGENTS.md that
    documents the tag format is showing an example, not claiming coverage, and
    reading those as real tags made the tool fail on its own documentation.
    """
    tags = []
    for directory_path, directory_names, file_names in os.walk(root):
        directory_names[:] = [
            name for name in directory_names if name not in SKIPPED_DIRECTORIES
        ]
        for file_name in file_names:
            extension = os.path.splitext(file_name)[1].lower()
            if extension in SKIPPED_EXTENSIONS:
                continue
            file_path = os.path.join(directory_path, file_name)
            relative_path = os.path.relpath(file_path, root)
            if is_excluded_path(relative_path, excluded_patterns):
                continue
            text = read_file_text(file_path)
            if text is None:
                continue
            if extension in MARKDOWN_EXTENSIONS:
                text = strip_code_fences(text)
            for kind, parsed_tags in parse_traceability_tags(text).items():
                for feature_key, requirement_id in parsed_tags:
                    tags.append((feature_key, requirement_id, kind, relative_path))
    return tags


def is_excluded_path(relative_path, excluded_patterns):
    """True when a path matches an --exclude glob, by full path or by name."""
    posix_path = relative_path.replace(os.sep, "/")
    for pattern in excluded_patterns:
        if (fnmatch.fnmatch(posix_path, pattern)
                or fnmatch.fnmatch(os.path.basename(posix_path), pattern)):
            return True
    return False


def strip_code_fences(text):
    """Blank out fenced code blocks, keeping line numbers intact.

    ponytail: a plain open/close toggle, so a nested fence inside a fenced block
    flips the parity for the rest of the file. Markdown holds examples, not
    coverage, so the cost is a stray tag either way -- reach for --exclude, and
    only write a real fence parser if a project keeps real tags in Markdown.
    """
    lines = text.splitlines()
    is_inside_fence = False
    for index, line in enumerate(lines):
        if CODE_FENCE_PATTERN.match(line):
            is_inside_fence = not is_inside_fence
            lines[index] = ""
        elif is_inside_fence:
            lines[index] = ""
    return "\n".join(lines)


def get_valid_tag_targets(specs_by_slug):
    """Return the set of (feature_key, id) pairs a tag is allowed to reference."""
    valid_targets = set()
    for spec in specs_by_slug.values():
        feature_key = spec["feature_key"]
        for requirement_id in spec["active_ids"]:
            valid_targets.add((feature_key, requirement_id))
        for test_id in spec["test_ids"]:
            valid_targets.add((feature_key, test_id))
    return valid_targets


def check_tag_targets(tags, valid_targets, slug_by_key, report):
    """Checks 4 and 5 — every tag is key-namespaced and resolves to a real ID."""
    for feature_key, requirement_id, kind, relative_path in tags:
        if feature_key is None:
            report.warn("unkeyed-tag",
                        "Unkeyed tag '%s' in %s — re-key as KEY:%s."
                        % (requirement_id, kind, requirement_id), relative_path)
            continue
        if (feature_key, requirement_id) in valid_targets:
            continue
        if feature_key not in slug_by_key:
            report.error("dangling-tag",
                         "Tag %s:%s (%s) references unknown Feature Key '%s'."
                         % (feature_key, requirement_id, kind, feature_key),
                         relative_path)
        else:
            report.error("dangling-tag",
                         "Tag %s:%s (%s) references an ID not defined in feature '%s'."
                         % (feature_key, requirement_id, kind,
                            slug_by_key[feature_key]), relative_path)


def check_requirement_coverage(root, specs_by_slug, spec_paths_by_slug, tags, report):
    """Checks 2, 3, 9 — every requirement is implemented, tested, and planned."""
    implemented_targets = {
        (key, requirement_id)
        for key, requirement_id, kind, _ in tags
        if kind == "IMPLEMENTS" and key
    }
    covered_targets = {
        (key, requirement_id)
        for key, requirement_id, kind, _ in tags
        if kind == "COVERS" and key
    }

    for slug, spec in specs_by_slug.items():
        feature_key = spec["feature_key"]
        location = os.path.relpath(spec_paths_by_slug[slug], root)
        test_plan_text = spec["test_plan_text"]
        test_plan_location = spec["test_plan_location"]

        for requirement_id in sorted(spec["active_ids"]):
            if requirement_id in spec["outside_code_nfrs"]:
                report.info("outside-code",
                            "%s:%s validated outside code — exempt from "
                            "IMPLEMENTS/COVERS." % (feature_key, requirement_id),
                            location)
                continue
            if (feature_key, requirement_id) not in implemented_targets:
                report.error("trace-code",
                             "%s:%s has no IMPLEMENTS: header in any source file."
                             % (feature_key, requirement_id), location)
            if (feature_key, requirement_id) not in covered_targets:
                report.error("trace-test",
                             "%s:%s has no COVERS: header in any test file."
                             % (feature_key, requirement_id), location)
            is_planned = re.search(r"\b%s\b" % re.escape(requirement_id),
                                   test_plan_text)
            if requirement_id.startswith("REQ-") and test_plan_text and not is_planned:
                report.warn("plan-coverage",
                            "%s not referenced by any row in the test plan."
                            % requirement_id, test_plan_location)

        # Check 13: the other direction — a planned test that nothing covers.
        for test_id in sorted(spec["test_ids"]):
            if (feature_key, test_id) not in covered_targets:
                report.warn("plan-test-uncovered",
                            "%s is planned in the test plan but no test file "
                            "COVERS it." % test_id, test_plan_location)


def check_ac_citations(root, specs_by_slug, spec_paths_by_slug, report):
    """Check 12 — every `AC-*` a requirement cites exists in the problem brief.

    Skipped when there is no brief: /sdlc-adopt documents code that predates one,
    and an uncited requirement is a gap to fill, not an error. What this catches
    is the break /sdlc-plan warns about — an AC renumbered or reworded upstream,
    leaving specs citing an id that no longer exists.
    """
    brief_path = find_first_existing_path(
        os.path.join(root, ".sdlc", "requirements", "problem-brief.md"),
        os.path.join(root, "requirements", "problem-brief.md"),
    )
    if not brief_path:
        return
    defined_ac_ids = set(AC_CITATION_PATTERN.findall(read_file_text(brief_path) or ""))
    if not defined_ac_ids:
        return

    brief_location = os.path.relpath(brief_path, root)
    for slug, spec in sorted(specs_by_slug.items()):
        location = os.path.relpath(spec_paths_by_slug[slug], root)
        for requirement_id, cited_ac_ids in sorted(spec["ac_citations"].items()):
            for ac_id in sorted(cited_ac_ids - defined_ac_ids):
                report.error("ac-citation",
                             "%s cites %s, which %s does not define."
                             % (requirement_id, ac_id, brief_location), location)


def parse_spec(text):
    """Parse a spec.md into its feature key, requirement IDs, texts, and test plan."""
    feature_key_match = FEATURE_KEY_PATTERN.search(text)
    declared_key_match = FEATURE_KEY_LINE_PATTERN.search(text)
    active_ids = {}          # id -> line number of its first active definition
    duplicate_ids = []
    removed_ids = set()
    requirement_texts = {}   # REQ id -> requirement text (active only)
    ac_citations = {}        # REQ id -> {AC ids it cites}
    outside_code_nfrs = set()

    is_outside_code_section = False
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped_line = line.strip()
        if stripped_line.startswith("#"):
            is_outside_code_section = (
                "validated outside code" in stripped_line.lower())

        definition_match = REQUIREMENT_LINE_PATTERN.match(line)
        if not definition_match:
            continue
        requirement_id, remainder = definition_match.group(1), definition_match.group(2)

        if REMOVED_MARKER_PATTERN.match(remainder):
            removed_ids.add(requirement_id)
            continue

        is_repeated_nfr = is_outside_code_section and requirement_id.startswith("NFR-")
        if is_repeated_nfr:
            outside_code_nfrs.add(requirement_id)
        if requirement_id in active_ids:
            # Re-listing an NFR under "NFRs Validated Outside Code" is expected —
            # it is the same NFR as in the table, not a second definition.
            if not is_repeated_nfr:
                duplicate_ids.append(requirement_id)
        else:
            active_ids[requirement_id] = line_number

        if requirement_id.startswith("REQ-"):
            requirement_texts[requirement_id] = get_requirement_text(remainder)
            ac_citations[requirement_id] = set(AC_CITATION_PATTERN.findall(
                get_requirement_citation(remainder)))

    test_plan_text = get_test_plan_section(text)
    return {
        "feature_key": feature_key_match.group(1) if feature_key_match else None,
        "declared_feature_key_token": (
            declared_key_match.group(1) if declared_key_match else None),
        "ac_citations": ac_citations,
        "active_ids": active_ids,
        "duplicate_ids": duplicate_ids,
        "removed_ids": removed_ids,
        "requirement_texts": requirement_texts,
        "outside_code_nfrs": outside_code_nfrs,
        "test_plan_text": test_plan_text,
        "test_ids": set(TEST_ID_PATTERN.findall(test_plan_text)),
    }


def get_requirement_text(remainder):
    """Return the requirement prose that follows the ID and its optional citation."""
    if ":" in remainder:
        return remainder.split(":", 1)[1].strip()
    return remainder.strip()


def get_requirement_citation(remainder):
    """Return the `(AC-NNN)` citation part that precedes the requirement prose."""
    return remainder.split(":", 1)[0] if ":" in remainder else ""


def get_test_plan_section(text):
    """Return the text under the spec's `## Test Plan` heading, or '' if absent."""
    heading_match = TEST_PLAN_HEADING_PATTERN.search(text)
    if not heading_match:
        return ""
    section_start = heading_match.end()
    heading_level = len(heading_match.group(0).split()[0])
    next_heading = re.compile(r"^#{1,%d}\s+" % heading_level, re.M)
    next_match = next_heading.search(text, section_start)
    return text[section_start:next_match.start()] if next_match else text[section_start:]


def parse_traceability_tags(text):
    """Return {kind: [(feature_key_or_None, id), ...]} for one file's tags."""
    tags_by_kind = {"IMPLEMENTS": [], "COVERS": [], "@sdlc": []}
    patterns_by_kind = {
        "IMPLEMENTS": IMPLEMENTS_PATTERN,
        "COVERS": COVERS_PATTERN,
        "@sdlc": INLINE_TAG_PATTERN,
    }
    for line in text.splitlines():
        for kind, pattern in patterns_by_kind.items():
            match = pattern.search(line)
            if not match:
                continue
            for token in TAG_TOKEN_PATTERN.finditer(match.group(1)):
                tags_by_kind[kind].append((token.group(1), token.group(2)))
    return tags_by_kind


def get_spec_paths_by_slug(root):
    """Return {slug: spec_path} across the canonical and legacy spec locations."""
    spec_paths_by_slug = {}
    for base in (os.path.join(root, ".sdlc", "specs"), os.path.join(root, "specs")):
        if not os.path.isdir(base):
            continue
        for slug in sorted(os.listdir(base)):
            spec_path = os.path.join(base, slug, "spec.md")
            if os.path.exists(spec_path) and slug not in spec_paths_by_slug:
                spec_paths_by_slug[slug] = spec_path
    return spec_paths_by_slug


def find_first_existing_path(*paths):
    """Return the first path that exists, else None."""
    for path in paths:
        if path and os.path.exists(path):
            return path
    return None


def read_file_text(path):
    """Return a file's text, or None if it is missing, binary, or oversized."""
    try:
        if os.path.getsize(path) > MAX_SCANNED_BYTES:
            return None
        with open(path, "rb") as file_handle:
            raw_bytes = file_handle.read()
        if b"\x00" in raw_bytes:
            return None
        return raw_bytes.decode("utf-8", errors="replace")
    except (OSError, ValueError):
        return None


class Report:
    """Collects findings, each one a (severity, check, message, location) tuple."""

    def __init__(self):
        self.findings = []

    def error(self, check, message, location=""):
        self.findings.append((ERROR, check, message, location))

    def warn(self, check, message, location=""):
        self.findings.append((WARNING, check, message, location))

    def info(self, check, message, location=""):
        self.findings.append((INFO, check, message, location))

    def count_by_severity(self):
        """Return (error_count, warning_count, info_count)."""
        severities = [finding[0] for finding in self.findings]
        return (severities.count(ERROR), severities.count(WARNING),
                severities.count(INFO))


def emit_text_report(report):
    """Print findings most-severe first, then the summary line."""
    severity_order = {ERROR: 0, WARNING: 1, INFO: 2}
    sorted_findings = sorted(report.findings,
                             key=lambda finding: severity_order[finding[0]])
    for severity, check, message, location in sorted_findings:
        suffix = " (%s)" % location if location else ""
        print("%s: %s — %s%s" % (severity, check, message, suffix))
    error_count, warning_count, info_count = report.count_by_severity()
    print("\n%d errors, %d warnings, %d info"
          % (error_count, warning_count, info_count))


def emit_json_report(report):
    """Print the same findings as JSON, for CI and other tools."""
    error_count, warning_count, info_count = report.count_by_severity()
    print(json.dumps({
        "summary": {
            "errors": error_count,
            "warnings": warning_count,
            "info": info_count,
        },
        "findings": [
            {"severity": severity, "check": check,
             "message": message, "location": location}
            for severity, check, message, location in report.findings
        ],
    }, indent=2))


if __name__ == "__main__":
    sys.exit(main())
