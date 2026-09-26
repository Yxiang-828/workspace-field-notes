---
name: google-maps-platform
description: Use Google Maps Platform APIs from local env credentials for geocoding, reverse geocoding, place search/details, route computation, route matrices, weather, address validation, and map-backed planning. Use when the user asks about Google Maps, Places, Routes, Weather API, geocoding addresses, finding nearby places, calculating travel distance/time, validating addresses, or using a Maps API key such as MAP_API_KEY.
---

# Google Maps Platform

Use Google Maps Platform with the user's local API key. Prefer small, targeted requests and return concise, source-backed results with enough raw evidence to verify.

## Rules

- Read `MAP_API_KEY`, `GOOGLE_MAPS_API_KEY`, or `GOOGLE_MAPS_PLATFORM_API_KEY` from env, current `.env`, parent `.env`, or `~/.alibaba/keys.env`; never print the key.
- Use official Google Maps docs when adding unsupported endpoints or changing request shapes.
- Prefer `scripts/maps_cli.py` for repeatable requests.
- Use minimal field masks for Places and Routes to control response size and billing.
- Do not make broad/bulk route matrices, place searches, or weather scans without explicit user intent.
- For frontend map rendering, use this skill for API/data calls and follow the frontend app rules for UI implementation.

## Workflow

1. Pick the endpoint.
   - Address to coordinates: `geocode`.
   - Coordinates to address: `reverse-geocode`.
   - Place discovery: `places-text`.
   - Place details by place id: `place-details`.
   - Point-to-point route: `route`.
   - Many origins/destinations: `route-matrix` only when the user really needs a matrix.
   - Postal address quality/deliverability: `address-validate`.
   - Weather at coordinates: `weather-current`.
   - Maps Grounding Lite: configure the MCP server from `references/endpoints.md`; do not treat it as a normal REST geocode call.

2. Load references only as needed.
   - Read `references/endpoints.md` for endpoint shapes, field masks, and doc links.
   - Read `references/safety.md` before bulk queries, user-location tracking, stored location data, or billing-sensitive requests.

3. Run the helper.
   ```powershell
   py skills\google-maps-platform\scripts\maps_cli.py geocode "National University of Singapore"
   py skills\google-maps-platform\scripts\maps_cli.py places-text "cafes near NUS" --limit 5
   py skills\google-maps-platform\scripts\maps_cli.py route "NUS, Singapore" "Changi Airport" --mode DRIVE
   py skills\google-maps-platform\scripts\maps_cli.py route-matrix --origin "NUS" --origin "SMU" --destination "Changi Airport"
   py skills\google-maps-platform\scripts\maps_cli.py address-validate "21 Lower Kent Ridge Rd, Singapore" --region-code SG
   py skills\google-maps-platform\scripts\maps_cli.py weather-current 1.2966 103.7764
   ```

4. Interpret results.
   - Report the normalized result first: address/name, coordinates, distance/duration, rating, weather, or route.
   - Include IDs only when useful for follow-up, such as `place_id`.
   - If Google returns no result, say that clearly and suggest a narrower query.
   - If auth fails, tell the user to enable the specific API, verify billing, and check key restrictions; do not ask for the key in chat.
   - If `REQUEST_DENIED` appears with an `error_message`, report that message and the likely Console fix.

## Env Setup

The helper searches these env var names:

```dotenv
MAP_API_KEY=
GOOGLE_MAPS_API_KEY=
GOOGLE_MAPS_PLATFORM_API_KEY=
```

If missing, add one to the project `.env` or `~/.alibaba/keys.env`.
