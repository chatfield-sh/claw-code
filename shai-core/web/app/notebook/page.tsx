import Shell from "../components/Shell";

// Screen 6: Notebook — meetings + knowledge; process notes; ask-your-knowledge.
export default function NotebookPage() {
  return (
    <Shell title="Notebook">
      <p style={{ color: "#6b7280" }}>
        Paste meeting notes for summary, decisions, and action items. Drop notes
        to embed and recall on demand.
      </p>
      <p style={{ color: "#9ca3af" }}>
        The API endpoints <code>/notebook/meeting</code> and
        <code> /notebook/ask</code> are live. Embeddings land in sprint-4.
      </p>
    </Shell>
  );
}
