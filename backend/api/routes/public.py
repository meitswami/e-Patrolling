"""Public website endpoints (no auth)."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.website import IndiaLocationsResponse, SafetyRequestCreate, SafetyRequestResponse
from database.connection import get_session
from database.models import WebsiteRequestStatus, WebsiteSafetyRequest
from utils.profile_parse import parse_profile_input

router = APIRouter()

_LOCATIONS_PATH = Path(__file__).resolve().parents[2] / "data" / "india_locations.json"
_locations_cache: dict[str, list[str]] | None = None


def _load_locations() -> dict[str, list[str]]:
    global _locations_cache
    if _locations_cache is None:
        with open(_LOCATIONS_PATH, encoding="utf-8") as f:
            _locations_cache = json.load(f)
    return _locations_cache


@router.get("/locations/india", response_model=IndiaLocationsResponse)
async def india_locations() -> IndiaLocationsResponse:
    """State and city dropdown data for the public safety form."""
    data = _load_locations()
    states = sorted(data.keys())
    return IndiaLocationsResponse(states=states, cities_by_state=data)


@router.post(
    "/safety-request",
    response_model=SafetyRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_safety_request(
    body: SafetyRequestCreate,
    session: AsyncSession = Depends(get_session),
) -> SafetyRequestResponse:
    """Public form: Want to be Safe — website intake (not admin targets)."""
    locations = _load_locations()
    if body.state not in locations:
        raise HTTPException(status_code=400, detail="Invalid state")
    if body.city not in locations[body.state]:
        raise HTTPException(status_code=400, detail="Invalid city for selected state")

    parsed_entries: list[dict] = []
    for entry in body.profile_entries:
        try:
            platform, username, profile_url = parse_profile_input(entry.value)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        parsed_entries.append(
            {
                "raw": entry.value.strip(),
                "platform": platform.value,
                "username": username,
                "profile_url": profile_url,
            }
        )

    row = WebsiteSafetyRequest(
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        profile_entries=parsed_entries,
        state=body.state,
        city=body.city,
        message=body.message,
        status=WebsiteRequestStatus.PENDING,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return SafetyRequestResponse.model_validate(row)
