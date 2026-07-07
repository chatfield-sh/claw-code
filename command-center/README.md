# Command Center

A single-file personal dashboard for Chris Chatfield (Area Manager, Superhost
Hospitality): calendar load and agenda, STR portfolio pulse, inbox triage,
travel schedule, dev-desk status for this repo, and an alert band for anything
that needs action.

## What it is

`index.html` is a self-contained snapshot — no build step, no dependencies, no
network calls. Open it in any browser. It supports light and dark themes via
`prefers-color-scheme`.

The data inside is a point-in-time pull (see the masthead timestamp) from:

- **Gmail** — important inbox threads
- **Google Calendar** — events, stays, and conflicts
- **GitHub** — PRs, issues, and commits for `chatfield-sh/claw-code`

## Refreshing it

The snapshot does not update itself. To refresh, open a Claude Code session on
this repo and say:

> refresh my command center

Claude re-pulls the same sources, regenerates `index.html` with current data,
and commits the result. Connecting Google Drive and Zoom in an interactive
session adds two more modules (recent files, meeting recaps).

## Design notes

- Palette: warm paper ground, pine accent, brass labels; status colors follow
  the validated data-viz palette (chart marks `#1e8a5e` light / `#35a97a`
  dark, both ≥3:1 on their surfaces).
- Type: serif masthead, system sans UI, monospace tabular figures for times.
- No secrets are ever embedded — credentials found in source data are surfaced
  as masked alerts only.
