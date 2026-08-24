# Case study: structured data-integrity investigation

## Problem

Data-integrity investigations need a coherent record of the initial signal, evidence, ALCOA+ observations, hypotheses, decisions, and CAPA readiness.

## Users and outcome

Investigators organize evidence and findings; quality reviewers reconstruct the reasoning and history. Optional local AI suggests triage text but cannot commit records without human review.

## Engineering decisions

- FastAPI centralizes case and evidence rules.
- Append-oriented history supports attributable reconstruction.
- A local Ollama integration keeps AI assistance optional and isolates it from authoritative writes.
- Synthetic case records, SQLite, Docker, and mocked AI tests make the public demo repeatable.

## Evidence

The repository includes security controls, automated contract and security tests, CI, Dependabot, architecture documentation, and regulatory references.

## Boundary

The workspace is educational and contains only fictional investigations. It must not be used for regulatory filings, batch release, official CAPA, or production quality decisions.
