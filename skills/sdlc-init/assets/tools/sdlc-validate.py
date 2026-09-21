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
                   reported on. A slug with no spec is an ERROR, not a clean
                   run -- otherwise a typo buys a passing gate.
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
   14  --feature names a slug with no spec .............. ERROR
   15  Tag in the wrong kind of file (role) ............. ERROR
   16  Unusable .sdlc/config.json ....................... ERROR
   17  File skipped while scanning for tags ............. WARNING

FILE ROLES
    Every scanned file is SOURCE, TEST, or DOC.
      - DOC  (.md, .rst, .adoc, ...) is never scanned: documentation shows the
             tag format, it does not claim coverage.
      - TEST is decided by path COMPONENTS and filename STEMS -- `tests/`,
             `test_*.py`, `*_test.go`, `src/test/java/`, `*.spec.ts`, and so on
             -- never by substring, so `src/contest/` stays source.
      - SOURCE is everything else.
    `IMPLEMENTS:` only counts from a SOURCE file, `COVERS:` only from a TEST
    file, and a tag only counts inside a real comment. Without those three
    rules a single file carrying both headers, with no test suite at all,
    validated clean.

    Override any of it in `.sdlc/config.json` (see CONVENTIONS.md).
"""

import argparse
import collections
import fnmatch
import json
import os
import re
import sys

ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"

TraceabilityTag = collections.namedtuple(
    "TraceabilityTag",
    "feature_key requirement_id kind relative_path role")

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

# Documentation carries examples of the tag format, never coverage. Tags in these
# files are ignored silently rather than reported, so a README may show the
# format freely.
DOCUMENTATION_EXTENSIONS = {
    ".md", ".markdown", ".rst", ".adoc", ".asciidoc", ".org",
}

# --- File roles -----------------------------------------------------------
# Every scanned code file is SOURCE or TEST; documentation is DOC and ignored.
# A tag in a code file always belongs somewhere, so there is no fourth
# "unclassifiable" role: the report is always which kind of file it belongs in.
ROLE_SOURCE, ROLE_TEST, ROLE_DOC = "source", "test", "doc"

# Matched on path COMPONENTS and filename STEMS, never on substrings -- so
# `src/contest/models.py` and `src/latest_prices.py` stay source.
DEFAULT_TEST_DIRECTORY_NAMES = [
    "tests", "test", "spec", "specs", "__tests__", "testing",
]
DEFAULT_TEST_STEM_PATTERNS = [
    "test_*", "*_test", "*_tests", "*_spec", "*.test", "*.spec",
    "*Test", "*Tests", "*Spec", "*Specs", "conftest",
]
DEFAULT_TEST_PATH_FRAGMENTS = ["src/test/", "src/it/", "src/androidTest/"]

# --- Comment syntax -------------------------------------------------------
# A tag counts only inside a real comment, which separates a claim from a string
# literal or a line of prose.
#
# An extension may carry several leaders: `.m` is both Objective-C and MATLAB,
# and accepting both loses fewer real tags than picking one.
LINE_COMMENT_EXTENSIONS_BY_LEADER = {
    "#": (".py", ".rb", ".sh", ".bash", ".zsh", ".fish", ".pl", ".pm", ".r",
          ".yaml", ".yml", ".toml", ".tf", ".tfvars", ".ex", ".exs", ".jl",
          ".nim", ".cr", ".conf", ".cmake", ".mk", ".pp", ".rake", ".tcl",
          ".awk", ".ps1", ".gemspec", ".dockerfile"),
    "//": (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".rs", ".java",
           ".c", ".h", ".cpp", ".hpp", ".cc", ".hh", ".cs", ".swift", ".kt",
           ".kts", ".scala", ".dart", ".php", ".proto", ".gradle", ".groovy",
           ".sol", ".zig", ".m", ".mm", ".scss", ".less", ".jsonc", ".json5",
           ".v", ".sv", ".glsl", ".hlsl"),
    "--": (".sql", ".hs", ".lhs", ".lua", ".elm", ".adb", ".ads", ".vhd",
           ".vhdl", ".applescript"),
    ";": (".lisp", ".cl", ".clj", ".cljs", ".cljc", ".el", ".scm", ".rkt",
          ".ini", ".asm", ".s"),
    "%": (".tex", ".sty", ".erl", ".hrl", ".prolog"),
    "!": (".f", ".f90", ".f95", ".f03", ".f08"),
    "'": (".vb", ".vbs", ".bas"),
    '"': (".vim", ".vimrc"),
    "REM ": (".bat", ".cmd"),
}
BLOCK_COMMENT_EXTENSIONS_BY_PAIR = {
    ("/*", "*/"): (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".rs",
                   ".java", ".c", ".h", ".cpp", ".hpp", ".cc", ".hh", ".cs",
                   ".swift", ".kt", ".kts", ".scala", ".dart", ".php", ".css",
                   ".scss", ".less", ".proto", ".sol", ".groovy", ".gradle",
                   ".m", ".mm", ".v", ".sv", ".glsl", ".hlsl"),
    ("<!--", "-->"): (".html", ".htm", ".xhtml", ".xml", ".xsl", ".xslt",
                      ".svg", ".vue", ".svelte", ".astro", ".plist", ".resx"),
    ("=begin", "=end"): (".rb",),
    ("{-", "-}"): (".hs", ".lhs", ".elm"),
    ("--[[", "]]"): (".lua",),
}
# Used when an extension appears in neither table. Deliberately broad so an
# unlisted language keeps its tags; prose still fails, carrying no leader.
FALLBACK_LINE_COMMENT_LEADERS = ("#", "//", "--", ";", "%", "!")

# Continuation markers a comment body may open with: the `*` of a javadoc line,
# a doubled leader, box-drawing dashes. Stripped before the tag is matched.
COMMENT_CONTINUATION_PATTERN = re.compile(r"^[\s*#/\-!;%]*")


def get_inverted_extension_table(extensions_by_marker):
    """Invert {marker: (ext, ...)} into {ext: [marker, ...]} for lookup by file."""
    markers_by_extension = {}
    for marker, extensions in extensions_by_marker.items():
        for extension in extensions:
            markers_by_extension.setdefault(extension, []).append(marker)
    return markers_by_extension


LINE_COMMENT_LEADERS_BY_EXTENSION = get_inverted_extension_table(
    LINE_COMMENT_EXTENSIONS_BY_LEADER)
BLOCK_COMMENT_PAIRS_BY_EXTENSION = get_inverted_extension_table(
    BLOCK_COMMENT_EXTENSIONS_BY_PAIR)

CONFIG_RELATIVE_PATH = os.path.join(".sdlc", "config.json")
CONFIG_LIST_FIELDS = {
    "layout": ("test_directory_names", "test_stem_patterns",
               "test_path_fragments", "source_overrides", "test_overrides"),
    "headings": ("test_plan", "outside_code"),
    "scan": ("skip_directories", "scan_directories"),
}

# The template writes the key in bold, but a spec that drops the asterisks still
# declares one. An unrecognised declaration falls back to the uppercased slug,
# so the pattern accepts both forms.
FEATURE_KEY_PATTERN = re.compile(
    r"^\s*(?:[-*+]\s*)?(?:\*\*|__)?Feature Key(?:\*\*|__)?\s*:\s*"
    r"(?:\*\*|`)?\s*([A-Z][A-Z0-9_-]*)", re.M)
# What was written on the Feature Key line, valid or not, so a malformed key
# reports as malformed instead of as missing.
FEATURE_KEY_LINE_PATTERN = re.compile(
    r"^\s*(?:[-*+]\s*)?(?:\*\*|__)?Feature Key(?:\*\*|__)?\s*:\s*"
    r"(?:\*\*|`)?\s*(\S+)", re.M)
FEATURE_KEY_TOKEN_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]*$")
# An ID token, optionally key-prefixed: KEY:REQ-001 or REQ-001.
TAG_TOKEN_PATTERN = re.compile(
    r"\b(?:([A-Z][A-Z0-9_-]*):)?((?:REQ|NFR|UT|IT|E2E|PBT)-\d+)\b")
# A requirement or NFR definition line in spec.md. The ID needs both a list or
# table marker and a definition punctuator after it -- `:`, an `(AC-NNN)`
# citation, or a table cell boundary. Prose that merely names an ID, such as
# `- REQ-001 was the hardest one to get right`, defines nothing and is skipped.
REQUIREMENT_LINE_PATTERN = re.compile(
    r"^\s*(?:[-*+]|\|)\s*`?((?:REQ|NFR)-\d+)`?\s*(?=[:(|]|$)(.*)$")
TEST_ID_PATTERN = re.compile(r"\b((?:UT|IT|E2E|PBT)-\d+)\b")
REQUIREMENT_ID_PATTERN = re.compile(r"\b((?:REQ|NFR)-\d+)\b")
AC_CITATION_PATTERN = re.compile(r"\b(AC-\d+)\b")
# The `(AC-NNN)` citation sits immediately after the ID, before the prose.
CITATION_PATTERN = re.compile(r"^\s*\(([^)]*)\)")
# The brief DEFINES an AC on a list or table line; it MENTIONS one anywhere.
# Matching mentions let `- AC-777 was DELETED in March` define AC-777, so the
# citation check waved through exactly the renumbering it exists to catch.
AC_DEFINITION_PATTERN = re.compile(
    r"^\s*(?:[-*+]|\|)\s*(?:\[[ xX]\]\s*)?`?(AC-\d+)`?\s*(?=[:(|]|$)", re.M)
# Anchored to the START of a comment body. The unanchored forms these replace
# counted `# This file does NOT IMPLEMENTS: KEY:REQ-001` and `# REIMPLEMENTS:`
# as real coverage, and matched inside string literals and plain prose.
ANCHORED_TAG_PATTERNS_BY_KIND = {
    "IMPLEMENTS": re.compile(r"^IMPLEMENTS:\s*(.+)"),
    "COVERS": re.compile(r"^COVERS:\s*(.+)"),
    "@sdlc": re.compile(r"^@sdlc\s+(.+)"),
}
# Templates are project-owned and meant to be edited, so the heading is matched
# by meaning rather than by literal text. Anything outside this set goes in
# `headings.test_plan` in .sdlc/config.json.
TEST_PLAN_HEADING_PATTERN = re.compile(
    r"^#{2,4}\s+(?:Test Plan|Tests|Test Cases|Test Design|Testing|Test Strategy)\b",
    re.M | re.I)
# Likewise the exemption heading: what matters is that it says the NFR is
# validated somewhere other than the code, not the exact wording.
OUTSIDE_CODE_HEADING_PATTERN = re.compile(
    r"\boutside\b[^#]{0,32}\bcode\b|\bnot\b[^#]{0,32}\bin\s+code\b"
    r"|\bvalidated\b[^#]{0,32}\b(?:infra|infrastructure|externally|process)\b",
    re.I)
# A fence opens with 3+ backticks or tildes and closes only on the same
# character, at least as long, with no info string. Tracking the opener rather
# than toggling a flag lets a fenced block contain a shorter fence.
CODE_FENCE_PATTERN = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*(\S*)")

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
    (re.compile(r"\bUNLESS\b"),
     "UNLESS -> 'IF NOT ..., THEN ... SHALL ...' (or WHERE)"),
]
# The two THEN dialects need a predicate, not a regex: `WHERE the audit module
# is included, IF the record is deleted, THEN ...` is the canonical composite
# CONVENTIONS.md endorses, and a regex for `WHERE ... THEN` flagged it.
DEPRECATED_LEADING_THEN_HINTS = [
    ("WHERE", "WHERE ... THEN (state-driven) -> 'WHILE ..., the <system> SHALL ...'"),
    ("AS", "AS ... THEN -> 'IF ..., THEN ... SHALL ...'"),
]

# A quoted span is copy the system emits, not vocabulary the requirement uses.
# Blanked to a space so word boundaries survive.
QUOTED_SPAN_PATTERN = re.compile(
    "`[^`]*`|\"[^\"]*\"|'[^']*'|\u201c[^\u201d]*\u201d")

# An uppercase opener that is not one of these is not an EARS keyword.
EARS_LEADING_KEYWORDS = frozenset(("WHEN", "WHILE", "WHERE", "IF", "THEN"))
NON_EARS_KEYWORD_HINTS = {
    "AFTER": "WHEN", "BEFORE": "WHILE ... has not yet", "ONCE": "WHEN",
    "UNTIL": "WHILE", "GIVEN": "WHERE or WHILE", "DURING": "WHILE",
    "WHENEVER": "WHEN", "UPON": "WHEN", "ASSUMING": "WHERE", "PROVIDED": "WHERE",
}
FIRST_WORD_PATTERN = re.compile(r"^\s*([A-Z][A-Z0-9-]{1,})\b")
# The main clause needs a subject between the trigger and SHALL.
EARS_MAIN_CLAUSE_PATTERN = re.compile(r"(?:^|,)\s*(?:THEN\s+)?(\S.*?)\bSHALL\b")
# Unverifiable words. A requirement that uses one cannot be tested, which is the
# whole point of writing it in EARS.
VAGUE_TERMS = frozenset((
    "fast", "slow", "quick", "quickly", "responsive", "user-friendly",
    "easy", "intuitive", "simple", "robust", "scalable", "efficient",
    "reliable", "performant", "seamless", "appropriate", "reasonable",
    "adequate", "sufficient", "optimal", "flexible", "lightweight",
))
VAGUE_TERM_PATTERN = re.compile(
    r"\b(%s)\b" % "|".join(sorted(VAGUE_TERMS)), re.I)

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
# Applied to the requirement text, which get_requirement_text has already
# stripped of its ID, citation and separator. Only a leading marker retires a
# requirement; one that merely mentions a removed thing stays active.
REMOVED_MARKER_PATTERN = re.compile(r"^[`*_\s]*REMOVED\b")

# Legacy artifacts are recognised by CONTENT, case-sensitively, never by
# directory name: most projects have a docs/ directory and it is evidence of
# nothing, and `ARCHITECTURE.md` is a project's own document while
# `architecture.md` is the one /sdlc-init writes. A near-miss is a miss.
# `product.md`, `tech.md` and `test-strategy.md` are names this project writes
# and almost nobody else does. `architecture.md` is a name MkDocs, Docusaurus
# and Diataxis all produce by default, so on its own it is evidence of nothing
# -- and treating it as evidence made /sdlc-init refuse to write steering
# documents on projects that had never run these skills at all.
UNAMBIGUOUS_LEGACY_STEERING_NAMES = {
    "product.md", "tech.md", "test-strategy.md"}
CORROBORATED_LEGACY_STEERING_NAMES = {"architecture.md"}
LEGACY_STEERING_DOCUMENT_NAMES = (
    UNAMBIGUOUS_LEGACY_STEERING_NAMES | CORROBORATED_LEGACY_STEERING_NAMES)
# A weak name counts only when its own text cross-references the scheme.
LEGACY_SCHEME_REFERENCE_PATTERN = re.compile(
    r"\.sdlc/|\bADR-\d|\bRULE-\d|\bUS-\d|\bAC-\d|\bNFR-\d|\bFeature Key\b")
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


def validate_project(root, only_feature=None, report=None, excluded_patterns=(),
                     config=None):
    """Run every check over the project at `root` and return the filled Report.

    `only_feature` narrows what is REPORTED, not what is parsed. Every spec is
    read, so the keys and ids of the other features stay resolvable — scoping
    the parse instead made every other feature's tags report as dangling, which
    turned a single-feature review into a wall of false errors.
    """
    report = report or Report()
    config = load_config(root, report) if config is None else config

    check_legacy_layout(root, report)

    spec_paths_by_slug = get_spec_paths_by_slug(root)
    if not spec_paths_by_slug:
        report.info("no-specs",
                    "No SDLC specs found (looked in .sdlc/specs/ and specs/).")
        return report
    if only_feature and only_feature not in spec_paths_by_slug:
        # An ERROR, not an INFO: /sdlc-review runs `--feature <slug> --strict` and
        # maps a clean validator to APPROVE, so a mistyped or re-derived slug used
        # to buy a green review for a feature that was never checked at all.
        report.error("unknown-feature",
                     "No spec found for feature '%s' (looked in .sdlc/specs/ "
                     "and specs/). Known features: %s."
                     % (only_feature,
                        ", ".join(sorted(spec_paths_by_slug)) or "none"))
        return report
    reported_slugs = {only_feature} if only_feature else set(spec_paths_by_slug)

    specs_by_slug, slug_by_key = check_spec_hygiene(
        root, spec_paths_by_slug, report, reported_slugs, config)
    tags = collect_traceability_tags(root, config, report, excluded_patterns)
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
                if tag.feature_key is None or tag.feature_key in reported_keys]
    check_tag_targets(tags, valid_targets, slug_by_key, report)
    check_tag_roles(tags, report)

    reported_specs = {
        slug: spec for slug, spec in specs_by_slug.items() if slug in reported_slugs
    }
    check_requirement_coverage(root, reported_specs, spec_paths_by_slug, tags, report)
    check_ac_citations(root, reported_specs, spec_paths_by_slug, report)
    return report


def load_config(root, report):
    """Return the project configuration, merged over the built-in defaults.

    Absent config is the normal case -- the defaults cover conventional layouts,
    so the validator works on a project that has never seen `.sdlc/config.json`.
    Config is an override, never a prerequisite. Malformed config is an ERROR
    naming the key rather than a silent fallback, because silently ignoring a
    layout declaration would report a project's real tags as missing.
    """
    config = get_default_config()
    config_path = os.path.join(root, CONFIG_RELATIVE_PATH)
    if not os.path.exists(config_path):
        return config

    raw_text = read_file_text(config_path)
    if raw_text is None:
        report.error("config", "Could not read %s." % CONFIG_RELATIVE_PATH,
                     CONFIG_RELATIVE_PATH)
        return config
    try:
        declared = json.loads(raw_text)
    except ValueError as error:
        report.error("config", "%s is not valid JSON: %s"
                     % (CONFIG_RELATIVE_PATH, error), CONFIG_RELATIVE_PATH)
        return config
    if not isinstance(declared, dict):
        report.error("config", "%s must hold a JSON object."
                     % CONFIG_RELATIVE_PATH, CONFIG_RELATIVE_PATH)
        return config

    for section_name, section in sorted(declared.items()):
        if section_name not in config:
            report.warn("config", "Unknown section '%s' in %s -- known sections "
                        "are %s." % (section_name, CONFIG_RELATIVE_PATH,
                                     ", ".join(sorted(config))),
                        CONFIG_RELATIVE_PATH)
            continue
        if not isinstance(section, dict):
            report.error("config", "Section '%s' in %s must be an object."
                         % (section_name, CONFIG_RELATIVE_PATH),
                         CONFIG_RELATIVE_PATH)
            continue
        merge_config_section(config, section_name, section, report)
    return config


def get_default_config():
    """Return a fresh copy of the built-in defaults, safe for the caller to edit."""
    return {
        "layout": {
            "test_directory_names": list(DEFAULT_TEST_DIRECTORY_NAMES),
            "test_stem_patterns": list(DEFAULT_TEST_STEM_PATTERNS),
            "test_path_fragments": list(DEFAULT_TEST_PATH_FRAGMENTS),
            "source_overrides": [],
            "test_overrides": [],
        },
        "headings": {"test_plan": [], "outside_code": []},
        "comments": {},
        "scan": {
            "skip_directories": sorted(SKIPPED_DIRECTORIES),
            "scan_directories": [],
            "max_file_bytes": MAX_SCANNED_BYTES,
        },
    }


def merge_config_section(config, section_name, section, report):
    """Merge one declared section into `config`, reporting anything unusable."""
    for key, value in sorted(section.items()):
        if section_name == "comments":
            merge_comment_declaration(config, key, value, report)
        elif key in CONFIG_LIST_FIELDS.get(section_name, ()):
            if is_list_of_strings(value):
                config[section_name][key] = (
                    config[section_name][key] + [item for item in value
                                                 if item not in config[section_name][key]])
            else:
                report.error("config", "%s.%s in %s must be a list of strings."
                             % (section_name, key, CONFIG_RELATIVE_PATH),
                             CONFIG_RELATIVE_PATH)
        elif section_name == "scan" and key == "max_file_bytes":
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                config["scan"]["max_file_bytes"] = value
            else:
                report.error("config", "scan.max_file_bytes in %s must be a "
                             "positive integer." % CONFIG_RELATIVE_PATH,
                             CONFIG_RELATIVE_PATH)
        else:
            report.warn("config", "Unknown key '%s.%s' in %s."
                        % (section_name, key, CONFIG_RELATIVE_PATH),
                        CONFIG_RELATIVE_PATH)


def merge_comment_declaration(config, extension, declaration, report):
    """Record a project-declared comment syntax for one file extension."""
    location = CONFIG_RELATIVE_PATH
    if not extension.startswith("."):
        report.error("config", "Comment key '%s' in %s must be a file extension "
                     "starting with a dot." % (extension, location), location)
        return
    if not isinstance(declaration, dict):
        report.error("config", "comments['%s'] in %s must be an object with "
                     "'line' and/or 'block'." % (extension, location), location)
        return
    line_leaders = declaration.get("line", [])
    block_pairs = declaration.get("block", [])
    if not is_list_of_strings(line_leaders):
        report.error("config", "comments['%s'].line in %s must be a list of "
                     "strings." % (extension, location), location)
        return
    if not is_list_of_pairs(block_pairs):
        report.error("config", "comments['%s'].block in %s must be a list of "
                     "[open, close] string pairs." % (extension, location), location)
        return
    config["comments"][extension] = {
        "line": list(line_leaders),
        "block": [tuple(pair) for pair in block_pairs],
    }


def is_list_of_strings(value):
    """Return True when `value` is a list holding only strings."""
    return (isinstance(value, list)
            and all(isinstance(item, str) for item in value))


def is_list_of_pairs(value):
    """Return True when `value` is a list of two-string lists or tuples."""
    return (isinstance(value, list)
            and all(isinstance(pair, (list, tuple)) and len(pair) == 2
                    and all(isinstance(item, str) for item in pair)
                    for pair in value))


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
    if has_legacy_steering_documents(root):
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


def has_legacy_steering_documents(root):
    """True when `docs/` holds steering documents this project actually wrote.

    An unambiguous name is enough on its own. A weak name -- `architecture.md`,
    which half the documentation generators in the world emit -- counts only
    when its text cross-references the scheme, so an ordinary project's
    `docs/architecture.md` is not mistaken for a legacy SDLC layout.
    """
    entry_names = set(get_entry_names(root, "docs"))
    if UNAMBIGUOUS_LEGACY_STEERING_NAMES & entry_names:
        return True
    for name in sorted(CORROBORATED_LEGACY_STEERING_NAMES & entry_names):
        document_text = read_file_text(os.path.join(root, "docs", name))
        if document_text and LEGACY_SCHEME_REFERENCE_PATTERN.search(document_text):
            return True
    return False


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


def check_spec_hygiene(root, spec_paths_by_slug, report, reported_slugs=None,
                       config=None):
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

        spec = parse_spec(text, config)
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

        for requirement_id in sorted(spec["relisted_nfrs"]):
            spec_report.info(
                "nfr-relisted",
                "%s is listed twice but under no recognised 'NFRs Validated "
                "Outside Code' heading, so it is NOT exempt from "
                "IMPLEMENTS:/COVERS:." % requirement_id, location)

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
    for requirement_id, raw_text in sorted(requirement_texts.items()):
        text = get_unquoted_text(raw_text)
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
        if not SHALL_PATTERN.search(text):
            if LOWERCASE_SHALL_PATTERN.search(text):
                report.warn("ears",
                            "%s uses lowercase 'shall' — EARS keywords are uppercase."
                            % requirement_id, location)
            else:
                report.warn("ears",
                            "%s has no SHALL/EARS keyword — restate in canonical EARS."
                            % requirement_id, location)
            continue

        shall_count = len(SHALL_PATTERN.findall(text))
        if shall_count > 1:
            report.warn("ears",
                        "%s contains %d SHALL clauses — one requirement, one "
                        "SHALL. Split it, keeping %s for the first."
                        % (requirement_id, shall_count, requirement_id), location)
            continue

        if get_ears_structure_problem(text):
            report.warn("ears",
                        "%s has no subject before SHALL — write 'the <system> "
                        "SHALL <response>'." % requirement_id, location)
            continue

        non_ears_keyword = get_non_ears_leading_keyword(text)
        if non_ears_keyword:
            hint = NON_EARS_KEYWORD_HINTS.get(non_ears_keyword)
            report.warn("ears",
                        "%s opens with '%s', which is not an EARS keyword%s."
                        % (requirement_id, non_ears_keyword,
                           " — use %s" % hint if hint else
                           " — use WHEN, WHILE, WHERE, IF, or a ubiquitous "
                           "'The <system> SHALL ...'"),
                        location)
            continue

        vague_match = VAGUE_TERM_PATTERN.search(text)
        if vague_match:
            report.warn("ears",
                        "%s uses the unverifiable term '%s' — state a measurable "
                        "target, or move it to the NFR table."
                        % (requirement_id, vague_match.group(1)), location)


def get_deprecated_ears_hint(text):
    """Return the migration hint for the first deprecated pattern, else None."""
    for pattern, hint in DEPRECATED_EARS_PATTERNS:
        if pattern.search(text):
            return hint
    for keyword, hint in DEPRECATED_LEADING_THEN_HINTS:
        if is_deprecated_leading_then(text, keyword):
            return hint
    return None


def is_deprecated_leading_then(text, keyword):
    """True when `keyword` opens the requirement and owns the THEN that follows.

    A THEN with an IF, WHEN or WHILE between it and the keyword belongs to that
    clause rather than to the keyword, which is why the canonical composite
    `WHERE <feature>, IF <condition>, THEN ... SHALL ...` is not deprecated.
    """
    opening = re.match(r"\s*%s\b" % keyword, text)
    if not opening:
        return False
    then_match = re.search(r"\bTHEN\b", text)
    if not then_match:
        return False
    return not re.search(r"\b(?:IF|WHEN|WHILE)\b",
                         text[opening.end():then_match.start()])


def get_unquoted_text(text):
    """Return the requirement with quoted and backticked spans blanked out."""
    return QUOTED_SPAN_PATTERN.sub(" ", text)


def get_ears_structure_problem(text):
    """Return True when no subject sits between the trigger and SHALL."""
    match = EARS_MAIN_CLAUSE_PATTERN.search(text)
    return not match or not match.group(1).strip()


def get_non_ears_leading_keyword(text):
    """Return an uppercase opening word that is not an EARS keyword, else None."""
    first_word_match = FIRST_WORD_PATTERN.match(text)
    if not first_word_match:
        return None
    first_word = first_word_match.group(1)
    if first_word in EARS_LEADING_KEYWORDS or first_word == "SHALL":
        return None
    return first_word


def collect_traceability_tags(root, config, report, excluded_patterns=()):
    """Walk the project, returning every traceability tag found in a comment.

    Documentation is skipped entirely, so a README showing the tag format
    neither claims coverage nor reports as a dangling tag. Every other file is
    read for comments and classified as source or test, since a tag means
    different things in each.
    """
    skipped_directories = set(config["scan"]["skip_directories"])
    skipped_directories -= set(config["scan"]["scan_directories"])
    maximum_bytes = config["scan"]["max_file_bytes"]
    tags = []
    for directory_path, directory_names, file_names in os.walk(root):
        directory_names[:] = [
            name for name in directory_names if name not in skipped_directories
        ]
        for file_name in file_names:
            extension = os.path.splitext(file_name)[1].lower()
            if extension in SKIPPED_EXTENSIONS:
                continue
            file_path = os.path.join(directory_path, file_name)
            relative_path = os.path.relpath(file_path, root)
            if is_excluded_path(relative_path, excluded_patterns):
                continue
            role = get_file_role(relative_path, config)
            if role == ROLE_DOC:
                continue
            file_text = read_file_text(file_path, maximum_bytes, relative_path, report)
            if file_text is None:
                continue
            parsed_tags_by_kind = parse_traceability_tags(file_text, extension, config)
            for kind, parsed_tags in parsed_tags_by_kind.items():
                for feature_key, requirement_id in parsed_tags:
                    tags.append(TraceabilityTag(feature_key, requirement_id,
                                                kind, relative_path, role))
    return tags


def get_file_role(relative_path, config):
    """Classify a scanned file as source, test, or documentation.

    Every code file is source or test; only documentation is neither. That
    keeps the report actionable -- a misplaced tag is always "the wrong kind of
    file", never "unclassifiable".
    """
    posix_path = relative_path.replace(os.sep, "/")
    if os.path.splitext(posix_path)[1].lower() in DOCUMENTATION_EXTENSIONS:
        return ROLE_DOC
    layout = config["layout"]
    if is_matching_any_glob(posix_path, layout["source_overrides"]):
        return ROLE_SOURCE
    if is_matching_any_glob(posix_path, layout["test_overrides"]):
        return ROLE_TEST
    return ROLE_TEST if is_test_path(posix_path, layout) else ROLE_SOURCE


def is_test_path(posix_path, layout):
    """True when a path names a test by directory, path fragment, or filename stem.

    Matched on path COMPONENTS and filename STEMS, never on substrings, so
    `src/contest/models.py` and `src/latest_prices.py` stay source.
    """
    directory_names = set(posix_path.split("/")[:-1])
    if directory_names & set(layout["test_directory_names"]):
        return True
    if any(fragment in posix_path for fragment in layout["test_path_fragments"]):
        return True
    stem = posix_path.rsplit("/", 1)[-1]
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]
    return any(fnmatch.fnmatch(stem, pattern)
               for pattern in layout["test_stem_patterns"])


def is_matching_any_glob(posix_path, patterns):
    """True when the path matches any of the globs, by full path or by name."""
    base_name = posix_path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(posix_path, pattern)
               or fnmatch.fnmatch(base_name, pattern)
               for pattern in patterns)


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

    A fence closes only on the same character, at least as long as the opener,
    and with no info string, so a fenced block may itself contain a shorter
    fence. An unclosed fence blanks everything after it: in a document, a
    missed example costs less than an invented tag.
    """
    lines = text.splitlines()
    open_marker = None
    for index, line in enumerate(lines):
        fence_match = CODE_FENCE_PATTERN.match(line)
        if open_marker is None:
            if fence_match:
                open_marker = fence_match.group(1)
                lines[index] = ""
            continue
        if (fence_match
                and fence_match.group(1)[0] == open_marker[0]
                and len(fence_match.group(1)) >= len(open_marker)
                and not fence_match.group(2)):
            open_marker = None
        lines[index] = ""
    return "\n".join(lines)


