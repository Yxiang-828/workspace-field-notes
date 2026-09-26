#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


KEY_NAMES = ("MAP_API_KEY", "GOOGLE_MAPS_API_KEY", "GOOGLE_MAPS_PLATFORM_API_KEY")


def _parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def load_env(extra: str | None = None) -> dict[str, str]:
    env: dict[str, str] = {}
    cwd = Path.cwd()
    candidates = [
        cwd / ".env",
        cwd.parent / ".env",
        Path.home() / ".alibaba" / "keys.env",
    ]
    if extra:
        candidates.insert(0, Path(extra))
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        env.update(_parse_env(path))
    env.update({k: v for k, v in os.environ.items() if isinstance(v, str)})
    return env


def api_key(args: argparse.Namespace) -> str:
    env = load_env(args.env_file)
    for name in KEY_NAMES:
        value = (env.get(name) or "").strip()
        if value:
            return value
    raise SystemExit("MAP_API_KEY is missing. Add it to .env or ~/.alibaba/keys.env.")


def request_json(method: str, url: str, headers: dict[str, str] | None = None, body: dict[str, Any] | None = None) -> Any:
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail[:1000]}") from exc


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def google_status(data: dict[str, Any]) -> dict[str, Any]:
    out = {"status": data.get("status")}
    if data.get("error_message"):
        out["error_message"] = data.get("error_message")
    return out


