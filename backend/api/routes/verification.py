"""Manual verification API — verify evidence as abusive or false positive."""

import math
import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api.schemas.common import PaginatedResponse
from api.schemas.evidence import EvidenceListItem
from api.schemas.verification import VerifyEvidenceRequest, VerifyEvidenceResponse
from auth.middleware import get_current_user
from auth.rbac import require_analyst
from database.connection import get_session
from api.helpers.evidence_abuse import apply_evidence_abuse_fields
from database.models import (
    AIResult,
    AccusedProfile,
    EvidenceReport,
    TargetAccount,
    User,
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/{evidence_id}/verify", response_model=VerifyEvidenceResponse)
async def verify_evidence(
    evidence_id: UUID,
    body: VerifyEvidenceRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_analyst),
) -> VerifyEvidenceResponse:
    """
    Verify an evidence report as abusive or false positive.
    Optionally adds the detected term to the abuse dictionary.
    """
    evidence = await session.get(EvidenceReport, evidence_id)
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found"
        )

    now = datetime.now(timezone.utc)
    added_to_dictionary = False
    term_id = None

    if body.is_abusive:
        evidence.verification_status = "verified_abusive"

        if body.add_to_dictionary:
            # Escape special regex characters in the comment text for pattern use
            pattern = re.escape(evidence.comment_text.strip())
            label = body.label or "abusive"
            term_id = _add_to_dictionary(
                word=evidence.comment_text.strip(),
                regex_pattern=pattern,
                label=label,
                meaning_en=body.meaning_en or "",
                offender_implication=body.offender_implication or "",
            )
            added_to_dictionary = True
    else:
        evidence.verification_status = "false_positive"

    evidence.verified_at = now
    evidence.verified_by = current_user.id

    await session.flush()

    return VerifyEvidenceResponse(
        id=evidence.id,
        evidence_id=evidence.evidence_id,
        verification_status=evidence.verification_status,
        verified_at=now,
        added_to_dictionary=added_to_dictionary,
        term_id=term_id,
    )


@router.get("/unverified", response_model=PaginatedResponse[EvidenceListItem])
async def list_unverified(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> PaginatedResponse[EvidenceListItem]:
    """Paginated list of evidence that has not yet been verified."""
    TargetAlias = aliased(TargetAccount)
    AccusedAlias = aliased(AccusedProfile)

    filter_cond = or_(
        EvidenceReport.verification_status.is_(None),
        EvidenceReport.verification_status == "pending",
    )

    base = (
        select(
            EvidenceReport,
            TargetAlias.username.label("target_username"),
            AccusedAlias.username.label("accused_username"),
            AIResult,
        )
        .outerjoin(TargetAlias, EvidenceReport.target_id == TargetAlias.id)
        .outerjoin(AccusedAlias, EvidenceReport.accused_id == AccusedAlias.id)
        .outerjoin(AIResult, EvidenceReport.ai_result_id == AIResult.id)
        .where(filter_cond)
    )

    count_q = (
        select(func.count())
        .select_from(EvidenceReport)
        .where(filter_cond)
    )

    total = await session.scalar(count_q) or 0
    offset = (page - 1) * page_size
    rows = await session.execute(
        base.order_by(EvidenceReport.created_at.desc()).offset(offset).limit(page_size)
    )

    items: list[EvidenceListItem] = []
    for evidence, target_username, accused_username, ai_row in rows.all():
        item = EvidenceListItem.model_validate(evidence)
        item.target_username = target_username
        item.accused_username = accused_username
        apply_evidence_abuse_fields(item, evidence, ai_row)
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)) if total else 1,
    )


def _add_to_dictionary(
    word: str,
    regex_pattern: str,
    label: str,
    meaning_en: str,
    offender_implication: str,
) -> str:
    """Add term to both abuse_lexicon.json and abuse_term_glossary.json, reload engine."""
    from api.routes.lexicon import _load_json, _save_json, _reload_keyword_engine
    from api.routes.lexicon import _LEXICON_PATH, _GLOSSARY_PATH

    term_id = word.lower().replace(" ", "_").replace("/", "_")

    # Add to abuse_lexicon.json
    lexicon = _load_json(_LEXICON_PATH)
    patterns = lexicon.get("patterns", [])

    # Skip if duplicate regex exists
    if not any(p["regex"] == regex_pattern for p in patterns):
        patterns.append({
            "regex": regex_pattern,
            "score": 0.8,
            "label": label,
        })
        lexicon["patterns"] = patterns
        _save_json(_LEXICON_PATH, lexicon)

    # Add to abuse_term_glossary.json
    glossary = _load_json(_GLOSSARY_PATH)
    terms = glossary.get("terms", [])

    if not any(t["id"] == term_id for t in terms):
        terms.append({
            "id": term_id,
            "detect": regex_pattern,
            "display": word,
            "categories": [label],
            "meaning_en": meaning_en,
            "offender_implication": offender_implication,
        })
        glossary["terms"] = terms
        _save_json(_GLOSSARY_PATH, glossary)

    # Reload keyword engine
    _reload_keyword_engine()

    logger.info("Verification: added term '%s' to dictionary (label=%s)", word, label)
    return term_id
