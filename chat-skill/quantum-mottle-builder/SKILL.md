---
name: quantum-mottle-builder
description: Assemble and build Henry Knipe's monthly Radiopaedia editors' newsletter, Quantum Mottle, as a finished HTML email in the house Postcards design, plus a send-ready .eml with the dashboard screenshot embedded. Use this whenever Henry wants to put together, draft, build, lay out or produce a Quantum Mottle issue or "the newsletter" for a given month, uploads a dashboard screenshot, or pastes release notes, Social Magic Moments, Arlene's style guide piece or meet-up notes for the newsletter, even if he doesn't name the skill. Works with the quantum-mottle-voice skill, which covers how the words should sound.
---

# Quantum Mottle builder

Henry sends Quantum Mottle to the Radiopaedia editorial board (~80 editors, worldwide) once a month, from Gmail, by BCC. This skill turns his material into the finished email: a fixed Postcards-derived HTML design (`templates/newsletter.html.j2`) filled from one small `content.yaml` per issue.

You write `content.yaml`; `scripts/build.py` does all the HTML. Never hand-edit HTML: the template carries Outlook/Gmail workarounds that are easy to break.

## Before you start

- Load the **quantum-mottle-voice** skill. Everything you write must follow it: hyphens never em dashes, Australian spelling, name people for work done but never for opinions offered in an internal Chat thread.
- Read one or two past issues in `examples/` (e.g. `examples/2026-09/content.yaml`). They show every section as actually sent and are the best guide to length and tone.
- The renderer needs `jinja2`, `pyyaml` and `markupsafe`. If an import fails: `pip install jinja2 pyyaml markupsafe --break-system-packages`.

## What Henry provides each month

Ask for whatever is missing, in one short message, rather than inventing it:

| Section | Where it comes from |
|---|---|
| From the Editor in Chief | Henry's own words, or his notes for you to draft from (one idea, 120-250 words) |
| Dashboard | a screenshot of radiopaedia.org/admin/restricted_pages/3606 (uploaded image) |
| Updates | what Henry tells you; 2-4 short blocks |
| Release Updates | text pasted from radiopaedia.org/release-notes |
| The Style Guide | Arlene Campos's piece. If the Google Drive connector is available, read her doc (id `1UXBCNyfSWjalRA64DuDwOyJtwiHRqV2CUlJydv-q8p8`) and take the section for this month; otherwise ask Henry to paste it |
| Editor Meet-up | what was discussed (Henry's notes) and the next date from radiopaedia.org/next-editor-meeting |
| Priority Project | the current Operation's name, progress and a line of encouragement |
| Social Magic Moments | a message pasted from the #social-magic-moments Chat channel, and who shared it |

radiopaedia.org pages behind a login (the dashboard, Chat) can't be fetched from here, so rely on what Henry pastes or uploads.

## Steps

1. **Set up the issue folder.** The folder name is the month the issue is **sent**, `YYYY-MM`:
   ```bash
   python <skill>/scripts/build.py new /home/claude/qm/2026-10
   ```
   This writes a commented `content.yaml` skeleton. Copy Henry's uploaded screenshot into the folder as `dashboard.png` (any uploaded images go here, referenced by file name).

2. **Fill `content.yaml`.** Field notes:
   - Text accepts light markdown: `**bold**`, `*italic*`, `[link](https://...)`, blank line = new paragraph, `- item` = bullet, `→ item` = arrow line.
   - `editor_in_chief.body` (or `editor_in_chief.md` via `body_file`): Henry's note. The `-H` sign-off is added automatically. If he gave notes rather than prose, draft it in his voice and say it's a draft.
   - `updates`: each has `title`, `body`, optional `url`, and `icon` - a name from `icons:` in `config.yaml` (evidence, mcq, mri, add, clown, search, muscle, default, release) that suits the topic. Updates sit two per row; an odd last one goes full width. Only include updates Henry gave you.
   - `release_updates.items`: about three terse, user-facing bullets. No ticket numbers or developer jargon. With many changes, group them under bold lead-ins (`**Viewer & offline:** ...`) as in `examples/2026-04`.
   - `style_guide.body`: Arlene's words, kept as she wrote them. Only fix formatting (bold headings, bullets, links).
   - `meetup`: `month` (the month of the meeting being reported), `discussed` (list), `next` formatted like `Wed 30th September 0730 UTC`, optional `who`, optional `style: arrows`.
   - `priority_project`: `name` (two lines allowed, e.g. "Operation Annotation Aces" / "Core Conditions Edition"), optional `body`, optional `label: Editorial Project`. Keep Operation names exactly as coined.
   - `social_magic_moments.items`: each has `intro` crediting who shared it ("Thanks to Rachel for sharing this lovely message:"), `body` with the reader's words signed as they signed it, and optional `image`. Set `heading: false` to drop the section title, as in September 2026.
   - Delete a section, or leave its body empty, to leave it out.

3. **Check and build:**
   ```bash
   python <skill>/scripts/build.py check /home/claude/qm/2026-10
   python <skill>/scripts/build.py build /home/claude/qm/2026-10
   ```
   Fix every warning you can (em dashes, US spellings, leftover TODOs). Leave a TODO only where Henry alone can supply the content, and tell him which.

4. **Hand over** both files from `build/` (copy them to `/mnt/user-data/outputs/` or wherever this environment makes files downloadable):
   - `newsletter.html` - the preview. Images are embedded, so it opens on its own in a browser.
   - `newsletter.eml` - the email to send.

   Then give Henry the sending steps:
   1. Download `newsletter.eml` and double-click it. It opens in Apple Mail.
   2. **Message → Send Again** (⇧⌘D) opens it as a new email with images in place. Check **From** is his Radiopaedia Gmail account.
   3. Send it to himself first and check it on computer and phone; then do it again with the editors in **Bcc**.

   Don't create the newsletter as a Gmail draft with the Gmail connector: it strips images, background images and styling, and the email arrives broken.

## Revisions

When Henry asks for changes, edit `content.yaml` and rebuild; don't patch the HTML. Keep the same issue folder so earlier decisions carry through.
