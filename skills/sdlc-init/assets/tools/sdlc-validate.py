#!/usr/bin/env python3
"""sdlc-validate.py — deterministic validator for SDLC artifacts.

Installed into a project at `.sdlc/tools/sdlc-validate.py` by `/sdlc-init`.
Run it by hand, from a skill ("validate -> fix -> repeat"), or as a CI gate.
Stdlib only; Python 3.8+. This file is the only copy.

USAGE
    python3 sdlc-validate.py [--root DIR] [--feature SLUG] [--strict] [--json]
                             [--exclude GLOB ...] [--relax-tag-roles]

    --root DIR     Project root to scan (default: current directory).
    --feature SLUG Restrict FINDINGS to one feature. Every spec is still parsed,
                   so other features' tags resolve. An unknown slug is an ERROR.
    --strict       Warnings exit non-zero too.
    --json         Machine-readable report.
    --exclude GLOB Skip matching files when scanning for tags (repeatable).
    --relax-tag-roles
                   Migration ramp: a tag counts wherever it sits and a misplaced
                   one is a WARNING. Same as `gate.enforce_tag_roles: false`.

EXIT CODES
    0 clean   1 warnings under --strict   2 errors

TAGS (see .sdlc/CONVENTIONS.md)
    Source:  IMPLEMENTS: KEY:REQ-001, KEY:NFR-002
    Test:    COVERS: KEY:REQ-002, KEY:UT-005
    Inline:  @sdlc KEY:REQ-003
    A tag counts only inside a real comment, and it must open that comment.
    IMPLEMENTS counts only from a SOURCE file, COVERS only from a TEST file.
    DOC files (.md, .rst, .txt, .json, ...) are never scanned. A file is TEST
    by path component or filename stem (`tests/`, `*_test.go`, `src/test/`),
    never by substring; everything else is SOURCE. `.sdlc/config.json`
    overrides all of it.

FINDINGS (check id — severity)
    config ............... ERROR unusable config / WARNING unknown key
    gate-relaxed ......... WARNING  tag-role enforcement is off
    legacy-layout ........ INFO     artifacts at pre-.sdlc/ paths
    no-specs ............. INFO
    unknown-feature ...... ERROR    --feature names a slug with no spec
    read ................. ERROR    spec unreadable
    unclosed-fence ....... WARNING  in a spec or the brief
    feature-key .......... ERROR invalid / INFO defaulted from the slug
    key-unique ........... ERROR
    dup-id ............... ERROR    ID defined twice under one heading
    recycled-id .......... ERROR    ID both REMOVED and active
    nfr-relisted ......... INFO     NFR repeated outside an exemption heading
    ears ................. WARNING
    missing-test-plan .... WARNING
    legacy-test-plan ..... INFO     separate test-plan.md
    unkeyed-tag .......... WARNING  and does not satisfy coverage
    dangling-tag ......... ERROR
    tag-role ............. ERROR (WARNING when relaxed)
    exemption-heading .... WARNING  REQ-* under the NFR-only heading
    outside-code ......... INFO     exempted requirement, reported every run
    trace-code/trace-test  ERROR    requirement with no IMPLEMENTS / COVERS
    plan-coverage ........ WARNING  REQ-* with no test-plan row
    plan-stale-row ....... ERROR    plan row cites a REMOVED ID
    plan-unknown-row ..... ERROR    plan row cites an undefined ID
    plan-test-uncovered .. WARNING  planned test id nothing COVERS
    ac-citation .......... ERROR    requirement cites an AC the brief lacks
    ac-uncited ........... INFO     brief AC no active requirement cites
                                    (whole-project runs only)
    skipped-file ......... WARNING oversized/unreadable / INFO binary
"""

# SPEC: .sdlc/specs/validator/spec.md
# IMPLEMENTS: VAL:REQ-001, VAL:REQ-002, VAL:REQ-003, VAL:REQ-004, VAL:REQ-005, VAL:REQ-006, VAL:REQ-007, VAL:REQ-008, VAL:REQ-009, VAL:REQ-010, VAL:REQ-011, VAL:REQ-012, VAL:REQ-013, VAL:REQ-014, VAL:REQ-015, VAL:REQ-016, VAL:REQ-017, VAL:REQ-018, VAL:REQ-019, VAL:REQ-020, VAL:REQ-021, VAL:NFR-001

import argparse
import collections
import fnmatch
import json
import os
import re
import sys

ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"
EXIT_CLEAN, EXIT_WARNINGS, EXIT_ERRORS = 0, 1, 2

TraceabilityTag = collections.namedtuple(
    "TraceabilityTag", "feature_key requirement_id kind relative_path role"
)

SKIPPED_DIRECTORIES = set(
    ".git .sdlc node_modules dist build __pycache__ .venv venv .mypy_cache"
    " .pytest_cache target .next coverage .tox".split()
)
SKIPPED_EXTENSIONS = set(
    ".png .jpg .jpeg .gif .pdf .zip .gz .tar .lock .ico .woff .woff2 .ttf .eot"
    " .mp4 .mp3 .bin .so .dll .dylib .class .jar .wasm .pyc".split()
)
MAX_SCANNED_BYTES = 2 * 1024 * 1024

# Never scanned. Documentation shows the tag format rather than claiming it;
# prose and data implement nothing. `.jsonc`/`.json5` carry real comments, so
# they stay scannable.
DOCUMENTATION_EXTENSIONS = set(".md .markdown .rst .adoc .asciidoc .org".split())
UNTAGGABLE_EXTENSIONS = set(
    ".txt .text .log .csv .tsv .json .jsonl .ndjson .geojson".split()
)
UNSCANNED_EXTENSIONS = DOCUMENTATION_EXTENSIONS | UNTAGGABLE_EXTENSIONS

# Every scanned file is SOURCE or TEST; DOC files are skipped before reading.
ROLE_SOURCE, ROLE_TEST, ROLE_DOC = "source", "test", "doc"
EXPECTED_ROLE_BY_KIND = {"IMPLEMENTS": ROLE_SOURCE, "COVERS": ROLE_TEST}

# Matched on path COMPONENTS and filename STEMS, never substrings, so
# `src/contest/` stays source. `features` is deliberately absent: `src/features/`
# is a component directory more often than a Cucumber suite.
DEFAULT_TEST_DIRECTORY_NAMES = (
    "tests test spec specs __tests__ testing e2e cypress"
    " integration-tests integration_tests".split()
)
DEFAULT_TEST_STEM_PATTERNS = (
    "test_* *_test *_tests *_spec *.test *.spec *Test *Tests *Spec *Specs"
    " conftest *.cy *.e2e *_e2e *IT *ITCase *TestCase *.tftest".split()
)
DEFAULT_TEST_PATH_FRAGMENTS = (
    "src/test/ src/it/ src/androidTest/ src/integrationTest/"
    " src/functionalTest/".split()
)

