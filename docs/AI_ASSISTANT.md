# AI-Assisted ALCOA+ Gap Triage (Prototype)

## Purpose

This module demonstrates one way a locally hosted, open-source LLM can support—never
replace—human review in a GxP-adjacent data integrity workflow. It reflects the FDA
Computer Software Assurance (CSA) principle of applying human critical thinking to
AI-generated output rather than treating that output as a validated decision.

## Design principles

- The model runs fully locally via [Ollama](https://ollama.com); no case data leaves
  the Docker network or reaches a third-party API.
- The model never writes directly to case records. It only produces suggestions.
- Every suggestion is stored with the model name, provider, prompt version, and a
  SHA-256 hash of the raw response, before any human review occurs.
- A qualified reviewer must explicitly accept, reject, or modify each suggestion.
  That decision, the reviewer's identity, and a server-generated UTC timestamp are
  recorded as a separate, later audit event — distinct from the generation event.
- If the local model is unreachable, the API returns HTTP 503 and the rest of the
  application continues to operate normally.

## Data flow

1. `POST /cases/{id}/ai-suggest-gaps` sends the case title, system, and signal type
   to a local Ollama instance using the `/api/chat` endpoint.
2. The model returns strictly structured JSON: a list of ALCOA+ attributes, a risk
   level, a rationale, and a limitations statement.
3. The API validates that JSON against a Pydantic schema (`AiGapResponse`) before
   persisting anything.
4. `GET /cases/{id}/ai-suggestions` lists prior suggestions for a case.
5. `POST /ai-suggestions/{id}/review` records the human decision.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Base URL of the Ollama HTTP API |
| `OLLAMA_MODEL` | `llama3.2:3b` | Local model used for triage suggestions |

In Docker Compose, `OLLAMA_BASE_URL` is set to `http://ollama:11434` so the API
container can reach the Ollama container over the internal network.

## Explicit limitations

This prototype is not a validated AI system, does not perform any regulatory
determination, and must not be used with real case data. It illustrates an
assurance-first pattern for human-in-the-loop AI review, not a production-ready
AI governance program.
