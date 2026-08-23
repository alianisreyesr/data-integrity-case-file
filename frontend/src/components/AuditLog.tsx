import { useEffect, useState } from "react";
import { api } from "../api";
import type { AuditEntry } from "../types";

export default function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [caseFilter, setCaseFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = caseFilter ? Number(caseFilter) : undefined;
    api.auditLog(id).then(setEntries).catch((e) => setError(String(e)));
  }, [caseFilter]);

  return (
    <div>
      <div className="filters">
        <label htmlFor="case-filter">Filter by case ID</label>
        <input
          id="case-filter"
          value={caseFilter}
          onChange={(e) => setCaseFilter(e.target.value)}
          placeholder="e.g. 1"
          style={{ maxWidth: "120px" }}
          inputMode="numeric"
        />
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <h2 className="sr-only">Audit log entries</h2>
      <ul className="timeline" aria-live="polite">
        {entries.map((entry) => (
          <li key={entry.id}>
            <span className="actor">{entry.actor}</span> {entry.action}
            {entry.detail ? ` — ${entry.detail}` : ""}
            <div className="time">
              {entry.case_id ? `Case #${entry.case_id} · ` : ""}
              <time dateTime={entry.created_at}>{new Date(entry.created_at).toISOString()}</time>
            </div>
          </li>
        ))}
      </ul>
      {entries.length === 0 && <p className="muted">No audit entries match this filter.</p>}
    </div>
  );
}
