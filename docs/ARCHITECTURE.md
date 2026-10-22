# Architecture

## Architectural style

Start with a modular monolith: one FastAPI application, one relational database, clear internal modules, and provider adapters. This keeps the prototype testable and deployable without the operational overhead of microservices.

## Planned runtime components

- **React + TypeScript + Vite:** public discovery, customer application, and distinct operator/admin portal layouts.
- **FastAPI + Pydantic:** versioned HTTP API, input/response schemas, authentication dependencies, authorization policies, and structured error responses.
- **SQLAlchemy + Alembic:** relational persistence and repeatable schema migrations.
- **PostgreSQL:** deployment database. SQLite is permitted for local smoke tests only where behavior remains compatible with PostgreSQL.
- **Provider adapters:** mapping, email, optional LLM, and any future transport/disruption data source. Provider credentials remain environment-based.
- **Pytest and frontend/e2e tooling:** business-rule, API, authorization, and critical workflow tests.

## Module boundaries

`auth`, `profiles`, `catalog` (destinations/places/treks), `listings` (stays/food/transport/contacts), `trips`, `planning`, `expenses`, `recovery`, `gamification`, `community`, `admin`, `audit`, and `integrations`.

Modules may share a database and transaction boundary but should not bypass each other's service rules by importing arbitrary internal persistence details. Keep route handlers thin: validate input, invoke a service, return a typed response.

## Key design decisions

1. **Backend authority:** permissions, budget calculations, constraint checks, publication state, and XP awards are enforced server-side.
2. **Recovery is deterministic:** an LLM can parse a traveller's natural-language preferences or explain a ranked plan. Candidate feasibility and hard-constraint rejection use ordinary backend code.
3. **Provenance travels with data:** source, verification, timestamp and simulation flags are part of listing/operational records and API responses.
4. **Versioned plans:** a saved trip keeps itinerary versions so recovery does not silently overwrite the original plan.
5. **Audit sensitive changes:** role changes, content publication, disruption/recovery decisions, and XP adjustments generate audit records.
6. **No implied bookings:** the MVP links out to providers; it does not claim reservations or cancellations succeeded.
7. **Provider isolation:** maps, email, and LLM services are adapters so credentials or vendors can change without rewriting core business logic.

## Security baseline

Use secure password hashing, short-lived one-time verification/reset challenges, normalized identity fields, rate limiting, session invalidation, backend role checks, ownership checks on private trips, upload size/type validation, least privilege, restricted CORS, safe errors, and no secret/OTP/token logging. Cookie-based browser sessions require CSRF protection and production Secure/HttpOnly/SameSite settings.

## Deployment shape

A frontend static build and one API service backed by managed PostgreSQL are sufficient for the MVP. Run Alembic migrations as a deployment step, not implicit startup behavior. Add structured logs, health/readiness checks, dependency checks, backups, and environment-specific configuration before production use.

## Current state

Only the FastAPI application shell and health/root endpoints exist. The frontend directory is reserved but has no implemented UI. No database models, migrations, authentication, external provider, or recovery workflow are currently wired up.
