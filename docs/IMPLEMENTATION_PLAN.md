# Implementation plan and current status

## Completed in this iteration: vertical slice 1 foundation

- SQLAlchemy models and an Alembic migration for users, profiles, verification challenges, and server-side sessions.
- Registration with normalized unique username/email, required consent, password confirmation/policy validation, and scrypt password hashing.
- Development/test-only email verification code delivery, 10-minute expiry, single-use challenge, and five-attempt cap.
- Username-or-email sign-in, verified-email requirement, opaque HttpOnly session cookie, server-side session persistence, and sign-out invalidation.
- Authenticated profile read/update and a database-backed dashboard response.
- React + TypeScript forms for registration, verification, sign-in, profile onboarding/editing, and dashboard empty state, wired to real API endpoints.
- Automated backend workflow and authorization tests.

## Explicitly not implemented yet

- Production email delivery adapter, resend cooldown/rate limiter, and forgot/reset-password workflow.
- CSRF token mechanism for deployments that require it, broader rate limiting, and account lockout/abuse monitoring.
- Frontend automated component/E2E tests; npm dependency installation could not be completed in the current environment.
- Destination catalogue, operator/admin roles, trips, budget estimator, and the competition-critical disruption recovery engine.

## Next acceptance scenario

Continue vertical slice 1 by implementing configured email delivery and password reset with OTP lifecycle controls; then add frontend component tests and run the production frontend build in an environment where npm dependencies can be installed. After that, prioritize the planning/recovery vertical slice (acceptance scenario E / PS 4.1) before gamification or community work.


## Iteration: password reset vertical slice

- [x] Add persisted password-reset challenge records and Alembic migration `0002_password_reset`.
- [x] Add reset request, code verification, and completion endpoints.
- [x] Add generic request responses to reduce account enumeration, code expiration, five-attempt limit, request cooldown, one-use reset authorization, password validation, and session invalidation.
- [x] Connect forgot-password/reset-code/new-password screens to the API with busy, error, and success states.
- [x] Add automated tests for successful reset, old-password rejection, session invalidation, replay rejection, invalid code, password mismatch, and unknown email behavior.
- [x] Backend tests: 12 passed. Alembic upgrade and downgrade both succeeded on SQLite.
- [ ] Frontend production build and browser-level verification remain blocked until npm dependencies are available.
- [ ] Configure real email delivery before production use.

## Iteration 4 — Functional travel MVP (implemented, local verification)

- Added destination discovery API with a clearly labelled seeded demo catalogue.
- Added authenticated trip creation/list/detail endpoints with user ownership checks.
- Added deterministic group-budget validation and itinerary segments.
- Added controlled disruption recovery for transport cancellation, route closure, activity unavailability, and accommodation unavailability.
- Added persisted recovery history and a dashboard workspace for Overview, Explore, Plan a trip, My trips, and Recovery.
- Added migration `0003_travel_mvp`.
- Backend verification in the development container: 16 tests passed; upgrade/downgrade migration cycle passed.
- Frontend production build remains unverified because `npm install` timed out in this environment.
- Seeded destination listings, estimated costs, and disruption scenarios are simulated data; there are no live provider feeds or bookings.
