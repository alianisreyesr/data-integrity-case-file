# Roadmap — Data Integrity Case File

## Phase 0 — Documentation
- [x] README (EN + ES)
- [x] Regulatory references (FDA DI guidance, MHRA, PIC/S, ALCOA+)
- [x] Investigation playbook (educational)
- [x] LICENSE · SECURITY.md

## Phase 1 — Domain
- [x] Case, Finding, AlcoaAssessment, EvidenceItem, CapaAction models
- [x] Status workflow with audit-oriented events
- [x] Synthetic seed cases (shared login, missing audit trail review, backdated entry — fictional)

## Phase 2 — API & UI
- [x] FastAPI
- [x] Case board + detail views
- [x] Local AI triage with mandatory human review

## Phase 3 — Hardening
- [x] Tests · CI · Docker
- [x] API key, rate limits, security headers
- [ ] Coverage gate published in CI
- [ ] Production IAM / e-signatures (explicitly out of scope for this prototype)

## Ethics
Never load real batch, patient, or employer data. Stories stay clearly labeled synthetic.
