# SHAI Core — web

Next.js (App Router) frontend. Six screens, none industry-specific; only the
Insights screen is module-driven.

```bash
npm install
npm run dev   # http://localhost:3000
```

Set `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`) to point at the API.

| Route | Screen |
| --- | --- |
| `/` | Brief (home) |
| `/inbox` | Inbox — triage + draft approve |
| `/tasks` | Tasks — ranked by weight |
| `/insights` | Insights — active module returns the read |
| `/initiatives` | Initiatives — advice → tasks |
| `/notebook` | Notebook — meetings + knowledge |

Styling is intentionally minimal inline CSS — swap for your design system later.