def get_declared_heading_match(text, extra_headings):
    """Return a match for the first project-declared heading found, or None."""
    for declared in extra_headings:
        title = re.escape(declared.lstrip("#").strip())
        match = re.search(r"^#{2,4}\s+%s\s*$" % title, text, re.M | re.I)
        if match:
            return match
    return None


def parse_traceability_tags(file_text, extension, config):
    """Return {kind: [(feature_key_or_None, id), ...]} for one file's tags.

    Only comment text is read, and a header tag must OPEN its comment. Scanning
    every line unanchored counted a string literal, a line of prose, and
    `# This file does NOT IMPLEMENTS: KEY:REQ-001` as real coverage.
    """
    tags_by_kind = {"IMPLEMENTS": [], "COVERS": [], "@sdlc": []}
    for comment_text in get_comment_texts(file_text, extension, config):
        body = COMMENT_CONTINUATION_PATTERN.sub("", comment_text, count=1)
        for kind, pattern in ANCHORED_TAG_PATTERNS_BY_KIND.items():
            match = pattern.match(body)
            if not match:
                continue
            for token in TAG_TOKEN_PATTERN.finditer(match.group(1)):
                tags_by_kind[kind].append((token.group(1), token.group(2)))
    return tags_by_kind


def get_comment_texts(file_text, extension, config):
    """Return the comment text of every line, one entry per line that has one.

    Not a lexer. A single left-to-right pass that skips string literals, so
    `MSG = "IMPLEMENTS: KEY:REQ-001"` stops claiming coverage, while a tag in a
    `/* ... */` block or a Python docstring is still seen. Block state carries
    across lines.
    """
    line_leaders, block_pairs = get_comment_syntax(extension, config)
    comment_texts = []
    close_marker = None
    for line in file_text.splitlines():
        while line:
            if close_marker:
                body, found, remainder = line.partition(close_marker)
                comment_texts.append(body)
                if not found:
                    break
                close_marker, line = None, remainder
                continue
            opener, offset, marker_length = get_first_comment_opener(
                line, line_leaders, block_pairs)
            if opener is None:
                break
            if opener == "line":
                comment_texts.append(line[offset + marker_length:])
                break
            close_marker = opener
            line = line[offset + marker_length:]
    return comment_texts


