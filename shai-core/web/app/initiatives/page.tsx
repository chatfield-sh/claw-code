import Shell from "../components/Shell";

// Screen 5: Initiatives — one card per initiative; advice -> tasks.
export default function InitiativesPage() {
  return (
    <Shell title="Initiatives">
      <p style={{ color: "#6b7280" }}>
        One workspace per initiative. SHAI advises and spins off next-step tasks —
        for any venture, no vertical required.
      </p>
      <p style={{ color: "#9ca3af" }}>
        The API endpoint <code>/initiatives/advise</code> is live.
      </p>
    </Shell>
  );
}
