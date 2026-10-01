#!/usr/bin/env python3
"""Quantum Mottle builder (Claude Chat edition).

    python scripts/build.py new   /home/claude/qm/2026-10   # create content.yaml skeleton
    python scripts/build.py check /home/claude/qm/2026-10   # house-style / completeness warnings
    python scripts/build.py build /home/claude/qm/2026-10   # -> build/newsletter.html + build/newsletter.eml

The issue folder must be named YYYY-MM (the month the issue is SENT). Put
images (e.g. dashboard.png) in that folder and reference them by file name.
"""

import argparse
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL))

from jinja2 import Template  # noqa: E402

from qm import config  # noqa: E402
from qm.config import Issue  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["new", "check", "build"])
    ap.add_argument("issue_dir", type=Path)
    a = ap.parse_args()

    issue_dir = a.issue_dir.resolve()
    config.ISSUES = issue_dir.parent  # Issue.dir resolves against this
    issue = Issue.parse(issue_dir.name)

    if a.cmd == "new":
        issue_dir.mkdir(parents=True, exist_ok=True)
        if issue.content_path.exists():
            sys.exit(f"{issue.content_path} already exists")
        tpl = Template((SKILL / "templates" / "content.yaml.j2").read_text(encoding="utf-8"))
        issue.content_path.write_text(tpl.render(issue=issue), encoding="utf-8")
        print("created", issue.content_path)
        return

    from qm.render import build, lint

    warnings = lint(issue)
    for w in warnings:
        print("warning:", w)
    if a.cmd == "check":
        print("No problems found." if not warnings else f"{len(warnings)} warning(s).")
        return
    # Images are embedded in both outputs: data: URIs in the HTML (so the preview
    # works on its own), inline attachments in the .eml (what actually gets sent).
    for p in build(issue, inline_images=True):
        print("wrote", p)


if __name__ == "__main__":
    main()