# A tag counts only inside a real comment. An extension may carry several
# leaders (`.m` is Objective-C and MATLAB): accepting both loses fewer tags.
LINE_COMMENT_EXTENSIONS_BY_LEADER = {
    "#": ".py .rb .sh .bash .zsh .fish .pl .pm .r .yaml .yml .toml .tf .tfvars"
    " .ex .exs .jl .nim .cr .conf .cmake .mk .pp .rake .tcl .awk .ps1 .gemspec"
    " .dockerfile",
    "//": ".js .jsx .mjs .cjs .ts .tsx .go .rs .java .c .h .cpp .hpp .cc .hh .cs"
    " .swift .kt .kts .scala .dart .php .proto .gradle .groovy .sol .zig .m .mm"
    " .scss .less .jsonc .json5 .v .sv .glsl .hlsl",
    "--": ".sql .hs .lhs .lua .elm .adb .ads .vhd .vhdl .applescript",
    ";": ".lisp .cl .clj .cljs .cljc .el .scm .rkt .ini .asm .s",
    "%": ".tex .sty .erl .hrl .prolog",
    "!": ".f .f90 .f95 .f03 .f08",
    "'": ".vb .vbs .bas",
    '"': ".vim .vimrc",
    "REM ": ".bat .cmd",
}
BLOCK_COMMENT_EXTENSIONS_BY_PAIR = {
    ("/*", "*/"): ".js .jsx .mjs .cjs .ts .tsx .go .rs .java .c .h .cpp .hpp .cc"
    " .hh .cs .swift .kt .kts .scala .dart .php .css .scss .less .proto .sol"
    " .groovy .gradle .m .mm .v .sv .glsl .hlsl",
    ("<!--", "-->"): ".html .htm .xhtml .xml .xsl .xslt .svg .vue .svelte .astro"
    " .plist .resx",
    ("=begin", "=end"): ".rb",
    ("{-", "-}"): ".hs .lhs .elm",
    ("--[[", "]]"): ".lua",
}
# For an extension in neither table: broad, so an unlisted language keeps its
# tags. Prose still fails, carrying no leader.
FALLBACK_LINE_COMMENT_LEADERS = ("#", "//", "--", ";", "%", "!")

# Continuation markers a comment body may open with (javadoc `*`, doubled
# leaders, box-drawing dashes), stripped before the tag is matched.
COMMENT_CONTINUATION_PATTERN = re.compile(r"^[\s*#/\-!;%]*")


def get_inverted_extension_table(extensions_by_marker):
    """Invert {marker: "ext ext ..."} into {ext: [marker, ...]}."""
    markers_by_extension = {}
    for marker, extensions in extensions_by_marker.items():
        for extension in extensions.split():
            markers_by_extension.setdefault(extension, []).append(marker)
    return markers_by_extension


LINE_COMMENT_LEADERS_BY_EXTENSION = get_inverted_extension_table(
    LINE_COMMENT_EXTENSIONS_BY_LEADER
)
BLOCK_COMMENT_PAIRS_BY_EXTENSION = get_inverted_extension_table(
    BLOCK_COMMENT_EXTENSIONS_BY_PAIR
)

CONFIG_RELATIVE_PATH = os.path.join(".sdlc", "config.json")
CONFIG_LIST_FIELDS = {
    "layout": (
        "test_directory_names",
        "test_stem_patterns",
        "test_path_fragments",
        "source_overrides",
        "test_overrides",
        "generated_globs",
        "vendored_globs",
    ),
    "headings": ("test_plan", "outside_code", "outside_code_functional"),
    "scan": ("skip_directories", "scan_directories"),
}

# The template bolds the key, but a spec that drops the asterisks still
# declares one. The LINE pattern captures whatever was written, valid or not,
# so a malformed key reports as malformed rather than missing.
_FEATURE_KEY_PREFIX = (
    r"^\s*(?:[-*+]\s*)?(?:\*\*|__)?Feature Key(?:\*\*|__)?\s*:\s*(?:\*\*|`)?\s*"
)
FEATURE_KEY_PATTERN = re.compile(_FEATURE_KEY_PREFIX + r"([A-Z][A-Z0-9_-]*)", re.M)
FEATURE_KEY_LINE_PATTERN = re.compile(_FEATURE_KEY_PREFIX + r"(\S+)", re.M)
FEATURE_KEY_TOKEN_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]*$")
# An ID token, optionally key-prefixed: KEY:REQ-001 or REQ-001.
TAG_TOKEN_PATTERN = re.compile(
    r"\b(?:([A-Z][A-Z0-9_-]*):)?((?:REQ|NFR|UT|IT|E2E|PBT)-\d+)\b"
)
# A definition needs a list/table marker before the ID and `:`, `(AC-NNN)` or a
# cell boundary after it. `- REQ-001 was hard` names an ID; it defines nothing.
REQUIREMENT_LINE_PATTERN = re.compile(
    r"^\s*(?:[-*+]|\|)\s*`?((?:REQ|NFR)-\d+)`?\s*(?=[:(|]|$)(.*)$"
)
TEST_ID_PATTERN = re.compile(r"\b((?:UT|IT|E2E|PBT)-\d+)\b")
REQUIREMENT_ID_PATTERN = re.compile(r"\b((?:REQ|NFR)-\d+)\b")
AC_CITATION_PATTERN = re.compile(r"\b(AC-\d+)\b")
# The `(AC-NNN)` citation sits immediately after the ID, before the prose.
CITATION_PATTERN = re.compile(r"^\s*\(([^)]*)\)")
# The brief DEFINES an AC on a list or table line; a mention elsewhere does not.
AC_DEFINITION_PATTERN = re.compile(
    r"^\s*(?:[-*+]|\|)\s*(?:\[[ xX]\]\s*)?`?(AC-\d+)`?\s*(?=[:(|]|$)", re.M
)
# Anchored to the START of a comment body, so `# does NOT IMPLEMENTS: X` and
# `# REIMPLEMENTS:` are not claims.
ANCHORED_TAG_PATTERNS_BY_KIND = {
    "IMPLEMENTS": re.compile(r"^IMPLEMENTS:\s*(.+)"),
    "COVERS": re.compile(r"^COVERS:\s*(.+)"),
    "@sdlc": re.compile(r"^@sdlc\s+(.+)"),
}
# Headings are matched by meaning, since templates are project-owned. Anything
# else goes in `headings.*` in .sdlc/config.json.
TEST_PLAN_HEADING_PATTERN = re.compile(
    r"^#{2,4}\s+(?:Test Plan|Tests|Test Cases|Test Design|Testing|Test Strategy)\b",
    re.M | re.I,
)
# The NFR exemption heading ("NFRs Validated Outside Code" and rewordings).
OUTSIDE_CODE_HEADING_PATTERN = re.compile(
    r"\boutside\b[^#]{0,32}\bcode\b|\bnot\b[^#]{0,32}\bin\s+code\b"
    r"|\bvalidated\b[^#]{0,32}\b(?:infra|infrastructure|externally|process)\b",
    re.I,
)
# The functional (REQ-*) exemption heading. A separate heading, because
# exempting what the code is FOR is a bigger claim than exempting an NFR, and a
# shared heading would let a REQ-* be exempted by moving its line. It must stay
# disjoint from the NFR pattern (pinned by a test): a heading matching both
# would silently stop tracking an NFR listed under it.
FUNCTIONAL_OUTSIDE_CODE_HEADING_PATTERN = re.compile(
    r"\bno\b[^#]{0,24}\bin-?code\b[^#]{0,24}\bverif"
    r"|\bwithout\b[^#]{0,24}\b(?:no\s+)?in-?code\b[^#]{0,24}\bverif"
    r"|\bwithout\b[^#]{0,32}\bverif",
    re.I,
)
# A fence opens with 3+ backticks or tildes and closes only on the same
# character, at least as long, with no info string.
CODE_FENCE_PATTERN = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*(\S*)")

