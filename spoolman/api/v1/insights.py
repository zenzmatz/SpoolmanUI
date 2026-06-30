"""Insights dashboard endpoints."""

import json
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from spoolman.api.v1.models import SpoolmanDateTime
from spoolman.database import insights, setting as db_setting
from spoolman.database.database import get_db_session
from spoolman.exceptions import ItemNotFoundError
from spoolman.settings import parse_setting

router = APIRouter(
    prefix="/insights",
    tags=["insights"],
)


class InsightsOverview(BaseModel):
    spool_count: int = Field()
    active_spool_count: int = Field()
    archived_spool_count: int = Field()
    low_stock_count: int = Field()
    out_of_stock_count: int = Field()
    material_count: int = Field()
    location_count: int = Field()
    vendor_count: int = Field()
    remaining_weight_total_g: float = Field()
    used_weight_total_g: float = Field()
    updated_at: SpoolmanDateTime = Field()


class LowStockSpool(BaseModel):
    spool_id: int = Field()
    filament_id: int = Field()
    vendor_name: str | None = Field(None)
    filament_name: str | None = Field(None)
    material: str | None = Field(None)
    location: str | None = Field(None)
    remaining_weight_g: float | None = Field(None)
    used_weight_g: float = Field()
    color_hex: str | None = Field(None)
    multi_color_hexes: str | None = Field(None)
    last_used: SpoolmanDateTime | None = Field(None)
    archived: bool = Field()


class LowStockResponse(BaseModel):
    threshold_g: float = Field()
    total: int = Field()
    items: list[LowStockSpool] = Field(default_factory=list)


class MaterialSummary(BaseModel):
    material: str = Field()
    spool_count: int = Field()
    low_stock_count: int = Field()
    remaining_weight_total_g: float = Field()
    used_weight_total_g: float = Field()
    percentage_of_inventory: float = Field()


class MaterialSummaryResponse(BaseModel):
    items: list[MaterialSummary] = Field(default_factory=list)


class LocationSummary(BaseModel):
    location: str = Field()
    spool_count: int = Field()
    low_stock_count: int = Field()
    remaining_weight_total_g: float = Field()
    materials: list[str] = Field(default_factory=list)


class LocationSummaryResponse(BaseModel):
    items: list[LocationSummary] = Field(default_factory=list)


class ColorSummary(BaseModel):
    color_key: str = Field()
    display_name: str = Field()
    display_hex: str | None = Field(None)
    spool_count: int = Field()
    remaining_weight_total_g: float = Field()


class ColorSummaryResponse(BaseModel):
    items: list[ColorSummary] = Field(default_factory=list)


class RecentActivityItem(BaseModel):
    spool_id: int = Field()
    filament_name: str | None = Field(None)
    vendor_name: str | None = Field(None)
    material: str | None = Field(None)
    location: str | None = Field(None)
    last_used: SpoolmanDateTime = Field()
    remaining_weight_g: float | None = Field(None)
    used_weight_g: float = Field()


class RecentActivityResponse(BaseModel):
    days: int = Field()
    items: list[RecentActivityItem] = Field(default_factory=list)


def _parse_id_list(value: str | None) -> int | Sequence[int] | None:
    if value is None:
        return None
    values = [int(item) for item in value.split(",")]
    if len(values) == 1:
        return values[0]
    return values


def _common_filters(
    *,
    allow_archived: bool,
    location: str | None,
    material: str | None,
    vendor_id: str | None,
    filament_id: str | None,
) -> dict[str, int | Sequence[int] | str | bool | None]:
    return {
        "allow_archived": allow_archived,
        "location": location,
        "material": material,
        "vendor_id": _parse_id_list(vendor_id),
        "filament_id": _parse_id_list(filament_id),
    }


async def _resolve_threshold_g(db: AsyncSession, threshold_g: float | None) -> float:
    if threshold_g is not None:
        return threshold_g

    definition = parse_setting("insights_low_stock_threshold_g")
    try:
        db_item = await db_setting.get(db, definition)
        return float(json.loads(db_item.value))
    except ItemNotFoundError:
        return float(json.loads(definition.default))


@router.get("/overview")
async def overview(
    *,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    allow_archived: bool = False,
    threshold_g: Annotated[float | None, Query(ge=0)] = None,
    location: str | None = None,
    material: str | None = None,
    vendor_id: Annotated[str | None, Query(pattern=r"^-?\d+(,-?\d+)*$")] = None,
    filament_id: Annotated[str | None, Query(pattern=r"^-?\d+(,-?\d+)*$")] = None,
) -> InsightsOverview:
    resolved_threshold_g = await _resolve_threshold_g(db, threshold_g)
    return InsightsOverview(
        **await insights.get_overview(
            db=db,
            threshold_g=resolved_threshold_g,
            **_common_filters(
                allow_archived=allow_archived,
                location=location,
                material=material,
                vendor_id=vendor_id,
                filament_id=filament_id,
            ),
        ),
    )