def get_first_comment_opener(line, line_leaders, block_pairs):
    """Return (opener, offset, marker_length) for the first comment on a line.

    `opener` is "line" for a line comment, the closing marker for a block
    comment, or None when the line holds no comment. A marker inside a quoted
    span is skipped, so the earliest marker returned is one that really opens
    a comment.
    """
    best = (None, len(line), 0)
    for leader in line_leaders:
        offset = line.find(leader)
        while offset != -1:
            if not is_inside_string_literal(line, offset):
                if offset < best[1]:
                    best = ("line", offset, len(leader))
                break
            offset = line.find(leader, offset + 1)
    for open_marker, close_marker in block_pairs:
        offset = line.find(open_marker)
        while offset != -1:
            if not is_inside_string_literal(line, offset):
                if offset < best[1]:
                    best = (close_marker, offset, len(open_marker))
                break
            offset = line.find(open_marker, offset + 1)
    return best if best[0] is not None else (None, 0, 0)


def is_inside_string_literal(line, offset):
    """True when `offset` sits inside a quoted span earlier on the same line.

    Counts unescaped quotes before the offset. This is an approximation, not a
    lexer: it rejects a comment marker inside an ordinary string without
    tokenising the language.
    """
    for quote in ('"', "'"):
        count, index = 0, 0
        while index < offset:
            character = line[index]
            if character == "\\":
                index += 2
                continue
            if character == quote:
                count += 1
            index += 1
        if count % 2:
            return True
    return False


