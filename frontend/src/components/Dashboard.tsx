import { useEffect, useState } from "react";
import { api } from "../api";
import type { Summary } from "../types";

function MetricCard({ value, label }: { value: number; label: string }) {
  return (
    <div className="card" role="group" aria-label={`${label}: ${value}`}>
      <div className="value" aria-hidden="true">
        {value}
      </div>
      <div className="label" aria-hidden="true">
        {label}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.summary().then(setSummary).catch((e) => setError(String(e)));
  }, []);

  if (error)
    return (
      <p className="error" role="alert">
        {error}
      </p>
    );
  if (!summary)
    return (
      <p className="muted" role="status" aria-live="polite">
        Loading summary...
      </p>
    );

  return (
    <div>
      <h2 className="sr-only">Case summary metrics</h2>
      <div className="cards">
        <MetricCard value={summary.total_cases} label="Total cases" />
        <MetricCard value={summary.open_cases} label="Open cases" />
        <MetricCard value={summary.closed_cases} label="Closed cases" />
        <MetricCard value={summary.total_gaps_found} label="ALCOA+ gaps found" />
        <MetricCard value={summary.total_capas} label="Total CAPAs" />
        <MetricCard value={summary.open_capas} label="Open CAPAs" />
      </div>
      <p className="muted">{summary.data_boundary}</p>
    </div>
  );
}
