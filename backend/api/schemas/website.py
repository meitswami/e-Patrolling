"""Website safety intake schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from database.models import WebsiteRequestStatus


class ProfileEntryInput(BaseModel):
    value: str = Field(min_length=1, max_length=2000, description="Username or profile URL")


class SafetyRequestCreate(BaseModel):
    profile_entries: list[ProfileEntryInput] = Field(min_length=1, max_length=10)
    state: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    contact_name: Optional[str] = Field(default=None, max_length=255)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    message: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("profile_entries")
    @classmethod
    def at_least_one_profile(cls, v: list[ProfileEntryInput]) -> list[ProfileEntryInput]:
        if not v:
            raise ValueError("Add at least one profile username or link")
        return v


class SafetyRequestResponse(BaseModel):
    id: UUID
    contact_name: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    profile_entries: list[dict]
    state: str
    city: str
    message: Optional[str]
    status: WebsiteRequestStatus
    admin_notes: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SafetyRequestUpdate(BaseModel):
    status: Optional[WebsiteRequestStatus] = None
    admin_notes: Optional[str] = None


class IndiaLocationsResponse(BaseModel):
    states: list[str]
    cities_by_state: dict[str, list[str]]
