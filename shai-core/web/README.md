# SHAI Core — web

Next.js (App Router) frontend. Six screens, none industry-specific; only the
Insights screen is module-driven.

```bash
npm install
npm run dev   # http://localhost:3000
```

Set `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`) to point at the API.

| Route | Screen | Live API calls |
| --- | --- | --- |
| `/` | Brief (home) | `GET /brief` |
| `/inbox` | Inbox — triage + draft (never sends) | `POST /inbox/triage`, `POST /inbox/draft` |
| `/tasks` | Tasks — ranked by weight | `GET/POST /tasks`, `POST /tasks/{id}/status` |
| `/insights` | Insights — active module returns the read | `POST /insights/analyze` |
| `/initiatives` | Initiatives — advice → tasks | `GET/POST /initiatives`, `POST /initiatives/advise` |
| `/notebook` | Notebook — meetings + knowledge | `POST /notebook/meeting`, `POST /notebook/ask` |

All six screens are wired to the API (`lib/api.ts`) and degrade gracefully when
it is unreachable. Styling is intentionally minimal inline CSS — swap for your
design system later.

```bash
npm run build   # type-checks (strict) + lints all routes
```
