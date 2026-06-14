#!/usr/bin/env python3
"""sync_skills.py — keep bundled scripts and shared templates in sync.

Some files must travel *inside* a skill directory (the installer copies skill
dirs verbatim — it does not run this repo's tooling), yet several skills need
the *same* file. Keeping hand-maintained copies in each skill drifts. So the
canonical source lives once under scripts/ and this script regenerates every
bundled copy from it.

Two mechanisms, both manifest-driven below:

  SCRIPT_COPIES      — copy a file from scripts/ verbatim into each listed
                       skill dir (e.g. the validator into sdlc-init + sdlc-migrate).

  TEMPLATE_INJECTS   — splice a markdown template from scripts/templates/ into a
                       marked region of each listed skill's SKILL.md, so the
                       template stays inline (the LLM reads SKILL.md and needs it
                       there) while having a single source of truth. The target
                       SKILL.md must contain a matching marker pair:
                           <!-- SYNC:BEGIN <name> -->
                           <!-- SYNC:END <name> -->

USAGE
    python3 scripts/sync_skills.py            # apply: rewrite bundled copies
    python3 scripts/sync_skills.py --check    # verify only; exit 1 if drifted

EXIT CODES
    0  in sync (after applying, or --check found no drift)
    1  --check found drift, or a target/marker was missing
"""

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
TEMPLATES = os.path.join(SCRIPTS, "templates")
SKILLS = os.path.join(ROOT, "skills")

# --- manifest -------------------------------------------------------------

# scripts/<src>  ->  skills/<skill>/<src>  (verbatim copy)
SCRIPT_COPIES = [
    ("sdlc-validate.py", ["sdlc-init", "sdlc-migrate"]),
]

# scripts/templates/<src>  ->  injected into skills/<skill>/SKILL.md
# between <!-- SYNC:BEGIN <name> --> and <!-- SYNC:END <name> -->.
# name defaults to <src>; fence is the code-fence language for the block.
TEMPLATE_INJECTS = [
    {"src": "conventions.md", "fence": "markdown",
     "skills": ["sdlc-init", "sdlc-migrate"]},
]


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _render_injection(name, fence, body):
    """The exact text that lives between (and including) the SYNC markers."""
    return (
        "<!-- SYNC:BEGIN %s -->\n"
        "<!-- Generated from scripts/templates/%s — edit there, then run "
        "`python3 scripts/sync_skills.py` (or `zrb skill sync`). -->\n"
        "~~~%s\n%s\n~~~\n"
        "<!-- SYNC:END %s -->"
    ) % (name, name, fence, body.rstrip("\n"), name)


def _inject(skill_md_text, name, rendered):
    """Replace the marked region; return (new_text, error_or_None)."""
    pattern = re.compile(
        r"<!-- SYNC:BEGIN %s -->.*?<!-- SYNC:END %s -->" % (re.escape(name), re.escape(name)),
        re.DOTALL,
    )
    if not pattern.search(skill_md_text):
        return skill_md_text, "no SYNC markers for %r" % name
    # Function replacement => the returned string is used verbatim (no backref
    # or backslash processing), so `rendered` is spliced in as-is.
    return pattern.sub(lambda _m: rendered, skill_md_text), None


def plan():
    """Return list of (path, desired_text) and list of problems."""
    desired = []
    problems = []

    for src, skills in SCRIPT_COPIES:
        src_path = os.path.join(SCRIPTS, src)
        if not os.path.exists(src_path):
            problems.append("missing source scripts/%s" % src)
            continue
        body = _read(src_path)
        for skill in skills:
            desired.append((os.path.join(SKILLS, skill, src), body))

    for entry in TEMPLATE_INJECTS:
        src = entry["src"]
        name = entry.get("name", src)
        fence = entry.get("fence", "markdown")
        tpl_path = os.path.join(TEMPLATES, src)
        if not os.path.exists(tpl_path):
            problems.append("missing template scripts/templates/%s" % src)
            continue
        rendered = _render_injection(name, fence, _read(tpl_path))
        for skill in entry["skills"]:
            md_path = os.path.join(SKILLS, skill, "SKILL.md")
            if not os.path.exists(md_path):
                problems.append("missing %s/SKILL.md" % skill)
                continue
            new_text, err = _inject(_read(md_path), name, rendered)
            if err:
                problems.append("%s: %s" % (os.path.relpath(md_path, ROOT), err))
                continue
            desired.append((md_path, new_text))

    return desired, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sync bundled scripts and templates into skills.")
    ap.add_argument("--check", action="store_true", help="verify only; exit 1 on drift")
    args = ap.parse_args(argv)

    desired, problems = plan()
    for p in problems:
        print("PROBLEM: %s" % p)

    drift = []
    for path, text in desired:
        current = _read(path) if os.path.exists(path) else None
        if current != text:
            drift.append((path, current is None))

    rel = lambda p: os.path.relpath(p, ROOT)

    if args.check:
        for path, missing in drift:
            print("DRIFT: %s%s" % (rel(path), " (missing)" if missing else ""))
        if drift or problems:
            print("\n%d file(s) out of sync, %d problem(s). Run: python3 scripts/sync_skills.py"
                  % (len(drift), len(problems)))
            return 1
        print("All %d bundled file(s) in sync." % len(desired))
        return 0

    for path, text in desired:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    for path, missing in drift:
        print("WROTE: %s%s" % (rel(path), " (new)" if missing else ""))
    if not drift:
        print("Already in sync — nothing to write.")
    print("\n%d bundled file(s), %d updated, %d problem(s)."
          % (len(desired), len(drift), len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
