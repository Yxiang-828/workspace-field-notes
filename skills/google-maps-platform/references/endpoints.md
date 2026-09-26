# Google Maps Endpoint Notes

Official docs:

- Geocoding API: https://developers.google.com/maps/documentation/geocoding
- Places API (New): https://developers.google.com/maps/documentation/places/web-service
- Routes API: https://developers.google.com/maps/documentation/routes
- Weather API: https://developers.google.com/maps/documentation/weather
- Address Validation API: https://developers.google.com/maps/documentation/address-validation
- Maps Grounding Lite: https://developers.google.com/maps/ai/grounding-lite

## Geocoding

Use for address/place text to coordinates or coordinates to formatted addresses.

- REST geocode endpoint: `https://maps.googleapis.com/maps/api/geocode/json`
- Query params: `address=<text>` or `latlng=<lat,lng>`, plus `key`.
- Return key fields: `formatted_address`, `geometry.location`, `place_id`, `types`.

## Places API (New)

Use Text Search for place discovery. Official docs require a field mask.

- Text Search endpoint: `POST https://places.googleapis.com/v1/places:searchText`
- Headers:
  - `X-Goog-Api-Key: <key>`
  - `X-Goog-FieldMask: places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount`
- Body: `{"textQuery": "..."}`

Use Place Details only when a place id is known.

- Details endpoint: `GET https://places.googleapis.com/v1/places/{place_id}`
- Use a narrow `X-Goog-FieldMask`.

## Routes API

Use Compute Routes for one origin/destination.

- Endpoint: `POST https://routes.googleapis.com/directions/v2:computeRoutes`
- Headers:
  - `X-Goog-Api-Key: <key>`
  - `X-Goog-FieldMask: routes.distanceMeters,routes.duration,routes.staticDuration,routes.description`
- Body uses `origin.address` and `destination.address`, or `location.latLng`.

Use Compute Route Matrix only when multiple origins/destinations are necessary. Keep matrices small.

- Endpoint: `POST https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix`
- Required response field mask example: `originIndex,destinationIndex,status,condition,distanceMeters,duration`
- Include `status` in the field mask so per-element failures are visible.
- Google limits vary by request shape; avoid matrices larger than the real task needs.

## Address Validation

Use when the user needs a postal address checked, standardized, or made more deliverable.

- Endpoint: `POST https://addressvalidation.googleapis.com/v1:validateAddress`
- Minimal body: `{"address": {"regionCode": "SG", "addressLines": ["..."]}}`
- `regionCode` is optional but recommended when known.
- `enableUspsCass` is only for supported US/PR addresses.

## Weather API

Use current conditions only when the user asks for weather or context that needs weather.

- Weather docs: https://developers.google.com/maps/documentation/weather
- Current conditions endpoint: `GET https://weather.googleapis.com/v1/currentConditions:lookup`
- Weather endpoint availability can vary by launch state and project access; if an endpoint returns auth/not-enabled errors, report the API enablement issue and do not retry repeatedly.

## Maps Grounding Lite

Use when the user wants an LLM/agent to ground answers in Maps data through MCP. It is not a general REST endpoint for this helper script.

- MCP server URL: `https://mapstools.googleapis.com/mcp`
- Auth header for API key mode: `X-Goog-Api-Key: <key>`
- Tool categories exposed by the MCP server include `search_places`, `lookup_weather`, and `compute_routes`.
- Do not print or paste the configured API key; store it in the local MCP host config or env.
