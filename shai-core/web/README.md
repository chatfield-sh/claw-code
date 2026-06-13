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
| `/settings` | Settings — edit role/goals/comms that drive prompting | `GET/PUT /profile` |

All screens are wired to the API (`lib/api.ts`) and degrade gracefully when it
is unreachable. Styling is intentionally minimal inline CSS — swap for your
design system later.

## Auth (Clerk, optional)

Set `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` to enable Clerk: the app wraps in
`ClerkProvider`, shows sign-in / user-button chrome, and `lib/api.ts` attaches
the Clerk session token as a bearer so the API resolves the real user. Without
the key, the app runs un-authed against the API's dev identity — and the
production build still succeeds (the provider is gated off).

```bash
npm run build   # type-checks (strict) + lints all routes
```
