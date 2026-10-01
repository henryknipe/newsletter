"""Render an issue's content.yaml into newsletter.html (preview) and newsletter.eml (send-ready)."""

from __future__ import annotations

import base64
import mimetypes
import re
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

from . import formatting as fmt
from .config import ROOT, Issue, load_config

# Used when an update doesn't set its own `icon:` (the two from the Postcards template).
DEFAULT_ICONS = ["default", "release"]

GREY = "rgb(135,135,135)"


def _is_remote(src: str) -> bool:
    return bool(re.match(r"^(https?:|cid:|data:)", src))


class ImageRegistry:
    """Tracks local image files so they can become relative paths, data URIs or CID parts."""

    def __init__(self, issue: Issue, mode: str):
        self.issue = issue
        self.mode = mode  # "preview" | "inline" | "eml"
        self.parts: dict[str, tuple[str, Path]] = {}  # path -> (cid, file)
        self.missing: list[str] = []

    def resolve(self, src: str | None) -> str | None:
        if not src:
            return None
        if _is_remote(src):
            return src
        path = self._find(src)
        if path is None:
            self.missing.append(src)
            return None
        if self.mode == "preview":
            return Path("..", path.relative_to(self.issue.dir)).as_posix() if path.is_relative_to(self.issue.dir) else path.as_uri()
        if self.mode == "inline":
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"
        key = str(path)
        if key not in self.parts:
            self.parts[key] = (make_msgid(domain="quantum-mottle")[1:-1], path)
        return "cid:" + self.parts[key][0]

    def _find(self, src: str) -> Path | None:
        for base in (self.issue.dir, ROOT):
            p = (base / src).expanduser()
            if p.exists():
                return p.resolve()
        return None


def load_content(issue: Issue) -> dict:
    data = yaml.safe_load(issue.content_path.read_text(encoding="utf-8")) or {}
    _load_body_files(data, issue.dir)
    return data


def _load_body_files(node, base: Path):
    """Any mapping with `body_file: x.md` gets `body` filled from that file."""
    if isinstance(node, dict):
        if node.get("body_file") and not node.get("body"):
            p = base / node["body_file"]
            if p.exists():
                node["body"] = p.read_text(encoding="utf-8")
        for v in node.values():
            _load_body_files(v, base)
    elif isinstance(node, list):
        for v in node:
            _load_body_files(v, base)


def build_context(issue: Issue, content: dict, images: ImageRegistry) -> dict:
    cfg = load_config()
    nl = cfg.get("newsletter", {})

    eic = content.get("editor_in_chief") or {}
    eic_text = (eic.get("body") or "").rstrip()
    signoff = eic.get("signoff", "-H")
    if signoff and not eic_text.endswith(signoff):
        eic_text = f"{eic_text}\n\n{signoff}"
    eic_html = fmt.blocks(eic_text, size=18, line_height="140%", color=GREY)

    icons = cfg.get("icons", {})

    def icon(name):
        return images.resolve(icons.get(name, name)) if name else None

    dash = content.get("dashboard") or {}
    dashboard_src = images.resolve(dash.get("image_url") or dash.get("image"))

    cells = []
    for i, u in enumerate(content.get("updates") or []):
        cells.append(
            {
                "title": u.get("title", ""),
                "url": u.get("url"),
                "icon_src": icon(u.get("icon") or DEFAULT_ICONS[i % 2]),
                "body_html": Markup(fmt.blocks(u.get("body"), color=GREY)),
                "underline": False,
            }
        )
    rel = content.get("release_updates") or {}
    if rel.get("items") or rel.get("body"):
        body = rel.get("intro", "Summary of the latest updates:")
        if rel.get("items"):
            body += "\n\n" + "\n".join(f"- {item}" for item in rel["items"])
        if rel.get("body"):
            body += "\n\n" + rel["body"]
        cells.append(
            {
                "title": rel.get("title", "Release Updates"),
                "url": rel.get("url", "https://radiopaedia.org/release-notes"),
                "icon_src": icon(rel.get("icon") or "release"),
                "body_html": Markup(fmt.blocks(body, color=GREY)),
                "underline": True,
            }
        )
    # Two per row; an odd one out spans the full width (as in the September 2026 issue).
    rows = [cells[i : i + 2] for i in range(0, len(cells), 2)]

    sg = content.get("style_guide") or {}
    sg_body = sg.get("body") or ""
    if sg.get("link"):
        sg_body += f"\n\n[{sg.get('link_text', 'Read more in the style guide')}]({sg['link']})"
    style_guide_html = fmt.blocks(sg_body, size=18, line_height="22px", color="rgb(238,238,238)")

    mu = content.get("meetup") or {}
    mu_lines = [f"At the {str(mu.get('month', issue.month_name)).upper()} meeting, we discussed:"]
    items = mu.get("discussed") or []
    if items:
        marker = "→ " if mu.get("style") == "arrows" else "- "
        mu_lines[0] += "\n" + "\n".join(marker + str(x) for x in items)
    where = mu.get("where", "[bit.ly/radio-update](https://bit.ly/radio-update) (Google Meet)")
    mu_lines.append(
        f"Who: {mu.get('who', 'All Radiopaedia editors')}\n"
        f"Next Meet-Up: {mu.get('next', 'TBC')}\n"
        f"Where: {where}"
    )
    meetup_html = fmt.blocks("\n\n".join(mu_lines), color=GREY)

    pp = content.get("priority_project")
    project = None
    if pp and pp.get("name"):
        project = {
            "label": pp.get("label", "Priority Project"),
            "name_lines": [ln for ln in str(pp["name"]).splitlines() if ln.strip()],
            "body_html": Markup(fmt.blocks(pp.get("body"), size=20, color="rgb(255,255,255)", align="center")),
            "button_text": pp.get("button_text", "Get Involved!"),
            "button_url": pp.get("button_url", "https://www.radiopaedia.org/projects"),
        }

    sm = content.get("social_magic_moments") or {}
    social_items = []
    for it in sm.get("items") or ([sm] if sm.get("body") else []):
        text = "\n\n".join(x for x in (it.get("intro"), it.get("body")) if x)
        social_items.append(
            {
                "html": Markup(fmt.blocks(text, color=GREY)),
                "image_src": images.resolve(it.get("image_url") or it.get("image")),
            }
        )

    subject = content.get("subject") or nl.get("subject", "Quantum Mottle - {month} {year}").format(
        month=issue.month_name, year=issue.year
    )
    return {
        "subject": subject,
        "preheader": content.get("preheader", ""),
        "issue_label": content.get("issue_label", f"{issue.month_name} {issue.year}"),
        "eic_html": Markup(eic_html),
        "dashboard_src": dashboard_src,
        "dashboard_alt": dash.get("alt", f"Radiopaedia dashboard, {issue.month_name} {issue.year}"),
        "update_rows": rows,
        "style_guide_html": Markup(style_guide_html),
        "style_guide_author": sg.get("author", "Arlene Campos"),
        "meetup_html": Markup(meetup_html),
        "project": project,
        "social_heading": sm.get("heading", True),
        "social_items": social_items,
        "nav": nl.get("nav", []),
        "contact_email": nl.get("contact_email", "henry.knipe@radiopaedia.org"),
        "contact_dm_url": nl.get("contact_dm_url", "https://radiopaedia.org/chat/editorial-board/messages/@henryknipe"),
        "postcards_footer": nl.get("postcards_footer", True),
    }


