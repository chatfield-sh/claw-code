import Shell from "./components/Shell";
import { apiGet } from "../lib/api";

type Brief = {
  headline: string;
  priorities: string[];
  calendar: string[];
  inbox_needs_you: string[];
  tasks_due: string[];
  risks: string[];
};

// Screen 1: Brief (home) — priorities, calendar, inbox-needs-you, risk radar.
export default async function BriefPage() {
  let brief: Brief | null = null;
  try {
    brief = await apiGet<Brief>("/brief");
  } catch {
    brief = null;
  }

  return (
    <Shell title="Brief">
      {brief ? (
        <>
          <p style={{ fontSize: 18 }}>{brief.headline}</p>
          <Section label="Priorities" items={brief.priorities} />
          <Section label="Calendar" items={brief.calendar} />
          <Section label="Inbox needs you" items={brief.inbox_needs_you} />
          <Section label="Tasks due" items={brief.tasks_due} />
          <Section label="Risk radar" items={brief.risks} />
        </>
      ) : (
        <p>Start the API (<code>make api</code>) to load your brief.</p>
      )}
    </Shell>
  );
}

function Section({ label, items }: { label: string; items: string[] }) {
  return (
    <section style={{ marginTop: 20 }}>
      <h3>{label}</h3>
      {items.length ? (
        <ul>{items.map((i) => <li key={i}>{i}</li>)}</ul>
      ) : (
        <p style={{ color: "#9ca3af" }}>Nothing here.</p>
      )}
    </section>
  );
}
