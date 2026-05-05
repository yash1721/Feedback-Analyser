# Security Threat Model

## Assets

- Feedback text, OCR/PDF/CSV extracted content, and knowledge documents.
- PII in user-provided text and files.
- API keys and environment secrets.
- Retrieval traces, vector payloads, analysis runs, workflow tickets, and audit logs.

## Trust Boundaries

- External clients to FastAPI.
- FastAPI to PostgreSQL, Redis/Celery, and Qdrant.
- File and URL ingestion into local storage and extraction services.
- Retrieved evidence and feedback text into prompt construction.

## Threats

- Unauthorized API use.
- Expensive endpoint abuse.
- SSRF through image URL ingestion.
- Unsafe file uploads.
- PII leakage through logs, prompts, traces, or model output.
- Prompt injection from feedback or knowledge documents.
- Schema-valid but unsafe LLM output.
- Insecure production config.

## Mitigations

- API key auth and simple role permissions.
- In-memory rate limiting for local/demo protection.
- Existing URL validation plus credential and redirect rejection.
- File size, MIME, extension, and filename checks.
- Best-effort PII redaction and sanitized analysis text.
- Prompt injection detection.
- Pydantic schema validation plus output guardrails.
- Security audit logs and Prometheus security metrics.
- Production startup config validation.

## Remaining Risks

- Regex-based PII detection is best-effort, not complete DLP.
- Rule-based prompt injection detection can miss novel attacks.
- In-memory rate limiting is per-process.
- Phase 9 does not include OAuth, SSO, encryption-at-rest, malware scanning, WAF, or full enterprise IAM.