def get_comment_syntax(extension, config):
    """Return (line_leaders, block_pairs) for a file extension.

    An unknown extension falls back to a generous leader set rather than losing
    its tags: an exotic language should still be able to claim coverage, and
    prose fails the check anyway because it carries no leader at all.
    """
    declared = config["comments"].get(extension)
    if declared:
        return list(declared["line"]), list(declared["block"])
    line_leaders = list(LINE_COMMENT_LEADERS_BY_EXTENSION.get(extension, ()))
    block_pairs = list(BLOCK_COMMENT_PAIRS_BY_EXTENSION.get(extension, ()))
    if not line_leaders and not block_pairs:
        return list(FALLBACK_LINE_COMMENT_LEADERS), []
    return line_leaders, block_pairs


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
    for feature_key, requirement_id, kind, relative_path, _ in tags:
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


def check_tag_roles(tags, report):
    """Check 15 — IMPLEMENTS lives in source, COVERS lives in tests.

    Reported at the tag rather than at the requirement, which is nearer the
    edit that caused it. The matching coverage error names this path too, so
    the two findings read as one problem.
    """
    expected_role_by_kind = {"IMPLEMENTS": ROLE_SOURCE, "COVERS": ROLE_TEST}
    remedy_by_kind = {
        "IMPLEMENTS": "Move it to the source file that implements the "
                      "requirement, or list this path under layout.source_overrides",
        "COVERS": "Move it to the test that covers the requirement, or list "
                  "this path under layout.test_overrides",
    }
    for tag in tags:
        expected_role = expected_role_by_kind.get(tag.kind)
        if expected_role is None or tag.role == expected_role:
            continue
        report.error("tag-role",
                     "%s: %s:%s sits in %s, which is a %s file, so it does not "
                     "satisfy %s coverage. %s in %s."
                     % (tag.kind, tag.feature_key or "", tag.requirement_id,
                        tag.relative_path, tag.role,
                        "code" if tag.kind == "IMPLEMENTS" else "test",
                        remedy_by_kind[tag.kind], CONFIG_RELATIVE_PATH),
                     tag.relative_path)


