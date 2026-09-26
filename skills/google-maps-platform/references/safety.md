# Safety, Privacy, And Billing

- Never print API keys.
- Do not commit `.env` files with Maps keys.
- Prefer server-side calls for protected keys. Browser Maps JavaScript keys should be HTTP-restricted.
- For `scripts/maps_cli.py`, use a server-side compatible key: unrestricted for testing, or restricted by IP address plus allowed APIs. A key restricted to HTTP referrers is for browser Maps JavaScript and will fail from local Python.
- Use narrow field masks for Places and Routes.
- Avoid high-cardinality route matrices without explicit approval.
- Treat user location history as sensitive. Do not store precise home/work coordinates unless the user asks.
- If a request may incur large cost, ask before running it.
- When an API returns `REQUEST_DENIED`, `PERMISSION_DENIED`, `ApiNotActivatedMapError`, or similar, the likely causes are API not enabled, billing/key restrictions, wrong key, or unsupported endpoint access.
