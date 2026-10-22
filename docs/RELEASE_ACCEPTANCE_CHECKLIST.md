# Release acceptance checklist

Do not label a release fully verified until each applicable item has evidence.

## Clean setup
- [ ] Extract archive to a new folder; do not reuse a virtual environment from an older version.
- [ ] Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force` in the current PowerShell session if required by local policy.
- [ ] Run `./setup-local.ps1`; confirm it exits successfully.
- [ ] Confirm frontend `npm run build` passes.
- [ ] Confirm Alembic migration succeeds and `pytest` reports all tests passing.

## Runtime workflow
- [ ] Backend health endpoint responds.
- [ ] Frontend opens at `http://localhost:5173`.
- [ ] Register/sign in and complete profile.
- [ ] Explore destinations and search a map place.
- [ ] Create a trip and confirm it appears in saved trips after refresh/re-sign-in.
- [ ] Start trip and update a segment; confirm progress persists.
- [ ] Generate recovery alternatives; confirm proposal does not mutate the itinerary before acceptance.
- [ ] Accept a feasible alternative; confirm the saved itinerary changes and history is visible.
- [ ] Test unknown-cost trip and confirm the UI does not claim budget feasibility without cost data.
- [ ] Check loading, empty, validation, API error, and narrow-screen layouts.

## Safety and release hygiene
- [ ] Confirm `.env`, local databases, `.venv`, and `node_modules` are excluded from Git/archive.
- [ ] Use development-only accounts and credentials for the demo.
- [ ] Disclose external map/search/routing dependencies and simulated disruption data.
- [ ] Do not claim live traffic, live weather, verified road closures, booking, or Google Maps integration unless separately implemented and tested.
