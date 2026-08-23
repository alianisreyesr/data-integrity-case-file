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

  if (error)
    return (
      <p className="error" role="alert">
        {error}
      </p>
    );
  if (!caseData)
    return (
      <p className="muted" role="status" aria-live="polite">
        Loading case...
      </p>
    );

  return (
    <div>
      <button type="button" className="link" onClick={onBack}>
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
          <caption className="sr-only">ALCOA+ attribute assessments recorded for this case</caption>
          <thead>
            <tr>
              <th scope="col">Attribute</th>
              <th scope="col">Gap found</th>
              <th scope="col">Observation</th>
              <th scope="col">Assessed by</th>
            </tr>
          </thead>
          <tbody>
            {gaps.map((g) => (
              <tr key={g.id}>
                <th scope="row">{g.attribute}</th>
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
        <form onSubmit={submitGap} style={{ marginTop: "1rem" }} aria-label="Record ALCOA+ gap assessment">
          <fieldset>
            <legend>Record gap assessment</legend>
            <div>
              <label htmlFor="gap-attribute">Attribute</label>
              <select id="gap-attribute" value={gapAttribute} onChange={(e) => setGapAttribute(e.target.value)}>
                {ALCOA_ATTRIBUTES.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="gap-found">
                <input
                  id="gap-found"
                  type="checkbox"
                  checked={gapFound}
                  onChange={(e) => setGapFound(e.target.checked)}
                  style={{ width: "auto", marginRight: "0.4rem" }}
                />
                Gap found
              </label>
            </div>
            <div>
              <label htmlFor="gap-observation">Observation</label>
              <textarea
                id="gap-observation"
                value={gapObservation}
                onChange={(e) => setGapObservation(e.target.value)}
                rows={2}
              />
            </div>
            <div>
              <label htmlFor="gap-assessor">Assessed by</label>
              <input
                id="gap-assessor"
                value={gapAssessor}
                onChange={(e) => setGapAssessor(e.target.value)}
                required
                minLength={2}
              />
            </div>
            <button className="primary" type="submit">
              Record gap assessment
            </button>
          </fieldset>
        </form>
      </div>

      <div className="section">
        <h2>Evidence log</h2>
        <table>
          <caption className="sr-only">Evidence entries recorded for this case</caption>
          <thead>
            <tr>
              <th scope="col">Type</th>
              <th scope="col">Description</th>
              <th scope="col">Recorded by</th>
            </tr>
          </thead>
          <tbody>
            {evidence.map((ev) => (
              <tr key={ev.id}>
                <th scope="row">{ev.evidence_type}</th>
                <td>{ev.description}</td>
                <td>{ev.recorded_by}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {evidence.length === 0 && <p className="muted">No evidence recorded yet.</p>}
        <form onSubmit={submitEvidence} style={{ marginTop: "1rem" }} aria-label="Add evidence entry">
          <fieldset>
            <legend>Add evidence</legend>
            <div>
              <label htmlFor="evidence-type">Evidence type</label>
              <select id="evidence-type" value={evidenceType} onChange={(e) => setEvidenceType(e.target.value)}>
                {EVIDENCE_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="evidence-description">Description</label>
              <textarea
                id="evidence-description"
                value={evidenceDescription}
                onChange={(e) => setEvidenceDescription(e.target.value)}
                rows={2}
                required
                minLength={5}
              />
            </div>
            <div>
              <label htmlFor="evidence-recorder">Recorded by</label>
              <input
                id="evidence-recorder"
                value={evidenceRecorder}
                onChange={(e) => setEvidenceRecorder(e.target.value)}
                required
                minLength={2}
              />
            </div>
            <button className="primary" type="submit">
              Add evidence
            </button>
          </fieldset>
        </form>
      </div>

      <div className="section">
        <h2>CAPAs</h2>
        <table>
          <caption className="sr-only">Corrective and preventive actions recorded for this case</caption>
          <thead>
            <tr>
              <th scope="col">Reference</th>
              <th scope="col">Type</th>
              <th scope="col">Description</th>
              <th scope="col">Owner</th>
              <th scope="col">Due date</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {capas.map((c) => (
              <tr key={c.id}>
                <th scope="row">{c.capa_ref}</th>
                <td>{c.action_type}</td>
                <td>{c.description}</td>
                <td>{c.owner}</td>
                <td>
                  <time dateTime={c.due_date}>{c.due_date}</time>
                </td>
                <td>
                  <span className={`badge ${c.status === "closed" ? "closed" : "open"}`}>{c.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {capas.length === 0 && <p className="muted">No CAPAs recorded yet.</p>}
        <form onSubmit={submitCapa} style={{ marginTop: "1rem" }} aria-label="Add CAPA">
          <fieldset>
            <legend>Add CAPA</legend>
            <div>
              <label htmlFor="capa-type">Action type</label>
              <select
                id="capa-type"
                value={capaType}
                onChange={(e) => setCapaType(e.target.value as "corrective" | "preventive")}
              >
                <option value="corrective">corrective</option>
                <option value="preventive">preventive</option>
              </select>
            </div>
            <div>
              <label htmlFor="capa-description">Description</label>
              <textarea
                id="capa-description"
                value={capaDescription}
                onChange={(e) => setCapaDescription(e.target.value)}
                rows={2}
                required
                minLength={10}
              />
            </div>
            <div>
              <label htmlFor="capa-owner">Owner</label>
              <input id="capa-owner" value={capaOwner} onChange={(e) => setCapaOwner(e.target.value)} required minLength={2} />
            </div>
            <div>
              <label htmlFor="capa-due-date">Due date</label>
              <input
                id="capa-due-date"
                type="date"
                value={capaDueDate}
                onChange={(e) => setCapaDueDate(e.target.value)}
                required
              />
            </div>
            <button className="primary" type="submit">
              Add CAPA
            </button>
          </fieldset>
        </form>
      </div>
    </div>
  );
}
