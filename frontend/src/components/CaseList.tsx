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
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <table>
        <caption className="sr-only">
          Data integrity cases{status ? ` with status ${status}` : ""}. Activate a case reference to view its
          details.
        </caption>
        <thead>
          <tr>
            <th scope="col">Reference</th>
            <th scope="col">Title</th>
            <th scope="col">System</th>
            <th scope="col">Signal type</th>
            <th scope="col">Status</th>
            <th scope="col">Opened by</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.id}>
              <th scope="row">
                <button type="button" className="link" onClick={() => onSelect(c.id)}>
                  {c.case_ref}
                  <span className="sr-only"> — view case details</span>
                </button>
              </th>
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