@router.get("/low-stock")
async def low_stock(
    *,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    allow_archived: bool = False,
    threshold_g: Annotated[float | None, Query(ge=0)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    location: str | None = None,
    material: str | None = None,
    vendor_id: Annotated[str | None, Query(pattern=r"^-?\d+(,-?\d+)*$")] = None,
    filament_id: Annotated[str | None, Query(pattern=r"^-?\d+(,-?\d+)*$")] = None,
) -> LowStockResponse:
    resolved_threshold_g = await _resolve_threshold_g(db, threshold_g)
    return LowStockResponse(
        **await insights.get_low_stock(
            db=db,
            threshold_g=resolved_threshold_g,
            limit=limit,
            **_common_filters(
                allow_archived=allow_archived,
                location=location,
                material=material,
                vendor_id=vendor_id,
                filament_id=filament_id,
            ),
        ),
    )


@router.get("/by-material")
async def by_material(
    *,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    allow_archived: bool = False,
    threshold_g: Annotated[float | None, Query(ge=0)] = None,
    location: str | None = None,
    material: str | None = None,
    vendor_id: Annotated[str | None, Query(pattern=r"^-?\d+(,-?\d+)*$")] = None,
    filament_id: Annotated[str | None, Query(pattern=r"^-?\d+(,-?\d+)*$")] = None,
) -> MaterialSummaryResponse:
    resolved_threshold_g = await _resolve_threshold_g(db, threshold_g)
    items = await insights.get_material_summary(
        db=db,
        threshold_g=resolved_threshold_g,
        **_common_filters(
            allow_archived=allow_archived,
            location=location,
            material=material,
            vendor_id=vendor_id,
            filament_id=filament_id,
        ),
    )
    return MaterialSummaryResponse(items=[MaterialSummary(**item) for item in items])


@router.get("/by-location")
async def by_location(
    *,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    allow_archived: bool = False,
    threshold_g: Annotated[float | None, Query(ge=0)] = None,
    location: str | None = None,
    material: str | None = None,
    vendor_id: Annotated[str | None, Query(pattern=r"^-?\d+(,-?\d+)*$")] = None,
    filament_id: Annotated[str | None, Query(pattern=r"^-?\d+(,-?\d+)*$")] = None,
) -> LocationSummaryResponse:
    resolved_threshold_g = await _resolve_threshold_g(db, threshold_g)
    items = await insights.get_location_summary(
        db=db,
        threshold_g=resolved_threshold_g,
        **_common_filters(
            allow_archived=allow_archived,
            location=location,
            material=material,
            vendor_id=vendor_id,
            filament_id=filament_id,
        ),
    )
    return LocationSummaryResponse(items=[LocationSummary(**item) for item in items])


@router.get("/by-color")
async def by_color(
    *,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    allow_archived: bool = False,
    location: str | None = None,
    material: str | None = None,
    vendor_id: Annotated[str | None, Query(pattern=r"^-?\d+(,-?\d+)*$")] = None,
    filament_id: Annotated[str | None, Query(pattern=r"^-?\d+(,-?\d+)*$")] = None,
) -> ColorSummaryResponse:
    items = await insights.get_color_summary(
        db=db,
        **_common_filters(
            allow_archived=allow_archived,
            location=location,
            material=material,
            vendor_id=vendor_id,
            filament_id=filament_id,
        ),
    )
    return ColorSummaryResponse(items=[ColorSummary(**item) for item in items])


@router.get("/recent-activity")
async def recent_activity(
    *,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    allow_archived: bool = False,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    location: str | None = None,
    material: str | None = None,
    vendor_id: Annotated[str | None, Query(pattern=r"^-?\d+(,-?\d+)*$")] = None,
    filament_id: Annotated[str | None, Query(pattern=r"^-?\d+(,-?\d+)*$")] = None,
) -> RecentActivityResponse:
    return RecentActivityResponse(
        **await insights.get_recent_activity(
            db=db,
            days=days,
            limit=limit,
            **_common_filters(
                allow_archived=allow_archived,
                location=location,
                material=material,
                vendor_id=vendor_id,
                filament_id=filament_id,
            ),
        ),
    )