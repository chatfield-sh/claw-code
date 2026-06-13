"use client";

import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { apiGet, apiPost } from "../../lib/api";

type Initiative = { id?: string; name: string; goal?: string | null; status?: string };
type Advice = { advice: string; next_steps: { title: string }[] };

// Screen 5: Initiatives — one card per initiative; advice spins off next-step tasks.
export default function InitiativesPage() {
  const [items, setItems] = useState<Initiative[]>([]);
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const r = await apiGet<{ initiatives: Initiative[] }>("/initiatives");
      setItems(r.initiatives);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function create() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      await apiPost("/initiatives", { name, goal });
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function advise() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      setAdvice(await apiPost<Advice>("/initiatives/advise", { name, goal }));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell title="Initiatives">
      <div style={{ display: "grid", gap: 8, maxWidth: 560 }}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Initiative name" style={{ padding: 8 }} />
        <input value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="Goal" style={{ padding: 8 }} />
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={create} disabled={busy}>Create</button>
          <button onClick={advise} disabled={busy}>Advise → tasks</button>
        </div>
      </div>

      {error && <p style={{ color: "#C53030" }}>API unreachable — start it with <code>make api</code>.</p>}

      {advice && (
        <div style={{ marginTop: 16, padding: 16, border: "1px solid #e5e7eb", borderRadius: 8, maxWidth: 560 }}>
          <p style={{ marginTop: 0 }}>{advice.advice}</p>
          {advice.next_steps.length > 0 && (
            <>
              <strong>Spun-off next steps:</strong>
              <ul>{advice.next_steps.map((t, i) => <li key={i}>{t.title}</li>)}</ul>
            </>
          )}
        </div>
      )}

      <h3 style={{ marginTop: 24 }}>Active initiatives</h3>
      {items.length === 0 ? (
        <p style={{ color: "#9ca3af" }}>None yet.</p>
      ) : (
        <div style={{ display: "grid", gap: 8, maxWidth: 560 }}>
          {items.map((it) => (
            <div key={it.id ?? it.name} style={{ padding: 12, border: "1px solid #eee", borderRadius: 8 }}>
              <div style={{ fontWeight: 600 }}>{it.name}</div>
              {it.goal && <div style={{ color: "#6b7280", fontSize: 14 }}>{it.goal}</div>}
            </div>
          ))}
        </div>
      )}
    </Shell>
  );
}