def with_routing_preference(body: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if args.mode in {"DRIVE", "TWO_WHEELER"} and args.routing_preference:
        body["routingPreference"] = args.routing_preference
    return body


def geocode(args: argparse.Namespace) -> None:
    key = api_key(args)
    query = urllib.parse.urlencode({"address": args.address, "key": key})
    data = request_json("GET", f"https://maps.googleapis.com/maps/api/geocode/json?{query}")
    results = []
    for row in data.get("results", [])[: args.limit]:
        loc = row.get("geometry", {}).get("location", {})
        results.append({
            "formatted_address": row.get("formatted_address"),
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "place_id": row.get("place_id"),
            "types": row.get("types", []),
        })
    print_json({**google_status(data), "results": results})


def reverse_geocode(args: argparse.Namespace) -> None:
    key = api_key(args)
    query = urllib.parse.urlencode({"latlng": f"{args.lat},{args.lng}", "key": key})
    data = request_json("GET", f"https://maps.googleapis.com/maps/api/geocode/json?{query}")
    results = [
        {
            "formatted_address": row.get("formatted_address"),
            "place_id": row.get("place_id"),
            "types": row.get("types", []),
        }
        for row in data.get("results", [])[: args.limit]
    ]
    print_json({**google_status(data), "results": results})


def places_text(args: argparse.Namespace) -> None:
    key = api_key(args)
    fields = args.fields or "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount"
    body: dict[str, Any] = {"textQuery": args.query}
    if args.language:
        body["languageCode"] = args.language
    data = request_json(
        "POST",
        "https://places.googleapis.com/v1/places:searchText",
        headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": fields},
        body=body,
    )
    places = data.get("places", [])[: args.limit]
    print_json({"places": places})


def place_details(args: argparse.Namespace) -> None:
    key = api_key(args)
    fields = args.fields or "id,displayName,formattedAddress,location,rating,userRatingCount,internationalPhoneNumber,websiteUri,googleMapsUri"
    data = request_json(
        "GET",
        f"https://places.googleapis.com/v1/places/{urllib.parse.quote(args.place_id)}",
        headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": fields},
    )
    print_json(data)


def route(args: argparse.Namespace) -> None:
    key = api_key(args)
    fields = args.fields or "routes.distanceMeters,routes.duration,routes.staticDuration,routes.description"
    body = {
        "origin": {"address": args.origin},
        "destination": {"address": args.destination},
        "travelMode": args.mode,
    }
    body = with_routing_preference(body, args)
    data = request_json(
        "POST",
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": fields},
        body=body,
    )
    print_json(data)


def route_matrix(args: argparse.Namespace) -> None:
    key = api_key(args)
    if len(args.origin) * len(args.destination) > args.max_cells:
        raise SystemExit(f"Refusing {len(args.origin) * len(args.destination)} matrix cells; raise --max-cells deliberately if needed.")
    fields = args.fields or "originIndex,destinationIndex,status,condition,distanceMeters,duration"
    body = {
        "origins": [{"waypoint": {"address": origin}} for origin in args.origin],
        "destinations": [{"waypoint": {"address": destination}} for destination in args.destination],
        "travelMode": args.mode,
    }
    body = with_routing_preference(body, args)
    data = request_json(
        "POST",
        "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
        headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": fields},
        body=body,
    )
    print_json({"origin_count": len(args.origin), "destination_count": len(args.destination), "elements": data})


def address_validate(args: argparse.Namespace) -> None:
    key = api_key(args)
    address: dict[str, Any] = {"addressLines": [args.address]}
    if args.region_code:
        address["regionCode"] = args.region_code
    body: dict[str, Any] = {"address": address}
    if args.enable_usps_cass:
        body["enableUspsCass"] = True
    data = request_json(
        "POST",
        "https://addressvalidation.googleapis.com/v1:validateAddress",
        headers={"X-Goog-Api-Key": key},
        body=body,
    )
    result = data.get("result", {}) if isinstance(data, dict) else {}
    verdict = result.get("verdict", {})
    geocode_data = result.get("geocode", {})
    out = {
        "response_id": data.get("responseId") if isinstance(data, dict) else None,
        "verdict": verdict,
        "formatted_address": result.get("address", {}).get("formattedAddress"),
        "geocode": geocode_data.get("location"),
    }
    if args.raw:
        out["raw"] = data
    print_json(out)


def weather_current(args: argparse.Namespace) -> None:
    key = api_key(args)
    params = urllib.parse.urlencode({"key": key, "location.latitude": args.lat, "location.longitude": args.lng})
    url = f"https://weather.googleapis.com/v1/currentConditions:lookup?{params}"
    data = request_json("GET", url)
    print_json(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Maps Platform helper. Never prints API keys.")
    parser.add_argument("--env-file", help="Optional .env file to load before defaults.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("geocode")
    p.add_argument("address")
    p.add_argument("--limit", type=int, default=3)
    p.set_defaults(func=geocode)

    p = sub.add_parser("reverse-geocode")
    p.add_argument("lat", type=float)
    p.add_argument("lng", type=float)
    p.add_argument("--limit", type=int, default=3)
    p.set_defaults(func=reverse_geocode)

    p = sub.add_parser("places-text")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--fields")
    p.add_argument("--language")
    p.set_defaults(func=places_text)

    p = sub.add_parser("place-details")
    p.add_argument("place_id")
    p.add_argument("--fields")
    p.set_defaults(func=place_details)

    p = sub.add_parser("route")
    p.add_argument("origin")
    p.add_argument("destination")
    p.add_argument("--mode", default="DRIVE", choices=["DRIVE", "WALK", "BICYCLE", "TRANSIT", "TWO_WHEELER"])
    p.add_argument("--routing-preference", default="TRAFFIC_AWARE")
    p.add_argument("--fields")
    p.set_defaults(func=route)

    p = sub.add_parser("route-matrix")
    p.add_argument("--origin", action="append", required=True, help="Repeat for each origin address.")
    p.add_argument("--destination", action="append", required=True, help="Repeat for each destination address.")
    p.add_argument("--mode", default="DRIVE", choices=["DRIVE", "WALK", "BICYCLE", "TRANSIT", "TWO_WHEELER"])
    p.add_argument("--routing-preference", default="TRAFFIC_AWARE")
    p.add_argument("--fields")
    p.add_argument("--max-cells", type=int, default=25)
    p.set_defaults(func=route_matrix)

    p = sub.add_parser("address-validate")
    p.add_argument("address")
    p.add_argument("--region-code", help="Recommended ISO region code such as SG or US.")
    p.add_argument("--enable-usps-cass", action="store_true", help="Only for supported US/PR addresses.")
    p.add_argument("--raw", action="store_true", help="Include the full response for debugging.")
    p.set_defaults(func=address_validate)

    p = sub.add_parser("weather-current")
    p.add_argument("lat", type=float)
    p.add_argument("lng", type=float)
    p.set_defaults(func=weather_current)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
