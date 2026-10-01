"""Fetch the raw material for an issue using a logged-in browser profile.

Every fetcher writes into issues/YYYY-MM/sources/ (or the issue folder for the
dashboard image) and returns a one-line summary. They are independent, so one
failing (say, Google refusing the doc export) doesn't stop the rest.

Nothing here writes to Radiopaedia: every request is a GET, except the
Mattermost user-name lookup, which is a read-only POST.
"""

from __future__ import annotations

import calendar
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

from .config import Issue, load_config

SIGN_IN_URL = "https://radiopaedia.org/users/sign_in"


class LoginRequired(RuntimeError):
    pass


# ---------------------------------------------------------------- browser


def open_browser(headless: bool = True):
    from playwright.sync_api import sync_playwright

    cfg = load_config()
    profile = Path(cfg.get("browser_profile", "~/.quantum-mottle/browser-profile")).expanduser()
    profile.mkdir(parents=True, exist_ok=True)
    pw = sync_playwright().start()
    opts = dict(headless=headless, viewport={"width": 1200, "height": 900}, device_scale_factor=2)
    try:
        ctx = pw.chromium.launch_persistent_context(
            str(profile), executable_path=cfg.get("browser_executable") or None, **opts
        )
    except Exception as e:
        if "Executable doesn't exist" not in str(e):
            raise
        # Playwright's own Chromium isn't downloaded: fall back to the installed Google Chrome.
        print("Playwright's Chromium isn't installed - using your Google Chrome instead.")
        ctx = pw.chromium.launch_persistent_context(str(profile), channel="chrome", **opts)
    return pw, ctx


def login():
    """Open a visible browser so you can sign in to Radiopaedia (and Google). Cookies persist."""
    pw, ctx = open_browser(headless=False)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(SIGN_IN_URL)
        g = ctx.new_page()
        g.goto("https://accounts.google.com/")
        input(
            "\nSign in to Radiopaedia (first tab) and, optionally, Google (second tab)\n"
            "so Arlene's doc can be exported. Then press Enter here to save the session... "
        )
    finally:
        ctx.close()
        pw.stop()


def _check_login(page):
    if "sign_in" in page.url or "/login" in page.url or page.locator("input[type=password]").count():
        raise LoginRequired("Not signed in to Radiopaedia - run `python -m qm login` first.")


def _main_text(page) -> str:
    for sel in ("main", "#content", "article", "body"):
        loc = page.locator(sel)
        if loc.count():
            return loc.first.inner_text()
    return page.inner_text("body")


# ---------------------------------------------------------------- dates

_MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
DATE_RE = re.compile(
    rf"\b(\d{{4}}-\d{{2}}-\d{{2}}"
    rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})[a-z]*\.?,?\s+\d{{4}}"
    rf"|(?:{_MONTHS})[a-z]*\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}})\b",
    re.I,
)


def parse_date(s: str) -> date | None:
    s = re.sub(r"(\d)(st|nd|rd|th)", r"\1", s, flags=re.I).replace(",", "").replace(".", "")
    s = re.sub(r"\bSept\b", "Sep", s, flags=re.I)
    for f in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(s.strip(), f).date()
        except ValueError:
            pass
    return None


def split_dated_sections(text: str) -> list[tuple[date | None, str]]:
    """Split text into sections, each starting at a line containing a date."""
    sections: list[tuple[date | None, list[str]]] = [(None, [])]
    for line in text.splitlines():
        m = DATE_RE.search(line)
        d = parse_date(m.group(1)) if m and len(line) < 120 else None
        if d:
            sections.append((d, [line]))
        else:
            sections[-1][1].append(line)
    return [(d, "\n".join(lines).strip()) for d, lines in sections if "\n".join(lines).strip()]


# ---------------------------------------------------------------- fetchers


def fetch_dashboard(issue: Issue, ctx) -> str:
    cfg = load_config()["sources"]["dashboard"]
    page = ctx.new_page()
    page.set_viewport_size({"width": cfg.get("viewport_width", 1200), "height": 900})
    page.goto(cfg["url"], wait_until="networkidle", timeout=90_000)
    _check_login(page)
    page.wait_for_timeout(cfg.get("wait_ms", 3000))
    out = issue.dir / "dashboard.png"
    if cfg.get("selector"):
        page.locator(cfg["selector"]).first.screenshot(path=str(out))
    else:
        page.screenshot(path=str(out), full_page=True)
    (issue.sources_dir / "dashboard.txt").write_text(_main_text(page), encoding="utf-8")
    page.close()
    _shrink(out, 1200)
    return f"dashboard screenshot -> {out.relative_to(issue.dir.parent.parent)}"


