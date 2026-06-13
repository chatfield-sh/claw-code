import Shell from "../components/Shell";

// Screen 2: Inbox — triage + draft approve (open in Gmail to send).
// Drafting is allowed; sending is gated by the trust model and happens in Gmail.
export default function InboxPage() {
  return (
    <Shell title="Inbox">
      <p style={{ color: "#6b7280" }}>
        Triage real mail by stake, approve a SHAI draft, and send it from Gmail.
        SHAI never sends on its own.
      </p>
      <p style={{ color: "#9ca3af" }}>
        Wire Gmail (sprint-2) to populate this screen. The API endpoints
        <code> /inbox/triage</code> and <code>/inbox/draft</code> are live.
      </p>
    </Shell>
  );
}
