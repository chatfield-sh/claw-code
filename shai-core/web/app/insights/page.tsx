"use client";

import { useState } from "react";
import Shell from "../components/Shell";
import { apiPost } from "../../lib/api";

type Insight = {
  headline: string;
  narrative: string;
  impact: number | null;
  impact_unit: string | null;
  action: string | null;
  severity: "green" | "amber" | "red";
};

const SEVERITY_COLOR: Record<string, string> = {
  green: "#2E7D32",
  amber: "#B7791F",
  red: "#C53030",
};

// Screen 4: Insights — paste any structured data; the active module returns the read.
// This is the only screen that changes when a vertical module is loaded.
export default function InsightsPage() {
  const [raw, setRaw] = useState("metric,value\nrevenue,1200\ncost,800");
  const [label, setLabel] = useState("Q2 numbers");
  const [insight, setInsight] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function analyze() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiPost<{ insight: Insight }>("/insights/analyze", {
        module_key: "generic",
        label,
        raw_input: raw,
      });
      setInsight(res.insight);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Shell title="Insights — generic module">
      <input
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        placeholder="Label"
        style={{ display: "block", marginBottom: 8, padding: 6, width: 320 }}
      />
      <textarea
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        rows={8}
        style={{ width: "100%", maxWidth: 520, fontFamily: "monospace", padding: 8 }}
      />
      <div style={{ marginTop: 8 }}>
        <button onClick={analyze} disabled={loading} style={{ padding: "8px 16px" }}>
          {loading ? "Analyzing…" : "Analyze"}
        </button>
      </div>

      {error && <p style={{ color: "#C53030" }}>{error}</p>}

      {insight && (
        <div style={{ marginTop: 24, padding: 16, border: "1px solid #e5e7eb", borderRadius: 8, maxWidth: 520 }}>
          <div style={{ color: SEVERITY_COLOR[insight.severity], fontWeight: 700 }}>
            {insight.headline}
          </div>
          <p>{insight.narrative}</p>
          {insight.impact != null && (
            <p><strong>Impact:</strong> {insight.impact}{insight.impact_unit ?? ""}</p>
          )}
          {insight.action && <p><strong>Action:</strong> {insight.action}</p>}
        </div>
      )}
    </Shell>
  );
}