def check_requirement_coverage(root, specs_by_slug, spec_paths_by_slug, tags, report):
    """Checks 2, 3, 9 — every requirement is implemented, tested, and planned.

    A tag counts only from the right kind of file: IMPLEMENTS from source,
    COVERS from a test. `misplaced_paths_by_target` records the tags that fail
    that rule so the coverage error can name where they actually sit.
    """
    implemented_targets = {
        (tag.feature_key, tag.requirement_id) for tag in tags
        if tag.kind == "IMPLEMENTS" and tag.feature_key and tag.role == ROLE_SOURCE
    }
    covered_targets = {
        (tag.feature_key, tag.requirement_id) for tag in tags
        if tag.kind == "COVERS" and tag.feature_key and tag.role == ROLE_TEST
    }
    misplaced_paths_by_target = {}
    for tag in tags:
        if tag.kind not in ("IMPLEMENTS", "COVERS") or not tag.feature_key:
            continue
        expected_role = ROLE_SOURCE if tag.kind == "IMPLEMENTS" else ROLE_TEST
        if tag.role != expected_role:
            key = (tag.feature_key, tag.requirement_id, tag.kind)
            misplaced_paths_by_target.setdefault(key, []).append(tag.relative_path)

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
                             "%s:%s has no IMPLEMENTS: header in any source file.%s"
                             % (feature_key, requirement_id,
                                get_misplaced_hint(misplaced_paths_by_target,
                                                   feature_key, requirement_id,
                                                   "IMPLEMENTS", "a source")),
                             location)
            if (feature_key, requirement_id) not in covered_targets:
                report.error("trace-test",
                             "%s:%s has no COVERS: header in any test file.%s"
                             % (feature_key, requirement_id,
                                get_misplaced_hint(misplaced_paths_by_target,
                                                   feature_key, requirement_id,
                                                   "COVERS", "a test")),
                             location)
            is_planned = re.search(r"\b%s\b" % re.escape(requirement_id),
                                   test_plan_text)
            if requirement_id.startswith("REQ-") and test_plan_text and not is_planned:
                report.warn("plan-coverage",
                            "%s not referenced by any row in the test plan."
                            % requirement_id, test_plan_location)

        # Check 18: a plan row that points at nothing real.
        for referenced_id in sorted(set(REQUIREMENT_ID_PATTERN.findall(test_plan_text))):
            if referenced_id in spec["removed_ids"]:
                report.error("plan-stale-row",
                             "The test plan references %s, which is REMOVED. "
                             "Delete the row — the requirement it planned is "
                             "retired." % referenced_id, test_plan_location)
            elif referenced_id not in spec["active_ids"]:
                report.error("plan-unknown-row",
                             "The test plan references %s, which feature '%s' "
                             "does not define." % (referenced_id, slug),
                             test_plan_location)

        # Check 13: the other direction — a planned test that nothing covers.
        for test_id in sorted(spec["test_ids"]):
            if (feature_key, test_id) not in covered_targets:
                report.warn("plan-test-uncovered",
                            "%s is planned in the test plan but no test file "
                            "COVERS it." % test_id, test_plan_location)


