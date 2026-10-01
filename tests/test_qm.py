import email
from datetime import date

import pytest

from qm import config, formatting as fmt
from qm.config import Issue
from qm.render import build, lint
from qm.sources import extract_month_section, parse_date, split_dated_sections


def test_inline_escapes_and_formats():
    out = fmt.inline('**Bold** <script> *it* [Link](https://x.org/?a=1&b=2)')
    assert '<span style="font-weight:700">Bold</span>' in out
    assert "&lt;script&gt;" in out
    assert '<span style="font-style:italic">it</span>' in out
    assert 'href="https://x.org/?a=1&amp;b=2"' in out


def test_blocks_lists_and_arrows():
    out = fmt.blocks("Intro:\n- one\n- two\n\n→ arrow")
    assert out.count("<li") == 2 and "<ul" in out
    assert out.index("Intro:") < out.index("<ul")  # intro and list in one paragraph
    assert out.count("→ ") == 1
    assert "<br></div>" in out  # spacer between paragraphs


def test_issue_period():
    i = Issue.parse("2026-01")
    assert i.prev_month_name == "December"
    assert i.period_start == date(2025, 12, 1)


@pytest.mark.parametrize(
    "s,expected",
    [("2026-09-14", date(2026, 9, 14)), ("14th September 2026", date(2026, 9, 14)), ("Sept 3, 2026", date(2026, 9, 3))],
)
def test_parse_date(s, expected):
    assert parse_date(s) == expected


def test_split_dated_sections():
    text = "Release notes\n\n2 October 2026\n- thing A\n\n15 September 2026\n- thing B\n\n20 August 2026\n- old"
    secs = split_dated_sections(text)
    assert [d for d, _ in secs if d] == [date(2026, 10, 2), date(2026, 9, 15), date(2026, 8, 20)]
    assert "thing B" in secs[2][1]


def test_extract_month_section_markdown_and_plain():
    issue = Issue(2026, 10)
    md = "# Style guide\n## September 2026\nold\n## October 2026\nUse **3 cm**.\n\nMore.\n## November 2026\nnext"
    assert extract_month_section(md, issue) == "Use **3 cm**.\n\nMore."
    plain = "September\nold stuff\nOctober\nnew stuff\nNovember\nlater"
    assert extract_month_section(plain, issue) == "new stuff"


@pytest.fixture
def issue(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ISSUES", tmp_path)
    i = Issue(2026, 10)
    i.dir.mkdir()
    from PIL import Image

    Image.new("RGB", (10, 10)).save(i.dir / "dashboard.png")
    (i.dir / "eic.md").write_text("Hello — editors!\n", encoding="utf-8")
    (i.content_path).write_text(
        """
editor_in_chief: {body_file: eic.md}
dashboard: {image: dashboard.png}
updates:
  - {title: One, body: First}
  - {title: Two, body: Second}
  - {title: Three, body: Third}
release_updates: {items: [Fast, Faster]}
meetup: {discussed: [Stuff], next: Wed 1 Oct}
""",
        encoding="utf-8",
    )
    return i


def test_build_html_and_eml(issue):
    html_path, eml_path = build(issue)
    html = html_path.read_text(encoding="utf-8")
    assert "Hello" in html and "-H" in html
    assert 'src="../dashboard.png"' in html
    assert "Release Updates" in html and "Faster</span></li>" in html
    assert "At the OCTOBER meeting" in html
    assert html.count("width:50%;padding-top:0") == 4  # 3 updates + release = two full rows
    assert "The Style Guide" not in html  # empty section omitted

    msg = email.message_from_bytes(eml_path.read_bytes())
    assert msg["X-Unsent"] == "1"
    parts = list(msg.walk())
    img = [p for p in parts if p.get_content_type() == "image/png"]
    assert len(img) == 1
    cid = img[0]["Content-ID"].strip("<>")
    body = next(p for p in parts if p.get_content_type() == "text/html").get_payload(decode=True).decode()
    assert f"cid:{cid}" in body


def test_lint_flags_em_dash(issue):
    assert any("dash" in w for w in lint(issue))


@pytest.mark.parametrize("slug", ["2026-04", "2026-08", "2026-09"])
def test_examples_build(tmp_path, monkeypatch, slug):
    import shutil

    monkeypatch.setattr(config, "ISSUES", tmp_path)
    shutil.copytree(config.ROOT / "examples" / slug, tmp_path / slug)
    html = build(Issue.parse(slug))[0].read_text(encoding="utf-8")
    assert "Quantum Mottle" in html and "-H" in html
    assert "cloudfilesdm.com/postcards/CleanShot" in html  # hosted dashboard
    if slug == "2026-09":  # 2 updates + release: the odd one spans the row
        assert html.count("width:100%;padding-top:0") == 1


def test_gmail_prepare(issue, tmp_path):
    from qm import gmail

    build(issue)
    bccf = tmp_path / "bcc.txt"
    bccf.write_text("# editors\na@x.org\nB <b@y.org>, c@z.org\n", encoding="utf-8")
    bcc = gmail.read_bcc(str(bccf))
    assert bcc == ["a@x.org", "b@y.org", "c@z.org"]
    msg = email.message_from_bytes(gmail.prepare(issue, bcc=bcc, test=False))
    assert msg["Bcc"] == "a@x.org, b@y.org, c@z.org" and msg["X-Unsent"] is None
    test = email.message_from_bytes(gmail.prepare(issue, bcc=bcc, test=True))
    assert test["Bcc"] is None and test["Subject"].startswith("[TEST]")
