import { describe, expect, it } from "vitest";
import { UserFacingError, messageForApiFailure } from "../errors";

describe("messageForApiFailure", () => {
  it("maps 404 to a not-found message", () => {
    expect(messageForApiFailure(404, null)).toMatch(/could not be found/);
  });

  it("maps 422 with a known field to a field-specific message", () => {
    const body = { detail: [{ loc: ["body", "due_date"], msg: "x", type: "string_pattern_mismatch" }] };
    expect(messageForApiFailure(422, body)).toBe("Enter a valid due date in YYYY-MM-DD format.");
  });

  it("maps 422 missing fields to a generic required-fields message", () => {
    const body = { detail: [{ loc: ["body", "unknown_field"], type: "missing" }] };
    expect(messageForApiFailure(422, body)).toMatch(/required fields/);
  });

  it("maps 503 to the local AI message", () => {
    expect(messageForApiFailure(503, {})).toMatch(/Ollama/);
  });

  it("maps other 5xx and 4xx codes to generic messages", () => {
    expect(messageForApiFailure(500, null)).toMatch(/service could not complete/);
    expect(messageForApiFailure(409, null)).toMatch(/could not be completed/);
  });
});

describe("UserFacingError", () => {
  it("stringifies to its message only", () => {
    expect(String(new UserFacingError("boom"))).toBe("boom");
  });
});
