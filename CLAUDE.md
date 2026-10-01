# Quantum Mottle: notes for Claude

This repo builds Henry Knipe's monthly editors' newsletter. Read `README.md` for the tool itself.

## "Draft the <Month> issue"

1. Work out the issue slug: the month it is **sent**, as `YYYY-MM`. Its reporting period is the previous month.
2. If `issues/<slug>/` doesn't exist, run `python -m qm new <slug>`.
3. If `issues/<slug>/sources/` is empty, run `python -m qm gather <slug>`. It needs Henry's logged-in browser
   profile, so it only works on his machine. In a cloud session radiopaedia.org is usually unreachable: tell Henry
   to run gather locally and push, or ask him to paste the sources.
4. Load the `quantum-mottle-voice` skill and follow it for everything you write. Its rules always apply:
   hyphens never em dashes, Australian spelling, name people for work done but never for opinions in Chat.
5. Fill `content.yaml` from `sources/`:
   - **release_updates.items**: 3-6 terse bullets from `release_notes.txt`, user-facing changes only, no ticket numbers.
   - **meetup.next**: from `next_meeting.txt`, formatted like `Wednesday 15 October 0900 UTC`. Leave
     `meetup.discussed` as TODO unless Henry gave notes.
   - **style_guide**: `style_guide.md` is Arlene's text. Keep her words; only fix formatting (bold, links, the
     worked example). If `gather` couldn't reach the doc, read it with the Google Drive connector (doc id in `config.yaml`).
   - **social_magic_moments**: choose the best post in `social_magic_moments.md`. Quote the reader's thanks and credit
     whoever passed it on (e.g. "Passed on by Rachel"). If several are good, list them for Henry to choose.
   - **updates**: only from what Henry tells you or what is obvious in the sources. Never invent updates.
   - **editor_in_chief.md**: Henry writes this. Draft it only when asked, from his notes, in his voice.
6. Run `python -m qm check <slug>` and fix the warnings. Leave a TODO where only Henry can supply the content.
7. Run `python -m qm build <slug>` and say which sections still need Henry.

Past issues in `examples/` show the format and voice. Read one or two before drafting.

## Don't

- Commit anything under `issues/*/sources/` or `dashboard.png` (git-ignored: internal Chat posts and admin pages).
- Write to radiopaedia.org. Every fetcher is read-only.
- Edit the fixed template blocks (contact, mission, footer) unless asked.