def _shrink(path: Path, max_width: int):
    try:
        from PIL import Image
    except ImportError:
        return
    with Image.open(path) as im:
        if im.width > max_width:
            im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
            im.save(path, optimize=True)


def fetch_release_notes(issue: Issue, ctx) -> str:
    url = load_config()["sources"]["release_notes"]["url"]
    page = ctx.new_page()
    page.goto(url, wait_until="networkidle", timeout=60_000)
    text = _main_text(page)
    page.close()
    src = issue.sources_dir
    (src / "release_notes_full.txt").write_text(text, encoding="utf-8")
    sections = split_dated_sections(text)
    recent = [(d, s) for d, s in sections if d and d >= issue.period_start]
    if recent:
        body = "\n\n".join(s for _, s in recent)
        note = f"{len(recent)} release(s) since {issue.period_start:%d %b %Y}"
    else:
        body = text
        note = "no dated releases found in the period - saved the whole page"
    (src / "release_notes.txt").write_text(body, encoding="utf-8")
    return f"release notes: {note}"


def fetch_next_meeting(issue: Issue, ctx) -> str:
    url = load_config()["sources"]["next_meeting"]["url"]
    page = ctx.new_page()
    page.goto(url, wait_until="networkidle", timeout=60_000)
    page.wait_for_timeout(1500)
    final_url = page.url
    text = _main_text(page)
    page.close()
    dates = [m.group(1) for m in DATE_RE.finditer(text)]
    times = re.findall(r"\b\d{1,2}[:.]\d{2}\s*(?:am|pm)?\s*(?:UTC|GMT|AEST|AEDT)?|\b\d{4}\s*UTC\b", text, re.I)
    (issue.sources_dir / "next_meeting.txt").write_text(
        f"URL: {url}\nResolved to: {final_url}\nDates found: {dates[:5]}\nTimes found: {times[:5]}\n\n{text[:5000]}",
        encoding="utf-8",
    )
    return f"next meeting: {dates[0] if dates else 'no date found'} ({final_url})"


def fetch_social_magic_moments(issue: Issue, ctx) -> str:
    cfg = load_config()["sources"]["social_magic_moments"]
    base = cfg["chat_base"].rstrip("/") + "/api/v4"
    out_dir = issue.sources_dir
    try:
        posts, users = _mattermost_posts(ctx, base, cfg["team"], cfg["channel"], issue.period_start)
    except LoginRequired:
        raise
    except Exception as e:  # not Mattermost after all, or API blocked: fall back to the web page
        page = ctx.new_page()
        page.goto(f"{cfg['chat_base'].rstrip('/')}/{cfg['team']}/channels/{cfg['channel']}", wait_until="networkidle")
        _check_login(page)
        page.wait_for_timeout(4000)
        (out_dir / "social_magic_moments.txt").write_text(_main_text(page), encoding="utf-8")
        page.screenshot(path=str(out_dir / "social_magic_moments.png"), full_page=True)
        page.close()
        return f"social magic moments: API failed ({e}); saved page text + screenshot instead"

    files_dir = out_dir / "social_magic_moments_files"
    lines = [f"# Social Magic Moments since {issue.period_start:%d %b %Y}\n"]
    for p in posts:
        when = datetime.fromtimestamp(p["create_at"] / 1000, tz=timezone.utc)
        who = users.get(p["user_id"], p["user_id"])
        lines.append(f"## {when:%Y-%m-%d %H:%M} UTC - {who}\n\n{p.get('message', '').strip()}\n")
        for f in (p.get("metadata") or {}).get("files") or []:
            files_dir.mkdir(exist_ok=True)
            r = ctx.request.get(f"{base}/files/{f['id']}", headers={"X-Requested-With": "XMLHttpRequest"})
            if r.ok:
                dest = files_dir / f"{f['id']}_{f.get('name', 'file')}"
                dest.write_bytes(r.body())
                lines.append(f"Attachment: sources/{files_dir.name}/{dest.name}\n")
    (out_dir / "social_magic_moments.md").write_text("\n".join(lines), encoding="utf-8")
    return f"social magic moments: {len(posts)} post(s)"


