# Quantum Mottle

Semi-automated build of the monthly Radiopaedia editors' newsletter. The
Postcards design lives in `templates/newsletter.html.j2`. Each month you fill
one small `content.yaml` (with Claude's help), and `qm` turns it into the
email.

```
issues/2026-10/
  content.yaml          <- this month's text (sections, updates, meet-up...)
  editor_in_chief.md    <- your EIC note
  style_guide.md        <- Arlene's piece (pulled from her Google Doc)
  dashboard.png         <- screenshot of restricted_pages/3606
  sources/              <- raw material scraped by `qm gather` (git-ignored)
  build/newsletter.html <- preview
  build/newsletter.eml  <- send-ready draft, images embedded
```

## One-off setup

```bash
pip install -r requirements.txt
playwright install chromium
python -m qm login        # a browser opens: sign in to Radiopaedia (and Google, optionally)
```

The login is saved in `~/.quantum-mottle/browser-profile`, so later runs work headless.

## Each month

```bash
python -m qm new 2026-10      # issue folder for the month you SEND (covers September)
python -m qm gather 2026-10   # screenshot + scrape every source
```

Then draft. The easiest way is to open Claude Code in this repo and say
**"draft the October issue"**. `CLAUDE.md` tells Claude how to turn
`sources/` into `content.yaml` in house style. Or edit the YAML yourself.

```bash
python -m qm check 2026-10    # placeholders, em dashes, US spellings, empty sections
python -m qm build 2026-10    # writes build/newsletter.html + build/newsletter.eml
```

Open `newsletter.html` in a browser to proof it. To send, open
`newsletter.eml` in Apple Mail or Outlook: it opens as an unsent draft with the
dashboard screenshot embedded. Add the editorial board as BCC and send.

## Where each section comes from

| Section | Source | Automation |
|---|---|---|
| From the Editor in Chief | you | Claude can draft from your notes, using the `quantum-mottle-voice` skill |
| Dashboard | [restricted_pages/3606](https://radiopaedia.org/admin/restricted_pages/3606) | `gather` screenshots it (set `sources.dashboard.selector` in `config.yaml` to crop) |
| Updates | you / Chat | icons from [magnific.com/icons](https://www.magnific.com/icons) -> `assets/icons/` |
| Release Updates | [release-notes](https://radiopaedia.org/release-notes) | `gather` keeps releases since the start of last month; Claude summarises |
| The Style Guide | [Arlene's doc](https://docs.google.com/document/d/1UXBCNyfSWjalRA64DuDwOyJtwiHRqV2CUlJydv-q8p8/edit?tab=t.0) | `gather` exports it and takes the section headed with this month |
| Editor Meet-up | [next-editor-meeting](https://radiopaedia.org/next-editor-meeting) | `gather` grabs the date and time; you add what was discussed |
| Priority Project | you | |
| Social Magic Moments | [#social-magic-moments](https://radiopaedia.org/chat/editorial-board/channels/social-magic-moments) | `gather` pulls last month's posts and attachments via the Chat (Mattermost) API |

`gather` only reads; it never writes to Radiopaedia. If one source fails
(e.g. Google refuses the doc export), the others still run and `sources/gather.log` says why.

### If Arlene's doc won't export

Google often blocks sign-in inside automated browsers. Options, easiest first:

1. Ask Arlene to set the doc to "anyone with the link can view". Then no login is needed.
2. In Claude Code with the Google Drive connector, ask Claude to read the doc.
3. File -> Download -> Markdown, saved as `issues/YYYY-MM/sources/style_guide_doc.md`.

## Images

Email clients need images either at a public URL or embedded in the message.

- `newsletter.eml` embeds every local image (dashboard, local icons) as inline
  attachments. This works in every client, including Gmail recipients.
- `newsletter.html` points at local files, which is fine for proofing. If you
  paste the HTML into another sender, upload the images first and set
  `dashboard.image_url:` / `icon: https://...` instead.
- `build --inline-images` embeds images as data URIs. Apple Mail is fine with
  these but Gmail strips them.

## Changing the design

Edit `templates/newsletter.html.j2`. Fixed parts (header, contact, mission,
footer) are plain HTML. Monthly parts are `{{ ... }}` variables filled in by
`qm/render.py`. If you rework the design in Postcards, export it and copy the
changed blocks across.

## Tests

```bash
python -m pytest -q
```
