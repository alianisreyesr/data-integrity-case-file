import type {
  CaseOut,
  CaseCreate,
  AlcoaGapOut,
  AlcoaGapCreate,
  EvidenceOut,
  EvidenceCreate,
  CapaOut,
  CapaCreate,
  AuditEntry,
  Summary,
  AiSuggestionOut,
  AiSuggestionReviewCreate,
} from "./types";
import { UserFacingError, messageForApiFailure } from "./errors";

const BASE = "/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
  } catch {
    throw new UserFacingError(
      "The application could not reach the local service. Confirm Docker Compose is running, then try again."
    );
  }

  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }
    throw new UserFacingError(messageForApiFailure(response.status, body));
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; data_boundary: string }>("/health"),
  summary: () => request<Summary>("/summary"),
  listCases: (status?: string) =>
    request<CaseOut[]>(`/cases${status ? `?status=${status}` : ""}`),
  getCase: (id: number) => request<CaseOut>(`/cases/${id}`),
  createCase: (body: CaseCreate, actor: string) =>
    request<CaseOut>("/cases", {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "x-actor": actor },
    }),
  listGaps: (caseId: number) => request<AlcoaGapOut[]>(`/cases/${caseId}/alcoa-gaps`),
  addGap: (caseId: number, body: AlcoaGapCreate, actor: string) =>
    request<AlcoaGapOut>(`/cases/${caseId}/alcoa-gaps`, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "x-actor": actor },
    }),
  listEvidence: (caseId: number) => request<EvidenceOut[]>(`/cases/${caseId}/evidence`),
  addEvidence: (caseId: number, body: EvidenceCreate, actor: string) =>
    request<EvidenceOut>(`/cases/${caseId}/evidence`, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "x-actor": actor },
    }),
  listCapas: (caseId: number) => request<CapaOut[]>(`/cases/${caseId}/capas`),
  addCapa: (caseId: number, body: CapaCreate, actor: string) =>
    request<CapaOut>(`/cases/${caseId}/capas`, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "x-actor": actor },
    }),
  auditLog: (caseId?: number) =>
    request<AuditEntry[]>(`/audit-log${caseId ? `?case_id=${caseId}` : ""}`),
  generateAiSuggestions: (caseId: number, actor: string) =>
    request<AiSuggestionOut>(`/cases/${caseId}/ai-suggest-gaps`, {
      method: "POST",
      headers: { "x-actor": actor },
    }),
  listAiSuggestions: (caseId: number) =>
    request<AiSuggestionOut[]>(`/cases/${caseId}/ai-suggestions`),
  reviewAiSuggestion: (suggestionId: number, body: AiSuggestionReviewCreate, actor: string) =>
    request<AiSuggestionOut>(`/ai-suggestions/${suggestionId}/review`, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "x-actor": actor },
    }),
};