def _mattermost_posts(ctx, base, team, channel, since: date):
    h = {"X-Requested-With": "XMLHttpRequest"}

    def get(path):
        r = ctx.request.get(base + path, headers=h)
        if r.status == 401:
            raise LoginRequired("Not signed in to Radiopaedia Chat - run `python -m qm login` first.")
        if not r.ok:
            raise RuntimeError(f"GET {path} -> {r.status}")
        return r.json()

    t = get(f"/teams/name/{team}")
    ch = get(f"/teams/{t['id']}/channels/name/{channel}")
    since_ms = int(datetime(since.year, since.month, since.day, tzinfo=timezone.utc).timestamp() * 1000)
    data = get(f"/channels/{ch['id']}/posts?since={since_ms}")
    posts = [
        data["posts"][pid]
        for pid in data.get("order", [])
        if data["posts"][pid].get("create_at", 0) >= since_ms
        and not data["posts"][pid].get("delete_at")
        and not data["posts"][pid].get("type")  # skip system messages (joins etc.)
    ]
    posts.sort(key=lambda p: p["create_at"])

    users: dict[str, str] = {}
    ids = sorted({p["user_id"] for p in posts})
    if ids:
        csrf = next((c["value"] for c in ctx.cookies() if c["name"] == "MMCSRF"), "")
        r = ctx.request.post(base + "/users/ids", data=json.dumps(ids), headers={**h, "X-CSRF-Token": csrf, "Content-Type": "application/json"})
        if r.ok:
            for u in r.json():
                name = " ".join(x for x in (u.get("first_name"), u.get("last_name")) if x)
                users[u["id"]] = f"{name} (@{u['username']})" if name else f"@{u['username']}"
    return posts, users


def fetch_style_guide(issue: Issue, ctx) -> str:
    cfg = load_config()["sources"]["style_guide"]
    base = cfg.get("export_url") or f"https://docs.google.com/document/d/{cfg['doc_id']}/export"
    tab = f"&tab={cfg['tab']}" if cfg.get("tab") else ""
    text = None
    for fmt in ("md", "txt"):
        r = ctx.request.get(f"{base}?format={fmt}{tab}")
        ctype = r.headers.get("content-type", "")
        if r.ok and "text/html" not in ctype:
            text = r.body().decode("utf-8-sig")
            break
    if text is None:
        raise LoginRequired(
            "Couldn't export Arlene's doc (it needs a Google login). Either sign in to Google via "
            "`python -m qm login`, ask Arlene to share it 'anyone with the link can view', or "
            f"download it as Markdown/plain text to {issue.sources_dir / 'style_guide_doc.md'}."
        )
    (issue.sources_dir / "style_guide_doc.md").write_text(text, encoding="utf-8")
    section = extract_month_section(text, issue)
    draft = issue.dir / "style_guide.md"
    if section and not draft.exists():
        draft.write_text(section, encoding="utf-8")
        return f"style guide: found a '{issue.month_name}' section -> style_guide.md"
    return "style guide: saved the doc; no section headed with this month's name was found" if not section else "style guide: saved the doc (style_guide.md already exists, left untouched)"


_MONTH_LINE = re.compile(r"^\W*(" + "|".join(calendar.month_name[1:]) + r")\b.{0,30}$", re.I)


def extract_month_section(text: str, issue: Issue) -> str | None:
    """Return the block under the last short line/heading naming this issue's month.

    Works for Markdown headings ("## October 2026") and for plain lines
    ("October 2026" on its own). Stops at the next heading of the same level,
    or the next line that is just another month name.
    """
    lines = text.splitlines()
    want = re.compile(rf"\b({issue.month_name}|{issue.month_name[:3]})\b", re.I)
    start = None
    for i, ln in enumerate(lines):
        bare = ln.strip("#*_ \t")
        if bare and len(bare) < 60 and want.search(bare):
            start = i
    if start is None:
        return None
    heading = lines[start]
    level = len(heading) - len(heading.lstrip("#"))
    out = []
    for ln in lines[start + 1 :]:
        if level and ln.startswith("#") and len(ln) - len(ln.lstrip("#")) <= level:
            break
        if not level and _MONTH_LINE.match(ln.strip("*_ ")):
            break
        out.append(ln)
    return "\n".join(out).strip() or None


FETCHERS = {
    "dashboard": fetch_dashboard,
    "release-notes": fetch_release_notes,
    "next-meeting": fetch_next_meeting,
    "social": fetch_social_magic_moments,
    "style-guide": fetch_style_guide,
}


def gather(issue: Issue, only: list[str] | None = None) -> list[str]:
    issue.sources_dir.mkdir(parents=True, exist_ok=True)
    pw, ctx = open_browser(headless=True)
    results = []
    try:
        for name, fn in FETCHERS.items():
            if only and name not in only:
                continue
            try:
                results.append("OK   " + fn(issue, ctx))
            except Exception as e:
                results.append(f"FAIL {name}: {e}")
    finally:
        ctx.close()
        pw.stop()
    (issue.sources_dir / "gather.log").write_text("\n".join(results) + "\n", encoding="utf-8")
    return results