# EARS keywords are uppercase, so these match case-SENSITIVELY: the English
# words "as" and "unless" inside a canonical requirement are not keywords.
SHALL_PATTERN = re.compile(r"\bSHALL\b")
LOWERCASE_SHALL_PATTERN = re.compile(r"\bshall\b")
LOWERCASE_EARS_KEYWORD_PATTERN = re.compile(r"^(when|while|where|if)\b")
DEPRECATED_EARS_PATTERNS = [
    (
        re.compile(r"\bALWAYS\s+SHALL\b"),
        "ALWAYS SHALL -> ubiquitous (drop ALWAYS): 'The <system> SHALL ...'",
    ),
    (
        re.compile(r"\bUNLESS\b"),
        "UNLESS -> 'IF NOT ..., THEN ... SHALL ...' (or WHERE)",
    ),
]
# A predicate, not a regex: `WHERE <feature>, IF <cond>, THEN ...` is the
# canonical composite, and a `WHERE ... THEN` regex flagged it.
DEPRECATED_LEADING_THEN_HINTS = [
    ("WHERE", "WHERE ... THEN (state-driven) -> 'WHILE ..., the <system> SHALL ...'"),
    ("AS", "AS ... THEN -> 'IF ..., THEN ... SHALL ...'"),
]
# A quoted span is copy the system emits, not requirement vocabulary. Blanked
# to a space so word boundaries survive.
QUOTED_SPAN_PATTERN = re.compile("`[^`]*`|\"[^\"]*\"|'[^']*'|“[^”]*”")
EARS_LEADING_KEYWORDS = frozenset(("WHEN", "WHILE", "WHERE", "IF", "THEN"))
NON_EARS_KEYWORD_HINTS = {
    "AFTER": "WHEN",
    "BEFORE": "WHILE ... has not yet",
    "ONCE": "WHEN",
    "UNTIL": "WHILE",
    "GIVEN": "WHERE or WHILE",
    "DURING": "WHILE",
    "WHENEVER": "WHEN",
    "UPON": "WHEN",
    "ASSUMING": "WHERE",
    "PROVIDED": "WHERE",
}
FIRST_WORD_PATTERN = re.compile(r"^\s*([A-Z][A-Z0-9-]{1,})\b")
# The main clause needs a subject between the trigger and SHALL.
EARS_MAIN_CLAUSE_PATTERN = re.compile(r"(?:^|,)\s*(?:THEN\s+)?(\S.*?)\bSHALL\b")
# Unverifiable words: a requirement using one cannot be tested.
VAGUE_TERMS = frozenset(
    "fast slow quick quickly responsive user-friendly easy intuitive simple robust"
    " scalable efficient reliable performant seamless appropriate reasonable"
    " adequate sufficient optimal flexible lightweight".split()
)
VAGUE_TERM_PATTERN = re.compile(r"\b(%s)\b" % "|".join(sorted(VAGUE_TERMS)), re.I)

# Retired only when the requirement text (already stripped of ID, citation and
# separator) BEGINS with REMOVED; one that merely mentions a removed thing stays
# active.
REMOVED_MARKER_PATTERN = re.compile(r"^[`*_\s]*REMOVED\b")

# Legacy artifacts are recognised by exact, case-sensitive file name, never by
# directory name. `architecture.md` is a default of MkDocs, Docusaurus and
# Diataxis, so it counts only when its own text cross-references the scheme.
UNAMBIGUOUS_LEGACY_STEERING_NAMES = {"product.md", "tech.md", "test-strategy.md"}
CORROBORATED_LEGACY_STEERING_NAMES = {"architecture.md"}
LEGACY_SCHEME_REFERENCE_PATTERN = re.compile(
    r"\.sdlc/|\bADR-\d|\bRULE-\d|\bUS-\d|\bAC-\d|\bNFR-\d|\bFeature Key\b"
)
LEGACY_REQUIREMENT_NAMES = {"problem-brief.md", "entity-dictionary.md"}
LEGACY_SPEC_NAMES = {"spec.md", "requirements.md", "design.md"}


def main(argv=None):
    """Parse arguments, validate the project, emit the report, return an exit code."""
    parser = argparse.ArgumentParser(
        description="Validate SDLC traceability, EARS, and ID hygiene."
    )
    parser.add_argument("--root", default=".", help="project root (default: .)")
    parser.add_argument("--feature", default=None, help="restrict to one feature slug")
    parser.add_argument(
        "--strict", action="store_true", help="warnings exit non-zero too"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="skip files matching this glob when scanning for tags (repeatable)",
    )
    parser.add_argument(
        "--relax-tag-roles",
        action="store_true",
        help="migration ramp: count IMPLEMENTS:/COVERS: from any file and report "
        "a misplaced tag as a WARNING (same as gate.enforce_tag_roles: false)",
    )
    arguments = parser.parse_args(argv)

    root = os.path.abspath(arguments.root)
    report = validate_project(
        root,
        only_feature=arguments.feature,
        excluded_patterns=arguments.exclude,
        relax_tag_roles=arguments.relax_tag_roles,
    )

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


def validate_project(
    root,
    only_feature=None,
    report=None,
    excluded_patterns=(),
    config=None,
    relax_tag_roles=False,
):
    """Run every check over the project at `root` and return the filled Report.

    `only_feature` narrows what is REPORTED, not what is parsed, so the keys
    and ids of the other features stay resolvable.
    """
    report = report or Report()
    config = load_config(root, report) if config is None else config
    if relax_tag_roles:
        config["gate"]["enforce_tag_roles"] = False
    is_enforcing_roles = config["gate"]["enforce_tag_roles"]
    if not is_enforcing_roles:
        # A WARNING so the ramp stays visible and fails --strict, rather than
        # quietly becoming the permanent setting.
        report.warn(
            "gate-relaxed",
            "Tag-role enforcement is OFF: IMPLEMENTS:/COVERS: count "
            "from any file, so one file can satisfy both. This is the "
            "pre-migration behaviour, meant for the first pass over an "
            "existing project. Turn it back on by dropping "
            "--relax-tag-roles, or by setting gate.enforce_tag_roles "
            "to true in %s." % CONFIG_RELATIVE_PATH,
        )

    check_legacy_layout(root, report)

    spec_paths_by_slug = get_spec_paths_by_slug(root)
    if not spec_paths_by_slug:
        report.info(
            "no-specs", "No SDLC specs found (looked in .sdlc/specs/ and specs/)."
        )
        return report
    if only_feature and only_feature not in spec_paths_by_slug:
        # An ERROR: /sdlc-review maps a clean run to APPROVE, so a mistyped slug
        # must not pass.
        report.error(
            "unknown-feature",
            "No spec found for feature '%s' (looked in .sdlc/specs/ "
            "and specs/). Known features: %s."
            % (only_feature, ", ".join(sorted(spec_paths_by_slug)) or "none"),
        )
        return report
    reported_slugs = {only_feature} if only_feature else set(spec_paths_by_slug)

    specs_by_slug, slug_by_key = check_spec_hygiene(
        root, spec_paths_by_slug, report, reported_slugs, config
    )
    tags = collect_traceability_tags(root, config, report, excluded_patterns)
    valid_targets = get_valid_tag_targets(specs_by_slug)
    reported_keys = {
        specs_by_slug[slug]["feature_key"]
        for slug in reported_slugs
        if slug in specs_by_slug
    }
    if only_feature:
        # Unkeyed tags survive the filter: they belong to no feature by
        # definition, and dropping them would report the requirement they meant
        # to cover as untraced without the warning that explains why.
        tags = [
            tag
            for tag in tags
            if tag.feature_key is None or tag.feature_key in reported_keys
        ]
    check_tag_targets(tags, valid_targets, slug_by_key, report)
    check_tag_roles(tags, report, is_enforcing_roles)

    reported_specs = {
        slug: spec for slug, spec in specs_by_slug.items() if slug in reported_slugs
    }
    check_requirement_coverage(
        root, reported_specs, spec_paths_by_slug, tags, report, is_enforcing_roles
    )
    check_ac_citations(
        root, reported_specs, spec_paths_by_slug, report, not only_feature
    )
    return report


