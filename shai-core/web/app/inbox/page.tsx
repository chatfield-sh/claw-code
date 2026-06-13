"use client";

import { useState } from "react";
import Shell from "../components/Shell";
import { apiPost } from "../../lib/api";

type DraftResult = { draft: string; status: string; gmail_draft_id: string | null; sendable: boolean };

// Screen 2: Inbox — triage by stake + draft a reply. SHAI never sends: drafts go
// to Gmail Drafts (when connected) for you to approve and send.
export default function InboxPage() {
  const [sender, setSender] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [stake, setStake] = useState<number | null>(null);
  const [draft, setDraft] = useState<DraftResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(kind: "triage" | "draft") {
    setBusy(true);
    setError(null);
    try {
      if (kind === "triage") {
        const r = await apiPost<{ stake: number }>("/inbox/triage", { sender, subject, body });
        setStake(r.stake);
      } else {
        setDraft(await apiPost<DraftResult>("/inbox/draft", { sender, subject, body }));
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell title="Inbox">
      <p style={{ color: "#6b7280", marginTop: 0 }}>
        Triage by stake, then draft a reply. <strong>SHAI never sends</strong> — drafts land in
        Gmail Drafts for you to approve.
      </p>

      <div style={{ display: "grid", gap: 8, maxWidth: 560 }}>
        <input value={sender} onChange={(e) => setSender(e.target.value)} placeholder="From (email)" style={{ padding: 8 }} />
        <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Subject" style={{ padding: 8 }} />
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={6} placeholder="Paste the email body…" style={{ padding: 8 }} />
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => run("triage")} disabled={busy}>Triage</button>
          <button onClick={() => run("draft")} disabled={busy}>Draft reply</button>
        </div>
      </div>

      {error && <p style={{ color: "#C53030" }}>API unreachable — start it with <code>make api</code>.</p>}

      {stake !== null && (
        <p style={{ marginTop: 16 }}>
          <strong>Stake:</strong> {stake.toFixed(0)} / 100
        </p>
      )}

      {draft && (
        <div style={{ marginTop: 12, padding: 16, border: "1px solid #e5e7eb", borderRadius: 8, maxWidth: 560 }}>
          <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 8 }}>
            Status: {draft.status}
            {draft.gmail_draft_id ? ` · Gmail draft ${draft.gmail_draft_id}` : ""} · sendable: {String(draft.sendable)}
          </div>
          <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", margin: 0 }}>{draft.draft}</pre>
        </div>
      )}
    </Shell>
  );
}
