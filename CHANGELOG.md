# Changelog

All notable changes to this portfolio project are documented in this file.

The project follows semantic versioning for public portfolio releases. Version numbers describe the repository's software baseline; they do not indicate regulatory validation, approval, or fitness for a regulated intended use.

## [1.0.0] — 2026-08-27

### Added

- Case intake, ALCOA+ gap analysis, evidence log, and CAPA formulation workflow
- Local AI-assisted triage (Ollama + `llama3.2:3b`) with mandatory human review before any suggestion is recorded
- SHA-256 hashing of stored model responses so evidence is bitwise-verifiable
- FastAPI endpoints for cases, ALCOA+ gaps, evidence, CAPAs, AI suggestions, and audit log
- API key authentication, per-route rate limiting, and security headers
- React 19 investigation board and case detail reviewer UI
- SQLite (WAL) persistence with synthetic demonstration case library
- Docker Compose deployment (API, frontend, and local Ollama service)
- Non-root API container build
- Append-only audit log with attributable actor and server-generated UTC timestamps
- CI pipeline (pytest + coverage, pip-audit, npm audit, Vite build) and CodeQL scanning

### Known limitations

- No authentication beyond a static API key; no role-based access control
- SQLite is intended for local demonstration, not governed multi-user operation
- Audit records are protected by application behavior, not an independently secured audit subsystem
- Synthetic data only; not for real quality, release, compliance, or regulatory decisions
