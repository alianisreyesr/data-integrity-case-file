import { useEffect, useState } from "react";
import { api } from "../api";
import type { CaseOut } from "../types";

interface Props {
  onSelect: (id: number) => void;
}

const STATUSES = ["", "intake", "alcoa_assessment", "investigation", "capa_formulation", "closed"];

export default function CaseList({ onSelect }: Props) {
  const [cases, setCases] = useState<CaseOut[]>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listCases(status || undefined)
      .then(setCases)
      .catch((e) => setError(String(e)));
  }, [status]);

  return (
    <div>
      <div className="filters">
        <label htmlFor="status-filter">Filter by status</label>
        <select id="status-filter" value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s === "" ? "All statuses" : s}
            </option>
          ))}
        </select>
      </div>
      {error && <p className="error">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Reference</th>
            <th>Title</th>
            <th>System</th>
            <th>Signal type</th>
            <th>Status</th>
            <th>Opened by</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.id} onClick={() => onSelect(c.id)}>
              <td>{c.case_ref}</td>
              <td>{c.title}</td>
              <td>{c.system}</td>
              <td>{c.signal_type}</td>
              <td>
                <span className={`badge ${c.status === "closed" ? "closed" : "open"}`}>{c.status}</span>
              </td>
              <td>{c.opened_by}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {cases.length === 0 && <p className="muted">No cases match this filter.</p>}
    </div>
  );
}
