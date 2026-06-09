"""Manual verification schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VerifyEvidenceRequest(BaseModel):
    is_abusive: bool = Field(description="Whether the evidence is confirmed abusive")
    add_to_dictionary: bool = Field(
        default=False,
        description="If abusive, whether to add the term to the abuse dictionary",
    )
    label: Optional[str] = Field(
        default=None, description="Category label (hate_speech, threat, etc.)"
    )
    meaning_en: Optional[str] = Field(default=None, description="English meaning of the term")
    offender_implication: Optional[str] = Field(
        default=None, description="Implication of using this term"
    )


class VerifyEvidenceResponse(BaseModel):
    id: UUID
    evidence_id: str
    verification_status: str
    verified_at: datetime
    added_to_dictionary: bool
    term_id: Optional[str] = None
