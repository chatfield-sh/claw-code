import Link from "next/link";
import type { ReactNode } from "react";

// The six-screen shell. Identical chrome across every screen; only screen 4
// ("Insights") is module-driven.
const SCREENS = [
  { href: "/", label: "Brief" },
  { href: "/inbox", label: "Inbox" },
  { href: "/tasks", label: "Tasks" },
  { href: "/insights", label: "Insights" },
  { href: "/initiatives", label: "Initiatives" },
  { href: "/notebook", label: "Notebook" },
];

export default function Shell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}>
      <nav style={{ width: 200, borderRight: "1px solid #e5e7eb", padding: "24px 16px" }}>
        <div style={{ fontWeight: 700, color: "#1F4E79", marginBottom: 24 }}>SHAI Core</div>
        <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 8 }}>
          {SCREENS.map((s) => (
            <li key={s.href}>
              <Link href={s.href} style={{ textDecoration: "none", color: "#374151" }}>
                {s.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <main style={{ flex: 1, padding: "32px 40px" }}>
        <h1 style={{ marginTop: 0 }}>{title}</h1>
        {children}
      </main>
    </div>
  );
}