def render_html(issue: Issue, mode: str = "preview") -> tuple[str, ImageRegistry, dict]:
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=True,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    images = ImageRegistry(issue, mode)
    content = load_content(issue)
    ctx = build_context(issue, content, images)
    html = env.get_template("newsletter.html.j2").render(**ctx)
    return html, images, ctx


def build(issue: Issue, inline_images: bool = False) -> list[Path]:
    out_dir = issue.dir / "build"
    out_dir.mkdir(exist_ok=True)

    html, images, ctx = render_html(issue, "inline" if inline_images else "preview")
    for src in images.missing:
        print(f"warning: image not found, left out: {src}")
    html_path = out_dir / "newsletter.html"
    html_path.write_text(html, encoding="utf-8")

    eml_html, images, _ = render_html(issue, "eml")
    eml_path = out_dir / "newsletter.eml"
    eml_path.write_bytes(_to_eml(eml_html, images, ctx["subject"]))
    return [html_path, eml_path]


def _to_eml(html: str, images: ImageRegistry, subject: str) -> bytes:
    nl = load_config().get("newsletter", {})
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = nl.get("from", "")
    msg["To"] = nl.get("to", "")
    msg["X-Unsent"] = "1"  # Outlook/Apple Mail open this as an editable draft
    msg.set_content("This newsletter is best viewed in an HTML-capable mail client.")
    msg.add_alternative(html, subtype="html")
    html_part = msg.get_payload()[1]
    for cid, path in images.parts.values():
        maintype, subtype = (mimetypes.guess_type(path.name)[0] or "image/png").split("/")
        html_part.add_related(path.read_bytes(), maintype, subtype, cid=f"<{cid}>", filename=path.name)
    return bytes(msg)


# ---------------------------------------------------------------- checks

PLACEHOLDER = re.compile(r"\b(TODO|TBC|MONTH|DAY/DATE)\b|\[\[.*?\]\]")


def lint(issue: Issue) -> list[str]:
    """House-style and completeness checks on the raw content."""
    text = issue.content_path.read_text(encoding="utf-8")
    for f in issue.dir.glob("*.md"):
        text += "\n" + f.read_text(encoding="utf-8")
    warnings = []
    if "—" in text or "–" in text:
        warnings.append("Contains an em/en dash. House style is hyphens only.")
    for m in sorted({m.group(0) for m in PLACEHOLDER.finditer(text)}):
        warnings.append(f"Placeholder still present: {m}")
    content = load_content(issue)
    if not (content.get("editor_in_chief") or {}).get("body"):
        warnings.append("From the Editor in Chief is empty.")
    dash = content.get("dashboard") or {}
    if not (dash.get("image") or dash.get("image_url")):
        warnings.append("No dashboard image - ask Henry for the screenshot, or set dashboard.image_url.")
    if not (content.get("style_guide") or {}).get("body"):
        warnings.append("Style guide section is empty (it will be omitted).")
    for word in ("color", "tumor", "pediatric", "organize", "recognize", "center "):
        if re.search(rf"\b{word}", text, re.I):
            warnings.append(f"US spelling? '{word.strip()}'")
    return warnings