def get_misplaced_hint(misplaced_paths_by_target, feature_key, requirement_id,
                       kind, expected_description):
    """Return a clause naming where a misplaced tag for this target actually sits."""
    paths = misplaced_paths_by_target.get((feature_key, requirement_id, kind))
    if not paths:
        return ""
    return (" (a %s: tag for it exists in %s, which is not %s file)"
            % (kind, ", ".join(sorted(set(paths))), expected_description))


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
    brief_text = strip_code_fences(read_file_text(brief_path) or "")
    defined_ac_ids = set(AC_DEFINITION_PATTERN.findall(brief_text))
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


def is_matching_heading(heading, pattern, extra_headings):
    """True when a heading matches the built-in pattern or a project-declared one."""
    if pattern.search(heading):
        return True
    stripped = heading.lstrip("#").strip().lower()
    return any(stripped == declared.lstrip("#").strip().lower()
               for declared in extra_headings)


def parse_spec(text, config=None):
    """Parse a spec.md into its feature key, requirement IDs, texts, and test plan.

    Fenced blocks are blanked first, for the same reason the tag scanner blanks
    them: a spec that SHOWS the REMOVED form inside a fence is documenting it,
    and reading that example as a definition reported the real requirement as a
    recycled id. Blanking preserves line count, so line numbers stay true.
    """
    text = strip_code_fences(text)
    headings = (config or get_default_config())["headings"]
    feature_key_match = FEATURE_KEY_PATTERN.search(text)
    declared_key_match = FEATURE_KEY_LINE_PATTERN.search(text)
    active_ids = {}          # id -> line number of its first active definition
    duplicate_ids = []
    removed_ids = set()
    relisted_nfrs = set()    # NFR listed twice, but under no recognised heading
    requirement_texts = {}   # REQ id -> requirement text (active only)
    ac_citations = {}        # REQ id -> {AC ids it cites}
    outside_code_nfrs = set()

    is_outside_code_section = False
    current_heading = ""
    headings_by_id = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped_line = line.strip()
        if stripped_line.startswith("#"):
            current_heading = stripped_line
            is_outside_code_section = is_matching_heading(
                stripped_line, OUTSIDE_CODE_HEADING_PATTERN,
                headings["outside_code"])

        definition_match = REQUIREMENT_LINE_PATTERN.match(line)
        if not definition_match:
            continue
        requirement_id, remainder = definition_match.group(1), definition_match.group(2)

        if REMOVED_MARKER_PATTERN.match(get_requirement_text(remainder)):
            removed_ids.add(requirement_id)
            continue

        if is_outside_code_section and requirement_id.startswith("NFR-"):
            outside_code_nfrs.add(requirement_id)
        if requirement_id in active_ids:
            # An ID repeated under the SAME heading is a copy-paste mistake. The
            # same ID under two headings is the documented pattern — an NFR
            # listed in the table and repeated under the exemption heading — so
            # scoping by section means a reworded heading costs an exemption
            # rather than inventing a duplicate-definition error.
            if headings_by_id.get(requirement_id) == current_heading:
                duplicate_ids.append(requirement_id)
            elif (requirement_id.startswith("NFR-")
                    and requirement_id not in outside_code_nfrs):
                relisted_nfrs.add(requirement_id)
        else:
            active_ids[requirement_id] = line_number
            headings_by_id[requirement_id] = current_heading

        if requirement_id.startswith("REQ-"):
            requirement_texts[requirement_id] = get_requirement_text(remainder)
            ac_citations[requirement_id] = set(AC_CITATION_PATTERN.findall(
                get_requirement_citation(remainder)))

    test_plan_text = get_test_plan_section(text, headings["test_plan"])
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
        "relisted_nfrs": relisted_nfrs - outside_code_nfrs,
        "test_plan_text": test_plan_text,
        "test_ids": set(TEST_ID_PATTERN.findall(test_plan_text)),
    }


