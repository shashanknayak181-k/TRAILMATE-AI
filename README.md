# TRAILMATE AI

TRAILMATE AI is a travel-planning and journey-recovery MVP. It combines destination exploration, map-based stop selection, saved itineraries, trip-progress tracking, and a review-before-accept disruption-recovery workflow.

## Implemented in this version

- Account registration, development-only email verification, sign-in/sign-out, profile setup, and password reset.
- SQLite local development database and Alembic migrations.
- Curated regional destination catalogue with explicit demonstration-data labels.
- Dynamic place search through OpenStreetMap Nominatim, with cached search results and bounded result counts.
- Interactive street map and satellite imagery layer, destination markers, route drawing through OSRM when available, and opt-in browser geolocation.
- Map-selected custom destinations and stops persisted with coordinates. Unknown destination costs remain explicitly unknown rather than being presented as zero-cost verified estimates.
- Authenticated trip creation, saving, retrieval, itinerary progress, and Live Trip Mode.
- Deterministic budget estimates for known-cost itinerary segments.
- Simulated disruption analysis that generates multiple candidate recovery plans, reports budget feasibility, and requires explicit user acceptance before updating a saved itinerary.
- Recovery history and ownership checks for trip operations.
- Light/dark themes with the vibranium-violet design system.

## Run on Windows

Prerequisites: Python 3.11+, Node.js 20+, npm, and internet access for dependency installation and external map/search services.

1. Extract the project ZIP and open the root folder in VS Code.
2. If PowerShell blocks scripts, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal.
3. Run `./setup-local.ps1` and wait for dependency installation, migrations, and backend tests to finish.
4. In terminal 1 run `./start-backend.ps1`.
5. In terminal 2 run `./start-frontend.ps1`.
6. Open `http://localhost:5173`; API docs are at `http://127.0.0.1:8000/docs`.

Manual backend setup: `cd backend`; create/activate a virtual environment; install `requirements-local.txt`; run `python -m alembic -c alembic.ini upgrade head`; run `python -m pytest -q`; then `python -m uvicorn app.main:app --reload`.

Manual frontend setup: `cd frontend`; run `npm install`; then `npm run dev`. Run `npm run build` before packaging or presenting a release.

## External data and limitations

- Map tiles use OpenStreetMap; satellite imagery uses Esri World Imagery. Attribution is displayed in the map.
- Place search uses OpenStreetMap Nominatim with server-side caching and a request interval. It returns geocoding results, not verified tourism listings.
- Route drawing requests a route from the public OSRM service when available. It is not live traffic navigation and does not confirm closures.
- Curated destination details, costs, and disruption scenarios are demonstration data. Weather, live public transport, verified road-closure feeds, booking availability, and booking/cancellation integrations are not connected.
- Browser geolocation is opt-in and is used for a local map marker; it is not transmitted to the backend by this feature.
- Dynamic map destinations persist their coordinates, but destination-specific costs, opening hours, and access conditions remain unknown unless verified separately. The UI identifies the displayed known-cost subtotal.
- Email verification and password-reset codes use development-only delivery. Do not deploy this configuration publicly.

This is a local MVP and not yet a production-ready public service. The frontend production build and full browser-level end-to-end flow must be verified in the target development environment before a release claim.

## Verification performed for this iteration

- Backend automated tests: 22 passed.
- Python syntax compilation: passed.
- Frontend TypeScript syntax was checked with the globally available compiler, but the full type check and production build could not be completed because dependency installation was blocked by unavailable npm registry/cache packages in the build environment. Run `npm ci` (or `npm install`) and `npm run build` locally before demonstration.

## Version 0.3.0 — Workspace and map experience

The latest release adds a responsive travel-control dashboard, four clearly separated workflows (Explore, Plan a Trip, Live Trip, Recovery Lab), a recent-journeys panel, traveller preference summary, and a third map layer for terrain. See [`RELEASE_NOTES_v0.3.0.md`](RELEASE_NOTES_v0.3.0.md) for the exact scope and verification status.

The map uses OpenStreetMap street tiles and Esri satellite/topographic services; it is **not Google Maps** and does not include Google Street View, live traffic, or verified road closures.


## Version 0.4.0 — Engineering reliability

This iteration improves setup failure detection and adds a reproducible hackathon demo script and release acceptance checklist. See `RELEASE_NOTES_v0.4.0.md`, `docs/HACKATHON_DEMO_SCRIPT.md`, and `docs/RELEASE_ACCEPTANCE_CHECKLIST.md`. It is not a claim of production readiness; follow the checklist on the target machine.