def load_config(root, report):
    """Return the project configuration, merged over the built-in defaults.

    Absent config is normal: the defaults cover conventional layouts. Malformed
    config is an ERROR naming the key, since silently ignoring a layout
    declaration would report a project's real tags as missing.
    """
    config = get_default_config()
    config_path = os.path.join(root, CONFIG_RELATIVE_PATH)
    if not os.path.exists(config_path):
        return config

    raw_text = read_file_text(config_path)
    if raw_text is None:
        report_config(report, "Could not read the file.")
        return config
    try:
        declared = json.loads(raw_text)
    except ValueError as error:
        report_config(report, "The file is not valid JSON: %s" % error)
        return config
    if not isinstance(declared, dict):
        report_config(report, "Must hold a JSON object.")
        return config

    for section_name, section in sorted(declared.items()):
        if section_name not in config:
            report_config(
                report,
                "Unknown section '%s' -- known sections are %s."
                % (section_name, ", ".join(sorted(config))),
                report.warn,
            )
        elif not isinstance(section, dict):
            report_config(report, "Section '%s' must be an object." % section_name)
        else:
            merge_config_section(config, section_name, section, report)
    return config


def report_config(report, message, announce=None):
    """Report a config problem, located at .sdlc/config.json (ERROR by default)."""
    (announce or report.error)("config", message, CONFIG_RELATIVE_PATH)


def get_default_config():
    """Return a fresh copy of the built-in defaults, safe for the caller to edit."""
    return {
        "layout": {
            "test_directory_names": list(DEFAULT_TEST_DIRECTORY_NAMES),
            "test_stem_patterns": list(DEFAULT_TEST_STEM_PATTERNS),
            "test_path_fragments": list(DEFAULT_TEST_PATH_FRAGMENTS),
            "source_overrides": [],
            "test_overrides": [],
            "generated_globs": [],
            "vendored_globs": [],
        },
        "headings": {
            "test_plan": [],
            "outside_code": [],
            "outside_code_functional": [],
        },
        "comments": {},
        "gate": {"enforce_tag_roles": True},
        "scan": {
            "skip_directories": sorted(SKIPPED_DIRECTORIES),
            "scan_directories": [],
            "max_file_bytes": MAX_SCANNED_BYTES,
        },
    }


def merge_config_section(config, section_name, section, report):
    """Merge one declared section into `config`, reporting anything unusable.

    Lists EXTEND the defaults, so a config stays short and keeps working when
    the defaults grow.
    """
    for key, value in sorted(section.items()):
        name = "%s.%s" % (section_name, key)
        if section_name == "comments":
            merge_comment_declaration(config, key, value, report)
        elif key in CONFIG_LIST_FIELDS.get(section_name, ()):
            if not is_list_of_strings(value):
                report_config(report, "%s must be a list of strings." % name)
                continue
            current = config[section_name][key]
            current.extend(item for item in value if item not in current)
        elif name == "gate.enforce_tag_roles":
            if isinstance(value, bool):
                config["gate"]["enforce_tag_roles"] = value
            else:
                report_config(report, "%s must be true or false." % name)
        elif name == "scan.max_file_bytes":
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                config["scan"]["max_file_bytes"] = value
            else:
                report_config(report, "%s must be a positive integer." % name)
        else:
            report_config(report, "Unknown key '%s'." % name, report.warn)


def merge_comment_declaration(config, extension, declaration, report):
    """Record a project-declared comment syntax for one file extension."""
    if not extension.startswith("."):
        report_config(
            report,
            "Comment key '%s' must be a file extension starting with a dot."
            % extension,
        )
        return
    if not isinstance(declaration, dict):
        report_config(
            report,
            "comments['%s'] must be an object with 'line' and/or 'block'." % extension,
        )
        return
    line_leaders = declaration.get("line", [])
    block_pairs = declaration.get("block", [])
    if not is_list_of_strings(line_leaders):
        report_config(
            report, "comments['%s'].line must be a list of strings." % extension
        )
        return
    if not is_list_of_pairs(block_pairs):
        report_config(
            report,
            "comments['%s'].block must be a list of [open, close] string pairs."
            % extension,
        )
        return
    config["comments"][extension] = {
        "line": list(line_leaders),
        "block": [tuple(pair) for pair in block_pairs],
    }


def is_list_of_strings(value):
    """Return True when `value` is a list holding only strings."""
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def is_list_of_pairs(value):
    """Return True when `value` is a list of two-string lists or tuples."""
    return isinstance(value, list) and all(
        isinstance(pair, (list, tuple))
        and len(pair) == 2
        and all(isinstance(item, str) for item in pair)
        for pair in value
    )


def check_legacy_layout(root, report):
    """legacy-layout — report SDLC artifacts still sitting at pre-`.sdlc/` paths."""
    for label, legacy_path, canonical_path in get_legacy_artifacts(root):
        if os.path.exists(os.path.join(root, canonical_path)):
            continue
        report.info(
            "legacy-layout",
            "Legacy %s at %s — run /sdlc-adopt to consolidate under .sdlc/."
            % (label, legacy_path),
            legacy_path,
        )


def get_legacy_artifacts(root):
    """Yield (label, legacy_path, canonical_path) per legacy artifact found.

    Matched on the exact file names /sdlc-init writes.
    """
    if has_legacy_steering_documents(root):
        yield "steering docs", "docs", os.path.join(".sdlc", "docs")

    adr_directory = os.path.join("docs", "adr")
    if any(
        name.startswith("ADR-") and name.endswith(".md")
        for name in get_entry_names(root, adr_directory)
    ):
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

    A weak name (`architecture.md`) counts only when its text cross-references
    the scheme.
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
        if prefix and any(
            name.startswith(prefix) and name.endswith(".md") for name in entry_names
        ):
            return True
    return False


def get_entry_names(root, relative_path):
    """Return the exact entry names in a directory, or [] when it is absent."""
    try:
        return os.listdir(os.path.join(root, relative_path))
    except OSError:
        return []


