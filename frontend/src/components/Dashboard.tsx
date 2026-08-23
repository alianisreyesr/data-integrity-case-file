import { useEffect, useState } from "react";
import { api } from "../api";
import type { Summary } from "../types";

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.summary().then(setSummary).catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!summary) return <p className="muted">Loading summary...</p>;

  return (
    <div>
      <div className="cards">
        <div className="card">
          <div className="value">{summary.total_cases}</div>
          <div className="label">Total cases</div>
        </div>
        <div className="card">
          <div className="value">{summary.open_cases}</div>
          <div className="label">Open cases</div>
        </div>
        <div className="card">
          <div className="value">{summary.closed_cases}</div>
          <div className="label">Closed cases</div>
        </div>
        <div className="card">
          <div className="value">{summary.total_gaps_found}</div>
          <div className="label">ALCOA+ gaps found</div>
        </div>
        <div className="card">
          <div className="value">{summary.total_capas}</div>
          <div className="label">Total CAPAs</div>
        </div>
        <div className="card">
          <div className="value">{summary.open_capas}</div>
          <div className="label">Open CAPAs</div>
        </div>
      </div>
      <p className="muted">{summary.data_boundary}</p>
    </div>
  );
}
