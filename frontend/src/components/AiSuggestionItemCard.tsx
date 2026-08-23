import { useState } from "react";

const ATTRIBUTES = ["Attributable", "Legible", "Contemporaneous", "Original", "Accurate", "Complete", "Consistent", "Enduring", "Available"];
const RISKS = ["low", "medium", "high"];
type Action = "accepted" | "modified" | "rejected";

type Item = {
  item_index: number;
  original: { attribute: string; risk_level: string; rationale: string };
  review: null | {
    action: Action;
    final_attribute: string;
    final_risk_level: string;
    final_rationale: string;
    reviewer_comment: string | null;
    reviewed_by: string;
    reviewed_at: string;
  };
};

type Props = {
  item: Item;
  onReview: (itemIndex: number, body: {
    action: Action; final_attribute: string; final_risk_level: string;
    final_rationale: string; reviewer_comment?: string; reviewed_by: string;
  }) => Promise<void>;
};

export default function AiSuggestionItemCard({ item, onReview }: Props) {
  const [attribute, setAttribute] = useState(item.original.attribute);
  const [risk, setRisk] = useState(item.original.risk_level);
  const [rationale, setRationale] = useState(item.original.rationale);
  const [reviewer, setReviewer] = useState("");
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (item.review) {
    return <article className="section"><h3>{item.review.final_attribute}</h3><p><span className="badge ok">{item.review.action}</span> Reviewed by {item.review.reviewed_by}</p><p>{item.review.final_rationale}</p>{item.review.reviewer_comment && <p className="muted">Comment: {item.review.reviewer_comment}</p>}</article>;
  }

  async function submit(action: Action) {
    setError(null);
    if (reviewer.trim().length < 2) return setError("Reviewer name must contain at least 2 characters.");
    if ((action === "modified" || action === "rejected") && comment.trim().length === 0) return setError("A reviewer comment is required when modifying or rejecting a suggestion.");
    setSaving(true);
    try {
      await onReview(item.item_index, { action, final_attribute: attribute, final_risk_level: risk, final_rationale: rationale, reviewer_comment: comment || undefined, reviewed_by: reviewer });
    } catch (err) { setError(String(err)); } finally { setSaving(false); }
  }

  return <article className="section" aria-labelledby={`ai-item-${item.item_index}`}>
    <h3 id={`ai-item-${item.item_index}`}>AI suggestion {item.item_index + 1}</h3>
    <p className="muted">Original AI suggestion: {item.original.attribute} · {item.original.risk_level}</p>
    <form onSubmit={(event) => event.preventDefault()} aria-busy={saving}>
      <fieldset><legend>Edit and review suggestion</legend>
        <label htmlFor={`attribute-${item.item_index}`}>ALCOA+ attribute</label>
        <select id={`attribute-${item.item_index}`} value={attribute} onChange={(e) => setAttribute(e.target.value)}>{ATTRIBUTES.map((value) => <option key={value}>{value}</option>)}</select>
        <label htmlFor={`risk-${item.item_index}`}>Risk level</label>
        <select id={`risk-${item.item_index}`} value={risk} onChange={(e) => setRisk(e.target.value)}>{RISKS.map((value) => <option key={value}>{value}</option>)}</select>
        <label htmlFor={`rationale-${item.item_index}`}>Human-reviewed rationale</label>
        <textarea id={`rationale-${item.item_index}`} value={rationale} onChange={(e) => setRationale(e.target.value)} minLength={5} required rows={3} />
        <label htmlFor={`reviewer-${item.item_index}`}>Reviewer name</label>
        <input id={`reviewer-${item.item_index}`} value={reviewer} onChange={(e) => setReviewer(e.target.value)} minLength={2} required />
        <label htmlFor={`comment-${item.item_index}`}>Reviewer comment (required for modify or reject)</label>
        <textarea id={`comment-${item.item_index}`} value={comment} onChange={(e) => setComment(e.target.value)} rows={2} />
        {error && <p className="error" role="alert">{error}</p>}
        <div className="filters"><button type="button" className="primary" disabled={saving} onClick={() => submit("accepted")}>Accept</button><button type="button" className="primary" disabled={saving} onClick={() => submit("modified")}>Save modified</button><button type="button" className="link" disabled={saving} onClick={() => submit("rejected")}>Reject</button></div>
        <p className="muted" role="status">{saving ? "Saving human review..." : "AI suggestions do not modify records automatically."}</p>
      </fieldset>
    </form>
  </article>;
}
