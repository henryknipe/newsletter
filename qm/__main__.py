"""Quantum Mottle newsletter tool.

    python -m qm new 2026-10        create issues/2026-10/ from the skeleton
    python -m qm login              sign in once (Radiopaedia, optionally Google)
    python -m qm gather 2026-10     dashboard screenshot + raw sources
    python -m qm build 2026-10      render build/newsletter.html and .eml
    python -m qm check 2026-10      house-style / completeness warnings
"""

import argparse
import sys

from jinja2 import Template

from .config import ROOT, Issue


def cmd_new(issue: Issue, args):
    if issue.content_path.exists() and not args.force:
        sys.exit(f"{issue.content_path} already exists (use --force to overwrite).")
    issue.dir.mkdir(parents=True, exist_ok=True)
    (issue.sources_dir).mkdir(exist_ok=True)
    tpl = Template((ROOT / "templates" / "content.yaml.j2").read_text(encoding="utf-8"))
    issue.content_path.write_text(tpl.render(issue=issue), encoding="utf-8")
    eic = issue.dir / "editor_in_chief.md"
    if not eic.exists():
        eic.write_text("TODO: one idea, 120-250 words.\n", encoding="utf-8")
    print(f"Created {issue.dir.relative_to(ROOT)}/ - next: `python -m qm gather {issue.slug}`")


def cmd_login(issue, args):
    from .sources import login

    login()


def cmd_gather(issue: Issue, args):
    from .sources import gather

    if not issue.content_path.exists():
        cmd_new(issue, argparse.Namespace(force=False))
    for line in gather(issue, args.only):
        print(line)
    print(f"\nRaw material is in {issue.sources_dir.relative_to(ROOT)}/. Draft content.yaml from it, then build.")


def cmd_build(issue: Issue, args):
    from .render import build, lint

    for w in lint(issue):
        print("warning:", w)
    for p in build(issue, inline_images=args.inline_images):
        print("wrote", p.relative_to(ROOT))


def cmd_check(issue: Issue, args):
    from .render import lint

    warnings = lint(issue)
    for w in warnings:
        print("warning:", w)
    print("No problems found." if not warnings else f"{len(warnings)} warning(s).")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="qm", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("new", cmd_new), ("login", cmd_login), ("gather", cmd_gather), ("build", cmd_build), ("check", cmd_check)):
        p = sub.add_parser(name)
        p.set_defaults(fn=fn)
        if name != "login":
            p.add_argument("issue", nargs="?", help="YYYY-MM of the send month (default: this month)")
    sub.choices["new"].add_argument("--force", action="store_true")
    sub.choices["gather"].add_argument(
        "--only", nargs="+", choices=["dashboard", "release-notes", "next-meeting", "social", "style-guide"]
    )
    sub.choices["build"].add_argument(
        "--inline-images", action="store_true", help="embed local images as data: URIs in the HTML (not Gmail-safe)"
    )
    args = ap.parse_args(argv)
    args.fn(Issue.parse(getattr(args, "issue", None)), args)


if __name__ == "__main__":
    main()
