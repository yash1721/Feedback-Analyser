# Workflow Automation

Phase 6 converts validated AI analysis into operational workflow.

## Flow

```text
feedback_record
  -> latest llm_analysis_run
  -> duplicate check
  -> workflow ticket
  -> escalation rules
  -> human review when needed
  -> audit log
  -> mock/log notification
```

## Data Model

`workflow_tickets` stores the current operational item: title, description, category, severity, assigned team, status, duplicate link, SLA fields, and timestamps.

`workflow_review_items` stores human-in-the-loop decisions for low confidence, P0/P1 severity, missing team, or manual overrides.

`workflow_audit_logs` stores decision history separately from the ticket row. This keeps the current ticket state easy to query while preserving why decisions happened.

## Ticket Lifecycle

Supported statuses:

- `OPEN`
- `IN_REVIEW`
- `ASSIGNED`
- `ESCALATED`
- `RESOLVED`
- `CLOSED`
- `DUPLICATE`
- `REJECTED`

## Rules

Default deterministic rules:

- `P0` or `P1` severity escalates and creates human review.
- Confidence below `WORKFLOW_LOW_CONFIDENCE_THRESHOLD` creates human review.
- Missing routed team creates human review.
- Negative `PAYMENT` or `SECURITY` feedback escalates.

SLA due dates are calculated from:

- `WORKFLOW_DEFAULT_SLA_HOURS`
- `WORKFLOW_P0_SLA_HOURS`
- `WORKFLOW_P1_SLA_HOURS`

## Duplicate Detection

Phase 6 starts with deterministic duplicate detection. A new ticket is marked `DUPLICATE` if an open ticket already has the same category, assigned team, and generated title. This is intentionally simple and predictable; vector clustering can be added later.

## Notifications

Notifications go through `NotificationProvider`.

Current providers:

- `log`: writes local logs.
- `mock`: records calls in memory for tests.

No real Slack, Jira, or Zendesk API is called in Phase 6.

## Automatic Creation

`WORKFLOW_AUTO_CREATE_TICKETS=false` by default. When enabled, async processing can create a workflow ticket after successful Phase 5 analysis. Manual creation through the workflow API remains available.

## Verification

Run normal tests:

```powershell
.\.venv\Scripts\python -m pytest
```

Run the live verification:

```powershell
.\scripts\verify_phase6_live.ps1
```
