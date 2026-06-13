"use client";

import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { apiGet, apiPost } from "../../lib/api";

type Task = {
  id?: string;
  title: string;
  weight: number;
  status: string;
  due?: string | null;
};

const STATUS_COLOR: Record<string, string> = {
  open: "#1F4E79",
  doing: "#B7791F",
  blocked: "#C53030",
  done: "#9ca3af",
};

// Screen 3: Tasks — ranked by weight; create + mark done against the live API.
export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [weight, setWeight] = useState(10);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setTasks(await apiGet<Task[]>("/tasks"));
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function add() {
    if (!title.trim()) return;
    setBusy(true);
    try {
      await apiPost("/tasks", { title, weight, status: "open" });
      setTitle("");
      setWeight(10);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function markDone(id?: string) {
    if (!id) return;
    await apiPost(`/tasks/${id}/status`, { status: "done" });
    await load();
  }

  return (
    <Shell title="Tasks">
      <div style={{ display: "flex", gap: 8, marginBottom: 16, maxWidth: 560 }}>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder="New task…"
          style={{ flex: 1, padding: 8 }}
        />
        <input
          type="number"
          value={weight}
          onChange={(e) => setWeight(Number(e.target.value))}
          title="weight"
          style={{ width: 72, padding: 8 }}
        />
        <button onClick={add} disabled={busy} style={{ padding: "8px 16px" }}>
          Add
        </button>
      </div>

      {error && <p style={{ color: "#C53030" }}>API unreachable — start it with <code>make api</code>.</p>}

      {tasks.length === 0 ? (
        <p style={{ color: "#9ca3af" }}>No tasks yet.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, maxWidth: 560 }}>
          {tasks.map((t) => (
            <li
              key={t.id ?? t.title}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "8px 12px",
                borderBottom: "1px solid #eee",
                opacity: t.status === "done" ? 0.55 : 1,
              }}
            >
              <span style={{ width: 36, color: "#6b7280", fontVariantNumeric: "tabular-nums" }}>
                {t.weight}
              </span>
              <span style={{ flex: 1, textDecoration: t.status === "done" ? "line-through" : "none" }}>
                {t.title}
              </span>
              <span style={{ color: STATUS_COLOR[t.status] ?? "#374151", fontSize: 13 }}>
                {t.status}
              </span>
              {t.status !== "done" && t.id && (
                <button onClick={() => markDone(t.id)} style={{ fontSize: 12 }}>
                  Done
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </Shell>
  );
}
