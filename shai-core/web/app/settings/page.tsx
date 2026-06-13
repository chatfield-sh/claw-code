"use client";

import { useEffect, useState } from "react";
import Shell from "../components/Shell";
import { apiGet, apiPut } from "../../lib/api";

type Profile = {
  name: string | null;
  role: string | null;
  goals: string[];
  comms_style: string | null;
};

// Settings — edit the profile that drives role-aware prompting across every agent.
export default function SettingsPage() {
  const [role, setRole] = useState("");
  const [goals, setGoals] = useState("");
  const [comms, setComms] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function apply(p: Profile) {
    setRole(p.role ?? "");
    setGoals((p.goals ?? []).join("\n"));
    setComms(p.comms_style ?? "");
  }

  useEffect(() => {
    apiGet<Profile>("/profile").then(apply).catch((e) => setError(String(e)));
  }, []);

  async function save() {
    setStatus(null);
    setError(null);
    try {
      const updated = await apiPut<Profile>("/profile", {
        role,
        goals: goals.split("\n").map((g) => g.trim()).filter(Boolean),
        comms_style: comms,
      });
      apply(updated);
      setStatus("Saved. Every agent now prompts with this profile.");
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <Shell title="Settings">
      <p style={{ color: "#6b7280", marginTop: 0, maxWidth: 560 }}>
        These drive how SHAI thinks. The agents prompt as a <em>{role || "…"}</em> who
        values your stated goals — no industry is hardcoded.
      </p>

      <div style={{ display: "grid", gap: 12, maxWidth: 560 }}>
        <label>
          Role
          <input value={role} onChange={(e) => setRole(e.target.value)}
                 placeholder="founder, operator, RDO…" style={{ display: "block", width: "100%", padding: 8 }} />
        </label>
        <label>
          Goals (one per line)
          <textarea value={goals} onChange={(e) => setGoals(e.target.value)} rows={4}
                    style={{ display: "block", width: "100%", padding: 8 }} />
        </label>
        <label>
          Comms style
          <input value={comms} onChange={(e) => setComms(e.target.value)}
                 placeholder="direct, warm, concise" style={{ display: "block", width: "100%", padding: 8 }} />
        </label>
        <div>
          <button onClick={save} style={{ padding: "8px 16px" }}>Save profile</button>
        </div>
      </div>

      {status && <p style={{ color: "#2E7D32" }}>{status}</p>}
      {error && <p style={{ color: "#C53030" }}>API unreachable — start it with <code>make api</code>.</p>}
    </Shell>
  );
}
