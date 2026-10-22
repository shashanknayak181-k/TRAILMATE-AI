# Acceptance Criteria

## Vertical slice 1 — account and profile

- A visitor can register with valid identity fields and required consent.
- Duplicate normalized email or username is rejected by the database-backed service.
- Email verification challenges expire, are single-use, and have attempt/resend limits.
- Sign-in accepts username or email and password; secrets are never stored in browser local storage or logs.
- Password reset uses a configured delivery provider or an explicitly documented development-only delivery mode; production does not silently fall back to development mode.
- Protected profile endpoints reject anonymous requests and enforce ownership.
- Profile onboarding can be resumed; optional fields may be skipped.
- Profile changes persist after browser refresh and backend restart.

## Vertical slice 2 — catalogue management

- An authorized operator can create and save a draft with source/verification fields.
- An unauthorized customer cannot create or publish operator content.
- Authorized review transitions content to published; public discovery excludes drafts/archived items.
- Published content appears in discovery without a frontend redeploy and persists across restart.

## Vertical slice 3 — planning and recovery (competition-critical)

- A user can create and save a trip with ordered segments and budget/preferences.
- Missing cost or schedule data is identified as unknown; the system does not silently assume zero cost or availability.
- A clearly labelled simulated disruption identifies impacted segments and downstream dependencies.
- Candidate alternatives violating hard budget/time/accessibility/route constraints are rejected by deterministic backend logic.
- Feasible alternatives are ranked and produce a revised itinerary version with rationale and a diff from the prior plan.
- If no alternative is feasible, the API and UI state that explicitly.
- A user can review and save the revised plan; the original remains in history.
- Recovery events are auditable and no booking/cancellation occurs automatically.

## Cross-cutting quality gates

- Frontend/backend start instructions are reproducible.
- Migrations run explicitly and successfully.
- API, business-rule, authorization and critical end-to-end tests pass.
- UI supports loading, empty, error, success, validation, keyboard focus, and responsive states.
- Simulated data and unsupported integrations are clearly labelled.
- Secrets are excluded from source control and known limitations are documented.
