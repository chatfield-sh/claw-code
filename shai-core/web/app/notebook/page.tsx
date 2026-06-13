"use client";

import { useState } from "react";
import Shell from "../components/Shell";
import { apiPost } from "../../lib/api";

type MeetingResult = {
  summary: string;
  decisions: string[];
  action_items: string[];
  follow_up: string;
};
type Recall = { results: { title?: string; body: string }[] };

// Screen 6: Notebook — meetings + knowledge. Process notes; ask-your-knowledge.
export default function NotebookPage() {
  const [notes, setNotes] = useState("");
  const [meeting, setMeeting] = useState<MeetingResult | null>(null);
  const [query, setQuery] = useState("");
  const [recall, setRecall] = useState<Recall | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function process() {
    if (!notes.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setMeeting(await apiPost<MeetingResult>("/notebook/meeting", { title: "Meeting", notes }));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function ask() {
    setBusy(true);
    setError(null);
    try {
      setRecall(await apiPost<Recall>("/notebook/ask", { query }));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell title="Notebook">
      <h3 style={{ marginTop: 0 }}>Process meeting notes</h3>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={6}
        placeholder="Paste notes or a transcript…"
        style={{ width: "100%", maxWidth: 560, padding: 8 }}
      />
      <div style={{ marginTop: 8 }}>
        <button onClick={process} disabled={busy}>Summarize</button>
      </div>

      {error && <p style={{ color: "#C53030" }}>API unreachable — start it with <code>make api</code>.</p>}

      {meeting && (
        <div style={{ marginTop: 12, padding: 16, border: "1px solid #e5e7eb", borderRadius: 8, maxWidth: 560 }}>
          <p style={{ marginTop: 0 }}>{meeting.summary}</p>
          {meeting.action_items?.length > 0 && (
            <>
              <strong>Action items</strong>
              <ul>{meeting.action_items.map((a, i) => <li key={i}>{a}</li>)}</ul>
            </>
          )}
          {meeting.follow_up && (
            <>
              <strong>Drafted follow-up</strong>
              <p style={{ color: "#374151" }}>{meeting.follow_up}</p>
            </>
          )}
        </div>
      )}

      <h3 style={{ marginTop: 28 }}>Ask your knowledge</h3>
      <div style={{ display: "flex", gap: 8, maxWidth: 560 }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Search your notes…"
          style={{ flex: 1, padding: 8 }}
        />
        <button onClick={ask} disabled={busy}>Ask</button>
      </div>
      {recall && (
        <ul style={{ maxWidth: 560 }}>
          {recall.results.length === 0 ? (
            <li style={{ color: "#9ca3af", listStyle: "none" }}>No matches.</li>
          ) : (
            recall.results.map((r, i) => (
              <li key={i}>
                {r.title ? <strong>{r.title}: </strong> : null}
                {r.body}
              </li>
            ))
          )}
        </ul>
      )}
    </Shell>
  );
}
