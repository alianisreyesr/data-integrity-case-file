type ValidationDetail = {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
};

export class UserFacingError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "";
  }

  toString(): string {
    return this.message;
  }
}

const fieldMessages: Record<string, string> = {
  reviewed_by: "Reviewer name must contain at least 2 characters.",
  opened_by: "Opened by must contain at least 2 characters.",
  assessed_by: "Assessed by must contain at least 2 characters.",
  recorded_by: "Recorded by must contain at least 2 characters.",
  owner: "Owner must contain at least 2 characters.",
  title: "Case title must contain at least 3 characters.",
  system: "System must contain at least 2 characters.",
  description: "Description does not meet the required length.",
  due_date: "Enter a valid due date in YYYY-MM-DD format.",
};

function messageForValidation(detail: unknown): string {
  if (!Array.isArray(detail) || detail.length === 0) {
    return "Please review the form fields and correct the highlighted information.";
  }

  const first = detail[0] as ValidationDetail;
  const field = first.loc?.[first.loc.length - 1];
  if (typeof field === "string" && fieldMessages[field]) {
    return fieldMessages[field];
  }

  if (first.type === "missing") {
    return "Please complete the required fields and try again.";
  }

  return "Please review the form fields and correct the highlighted information.";
}

export function messageForApiFailure(status: number, body: unknown): string {
  const detail =
    body && typeof body === "object" && "detail" in body
      ? (body as { detail?: unknown }).detail
      : undefined;

  if (status === 404) {
    return "The requested record could not be found. It may have been removed or the page may be out of date.";
  }

  if (status === 422) {
    return messageForValidation(detail);
  }

  if (status === 503) {
    return "Local AI is taking longer than expected or is unavailable. Confirm Ollama is running and the model is installed, then try again.";
  }

  if (status >= 500) {
    return "The service could not complete the request. Please wait a moment and try again.";
  }

  return "The request could not be completed. Please review your information and try again.";
}
