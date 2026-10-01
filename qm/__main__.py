"""Quantum Mottle newsletter tool.

    python -m qm new 2026-10        create issues/2026-10/ from the skeleton
    python -m qm login              sign in once (Radiopaedia, optionally Google)
    python -m qm gather 2026-10     dashboard screenshot + raw sources
    python -m qm build 2026-10      render build/newsletter.html and .eml
    python -m qm check 2026-10      house-style / completeness warnings
    python -m qm gmail 2026-10      Gmail draft (images embedded); --test / --send
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


def cmd_gmail(issue: Issue, args):
    from . import gmail
    from .config import load_config

    bcc = gmail.read_bcc(args.bcc_file or load_config().get("newsletter", {}).get("bcc_file"))
    if args.test:
        print("Sent test to yourself:", gmail.send(issue, bcc=[], test=True))
    elif args.send:
        if not bcc:
            sys.exit("No BCC recipients - set newsletter.bcc_file in config.local.yaml or pass --bcc-file.")
        if input(f"Send {issue.slug} to {len(bcc)} BCC recipients now? Type 'send' to confirm: ").strip() != "send":
            sys.exit("Not sent.")
        print("Sent:", gmail.send(issue, bcc=bcc, test=False))
    else:
        print(f"Draft created ({len(bcc)} BCC):", gmail.create_draft(issue, bcc))
        print("Open Gmail > Drafts to check it. Sending from the draft is fine; `--send` sends exactly what was built.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="qm", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("new", cmd_new), ("login", cmd_login), ("gather", cmd_gather), ("build", cmd_build), ("check", cmd_check), ("gmail", cmd_gmail)):
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
    g = sub.choices["gmail"]
    g.add_argument("--test", action="store_true", help="send a [TEST] copy to yourself only")
    g.add_argument("--send", action="store_true", help="send to the BCC list (asks to confirm)")
    g.add_argument("--bcc-file", help="file of editor addresses, one per line")
    args = ap.parse_args(argv)
    args.fn(Issue.parse(getattr(args, "issue", None)), args)


if __name__ == "__main__":
    main()
