# TrailMate AI — v0.3.0

## What changed

### Workspace redesign
- Replaced the minimal overview with a travel control-centre dashboard.
- Added live, data-backed metrics for saved journeys, completed trips, planned/active trips, and destination ideas.
- Added distinct workflow cards for Explore, Plan a Trip, Live Trip, and Recovery Lab.
- Added a traveller profile summary, preference tags, a clear limitations notice, and a recent-journeys list with recovery shortcuts.
- Added responsive layouts for desktop, tablet, and mobile; added reduced visual density in narrow screens.
- The authenticated workspace now uses the full available width and a sticky navigation bar.

### Map layers
- Added a topographic Terrain layer alongside Street and Satellite + labels.
- The satellite layer uses Esri World Imagery with Esri place/boundary labels.
- The map explicitly labels its providers and limitations. This is not Google Maps and does not provide Google Street View, live traffic, verified road closures, or Google imagery.

### Engineering
- Frontend package version updated to 0.3.0.
- Backend behavior and API contracts are unchanged in this release.

## Verification
- Backend automated tests: 22 passed.
- TypeScript structural check of `App.tsx` and `TravelMap.tsx` passed using temporary React type stubs because the npm dependency installation did not complete in this environment.
- Full frontend dependency installation and production build were not verified.
- Browser-level end-to-end testing was not run.

## Important limitations
- Recovery is a controlled simulation, not a live booking or disruption integration.
- Destination discovery data, costs, public map imagery, geocoding, and OSRM routing depend on external services and may be incomplete or unavailable.
- A configured Google Maps API integration would be a separate implementation; this version does not pretend the Esri satellite layer is Google Maps.
