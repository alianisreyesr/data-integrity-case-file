import { useEffect, useState } from "react";
import { api } from "../api";
import {
  ALCOA_ATTRIBUTES,
  EVIDENCE_TYPES,
  type AlcoaGapOut,
  type CaseOut,
  type CapaOut,
  type EvidenceOut,
} from "../types";

interface Props {
  caseId: number;
  onBack: () => void;
}

export default function CaseDetail({ caseId, onBack }: Props) {
  const [caseData, setCaseData] = useState<CaseOut | null>(null);
  const [gaps, setGaps] = useState<AlcoaGapOut[]>([]);
  const [evidence, setEvidence] = useState<EvidenceOut[]>([]);
  const [capas, setCapas] = useState<CapaOut[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [gapAttribute, setGapAttribute] = useState<string>(ALCOA_ATTRIBUTES[0]);
  const [gapFound, setGapFound] = useState(false);
  const [gapObservation, setGapObservation] = useState("");
  const [gapAssessor, setGapAssessor] = useState("");

  const [evidenceType, setEvidenceType] = useState<string>(EVIDENCE_TYPES[0]);
  const [evidenceDescription, setEvidenceDescription] = useState("");
  const [evidenceRecorder, setEvidenceRecorder] = useState("");

  const [capaType, setCapaType] = useState<"corrective" | "preventive">("corrective");
  const [capaDescription, setCapaDescription] = useState("");
  const [capaOwner, setCapaOwner] = useState("");
  const [capaDueDate, setCapaDueDate] = useState("");

  function refresh() {
    api.getCase(caseId).then(setCaseData).catch((e) => setError(String(e)));
    api.listGaps(caseId).then(setGaps).catch((e) => setError(String(e)));
    api.listEvidence(caseId).then(setEvidence).catch((e) => setError(String(e)));
    api.listCapas(caseId).then(setCapas).catch((e) => setError(String(e)));
  }

  useEffect(refresh, [caseId]);

  async function submitGap(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.addGap(
        caseId,
        { attribute: gapAttribute, gap_found: gapFound, observation: gapObservation, assessed_by: gapAssessor },
        gapAssessor || "portfolio_user"
      );
      setGapObservation("");
      setGapAssessor("");
      refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  async function submitEvidence(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.addEvidence(
        caseId,
        { evidence_type: evidenceType, description: evidenceDescription, recorded_by: evidenceRecorder },
        evidenceRecorder || "portfolio_user"
      );
      setEvidenceDescription("");
      setEvidenceRecorder("");
      refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  async function submitCapa(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.addCapa(
        caseId,
        { action_type: capaType, description: capaDescription, owner: capaOwner, due_date: capaDueDate },
        capaOwner || "portfolio_user"
      );
      setCapaDescription("");
      setCapaOwner("");
      setCapaDueDate("");
      refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!caseData) return <p className="muted">Loading case...</p>;

  return (
    <div>
      <button className="link" onClick={onBack}>
        Back to cases
      </button>
      <h2 style={{ marginTop: "0.8rem" }}>
        {caseData.case_ref} - {caseData.title}
      </h2>
      <p className="muted">
        System: {caseData.system} | Signal: {caseData.signal_type} | Status: {caseData.status} | Opened by:{" "}
        {caseData.opened_by}
      </p>

      <div className="section">
        <h2>ALCOA+ gap matrix</h2>
        <table>
          <thead>
            <tr>
              <th>Attribute</th>
              <th>Gap found</th>
              <th>Observation</th>
              <th>Assessed by</th>
            </tr>
          </thead>
          <tbody>
            {gaps.map((g) => (
              <tr key={g.id}>
                <td>{g.attribute}</td>
                <td>
                  <span className={`badge ${g.gap_found ? "gap" : "ok"}`}>{g.gap_found ? "Gap" : "OK"}</span>
                </td>
                <td>{g.observation || "-"}</td>
                <td>{g.assessed_by}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {gaps.length === 0 && <p className="muted">No ALCOA+ assessment recorded yet.</p>}
        <form onSubmit={submitGap} style={{ marginTop: "1rem" }}>
          <div>
            <label>Attribute</label>
            <select value={gapAttribute} onChange={(e) => setGapAttribute(e.target.value)}>
              {ALCOA_ATTRIBUTES.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>
              <input
                type="checkbox"
                checked={gapFound}
                onChange={(e) => setGapFound(e.target.checked)}
                style={{ width: "auto", marginRight: "0.4rem" }}
              />
              Gap found
            </label>
          </div>
          <div>
            <label>Observation</label>
            <textarea value={gapObservation} onChange={(e) => setGapObservation(e.target.value)} rows={2} />
          </div>
          <div>
            <label>Assessed by</label>
            <input value={gapAssessor} onChange={(e) => setGapAssessor(e.target.value)} required minLength={2} />
          </div>
          <button className="primary" type="submit">
            Record gap assessment
          </button>
        </form>
      </div>

      <div className="section">
        <h2>Evidence log</h2>
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Description</th>
              <th>Recorded by</th>
            </tr>
          </thead>
          <tbody>
            {evidence.map((ev) => (
              <tr key={ev.id}>
                <td>{ev.evidence_type}</td>
                <td>{ev.description}</td>
                <td>{ev.recorded_by}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {evidence.length === 0 && <p className="muted">No evidence recorded yet.</p>}
        <form onSubmit={submitEvidence} style={{ marginTop: "1rem" }}>
          <div>
            <label>Evidence type</label>
            <select value={evidenceType} onChange={(e) => setEvidenceType(e.target.value)}>
              {EVIDENCE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>Description</label>
            <textarea
              value={evidenceDescription}
              onChange={(e) => setEvidenceDescription(e.target.value)}
              rows={2}
              required
              minLength={5}
            />
          </div>
          <div>
            <label>Recorded by</label>
            <input value={evidenceRecorder} onChange={(e) => setEvidenceRecorder(e.target.value)} required minLength={2} />
          </div>
          <button className="primary" type="submit">
            Add evidence
          </button>
        </form>
      </div>

      <div className="section">
        <h2>CAPAs</h2>
        <table>
          <thead>
            <tr>
              <th>Reference</th>
              <th>Type</th>
              <th>Description</th>
              <th>Owner</th>
              <th>Due date</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {capas.map((c) => (
              <tr key={c.id}>
                <td>{c.capa_ref}</td>
                <td>{c.action_type}</td>
                <td>{c.description}</td>
                <td>{c.owner}</td>
                <td>{c.due_date}</td>
                <td>
                  <span className={`badge ${c.status === "closed" ? "closed" : "open"}`}>{c.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {capas.length === 0 && <p className="muted">No CAPAs recorded yet.</p>}
        <form onSubmit={submitCapa} style={{ marginTop: "1rem" }}>
          <div>
            <label>Action type</label>
            <select value={capaType} onChange={(e) => setCapaType(e.target.value as "corrective" | "preventive")}>
              <option value="corrective">corrective</option>
              <option value="preventive">preventive</option>
            </select>
          </div>
          <div>
            <label>Description</label>
            <textarea
              value={capaDescription}
              onChange={(e) => setCapaDescription(e.target.value)}
              rows={2}
              required
              minLength={10}
            />
          </div>
          <div>
            <label>Owner</label>
            <input value={capaOwner} onChange={(e) => setCapaOwner(e.target.value)} required minLength={2} />
          </div>
          <div>
            <label>Due date</label>
            <input type="date" value={capaDueDate} onChange={(e) => setCapaDueDate(e.target.value)} required />
          </div>
          <button className="primary" type="submit">
            Add CAPA
          </button>
        </form>
      </div>
    </div>
  );
}