def get_requirement_text(remainder):
    """Return the requirement prose that follows the ID and its optional citation.

    Splitting on the first colon truncated a requirement at its own punctuation
    -- `the system SHALL set Retry-After: 30` lost the `30` and gained a bogus
    citation of everything before it.
    """
    return CITATION_PATTERN.sub("", remainder, count=1).lstrip(" \t:\u2014-").strip()


def get_requirement_citation(remainder):
    """Return the `(AC-NNN)` citation that precedes the requirement prose, or ''.

    Read positionally rather than by splitting on a colon, so a requirement
    written without one still has its citation checked, and a colon inside the
    requirement prose does not truncate it.
    """
    citation_match = CITATION_PATTERN.match(remainder)
    return citation_match.group(1) if citation_match else ""


def get_test_plan_section(text, extra_headings=()):
    """Return the text under the spec's test-plan heading, or '' if absent."""
    heading_match = TEST_PLAN_HEADING_PATTERN.search(text)
    if not heading_match:
        heading_match = get_declared_heading_match(text, extra_headings)
    if not heading_match:
        return ""
    section_start = heading_match.end()
    heading_level = len(heading_match.group(0).split()[0])
    next_heading = re.compile(r"^#{1,%d}\s+" % heading_level, re.M)
    next_match = next_heading.search(text, section_start)
    return text[section_start:next_match.start()] if next_match else text[section_start:]


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


