# Changelog

All notable changes to this portfolio project are documented in this file.

The project follows semantic versioning for public portfolio releases. Version numbers describe the repository's software baseline; they do not indicate regulatory validation, approval, or fitness for a regulated intended use.

## [Unreleased]

### Changed

- Rate limiter no longer trusts `X-Forwarded-For` unless the socket peer is in `TRUSTED_PROXIES`, validates the forwarded addresses, and bounds its memory (expired buckets are swept, tracked clients are capped)
- Ollama image pinned to `0.40.14` (was `latest`)
- CI: ruff and mypy added (all findings fixed), least-privilege `permissions:`, `npm ci` with the lockfile (CI and `frontend/Dockerfile`), coverage gate raised to 85 %, vitest step
- Dev requirements now include pinned ruff, mypy and pip-audit
- API and frontend versions aligned with the changelog (1.0.0)
- README: React 18 (not 19)
- Removed dead code (`require_api_key`, unused `_now` in `models.py`, redundant path check)

### Added

- Frontend unit tests (vitest) and rate-limiter / client-identification tests
- More complete `.gitignore`

## [1.0.0] — 2026-08-27

### Added

- Case intake, ALCOA+ gap analysis, evidence log, and CAPA formulation workflow
- Local AI-assisted triage (Ollama + `llama3.2:3b`) with mandatory human review before any suggestion is recorded
- SHA-256 hashing of stored model responses so evidence is bitwise-verifiable
- FastAPI endpoints for cases, ALCOA+ gaps, evidence, CAPAs, AI suggestions, and audit log
- API key authentication, per-route rate limiting, and security headers
- React 18 investigation board and case detail reviewer UI
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
