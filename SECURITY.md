# Security Policy

## Supported versions

This is a portfolio and learning project, not a hosted service or validated product.

| Version | Support status |
|---|---|
| Current `main` | Best-effort security fixes |
| Historical snapshots | Not supported |

## Reporting a vulnerability

Do **not** open a public issue containing exploit details, credentials, personal data, or regulated records.

1. Use GitHub private vulnerability reporting when available under the Security tab.
2. Otherwise contact the maintainer via the LinkedIn profile in the README and request a private channel.

Reports should use **synthetic data only**.

## In-scope examples

- API-key bypass on protected routes
- SQL injection
- stored XSS in the investigation UI
- ways to apply AI suggestions without human review
- secret leakage in the repository or workflows

## Out-of-scope examples

- missing production IAM / Part 11 controls already documented as out of scope
- local SQLite file tampering by a host administrator
- findings that used real employer, patient, or batch data
- requests to certify the software as validated

## Secrets and data handling

- Default demo key `dev-api-key-change-me` is intentional and not a production secret.
- Never commit real API keys, tokens, or investigation evidence.
- Ollama is local-only; do not point it at real regulated records.
