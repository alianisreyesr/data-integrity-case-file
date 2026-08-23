import { useState } from "react";
import { api } from "../api";
import { SIGNAL_TYPES } from "../types";

interface Props {
  onCreated: (id: number) => void;
}

export default function NewCaseForm({ onCreated }: Props) {
  const [title, setTitle] = useState("");
  const [system, setSystem] = useState("");
  const [signalType, setSignalType] = useState<string>(SIGNAL_TYPES[0]);
  const [openedBy, setOpenedBy] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await api.createCase(
        { title, system, signal_type: signalType, opened_by: openedBy },
        openedBy || "portfolio_user"
      );
      setTitle("");
      setSystem("");
      setOpenedBy("");
      onCreated(created.id);
    } catch (err) {
      setError(String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Create a new data integrity case" aria-busy={submitting}>
      <fieldset>
        <legend>New case details</legend>
        <div>
          <label htmlFor="title">Case title</label>
          <input id="title" value={title} onChange={(e) => setTitle(e.target.value)} required minLength={3} />
        </div>
        <div>
          <label htmlFor="system">System</label>
          <input id="system" value={system} onChange={(e) => setSystem(e.target.value)} required minLength={2} />
        </div>
        <div>
          <label htmlFor="signal-type">Signal type</label>
          <select id="signal-type" value={signalType} onChange={(e) => setSignalType(e.target.value)}>
            {SIGNAL_TYPES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="opened-by">Opened by</label>
          <input id="opened-by" value={openedBy} onChange={(e) => setOpenedBy(e.target.value)} required minLength={2} />
        </div>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button className="primary" type="submit" disabled={submitting}>
          {submitting ? "Creating..." : "Create case"}
        </button>
      </fieldset>
    </form>
  );
}