def check_spec_hygiene(
    root, spec_paths_by_slug, report, reported_slugs=None, config=None
):
    """Parse every spec and validate keys, IDs, and EARS.

    A spec outside `reported_slugs` (the --feature scope) is parsed so its key
    and ids resolve, but contributes no findings.

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
        if spec["unclosed_fence_line"]:
            spec_report.warn(
                "unclosed-fence",
                "Unclosed code fence opened at line %d — everything below it is "
                "ignored, so any requirement, NFR or test-plan row after that "
                "line is invisible to the validator. Close the fence."
                % spec["unclosed_fence_line"],
                location,
            )
        feature_key = resolve_feature_key(spec, slug, location, spec_report)

        if feature_key in slug_by_key and slug_by_key[feature_key] != slug:
            spec_report.error(
                "key-unique",
                "Feature Key '%s' is also used by feature '%s'."
                % (feature_key, slug_by_key[feature_key]),
                location,
            )
        else:
            slug_by_key[feature_key] = slug

        for requirement_id in sorted(set(spec["duplicate_ids"])):
            spec_report.error(
                "dup-id",
                "ID %s defined more than once (active) in %s." % (requirement_id, slug),
                location,
            )

        recycled_ids = spec["removed_ids"] & set(spec["active_ids"])
        for requirement_id in sorted(recycled_ids):
            spec_report.error(
                "recycled-id",
                "ID %s is marked REMOVED but also appears active." % requirement_id,
                location,
            )

        for requirement_id in sorted(spec["relisted_nfrs"]):
            spec_report.info(
                "nfr-relisted",
                "%s is listed twice but under no recognised 'NFRs Validated "
                "Outside Code' heading, so it is NOT exempt from "
                "IMPLEMENTS:/COVERS:." % requirement_id,
                location,
            )

        check_ears_syntax(spec["requirement_texts"], location, spec_report)

        # Here, not in the coverage pass: a legacy test plan's UT-/IT- ids are
        # COVERS targets, so they must be known before tags are resolved.
        resolve_test_plan(root, slug, spec, location, spec_report)

        specs_by_slug[slug] = spec
    return specs_by_slug, slug_by_key


def resolve_feature_key(spec, slug, location, report):
    """Return the spec's Feature Key, defaulting from the slug, and report it.

    The slug default is only usable when it is a valid key: `2FA:REQ-001` does
    not parse as key-prefixed, so a digit-led slug could never be traced.
    """
    if spec["feature_key"]:
        return spec["feature_key"]

    declared_token = spec["declared_feature_key_token"]
    spec["feature_key"] = slug.upper()
    if declared_token:
        report.error(
            "feature-key",
            "Declared Feature Key '%s' is not a valid key — a key is "
            "[A-Z][A-Z0-9_-]* (uppercase, starting with a letter). "
            "Tags will not resolve until it is fixed." % declared_token,
            location,
        )
    elif FEATURE_KEY_TOKEN_PATTERN.match(spec["feature_key"]):
        report.info(
            "feature-key",
            "No '**Feature Key:**' declared; defaulting to '%s'. "
            "Declare one explicitly." % spec["feature_key"],
            location,
        )
    else:
        report.error(
            "feature-key",
            "No '**Feature Key:**' declared, and '%s' cannot be one — "
            "a key is [A-Z][A-Z0-9_-]* and may not start with a digit. "
            "Declare one explicitly, e.g. '**Feature Key:** F%s'."
            % (spec["feature_key"], spec["feature_key"]),
            location,
        )
    return spec["feature_key"]


def resolve_test_plan(root, slug, spec, spec_location, report):
    """Locate the feature's test plan and record it on the spec.

    Falls back to the legacy `.sdlc/tests/<slug>/test-plan.md` so its test IDs
    stay valid COVERS targets.
    """
    spec["test_plan_location"] = spec_location
    if spec["test_plan_text"]:
        return

    legacy_path = find_first_existing_path(
        os.path.join(root, ".sdlc", "tests", slug, "test-plan.md"),
        os.path.join(root, "tests", slug, "test-plan.md"),
    )
    if not legacy_path:
        report.warn(
            "missing-test-plan",
            "Feature '%s' has no '## Test Plan' section in spec.md." % slug,
            spec_location,
        )
        return

    location = os.path.relpath(legacy_path, root)
    report.info(
        "legacy-test-plan",
        "Feature '%s' keeps its test plan at %s — /sdlc-adopt folds it "
        "into spec.md." % (slug, location),
        location,
    )
    spec["test_plan_text"] = read_file_text(legacy_path) or ""
    spec["test_plan_location"] = location
    spec["test_ids"] = set(TEST_ID_PATTERN.findall(spec["test_plan_text"]))


def check_ears_syntax(requirement_texts, location, report):
    """ears — every requirement uses canonical EARS with an uppercase SHALL.

    Case-sensitive: `the system shall charge the card` is prose, not EARS.
    """
    for requirement_id, raw_text in sorted(requirement_texts.items()):
        text = get_unquoted_text(raw_text)
        deprecated_hint = get_deprecated_ears_hint(text)
        if deprecated_hint:
            report.warn(
                "ears",
                "%s uses deprecated EARS dialect (%s)."
                % (requirement_id, deprecated_hint),
                location,
            )
            continue
        lowercase_keyword = LOWERCASE_EARS_KEYWORD_PATTERN.match(text)
        if lowercase_keyword:
            report.warn(
                "ears",
                "%s opens with lowercase '%s' — EARS keywords are "
                "uppercase (%s)."
                % (
                    requirement_id,
                    lowercase_keyword.group(1),
                    lowercase_keyword.group(1).upper(),
                ),
                location,
            )
            continue
        if not SHALL_PATTERN.search(text):
            if LOWERCASE_SHALL_PATTERN.search(text):
                report.warn(
                    "ears",
                    "%s uses lowercase 'shall' — EARS keywords are uppercase."
                    % requirement_id,
                    location,
                )
            else:
                report.warn(
                    "ears",
                    "%s has no SHALL/EARS keyword — restate in canonical EARS."
                    % requirement_id,
                    location,
                )
            continue

        shall_count = len(SHALL_PATTERN.findall(text))
        if shall_count > 1:
            report.warn(
                "ears",
                "%s contains %d SHALL clauses — one requirement, one "
                "SHALL. Split it, keeping %s for the first."
                % (requirement_id, shall_count, requirement_id),
                location,
            )
            continue

        if get_ears_structure_problem(text):
            report.warn(
                "ears",
                "%s has no subject before SHALL — write 'the <system> "
                "SHALL <response>'." % requirement_id,
                location,
            )
            continue

        non_ears_keyword = get_non_ears_leading_keyword(text)
        if non_ears_keyword:
            hint = NON_EARS_KEYWORD_HINTS.get(non_ears_keyword)
            report.warn(
                "ears",
                "%s opens with '%s', which is not an EARS keyword%s."
                % (
                    requirement_id,
                    non_ears_keyword,
                    (
                        " — use %s" % hint
                        if hint
                        else " — use WHEN, WHILE, WHERE, IF, or a ubiquitous "
                        "'The <system> SHALL ...'"
                    ),
                ),
                location,
            )
            continue

        vague_match = VAGUE_TERM_PATTERN.search(text)
        if vague_match:
            report.warn(
                "ears",
                "%s uses the unverifiable term '%s' — state a measurable "
                "target, or move it to the NFR table."
                % (requirement_id, vague_match.group(1)),
                location,
            )


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
    return not re.search(
        r"\b(?:IF|WHEN|WHILE)\b", text[opening.end() : then_match.start()]
    )


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

    DOC files and generated/vendored globs are skipped; every other file is
    read for comments and classified as source or test.
    """
    skipped_directories = set(config["scan"]["skip_directories"])
    skipped_directories -= set(config["scan"]["scan_directories"])
    maximum_bytes = config["scan"]["max_file_bytes"]
    unowned_patterns = (
        list(excluded_patterns)
        + config["layout"]["generated_globs"]
        + config["layout"]["vendored_globs"]
    )
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
            posix_path = relative_path.replace(os.sep, "/")
            if is_matching_any_glob(posix_path, unowned_patterns):
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
                    tags.append(
                        TraceabilityTag(
                            feature_key, requirement_id, kind, relative_path, role
                        )
                    )
    return tags


