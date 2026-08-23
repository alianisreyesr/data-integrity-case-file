export interface CaseOut {
  id: number;
  case_ref: string;
  title: string;
  system: string;
  signal_type: string;
  status: string;
  opened_by: string;
  opened_at: string;
  closed_at?: string | null;
}

export interface CaseCreate {
  title: string;
  system: string;
  signal_type: string;
  opened_by: string;
}

export const SIGNAL_TYPES = [
  "audit_finding",
  "system_discrepancy",
  "user_access_anomaly",
  "data_gap",
  "process_deviation",
] as const;

export const ALCOA_ATTRIBUTES = [
  "Attributable",
  "Legible",
  "Contemporaneous",
  "Original",
  "Accurate",
  "Complete",
  "Consistent",
  "Enduring",
  "Available",
] as const;

export interface AlcoaGapOut {
  id: number;
  case_id: number;
  attribute: string;
  gap_found: boolean;
  observation: string | null;
  assessed_by: string;
  assessed_at: string;
}

export interface AlcoaGapCreate {
  attribute: string;
  gap_found: boolean;
  observation?: string;
  assessed_by: string;
}

export const EVIDENCE_TYPES = [
  "audit_trail_review",
  "technical_metadata",
  "access_log",
  "screenshot",
  "interview_note",
] as const;

export interface EvidenceOut {
  id: number;
  case_id: number;
  evidence_type: string;
  description: string;
  recorded_by: string;
  recorded_at: string;
}

export interface EvidenceCreate {
  evidence_type: string;
  description: string;
  recorded_by: string;
}

export interface CapaOut {
  id: number;
  case_id: number;
  capa_ref: string;
  action_type: string;
  description: string;
  owner: string;
  due_date: string;
  status: string;
  created_at: string;
}

export interface CapaCreate {
  action_type: "corrective" | "preventive";
  description: string;
  owner: string;
  due_date: string;
}

export interface AuditEntry {
  id: number;
  case_id: number | null;
  actor: string;
  action: string;
  detail: string | null;
  created_at: string;
}

export interface Summary {
  total_cases: number;
  open_cases: number;
  closed_cases: number;
  total_gaps_found: number;
  total_capas: number;
  open_capas: number;
  data_boundary: string;
}
