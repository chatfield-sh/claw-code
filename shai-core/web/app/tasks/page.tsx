import Shell from "../components/Shell";

// Screen 3: Tasks — ranked by weight; filter by owner/blocked.
export default function TasksPage() {
  return (
    <Shell title="Tasks">
      <p style={{ color: "#6b7280" }}>
        Context-rich tasks ranked by weight, captured from any source.
      </p>
      <p style={{ color: "#9ca3af" }}>
        The API endpoints <code>/tasks/rank</code> and <code>/tasks/extract</code>
        are live. Wire persistence (sprint-3) to list real tasks here.
      </p>
    </Shell>
  );
}