def get_file_role(relative_path, config):
    """Classify a scanned file as source, test, or never-scanned.

    ROLE_DOC covers documentation, prose and data; those are never read, so a
    misplaced tag is always "the wrong kind of file", never "unclassifiable".
    """
    posix_path = relative_path.replace(os.sep, "/")
    if os.path.splitext(posix_path)[1].lower() in UNSCANNED_EXTENSIONS:
        return ROLE_DOC
    layout = config["layout"]
    if is_matching_any_glob(posix_path, layout["source_overrides"]):
        return ROLE_SOURCE
    if is_matching_any_glob(posix_path, layout["test_overrides"]):
        return ROLE_TEST
    return ROLE_TEST if is_test_path(posix_path, layout) else ROLE_SOURCE


def is_test_path(posix_path, layout):
    """True when a path names a test by directory, path fragment, or filename stem."""
    directory_names = set(posix_path.split("/")[:-1])
    if directory_names & set(layout["test_directory_names"]):
        return True
    if any(fragment in posix_path for fragment in layout["test_path_fragments"]):
        return True
    stem = posix_path.rsplit("/", 1)[-1]
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]
    return any(
        fnmatch.fnmatch(stem, pattern) for pattern in layout["test_stem_patterns"]
    )


def is_matching_any_glob(posix_path, patterns):
    """True when the path matches any of the globs, by full path or by name."""
    base_name = posix_path.rsplit("/", 1)[-1]
    return any(
        fnmatch.fnmatch(posix_path, pattern) or fnmatch.fnmatch(base_name, pattern)
        for pattern in patterns
    )


def scan_code_fences(text):
    """Return (text with fences blanked, line number of an unclosed fence).

    An unclosed fence blanks everything after it (a missed example costs less
    than an invented tag); its line number is returned so the caller can warn.
    """
    lines = text.splitlines()
    open_marker = None
    open_line_number = None
    for index, line in enumerate(lines):
        fence_match = CODE_FENCE_PATTERN.match(line)
        if open_marker is None:
            if fence_match:
                open_marker = fence_match.group(1)
                open_line_number = index + 1
                lines[index] = ""
            continue
        if (
            fence_match
            and fence_match.group(1)[0] == open_marker[0]
            and len(fence_match.group(1)) >= len(open_marker)
            and not fence_match.group(2)
        ):
            open_marker = None
            open_line_number = None
        lines[index] = ""
    return "\n".join(lines), open_line_number


def get_heading_title(heading):
    """Return a heading's text without its `#` marks, for comparison."""
    return heading.lstrip("#").strip().lower()


def get_declared_heading_match(text, extra_headings):
    """Return a match for the first project-declared heading found, or None."""
    for declared in extra_headings:
        title = re.escape(get_heading_title(declared))
        match = re.search(r"^#{2,4}\s+%s\s*$" % title, text, re.M | re.I)
        if match:
            return match
    return None


def parse_traceability_tags(file_text, extension, config):
    """Return {kind: [(feature_key_or_None, id), ...]} for one file's tags.

    Only comment text is read, and a tag must OPEN its comment.
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

    Not a lexer: one left-to-right pass that skips string literals. Block state
    carries across lines. A Python docstring is a string, so a header inside one
    does not count (ANNOTATION.md puts it after the docstring).
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
                line, line_leaders, block_pairs
            )
            if opener is None:
                break
            if opener == "line":
                comment_texts.append(line[offset + marker_length :])
                break
            close_marker = opener
            line = line[offset + marker_length :]
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

    An approximation, not a lexer: it rejects a comment marker inside an
    ordinary string without tokenising the language.
    """
    return any(start < offset < end for start, end in get_string_literal_spans(line))


def get_string_literal_spans(line):
    """Return (start, end) for every quoted span that opens AND closes on the line.

    One pass with a single active quote, so the apostrophe in `"it's here"`
    belongs to that string. A quote with no partner on the line opens nothing,
    so Rust's `&'a str` and Lisp's `'(a b)` keep their trailing comments.
    """
    spans = []
    index = 0
    while index < len(line):
        character = line[index]
        if character == "\\":
            index += 2
            continue
        if character in ('"', "'"):
            closing_index = get_closing_quote_index(line, index)
            if closing_index is not None:
                spans.append((index, closing_index))
                index = closing_index + 1
                continue
        index += 1
    return spans


def get_closing_quote_index(line, start):
    """Return the index of the quote closing the one at `start`, or None."""
    quote = line[start]
    index = start + 1
    while index < len(line):
        if line[index] == "\\":
            index += 2
            continue
        if line[index] == quote:
            return index
        index += 1
    return None


