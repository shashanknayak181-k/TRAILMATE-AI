# Requirements Specification

## Product objective

Help travellers discover regional destinations, plan trips, estimate expenses, and recover from disruptions. Initial geographic scope is Karnataka, especially the Western Ghats; the data model must support adding Kerala and other regions without a redesign.

## Primary users

- **Visitor:** explores published destinations and trekking information; registers or signs in.
- **Customer:** manages a profile, saves places, plans and edits trips, reviews budgets, and requests disruption recovery.
- **Content operator:** drafts and updates authorized destination and local-listing content, submits it for review, and handles assigned reports.
- **Administrator:** manages roles, publication, platform configuration, moderation, and audit records.

## Core requirements

1. Account security: registration, unique normalized email and username, email verification, secure sign-in, logout/session invalidation, OTP password reset, rate limiting, and server-enforced roles.
2. Profile: guided first-time setup, preferences, saved progress, editable details, and privacy controls.
3. Discovery: search, filtering, sorting, pagination, destination details, saved places, and adding places to trips.
4. Content governance: drafts, review, publication, archive, provenance, verification date, and history for destinations and lesser-known places.
5. Maps: provider-adapted map, standard/satellite modes where supported, markers, route display, filters, and graceful provider-failure states.
6. Listings: accommodation, food, transport and official/local contacts with source and verification metadata. Listings must not imply availability.
7. Trip planning: dates, starting point, destinations, group size, budget, interests, transport and accommodation preferences; validate sequence, travel time, access restrictions and budget before saving.
8. Budgeting: deterministic totals and per-person allocation; missing prices are unknown, not zero; simulated prices are labelled.
9. Disruption recovery (competition-critical): record disruption, determine affected segments/dependencies, enforce hard constraints, evaluate and rank alternatives, produce a revised itinerary, explain differences, allow review/save, and audit the event.
10. Gamification: backend-validated XP, append-only transaction history, idempotent awards, configurable levels/badges, period-aware leaderboards, opt-out, and anti-duplication controls.
11. Community: achievement feed, profile visibility, likes, reporting, and moderation, without exposing private contact or precise live-location data.
12. Operations: distinct customer/admin layouts, server-side authorization, search/filter/pagination, validation, audit logging, and persistent database-backed changes.
13. Quality: typed API contracts, migrations, automated tests, accessible responsive interfaces, secure file handling, configuration through environment variables, and documented limitations.

## Data provenance rules

Every material destination/listing/operational record should identify its source, verification state, retrieval/verification time where available, publication status, and whether it is simulated. No invented live schedules, prices, availability, official contacts, permit requirements, or verified safety claims.

## Explicit non-goals for the initial MVP

- Automatically purchasing, booking, or cancelling services.
- Claiming real-time satellite imagery or live disruption feeds without an integration.
- Using an LLM as the authority for feasibility, authorization, cost arithmetic, or XP awards.
- Starting with microservices absent a demonstrated need.
