"""Put the built newsletter into Gmail via the Gmail API, with images embedded.

Why not the Gmail connector in Claude? It strips <img> tags, background
images and <style> blocks from drafts, so the newsletter arrives broken. The
Gmail API takes the finished MIME message as-is.

One-off setup (see README "Gmail"):
  1. Create an OAuth client (Desktop app) in Google Cloud with the Gmail API enabled.
  2. Save its JSON as ~/.quantum-mottle/gmail-client.json.
  3. The first `qm gmail` run opens a browser to approve; the token is cached.
"""

from __future__ import annotations

import base64
import email
from email.utils import getaddresses
from pathlib import Path

from .config import ROOT, Issue, load_config

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
HOME = Path("~/.quantum-mottle").expanduser()


def _service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        raise SystemExit("Install the Gmail extras first: pip install -r requirements.txt")

    client = HOME / "gmail-client.json"
    token = HOME / "gmail-token.json"
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client.exists():
                raise SystemExit(f"Missing {client}. See README section 'Gmail' for the one-off setup.")
            creds = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES).run_local_server(port=0)
        HOME.mkdir(parents=True, exist_ok=True)
        token.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


def read_bcc(path: str | None) -> list[str]:
    """One address per line (or comma separated); blank lines and # comments ignored."""
    if not path:
        return []
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = ROOT / p
    text = "\n".join(ln.split("#", 1)[0] for ln in p.read_text(encoding="utf-8").splitlines())
    return [addr for _, addr in getaddresses([text.replace("\n", ",")]) if "@" in addr]


def prepare(issue: Issue, *, bcc: list[str], test: bool) -> bytes:
    """Return the issue's .eml bytes with recipients set for a draft, test or send."""
    eml = issue.dir / "build" / "newsletter.eml"
    if not eml.exists():
        raise SystemExit(f"{eml.relative_to(ROOT)} not found - run `python -m qm build {issue.slug}` first.")
    msg = email.message_from_bytes(eml.read_bytes())
    del msg["X-Unsent"]
    nl = load_config().get("newsletter", {})
    me = nl.get("to") or nl.get("from")
    del msg["To"]
    msg["To"] = me
    if test:
        subject = msg["Subject"]
        del msg["Subject"]
        msg["Subject"] = f"[TEST] {subject}"
    elif bcc:
        msg["Bcc"] = ", ".join(bcc)
    return msg.as_bytes()


def _raw(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode()


def create_draft(issue: Issue, bcc: list[str]) -> str:
    svc = _service()
    d = svc.users().drafts().create(userId="me", body={"message": {"raw": _raw(prepare(issue, bcc=bcc, test=False))}}).execute()
    return d["id"]


def send(issue: Issue, *, bcc: list[str], test: bool) -> str:
    svc = _service()
    m = svc.users().messages().send(userId="me", body={"raw": _raw(prepare(issue, bcc=bcc, test=test))}).execute()
    return m["id"]
