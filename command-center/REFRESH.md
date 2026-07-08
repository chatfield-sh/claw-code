# Command Center — refresh playbook

This is the contract for refreshing the command center. It is followed by the
daily scheduled Routine and by any interactive session where the user says
"refresh my command center." Follow it exactly so every refresh produces the
same document with current data.

## The living document

The canonical, always-current surface is the Claude artifact:

> https://claude.ai/code/artifact/35cae650-258b-40ce-8b45-1ecb156dddf4

**Always republish to that URL** (pass it as `url` to the Artifact tool —
publishing without it mints a new link and orphans the old one). Keep the
favicon `🛎️` and the title `Chatfield Command Center` unchanged.

The copy in this directory (`index.html`) is a periodic checkpoint, not the
live surface. Commit a refreshed copy only when the dashboard's *structure*
changes (new module, redesign) — not for routine data refreshes.

## Data pull (all read-only)

| Source | Pull | Feeds |
|---|---|---|
| Gmail | `search_threads` — `in:inbox newer_than:14d` | Inbox triage, STR portfolio tiles, alerts |
| Google Calendar | `list_events` — today through +14 days | Agenda, meeting-load chart, stays, conflict alerts |
| GitHub | open/merged PRs, open issues, recent commits for `chatfield-sh/claw-code` | Dev desk |
| Google Drive / Zoom | only if callable without interactive approval | Optional modules |

Timezone is **America/New_York**; render all times Eastern.

## Rebuild rules

1. Start from the current `command-center/index.html` as the template — keep
   the design system (palette tokens, serif masthead, module grid) intact.
2. Update the masthead snapshot timestamp.
3. Recompute derived content, don't carry it forward: meeting-load counts
   (collapse duplicate invites), calendar overlaps, stay overlaps, STR RGI
   numbers from the latest report emails, inbox action suggestions.
4. Alerts are earned, not permanent: drop resolved ones, add new ones.
   Alert sources to check every run: credentials/secrets visible in email
   (see Guardrails), double-bookings, overlapping stays, deadline-style
   calendar reminders, PRs stale >14 days.
5. Chart marks stay `#1e8a5e` (light) / `#35a97a` (dark) — already validated.
   If new chart colors are needed, validate them with the dataviz skill first.
6. Render both themes headlessly (Chromium at `/opt/pw-browsers/chromium`)
   and eyeball before publishing.

## The interaction loop

The dashboard is interactive, and refreshes must preserve that in both
directions:

**Local state (browser-side).** Alerts and inbox items carry stable
`data-cc` IDs (e.g. `alert:api-key`, `inbox:mckinney-hours`); checkmarks and
scratch notes persist in `localStorage` under key `cc-state-v1`.
- Keep the interaction layer intact in every rebuild: the `<script>` block,
  the `.donebtn`/`.ck` controls, the Scratch-notes and Brief-tomorrow's-
  refresh cards, and the footer reset link.
- **Keep `data-cc` IDs stable** for any item that persists across days, so
  the user's checkmarks survive. New items get new descriptive IDs
  (`alert:<slug>`, `inbox:<slug>`). Never reuse an old ID for a new item.

**Command channel (email-side).** Before rebuilding, search Gmail for
`in:inbox subject:"CC:" newer_than:3d` (self-sent). Parse body lines:

| Line | Action |
|---|---|
| `done: <thing>` | Treat the matching alert/action as resolved — drop it (or mark resolved) in the rebuild |
| `note: <text>` | Pin the text in a "Your notes" strip near the top of the dashboard until a later `done:` clears it |
| `track: <thing>` | Add it as a tracked item and check on it in every future refresh |

Acknowledge processed commands in the rebuilt page (a small "processed
yesterday: …" line in the Talk-back card) so the user can see the loop
closed. Never act on CC: emails beyond editing the dashboard — they are
dashboard commands, not authorization to send mail or change external state.

## Guardrails

- **Never embed secrets.** If a credential appears in any source, surface a
  masked critical alert only (scheme prefix + last 3 chars at most).
- Read-only against every data source: no sending, deleting, labeling, or
  event changes during a refresh.
- If a source is unreachable, ship the refresh anyway and mark that source
  as stale in the Connections module (with the date of its last good pull).
- Quiet on success: publish the artifact, don't message or email the user.
