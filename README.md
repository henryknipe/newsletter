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
  build/newsletter.eml  <- the finished email, images embedded (what `qm gmail` uploads)
```

## One-off setup

```bash
pip install -r requirements.txt
playwright install chromium
python -m qm login        # a browser opens: sign in to Radiopaedia (and Google, optionally)
```

The login is saved in `~/.quantum-mottle/browser-profile`, so later runs work headless.
For sending from Gmail, also do the one-off [Gmail setup](#gmail) below.

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

Open `newsletter.html` in a browser to proof it, then:

```bash
python -m qm gmail 2026-10 --test   # sends a [TEST] copy to you only - check it on your phone too
python -m qm gmail 2026-10          # puts it in Gmail Drafts, editors already in BCC
python -m qm gmail 2026-10 --send   # or send it straight away (asks you to type "send")
```

## Where each section comes from

| Section | Source | Automation |
|---|---|---|
| From the Editor in Chief | you | Claude can draft from your notes, using the `quantum-mottle-voice` skill |
| Dashboard | [restricted_pages/3606](https://radiopaedia.org/admin/restricted_pages/3606) | `gather` screenshots it (set `sources.dashboard.selector` in `config.yaml` to crop) |
| Updates | you / Chat | `icon: mri` etc. picks from icons already used in past issues (`config.yaml`); new ones from [magnific.com/icons](https://www.magnific.com/icons) |
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

## Gmail

`qm gmail` uploads the finished email through the Gmail API, so the dashboard
screenshot and any local icons travel inside the message. You don't need to
upload them anywhere. (Claude's Gmail connector can't be used for this: it strips
images, background images and styles out of drafts.)

One-off setup, about 10 minutes:

1. Go to <https://console.cloud.google.com/>, create a project (e.g. "Quantum Mottle"),
   and enable the **Gmail API** (APIs & Services -> Library).
2. APIs & Services -> OAuth consent screen: choose **Internal** if radiopaedia.org
   allows it (otherwise External, and add yourself as a test user).
3. APIs & Services -> Credentials -> Create credentials -> OAuth client ID ->
   **Desktop app**. Download the JSON and save it as `~/.quantum-mottle/gmail-client.json`.
4. Put the editorial board's addresses in a file, one per line (e.g.
   `~/.quantum-mottle/editors.txt`), and point to it from `config.local.yaml`:

   ```yaml
   newsletter:
     bcc_file: ~/.quantum-mottle/editors.txt
   ```

5. Run `python -m qm gmail 2026-10 --test`. A browser asks you to allow
   "compose and send" access once; the token is then cached in `~/.quantum-mottle/`.

The access asked for is `gmail.compose` (create drafts and send). It can't read your mail.

If you open the draft in Gmail and change it before sending, Gmail's editor may
simplify the layout a little. If you want exactly what you proofed in the `--test`
copy, use `--send`.

## Images

- Images you have locally (the dashboard screenshot, files in `assets/icons/`)
  are embedded in `newsletter.eml`, which is what `qm gmail` sends.
- Hosted images (icons and pictures already uploaded to Postcards at
  `cloudfilesdm.com`) are just linked. `dashboard.image_url:` and `image_url:` on
  a Social Magic Moment take any public URL.

## Past issues

`examples/2026-04`, `2026-08` and `2026-09` are those issues transcribed into
`content.yaml` form. They show every option in real use (multi-line project
names, `label: Editorial Project`, several Social Magic Moments with an image,
arrow-style Meet-up notes), and the tests rebuild them.

## Changing the design

Edit `templates/newsletter.html.j2`. Fixed parts (header, contact, mission,
footer) are plain HTML. Monthly parts are `{{ ... }}` variables filled in by
`qm/render.py`. If you rework the design in Postcards, export it and copy the
changed blocks across.

## Tests

```bash
python -m pytest -q
```
