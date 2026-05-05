# Security And Guardrails

Phase 9 adds API protection, privacy controls, AI guardrails, security audit logs, and security metrics.

## API Keys

Protected endpoints use `X-API-Key`. Local defaults keep auth disabled:

```env
AUTH_ENABLED=false
API_KEYS=local-admin-key:admin
```

In production, auth must be enabled and placeholder keys are rejected at startup.

Roles:

- `admin`: all actions.
- `analyst`: ingestion, feedback reads/writes, knowledge, retrieval, and analysis.
- `reviewer`: workflow, tickets, and reviews.
- `service`: processing, retrieval, analysis, and evaluations.

## Rate Limiting

The local limiter is in-memory and configurable:

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=120
RATE_LIMIT_BURST=30
```

It is suitable for local verification and single-process demos. Multi-instance production should use Redis or an API gateway.

## PII Redaction

FeedbackIQ detects and masks common PII patterns: emails, phone numbers, credit-card-like numbers, IP addresses, and ID-like long digit groups.

The system adds `sanitized_text`, `pii_detected`, and `pii_types_json` to feedback records. Existing raw fields remain for compatibility, but analysis uses sanitized text when `PII_ANALYSIS_USES_REDACTED_TEXT=true`.

## Prompt Injection

The detector flags inputs such as `ignore previous instructions`, `reveal system prompt`, `print secrets`, and `override policy`.

Modes:

- `warn`: audit and continue.
- `block`: reject high-risk input.
- `review`: reserved for workflows that require manual review.

## Output Guardrails

Structured output validation remains the first guardrail. Phase 9 adds semantic checks for unsafe terms, secret-exfiltration instructions, and PII-like content in summaries or recommended actions.

## Security Audit Logs

Security events are stored in `security_audit_logs`.

```http
GET /api/v1/security/audit-logs
X-API-Key: local-admin-key
```

## Metrics

Security metrics are exposed at `/metrics`, including auth failures, rate limits, PII redactions, prompt injection detections, unsafe URL blocks, file upload rejections, and guardrail violations.

## Verification

```powershell
.\scripts\verify_phase9_live.ps1
```
