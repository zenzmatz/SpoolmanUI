#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from typing import Any
from urllib import error, parse, request


FILAMAN_PAGE_SIZE = 200
SPOOLMAN_PAGE_SIZE = 200


class MigrationError(RuntimeError):
    pass


@dataclass
class MigrationStats:
    vendors_created: int = 0
    vendors_skipped: int = 0
    filaments_created: int = 0
    filaments_skipped: int = 0
    spools_created: int = 0
    spools_updated: int = 0
    spools_deleted: int = 0
    spools_skipped: int = 0
    extra_fields_created: int = 0
    warnings: list[str] = field(default_factory=list)


def _request_json(
    method: str,
    base_url: str,
    path: str,
    headers: dict[str, str],
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    if params:
        query = parse.urlencode({key: value for key, value in params.items() if value is not None})
        url = f"{url}?{query}"

    request_headers = dict(headers)
    data: bytes | None = None
    if json_body is not None:
        request_headers["Content-Type"] = "application/json"
        data = json.dumps(json_body).encode("utf-8")

    req = request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = response.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise MigrationError(f"{method} {path} failed with status {exc.code}: {detail[:300]}") from exc
    except error.URLError as exc:
        raise MigrationError(f"{method} {path} failed: {exc.reason}") from exc

    if not payload:
        return None

    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise MigrationError(f"{method} {path} returned invalid JSON") from exc


def _json_string(value: Any) -> str:
    return json.dumps(value)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_hex(hex_code: str | None) -> str | None:
    if not hex_code:
        return None
    return hex_code.strip().lstrip("#").upper()


def _extra_value(extra: dict[str, Any] | None, key: str) -> Any:
    if not extra:
        return None
    return extra.get(key)


def _parse_intish(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _parse_filaman_spoolman_id(item: dict[str, Any]) -> int | None:
    custom_fields = item.get("custom_fields") or {}
    spoolman_id = _extra_value(custom_fields, "spoolman_id")
    if spoolman_id is not None:
        return _parse_intish(spoolman_id)

    external_id = _clean_text(item.get("external_id"))
    if external_id and external_id.startswith("spoolman:"):
        return _parse_intish(external_id.split(":", 1)[1])

    return None


def _find_color_payload(filament: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    colors = filament.get("colors") or []
    hexes: list[str] = []
    for entry in sorted(colors, key=lambda item: item.get("position", 0)):
        color = entry.get("color") or {}
        normalized = _normalize_hex(color.get("hex_code"))
        if normalized:
            hexes.append(normalized)

    if not hexes:
        fallback = _normalize_hex(filament.get("manufacturer_color_name"))
        return fallback, None, None

    if len(hexes) == 1:
        return hexes[0], None, None

    style = filament.get("multi_color_style")
    direction = "coaxial" if style == "gradient" else "longitudinal"
    return None, ",".join(hexes), direction


class FilaManClient:
    def __init__(self, base_url: str, auth_header: str | None):
        headers = {"Accept": "application/json"}
        if auth_header:
            headers["Authorization"] = auth_header
        self.base_url = base_url.rstrip("/")
        self.headers = headers

    def close(self) -> None:
        return None

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return _request_json("GET", self.base_url, path, self.headers, params=params)

    def fetch_paginated(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        page = 1
        items: list[dict[str, Any]] = []
        while True:
            query = {"page": page, "page_size": FILAMAN_PAGE_SIZE}
            if params:
                query.update(params)
            payload = self._get(path, query)
            batch = payload.get("items")
            if not isinstance(batch, list):
                raise MigrationError(f"Unexpected FilaMan response for {path}: missing items list")
            items.extend(batch)
            if len(batch) < FILAMAN_PAGE_SIZE:
                break
            page += 1
        return items

    def get_manufacturers(self) -> list[dict[str, Any]]:
        return self.fetch_paginated("/api/v1/manufacturers")

    def get_filaments(self) -> list[dict[str, Any]]:
        return self.fetch_paginated("/api/v1/filaments")

    def get_spools(self, include_archived: bool) -> list[dict[str, Any]]:
        params = {"include_archived": str(include_archived).lower()}
        return self.fetch_paginated("/api/v1/spools", params)

    def get_locations(self) -> dict[int, str]:
        locations = self.fetch_paginated("/api/v1/locations")
        return {
            item["id"]: item["name"]
            for item in locations
            if isinstance(item, dict) and item.get("id") is not None and item.get("name")
        }

    def get_statuses(self) -> dict[int, str]:
        payload = self._get("/api/v1/spools/statuses")
        if not isinstance(payload, list):
            raise MigrationError("Unexpected FilaMan status response")
        return {item["id"]: item["key"] for item in payload if isinstance(item, dict)}


class SpoolmanClient:
    def __init__(self, base_url: str, auth_header: str | None, dry_run: bool):
        headers = {"Accept": "application/json"}
        if auth_header:
            headers["Authorization"] = auth_header
        self.base_url = base_url.rstrip("/")
        self.headers = headers
        self.dry_run = dry_run

    def close(self) -> None:
        return None

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        return _request_json(method, self.base_url, path, self.headers, **kwargs)

    def fetch_all(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        offset = 0
        items: list[dict[str, Any]] = []
        while True:
            query = {"limit": SPOOLMAN_PAGE_SIZE, "offset": offset}
            if params:
                query.update(params)
            batch = self._request("GET", path, params=query)
            if not isinstance(batch, list):
                raise MigrationError(f"Unexpected Spoolman response for {path}: expected list")
            items.extend(batch)
            if len(batch) < SPOOLMAN_PAGE_SIZE:
                break
            offset += SPOOLMAN_PAGE_SIZE
        return items

    def ensure_extra_field(self, key: str, name: str, field_type: str) -> bool:
        existing = self._request("GET", "/api/v1/field/spool")
        if any(field.get("key") == key for field in existing):
            return False
        if self.dry_run:
            return True
        self._request(
            "POST",
            f"/api/v1/field/spool/{key}",
            json_body={"name": name, "field_type": field_type},
        )
        return True

    def get_vendors(self) -> list[dict[str, Any]]:
        return self.fetch_all("/api/v1/vendor")

    def get_filaments(self) -> list[dict[str, Any]]:
        return self.fetch_all("/api/v1/filament")

    def get_spools(self) -> list[dict[str, Any]]:
        return self.fetch_all("/api/v1/spool", params={"allow_archived": "true"})

    def create_vendor(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.dry_run:
            return {"id": -1, **payload}
        return self._request("POST", "/api/v1/vendor", json_body=payload)

    def create_filament(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.dry_run:
            return {"id": -1, **payload}
        return self._request("POST", "/api/v1/filament", json_body=payload)

    def create_spool(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.dry_run:
            return {"id": -1, **payload}
        return self._request("POST", "/api/v1/spool", json_body=payload)

    def update_spool(self, spool_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        if self.dry_run:
            return {"id": spool_id, **payload}
        return self._request("PATCH", f"/api/v1/spool/{spool_id}", json_body=payload)

    def delete_spool(self, spool_id: int) -> None:
        if self.dry_run:
            return None
        self._request("DELETE", f"/api/v1/spool/{spool_id}")


def _parse_spool_extra_id(spool: dict[str, Any], key: str) -> str | None:
    extra = spool.get("extra") or {}
    value = extra.get(key)
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        parsed = value
    return _clean_text(parsed)


def _resolve_existing_spool(
    spool: dict[str, Any],
    spool_by_filaman_id: dict[str, dict[str, Any]],
    spool_by_id: dict[int, dict[str, Any]],
    claimed_spoolman_ids: set[int] | None = None,
) -> dict[str, Any] | None:
    filaman_spool_id = str(spool["id"])
    existing_spool = spool_by_filaman_id.get(filaman_spool_id)
    if existing_spool is not None:
        return existing_spool

    legacy_spoolman_id = _parse_filaman_spoolman_id(spool)
    if legacy_spoolman_id is not None:
        legacy_match = spool_by_id.get(legacy_spoolman_id)
        if legacy_match is None:
            return None
        if claimed_spoolman_ids is not None and legacy_match.get("id") in claimed_spoolman_ids:
            return None
        return legacy_match

    return None


def _build_spool_payload(
    spool: dict[str, Any],
    filament_id: int,
    location_name: str | None,
    archived: bool,
    existing_extra: dict[str, str] | None = None,
) -> dict[str, Any]:
    custom_fields = spool.get("custom_fields") or {}
    tag = _clean_text(custom_fields.get("tag")) or _clean_text(spool.get("rfid_uid"))
    last_dried = _clean_text(custom_fields.get("last_dried"))

    initial_total_weight = spool.get("initial_total_weight_g")
    spool_weight = spool.get("empty_spool_weight_g")
    initial_weight = None
    if initial_total_weight is not None and spool_weight is not None:
        initial_weight = max(initial_total_weight - spool_weight, 0)

    extra = dict(existing_extra or {})
    extra["filaman_spool_id"] = _json_string(str(spool["id"]))
    if tag:
        extra["tag"] = _json_string(tag)
    if last_dried:
        extra["last_dried"] = _json_string(last_dried)

    return {
        "first_used": spool.get("stocked_in_at"),
        "last_used": spool.get("last_used_at"),
        "filament_id": filament_id,
        "price": spool.get("purchase_price"),
        "initial_weight": initial_weight,
        "spool_weight": spool_weight,
        "remaining_weight": spool.get("remaining_weight_g"),
        "location": location_name,
        "lot_nr": _clean_text(spool.get("lot_number")),
        "comment": _clean_text(custom_fields.get("comment")),
        "archived": archived,
        "extra": extra,
    }


def migrate(args: argparse.Namespace) -> MigrationStats:
    stats = MigrationStats()
    filaman = FilaManClient(args.filaman_url, args.filaman_auth_header)
    spoolman = SpoolmanClient(args.spoolman_url, args.spoolman_auth_header, args.dry_run)
    try:
        for key, name, field_type in (
            ("filaman_spool_id", "FilaMan Spool ID", "text"),
            ("tag", "Tag", "text"),
            ("last_dried", "Last Dried", "datetime"),
        ):
            if spoolman.ensure_extra_field(key, name, field_type):
                stats.extra_fields_created += 1

        manufacturers = filaman.get_manufacturers()
        filaments = filaman.get_filaments()
        spools = filaman.get_spools(args.include_archived)
        location_names = filaman.get_locations()
        status_map = filaman.get_statuses()

        existing_vendors = spoolman.get_vendors()
        vendor_by_id = {vendor["id"]: vendor for vendor in existing_vendors if vendor.get("id") is not None}
        vendor_by_external_id = {
            vendor.get("external_id"): vendor
            for vendor in existing_vendors
            if vendor.get("external_id")
        }
        vendor_by_name = {
            vendor["name"].casefold(): vendor
            for vendor in existing_vendors
            if vendor.get("name")
        }

        vendor_ids: dict[int, int] = {}
        for manufacturer in manufacturers:
            external_id = f"filaman:manufacturer:{manufacturer['id']}"
            existing_vendor = vendor_by_external_id.get(external_id)
            if existing_vendor is None:
                legacy_spoolman_id = _parse_filaman_spoolman_id(manufacturer)
                if legacy_spoolman_id is not None:
                    existing_vendor = vendor_by_id.get(legacy_spoolman_id)
            if existing_vendor is None:
                existing_vendor = vendor_by_name.get(manufacturer["name"].casefold())

            if existing_vendor is not None:
                vendor_ids[manufacturer["id"]] = existing_vendor["id"]
                stats.vendors_skipped += 1
                continue

            payload = {
                "name": manufacturer["name"],
                "comment": None,
                "empty_spool_weight": manufacturer.get("empty_spool_weight_g"),
                "external_id": external_id,
            }
            created = spoolman.create_vendor(payload)
            vendor_ids[manufacturer["id"]] = created["id"]
            vendor_by_external_id[external_id] = created
            vendor_by_name[manufacturer["name"].casefold()] = created
            stats.vendors_created += 1

        existing_filaments = spoolman.get_filaments()
        filament_by_id = {
            filament["id"]: filament for filament in existing_filaments if filament.get("id") is not None
        }
        filament_by_external_id = {
            filament.get("external_id"): filament
            for filament in existing_filaments
            if filament.get("external_id")
        }
        filament_ids: dict[int, int] = {}

        for filament in filaments:
            external_id = f"filaman:filament:{filament['id']}"
            existing_filament = filament_by_external_id.get(external_id)
            if existing_filament is None:
                legacy_spoolman_id = _parse_filaman_spoolman_id(filament)
                if legacy_spoolman_id is not None:
                    existing_filament = filament_by_id.get(legacy_spoolman_id)
            if existing_filament is not None:
                filament_ids[filament["id"]] = existing_filament["id"]
                stats.filaments_skipped += 1
                continue

            vendor_id = vendor_ids.get(filament.get("manufacturer_id"))
            if vendor_id is None:
                stats.warnings.append(
                    f"Skipping filament {filament.get('id')}: manufacturer {filament.get('manufacturer_id')} missing"
                )
                continue

            color_hex, multi_color_hexes, multi_color_direction = _find_color_payload(filament)
            custom_fields = filament.get("custom_fields") or {}
            density = filament.get("density_g_cm3") or 1.24
            diameter = filament.get("diameter_mm") or 1.75
            payload = {
                "name": filament.get("designation") or f"FilaMan Filament {filament['id']}",
                "vendor_id": vendor_id,
                "material": filament.get("material_type") or "PLA",
                "price": filament.get("price"),
                "density": density,
                "diameter": diameter,
                "weight": filament.get("raw_material_weight_g"),
                "spool_weight": filament.get("default_spool_weight_g"),
                "article_number": _clean_text(custom_fields.get("article_number")),
                "comment": _clean_text(custom_fields.get("comment")),
                "settings_extruder_temp": custom_fields.get("settings_extruder_temp"),
                "settings_bed_temp": custom_fields.get("settings_bed_temp"),
                "color_hex": color_hex,
                "multi_color_hexes": multi_color_hexes,
                "multi_color_direction": multi_color_direction,
                "external_id": external_id,
            }
            created = spoolman.create_filament(payload)
            filament_ids[filament["id"]] = created["id"]
            filament_by_external_id[external_id] = created
            stats.filaments_created += 1

        existing_spools = spoolman.get_spools()
        spool_by_id = {spool["id"]: spool for spool in existing_spools if spool.get("id") is not None}
        spool_by_filaman_id = {
            parsed_id: spool
            for spool in existing_spools
            for parsed_id in [_parse_spool_extra_id(spool, "filaman_spool_id")]
            if parsed_id is not None
        }

        claimed_spoolman_ids = {
            spool["id"]
            for filaman_spool_id, spool in spool_by_filaman_id.items()
            if spool.get("id") is not None and any(str(candidate["id"]) == filaman_spool_id for candidate in spools)
        }

        incoming_existing_spool_ids: set[int] = set()
        for spool in spools:
            existing_spool = _resolve_existing_spool(
                spool,
                spool_by_filaman_id,
                spool_by_id,
                claimed_spoolman_ids=claimed_spoolman_ids,
            )
            if existing_spool is not None and existing_spool.get("id") is not None:
                incoming_existing_spool_ids.add(existing_spool["id"])

        if args.cleanup_first:
            for existing_spool in existing_spools:
                spool_id = existing_spool.get("id")
                if spool_id is None or spool_id in incoming_existing_spool_ids:
                    continue
                spoolman.delete_spool(spool_id)
                stats.spools_deleted += 1

        for spool in spools:
            filaman_spool_id = str(spool["id"])
            filament_id = filament_ids.get(spool.get("filament_id"))
            if filament_id is None:
                stats.warnings.append(
                    f"Skipping spool {spool.get('id')}: filament {spool.get('filament_id')} missing"
                )
                continue

            location_name = None
            if spool.get("location_id") is not None:
                location_name = location_names.get(spool["location_id"])
            if location_name is None and isinstance(spool.get("location"), dict):
                location_name = _clean_text(spool["location"].get("name"))

            status_key = status_map.get(spool.get("status_id"), "new")
            archived = status_key == "archived"
            existing_spool = _resolve_existing_spool(
                spool,
                spool_by_filaman_id,
                spool_by_id,
                claimed_spoolman_ids=claimed_spoolman_ids,
            )
            payload = _build_spool_payload(
                spool=spool,
                filament_id=filament_id,
                location_name=location_name,
                archived=archived,
                existing_extra=existing_spool.get("extra") if existing_spool is not None else None,
            )

            if existing_spool is not None:
                spoolman.update_spool(existing_spool["id"], payload)
                stats.spools_updated += 1
                continue

            legacy_spoolman_id = _parse_filaman_spoolman_id(spool)
            if legacy_spoolman_id is not None and legacy_spoolman_id in claimed_spoolman_ids:
                stats.warnings.append(
                    f"FilaMan spool {spool['id']} references legacy Spoolman spool {legacy_spoolman_id}, "
                    "but that Spoolman spool is already claimed by a direct filaman_spool_id match; creating a new spool."
                )

            spoolman.create_spool(payload)
            stats.spools_created += 1

        return stats
    finally:
        filaman.close()
        spoolman.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import manufacturers, filaments, and spools from a FilaMan instance into Spoolman.",
    )
    parser.add_argument("--filaman-url", required=True, help="Base URL of the FilaMan instance.")
    parser.add_argument("--spoolman-url", required=True, help="Base URL of the Spoolman instance.")
    parser.add_argument(
        "--filaman-auth-header",
        help="Raw Authorization header value for FilaMan, for example 'Bearer <token>'.",
    )
    parser.add_argument(
        "--spoolman-auth-header",
        help="Raw Authorization header value for Spoolman, for example 'Bearer <token>'.",
    )
    parser.add_argument(
        "--include-archived",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include archived FilaMan spools in the import.",
    )
    parser.add_argument(
        "--cleanup-first",
        action="store_true",
        help=(
            "Delete existing Spoolman spools that are not represented by the incoming FilaMan spool set before "
            "creating or updating spools."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and count actions without creating vendors, filaments, spools, or extra fields.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        stats = migrate(args)
    except MigrationError as exc:
        print(f"Migration error: {exc}")
        return 1

    print(f"Extra fields created: {stats.extra_fields_created}")
    print(f"Vendors created: {stats.vendors_created}, skipped: {stats.vendors_skipped}")
    print(f"Filaments created: {stats.filaments_created}, skipped: {stats.filaments_skipped}")
    print(
        "Spools created: "
        f"{stats.spools_created}, updated: {stats.spools_updated}, deleted: {stats.spools_deleted}, "
        f"skipped: {stats.spools_skipped}"
    )
    if stats.warnings:
        print("Warnings:")
        for warning in stats.warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())