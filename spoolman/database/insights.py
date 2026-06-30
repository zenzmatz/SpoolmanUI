"""Aggregation helpers for the insights dashboard."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from spoolman.database import spool
from spoolman.database import models as db_models


def _remaining_weight(db_spool: db_models.Spool) -> float | None:
    baseline = db_spool.initial_weight
    if baseline is None:
        baseline = db_spool.filament.weight
    if baseline is None:
        return None
    return max(baseline - db_spool.used_weight, 0.0)


def _normalized_location(location: str | None) -> str:
    if location is None or location.strip() == "":
        return "Unassigned"
    return location


def _normalized_material(material: str | None) -> str:
    if material is None or material.strip() == "":
        return "Unknown"
    return material


def _vendor_name(db_spool: db_models.Spool) -> str | None:
    vendor = db_spool.filament.vendor
    if vendor is None:
        return None
    return vendor.name


def _filament_name(db_spool: db_models.Spool) -> str | None:
    return db_spool.filament.name


def _color_bucket(db_spool: db_models.Spool) -> tuple[str, str, str | None]:
    filament = db_spool.filament
    if filament.color_hex:
        color_hex = filament.color_hex.replace("#", "").upper()
        return (f"#{color_hex}", f"#{color_hex}", color_hex)
    if filament.multi_color_hexes:
        return (f"MULTI:{filament.multi_color_hexes}", "Multi-color", None)
    return ("UNKNOWN", "Unknown", None)


async def _find_spools(
    *,
    db: AsyncSession,
    allow_archived: bool = False,
    location: str | None = None,
    material: str | None = None,
    vendor_id: int | Sequence[int] | None = None,
    filament_id: int | Sequence[int] | None = None,
) -> list[db_models.Spool]:
    db_items, _ = await spool.find(
        db=db,
        filament_id=filament_id,
        filament_material=material,
        vendor_id=vendor_id,
        location=location,
        allow_archived=allow_archived,
    )
    return db_items


async def get_overview(
    *,
    db: AsyncSession,
    allow_archived: bool = False,
    threshold_g: float = 200.0,
    location: str | None = None,
    material: str | None = None,
    vendor_id: int | Sequence[int] | None = None,
    filament_id: int | Sequence[int] | None = None,
) -> dict[str, Any]:
    spools = await _find_spools(
        db=db,
        allow_archived=allow_archived,
        location=location,
        material=material,
        vendor_id=vendor_id,
        filament_id=filament_id,
    )

    known_remaining_weights = [weight for item in spools if (weight := _remaining_weight(item)) is not None]
    low_stock_count = sum(1 for weight in known_remaining_weights if 0 < weight <= threshold_g)
    out_of_stock_count = sum(1 for weight in known_remaining_weights if weight <= 0)
    locations = {_normalized_location(item.location) for item in spools}
    materials = {_normalized_material(item.filament.material) for item in spools}
    vendor_ids = {item.filament.vendor.id for item in spools if item.filament.vendor is not None}

    return {
        "spool_count": len(spools),
        "active_spool_count": sum(1 for item in spools if not bool(item.archived)),
        "archived_spool_count": sum(1 for item in spools if bool(item.archived)),
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "material_count": len(materials),
        "location_count": len(locations),
        "vendor_count": len(vendor_ids),
        "remaining_weight_total_g": round(sum(known_remaining_weights), 2),
        "used_weight_total_g": round(sum(item.used_weight for item in spools), 2),
        "updated_at": datetime.now(timezone.utc),
    }


async def get_low_stock(
    *,
    db: AsyncSession,
    threshold_g: float = 200.0,
    limit: int = 20,
    allow_archived: bool = False,
    location: str | None = None,
    material: str | None = None,
    vendor_id: int | Sequence[int] | None = None,
    filament_id: int | Sequence[int] | None = None,
) -> dict[str, Any]:
    spools = await _find_spools(
        db=db,
        allow_archived=allow_archived,
        location=location,
        material=material,
        vendor_id=vendor_id,
        filament_id=filament_id,
    )

    items = []
    for item in spools:
        remaining_weight = _remaining_weight(item)
        if remaining_weight is None or remaining_weight > threshold_g:
            continue
        items.append(
            {
                "spool_id": item.id,
                "filament_id": item.filament_id,
                "vendor_name": _vendor_name(item),
                "filament_name": _filament_name(item),
                "material": _normalized_material(item.filament.material),
                "location": _normalized_location(item.location),
                "remaining_weight_g": round(remaining_weight, 2),
                "used_weight_g": round(item.used_weight, 2),
                "color_hex": item.filament.color_hex,
                "multi_color_hexes": item.filament.multi_color_hexes,
                "last_used": item.last_used,
                "archived": bool(item.archived),
            },
        )

    items.sort(key=lambda spool_item: (spool_item["remaining_weight_g"], spool_item["spool_id"]))
    return {
        "threshold_g": threshold_g,
        "total": len(items),
        "items": items[:limit],
    }


async def get_material_summary(
    *,
    db: AsyncSession,
    allow_archived: bool = False,
    threshold_g: float = 200.0,
    location: str | None = None,
    material: str | None = None,
    vendor_id: int | Sequence[int] | None = None,
    filament_id: int | Sequence[int] | None = None,
) -> list[dict[str, Any]]:
    spools = await _find_spools(
        db=db,
        allow_archived=allow_archived,
        location=location,
        material=material,
        vendor_id=vendor_id,
        filament_id=filament_id,
    )

    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "spool_count": 0,
            "low_stock_count": 0,
            "remaining_weight_total_g": 0.0,
            "used_weight_total_g": 0.0,
        },
    )

    total_remaining = 0.0
    for item in spools:
        key = _normalized_material(item.filament.material)
        group = grouped[key]
        group["spool_count"] += 1
        group["used_weight_total_g"] += item.used_weight

        remaining_weight = _remaining_weight(item)
        if remaining_weight is not None:
            group["remaining_weight_total_g"] += remaining_weight
            total_remaining += remaining_weight
            if 0 < remaining_weight <= threshold_g:
                group["low_stock_count"] += 1

    items = []
    for key, group in grouped.items():
        remaining_weight_total = round(group["remaining_weight_total_g"], 2)
        items.append(
            {
                "material": key,
                "spool_count": group["spool_count"],
                "low_stock_count": group["low_stock_count"],
                "remaining_weight_total_g": remaining_weight_total,
                "used_weight_total_g": round(group["used_weight_total_g"], 2),
                "percentage_of_inventory": round((remaining_weight_total / total_remaining) * 100, 2)
                if total_remaining > 0
                else 0.0,
            },
        )

    items.sort(key=lambda item: (-item["remaining_weight_total_g"], -item["spool_count"], item["material"]))
    return items


async def get_location_summary(
    *,
    db: AsyncSession,
    allow_archived: bool = False,
    threshold_g: float = 200.0,
    location: str | None = None,
    material: str | None = None,
    vendor_id: int | Sequence[int] | None = None,
    filament_id: int | Sequence[int] | None = None,
) -> list[dict[str, Any]]:
    spools = await _find_spools(
        db=db,
        allow_archived=allow_archived,
        location=location,
        material=material,
        vendor_id=vendor_id,
        filament_id=filament_id,
    )

    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "spool_count": 0,
            "low_stock_count": 0,
            "remaining_weight_total_g": 0.0,
            "materials": set(),
        },
    )

    for item in spools:
        key = _normalized_location(item.location)
        group = grouped[key]
        group["spool_count"] += 1
        group["materials"].add(_normalized_material(item.filament.material))

        remaining_weight = _remaining_weight(item)
        if remaining_weight is not None:
            group["remaining_weight_total_g"] += remaining_weight
            if 0 < remaining_weight <= threshold_g:
                group["low_stock_count"] += 1

    items = []
    for key, group in grouped.items():
        items.append(
            {
                "location": key,
                "spool_count": group["spool_count"],
                "low_stock_count": group["low_stock_count"],
                "remaining_weight_total_g": round(group["remaining_weight_total_g"], 2),
                "materials": sorted(group["materials"]),
            },
        )

    items.sort(key=lambda item: (-item["remaining_weight_total_g"], -item["spool_count"], item["location"]))
    return items


async def get_color_summary(
    *,
    db: AsyncSession,
    allow_archived: bool = False,
    location: str | None = None,
    material: str | None = None,
    vendor_id: int | Sequence[int] | None = None,
    filament_id: int | Sequence[int] | None = None,
) -> list[dict[str, Any]]:
    spools = await _find_spools(
        db=db,
        allow_archived=allow_archived,
        location=location,
        material=material,
        vendor_id=vendor_id,
        filament_id=filament_id,
    )

    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "display_name": "Unknown",
            "display_hex": None,
            "spool_count": 0,
            "remaining_weight_total_g": 0.0,
        },
    )

    for item in spools:
        color_key, display_name, display_hex = _color_bucket(item)
        group = grouped[color_key]
        group["display_name"] = display_name
        group["display_hex"] = display_hex
        group["spool_count"] += 1
        remaining_weight = _remaining_weight(item)
        if remaining_weight is not None:
            group["remaining_weight_total_g"] += remaining_weight

    items = []
    for color_key, group in grouped.items():
        items.append(
            {
                "color_key": color_key,
                "display_name": group["display_name"],
                "display_hex": group["display_hex"],
                "spool_count": group["spool_count"],
                "remaining_weight_total_g": round(group["remaining_weight_total_g"], 2),
            },
        )

    items.sort(key=lambda item: (-item["remaining_weight_total_g"], -item["spool_count"], item["display_name"]))
    return items


async def get_recent_activity(
    *,
    db: AsyncSession,
    days: int = 30,
    limit: int = 20,
    allow_archived: bool = False,
    location: str | None = None,
    material: str | None = None,
    vendor_id: int | Sequence[int] | None = None,
    filament_id: int | Sequence[int] | None = None,
) -> dict[str, Any]:
    spools = await _find_spools(
        db=db,
        allow_archived=allow_archived,
        location=location,
        material=material,
        vendor_id=vendor_id,
        filament_id=filament_id,
    )

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    items = []
    for item in spools:
        if item.last_used is None or item.last_used < cutoff:
            continue
        items.append(
            {
                "spool_id": item.id,
                "filament_name": _filament_name(item),
                "vendor_name": _vendor_name(item),
                "material": _normalized_material(item.filament.material),
                "location": _normalized_location(item.location),
                "last_used": item.last_used,
                "remaining_weight_g": round(_remaining_weight(item), 2) if _remaining_weight(item) is not None else None,
                "used_weight_g": round(item.used_weight, 2),
            },
        )

    items.sort(key=lambda item: (item["last_used"], item["spool_id"]), reverse=True)
    return {
        "days": days,
        "items": items[:limit],
    }