def read_file_text(path, maximum_bytes=None, relative_path=None, report=None):
    """Return a file's text, or None when it is missing, binary, or oversized.

    A scanner passes `report` so that a skip is announced: an oversized or
    binary file is otherwise indistinguishable from one holding no tags, and
    the requirement it covers reports as untraced with nothing to explain why.
    """
    maximum_bytes = MAX_SCANNED_BYTES if maximum_bytes is None else maximum_bytes
    try:
        file_size = os.path.getsize(path)
        if file_size > maximum_bytes:
            if report is not None:
                report.warn("skipped-file",
                            "%s was not scanned for tags (%.1f MB exceeds the "
                            "%.1f MB scan limit). Raise scan.max_file_bytes in "
                            "%s, or exclude the path."
                            % (relative_path, file_size / 1048576.0,
                               maximum_bytes / 1048576.0, CONFIG_RELATIVE_PATH),
                            relative_path)
            return None
        with open(path, "rb") as file_handle:
            raw_bytes = file_handle.read()
        if b"\x00" in raw_bytes:
            if report is not None:
                report.info("skipped-file",
                            "%s was not scanned for tags (binary content)."
                            % relative_path, relative_path)
            return None
        return raw_bytes.decode("utf-8", errors="replace")
    except (OSError, ValueError):
        if report is not None:
            report.warn("skipped-file", "%s could not be read."
                        % relative_path, relative_path)
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
