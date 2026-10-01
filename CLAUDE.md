# Quantum Mottle: notes for Claude

This repo builds Henry Knipe's monthly editors' newsletter. Read `README.md` for the tool itself.

## "Draft the <Month> issue"

1. Work out the issue slug: the month it is **sent**, as `YYYY-MM`. It covers what has happened since the
   previous issue (compare with last month's `issues/` folder so nothing is repeated).
2. If `issues/<slug>/` doesn't exist, run `python -m qm new <slug>`.
3. If `issues/<slug>/sources/` is empty, run `python -m qm gather <slug>`. It needs Henry's logged-in browser
   profile, so it only works on his machine. In a cloud session radiopaedia.org is usually unreachable: tell Henry
   to run gather locally and push, or ask him to paste the sources.
4. Load the `quantum-mottle-voice` skill and follow it for everything you write. Its rules always apply:
   hyphens never em dashes, Australian spelling, name people for work done but never for opinions in Chat.
5. Fill `content.yaml` from `sources/`:
   - **release_updates.items**: about 3 terse bullets from `release_notes.txt`, user-facing changes only, no ticket
     numbers. Group related changes under a bold lead-in when there are many (see `examples/2026-04`).
   - **meetup.next**: from `next_meeting.txt`, formatted like `Wed 30th September 0730 UTC`. Leave
     `meetup.discussed` as TODO unless Henry gave notes.
   - **style_guide**: `style_guide.md` is Arlene's text. Keep her words; only fix formatting (bold, links, the
     worked example). If `gather` couldn't reach the doc, read it with the Google Drive connector (doc id in `config.yaml`).
   - **social_magic_moments.items**: choose the best post(s) in `social_magic_moments.md`. `intro:` credits whoever
     shared it ("Thanks to Rachel for sharing this lovely message:"), `body:` is the reader's words, signed with their
     name and country as they gave it. If several are good, list them for Henry to choose.
   - **icons**: pick a name from `icons:` in `config.yaml` that fits each update, or leave the default.
   - **updates**: only from what Henry tells you or what is obvious in the sources. Never invent updates.
   - **editor_in_chief.md**: Henry writes this. Draft it only when asked, from his notes, in his voice.
6. Run `python -m qm check <slug>` and fix the warnings. Leave a TODO where only Henry can supply the content.
7. Run `python -m qm build <slug>` and say which sections still need Henry.
8. Henry sends with `python -m qm gmail <slug> --test`, then without `--test`. Don't use the Gmail connector to
   create the newsletter draft: it strips images and styling.

Past issues in `examples/` (as `content.yaml`) show the format and voice. Read one or two before drafting.

## Don't

- Commit anything under `issues/*/sources/` or `dashboard.png` (git-ignored: internal Chat posts and admin pages).
- Write to radiopaedia.org. Every fetcher is read-only.
- Edit the fixed template blocks (contact, mission, footer) unless asked.