def get_comment_syntax(extension, config):
    """Return (line_leaders, block_pairs) for a file extension.

    An unknown extension falls back to a generous leader set.
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
    """dangling-tag, unkeyed-tag — every tag is key-namespaced and resolves to a real ID."""
    for feature_key, requirement_id, kind, relative_path, _ in tags:
        if feature_key is None:
            report.warn(
                "unkeyed-tag",
                "Unkeyed tag '%s' in %s — re-key as KEY:%s."
                % (requirement_id, kind, requirement_id),
                relative_path,
            )
            continue
        if (feature_key, requirement_id) in valid_targets:
            continue
        if feature_key not in slug_by_key:
            report.error(
                "dangling-tag",
                "Tag %s:%s (%s) references unknown Feature Key '%s'."
                % (feature_key, requirement_id, kind, feature_key),
                relative_path,
            )
        else:
            report.error(
                "dangling-tag",
                "Tag %s:%s (%s) references an ID not defined in feature '%s'."
                % (feature_key, requirement_id, kind, slug_by_key[feature_key]),
                relative_path,
            )


def check_tag_roles(tags, report, is_enforced=True):
    """tag-role — IMPLEMENTS lives in source, COVERS lives in tests.

    Reported at the tag, nearest the edit that caused it. With the gate relaxed
    the finding is a WARNING and the tag still counts.
    """
    remedy_by_kind = {
        "IMPLEMENTS": "Move it to the source file that implements the "
        "requirement, or list this path under layout.source_overrides",
        "COVERS": "Move it to the test that covers the requirement, or list "
        "this path under layout.test_overrides",
    }
    for tag in tags:
        if not is_misplaced_tag(tag):
            continue
        announce = report.error if is_enforced else report.warn
        announce(
            "tag-role",
            "%s: %s:%s sits in %s, which is a %s file, so it does not "
            "satisfy %s coverage. %s in %s."
            % (
                tag.kind,
                tag.feature_key or "",
                tag.requirement_id,
                tag.relative_path,
                tag.role,
                "code" if tag.kind == "IMPLEMENTS" else "test",
                remedy_by_kind[tag.kind],
                CONFIG_RELATIVE_PATH,
            ),
            tag.relative_path,
        )


def check_requirement_coverage(
    root, specs_by_slug, spec_paths_by_slug, tags, report, is_enforcing_roles=True
):
    """trace-*, plan-* — every requirement is implemented, tested, and planned.

    A misplaced tag counts only when the role gate is relaxed; either way its
    path is recorded so the coverage error can name where it actually sits.
    """
    counted_targets = {"IMPLEMENTS": set(), "COVERS": set()}
    misplaced_paths_by_target = {}
    for tag in tags:
        if tag.kind not in counted_targets or not tag.feature_key:
            continue
        target = (tag.feature_key, tag.requirement_id)
        if is_misplaced_tag(tag):
            misplaced_paths_by_target.setdefault(target + (tag.kind,), []).append(
                tag.relative_path
            )
            if is_enforcing_roles:
                continue
        counted_targets[tag.kind].add(target)

    for slug, spec in specs_by_slug.items():
        feature_key = spec["feature_key"]
        location = os.path.relpath(spec_paths_by_slug[slug], root)
        test_plan_text = spec["test_plan_text"]
        test_plan_location = spec["test_plan_location"]

        for requirement_id in sorted(spec["active_ids"]):
            if requirement_id in spec["misplaced_exemptions"]:
                report.warn(
                    "exemption-heading",
                    "%s:%s sits under the outside-code heading, which exempts "
                    "NFR-* only. A functional requirement needs its own "
                    "heading — '## Requirements With No In-Code Verification' — "
                    "or a real test that COVERS it." % (feature_key, requirement_id),
                    location,
                )
            if requirement_id in spec["outside_code_nfrs"]:
                exemption = "validated outside code"
            elif requirement_id in spec["outside_code_requirements"]:
                exemption = "declared to have no in-code verification"
            else:
                exemption = None
            if exemption:
                report.info(
                    "outside-code",
                    "%s:%s %s — exempt from IMPLEMENTS/COVERS."
                    % (feature_key, requirement_id, exemption),
                    location,
                )
                continue
            for kind, check, file_kind in (
                ("IMPLEMENTS", "trace-code", "source"),
                ("COVERS", "trace-test", "test"),
            ):
                if (feature_key, requirement_id) in counted_targets[kind]:
                    continue
                report.error(
                    check,
                    "%s:%s has no %s: header in any %s file.%s"
                    % (
                        feature_key,
                        requirement_id,
                        kind,
                        file_kind,
                        get_misplaced_hint(
                            misplaced_paths_by_target.get(
                                (feature_key, requirement_id, kind)
                            ),
                            kind,
                            file_kind,
                        ),
                    ),
                    location,
                )
            is_planned = re.search(
                r"\b%s\b" % re.escape(requirement_id), test_plan_text
            )
            if requirement_id.startswith("REQ-") and test_plan_text and not is_planned:
                report.warn(
                    "plan-coverage",
                    "%s not referenced by any row in the test plan." % requirement_id,
                    test_plan_location,
                )

        for referenced_id in sorted(
            set(REQUIREMENT_ID_PATTERN.findall(test_plan_text))
        ):
            if referenced_id in spec["removed_ids"]:
                report.error(
                    "plan-stale-row",
                    "The test plan references %s, which is REMOVED. "
                    "Delete the row — the requirement it planned is "
                    "retired." % referenced_id,
                    test_plan_location,
                )
            elif referenced_id not in spec["active_ids"]:
                report.error(
                    "plan-unknown-row",
                    "The test plan references %s, which feature '%s' "
                    "does not define." % (referenced_id, slug),
                    test_plan_location,
                )

        for test_id in sorted(spec["test_ids"]):
            if (feature_key, test_id) not in counted_targets["COVERS"]:
                report.warn(
                    "plan-test-uncovered",
                    "%s is planned in the test plan but no test file "
                    "COVERS it." % test_id,
                    test_plan_location,
                )


def get_misplaced_hint(paths, kind, file_kind):
    """Return a clause naming where a misplaced tag for a target actually sits."""
    if not paths:
        return ""
    return " (a %s: tag for it exists in %s, which is not a %s file)" % (
        kind,
        ", ".join(sorted(set(paths))),
        file_kind,
    )


def is_misplaced_tag(tag):
    """True when an IMPLEMENTS/COVERS tag sits in the wrong kind of file."""
    expected_role = EXPECTED_ROLE_BY_KIND.get(tag.kind)
    return expected_role is not None and tag.role != expected_role


def check_ac_citations(
    root, specs_by_slug, spec_paths_by_slug, report, is_whole_project=True
):
    """ac-citation, ac-uncited — requirements and the brief's ACs agree.

    Every `AC-*` a requirement cites must exist in the brief (catches an AC
    renumbered upstream). On a whole-project run, every AC no active
    requirement cites is reported as INFO: usually unspecified backlog, so it
    must not fail --strict. Skipped when there is no brief.
    """
    brief_path = find_first_existing_path(
        os.path.join(root, ".sdlc", "requirements", "problem-brief.md"),
        os.path.join(root, "requirements", "problem-brief.md"),
    )
    if not brief_path:
        return
    brief_location = os.path.relpath(brief_path, root)
    brief_text, unclosed_fence_line = scan_code_fences(read_file_text(brief_path) or "")
    if unclosed_fence_line:
        report.warn(
            "unclosed-fence",
            "Unclosed code fence opened at line %d — every AC defined "
            "below it is invisible, so a requirement citing one reports "
            "as citing an AC the brief does not define." % unclosed_fence_line,
            brief_location,
        )
    defined_ac_ids = set(AC_DEFINITION_PATTERN.findall(brief_text))
    if not defined_ac_ids:
        return

    for slug, spec in sorted(specs_by_slug.items()):
        location = os.path.relpath(spec_paths_by_slug[slug], root)
        for requirement_id, cited_ac_ids in sorted(spec["ac_citations"].items()):
            for ac_id in sorted(cited_ac_ids - defined_ac_ids):
                report.error(
                    "ac-citation",
                    "%s cites %s, which %s does not define."
                    % (requirement_id, ac_id, brief_location),
                    location,
                )

    if not is_whole_project:
        return
    cited_ac_ids = set()
    for spec in specs_by_slug.values():
        for ac_ids in spec["ac_citations"].values():
            cited_ac_ids |= ac_ids
    for ac_id in sorted(defined_ac_ids - cited_ac_ids):
        report.info(
            "ac-uncited",
            "%s is cited by no active requirement — not yet specified, or "
            "dropped from every spec." % ac_id,
            brief_location,
        )


def is_matching_heading(heading, pattern, extra_headings):
    """True when a heading matches the built-in pattern or a project-declared one."""
    title = get_heading_title(heading)
    return bool(pattern.search(heading)) or any(
        title == get_heading_title(declared) for declared in extra_headings
    )


def parse_spec(text, config=None):
    """Parse a spec.md into its feature key, requirement IDs, texts, and test plan.

    Fenced blocks are blanked first (preserving line count), so an example of
    the REMOVED form inside a fence is not read as a definition.
    """
    text, unclosed_fence_line = scan_code_fences(text)
    headings = (config or get_default_config())["headings"]
    feature_key_match = FEATURE_KEY_PATTERN.search(text)
    declared_key_match = FEATURE_KEY_LINE_PATTERN.search(text)
    active_ids = {}  # id -> line number of its first active definition
    duplicate_ids = []
    removed_ids = set()
    relisted_nfrs = set()  # NFR listed twice, but under no recognised heading
    requirement_texts = {}  # REQ id -> requirement text (active only)
    ac_citations = {}  # REQ id -> {AC ids it cites}
    outside_code_nfrs = set()
    outside_code_requirements = set()  # REQ-* exempt via the functional heading
    misplaced_exemptions = set()  # REQ-* under the NFR-only heading

    is_outside_code_section = False
    is_functional_exemption_section = False
    current_heading = ""
    headings_by_id = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped_line = line.strip()
        if stripped_line.startswith("#"):
            current_heading = stripped_line
            is_outside_code_section = is_matching_heading(
                stripped_line, OUTSIDE_CODE_HEADING_PATTERN, headings["outside_code"]
            )
            is_functional_exemption_section = is_matching_heading(
                stripped_line,
                FUNCTIONAL_OUTSIDE_CODE_HEADING_PATTERN,
                headings["outside_code_functional"],
            )

        definition_match = REQUIREMENT_LINE_PATTERN.match(line)
        if not definition_match:
            continue
        requirement_id, remainder = definition_match.group(1), definition_match.group(2)

        if REMOVED_MARKER_PATTERN.match(get_requirement_text(remainder)):
            removed_ids.add(requirement_id)
            continue

        if is_outside_code_section and requirement_id.startswith("NFR-"):
            outside_code_nfrs.add(requirement_id)
        # A REQ-* under the NFR-only heading is not exempt; warn about it.
        if is_outside_code_section and requirement_id.startswith("REQ-"):
            misplaced_exemptions.add(requirement_id)
        if is_functional_exemption_section:
            outside_code_requirements.add(requirement_id)
            misplaced_exemptions.discard(requirement_id)

        if requirement_id in active_ids:
            # Repeated under the SAME heading is a copy-paste mistake. Under two
            # headings is the documented NFR-table-plus-exemption pattern.
            if headings_by_id.get(requirement_id) == current_heading:
                duplicate_ids.append(requirement_id)
            elif (
                requirement_id.startswith("NFR-")
                and requirement_id not in outside_code_nfrs
            ):
                relisted_nfrs.add(requirement_id)
            # A repeat (e.g. under an exemption heading) never redefines the
            # requirement's text or citation.
            continue
        active_ids[requirement_id] = line_number
        headings_by_id[requirement_id] = current_heading
        if requirement_id.startswith("REQ-"):
            requirement_texts[requirement_id] = get_requirement_text(remainder)
            ac_citations[requirement_id] = set(
                AC_CITATION_PATTERN.findall(get_requirement_citation(remainder))
            )

    test_plan_text = get_test_plan_section(text, headings["test_plan"])
    return {
        "feature_key": feature_key_match.group(1) if feature_key_match else None,
        "declared_feature_key_token": (
            declared_key_match.group(1) if declared_key_match else None
        ),
        "ac_citations": ac_citations,
        "active_ids": active_ids,
        "duplicate_ids": duplicate_ids,
        "removed_ids": removed_ids,
        "requirement_texts": requirement_texts,
        "outside_code_nfrs": outside_code_nfrs,
        "outside_code_requirements": outside_code_requirements,
        "misplaced_exemptions": misplaced_exemptions,
        "relisted_nfrs": relisted_nfrs - outside_code_nfrs,
        "test_plan_text": test_plan_text,
        "test_ids": set(TEST_ID_PATTERN.findall(test_plan_text)),
        "unclosed_fence_line": unclosed_fence_line,
    }


def get_requirement_text(remainder):
    """Return the requirement prose that follows the ID and its optional citation.

    Positional, not split on a colon: `SHALL set Retry-After: 30` keeps its 30.
    """
    return CITATION_PATTERN.sub("", remainder, count=1).lstrip(" \t:\u2014-").strip()


def get_requirement_citation(remainder):
    """Return the `(AC-NNN)` citation that precedes the requirement prose, or ''.

    Read positionally, so a citation with no colon after it is still checked.
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
    return (
        text[section_start : next_match.start()] if next_match else text[section_start:]
    )


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

    A scanner passes `report` so a skip is announced rather than looking like a
    file with no tags.
    """
    maximum_bytes = MAX_SCANNED_BYTES if maximum_bytes is None else maximum_bytes
    try:
        file_size = os.path.getsize(path)
        if file_size > maximum_bytes:
            if report is not None:
                report.warn(
                    "skipped-file",
                    "%s was not scanned for tags (%.1f MB exceeds the "
                    "%.1f MB scan limit). Raise scan.max_file_bytes in "
                    "%s, or exclude the path."
                    % (
                        relative_path,
                        file_size / 1048576.0,
                        maximum_bytes / 1048576.0,
                        CONFIG_RELATIVE_PATH,
                    ),
                    relative_path,
                )
            return None
        with open(path, "rb") as file_handle:
            raw_bytes = file_handle.read()
        if b"\x00" in raw_bytes:
            if report is not None:
                report.info(
                    "skipped-file",
                    "%s was not scanned for tags (binary content)." % relative_path,
                    relative_path,
                )
            return None
        return raw_bytes.decode("utf-8", errors="replace")
    except (OSError, ValueError):
        if report is not None:
            report.warn(
                "skipped-file", "%s could not be read." % relative_path, relative_path
            )
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
        return (
            severities.count(ERROR),
            severities.count(WARNING),
            severities.count(INFO),
        )


def emit_text_report(report):
    """Print findings most-severe first, then the summary line."""
    severity_order = {ERROR: 0, WARNING: 1, INFO: 2}
    sorted_findings = sorted(
        report.findings, key=lambda finding: severity_order[finding[0]]
    )
    for severity, check, message, location in sorted_findings:
        suffix = " (%s)" % location if location else ""
        print("%s: %s — %s%s" % (severity, check, message, suffix))
    error_count, warning_count, info_count = report.count_by_severity()
    print(
        "\n%d errors, %d warnings, %d info" % (error_count, warning_count, info_count)
    )


def emit_json_report(report):
    """Print the same findings as JSON, for CI and other tools."""
    error_count, warning_count, info_count = report.count_by_severity()
    print(
        json.dumps(
            {
                "summary": {
                    "errors": error_count,
                    "warnings": warning_count,
                    "info": info_count,
                },
                "findings": [
                    {
                        "severity": severity,
                        "check": check,
                        "message": message,
                        "location": location,
                    }
                    for severity, check, message, location in report.findings
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
