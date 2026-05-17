"""Run OSINT lookup for an accused username and persist results."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AccusedProfile, CrawledComment, EvidenceReport
from osint.avatar_hash import compute_avatar_hash
from osint.network_hints import extract_network_hints, merge_network_hints
from osint.profile_matcher import (
    find_database_matches,
    generate_platform_candidates,
    profile_to_dict,
)
from osint.bio_match import username_similarity
from services.accused_dossier import find_accused_profiles_by_username


async def refresh_profile_osint_fields(session: AsyncSession, profile: AccusedProfile) -> None:
    """Update avatar hash from stored avatar URL."""
    if profile.avatar_url and not getattr(profile, "avatar_hash", None):
        profile.avatar_hash = await compute_avatar_hash(profile.avatar_url)


async def run_osint_lookup(
    session: AsyncSession,
    username: str,
) -> Optional[dict[str, Any]]:
    """
    Cross-platform OSINT: match by username, display picture hash, bio, and name.
    Returns structured report; persists to accused_profiles.osint_data.
    """
    seed_profiles = await find_accused_profiles_by_username(session, username)
    if not seed_profiles:
        return None

    for p in seed_profiles:
        await refresh_profile_osint_fields(session, p)

    normalized = username.lstrip("@").lower()
    # Broader DB scan: similar usernames, same avatar hash, or bio overlap
    seed_hashes = {p.avatar_hash for p in seed_profiles if getattr(p, "avatar_hash", None)}
    conditions = [func.lower(AccusedProfile.username) == normalized]
    if seed_hashes:
        conditions.append(AccusedProfile.avatar_hash.in_(seed_hashes))
    for seed in seed_profiles:
        if seed.display_name:
            conditions.append(
                func.lower(AccusedProfile.display_name) == seed.display_name.lower()
            )

    result = await session.execute(
        select(AccusedProfile).where(or_(*conditions)).limit(500)
    )
    candidate_pool = list(result.scalars().all())

    # Also load profiles with similar username prefix
    prefix_result = await session.execute(
        select(AccusedProfile)
        .where(func.lower(AccusedProfile.username).like(f"{normalized[:4]}%"))
        .limit(200)
    )
    pool_ids = {p.id for p in candidate_pool}
    for p in prefix_result.scalars().all():
        if p.id not in pool_ids:
            if username_similarity(normalized, p.username) >= 0.7:
                candidate_pool.append(p)
                pool_ids.add(p.id)

    db_matches = find_database_matches(seed_profiles, candidate_pool)
    known_platforms = {p.platform.value for p in seed_profiles}
    for m in db_matches:
        known_platforms.add(m["platform"])

    platform_candidates = generate_platform_candidates(
        seed_profiles[0].username, known_platforms
    )

    # Network hints from evidence raw_data
    accused_ids = [p.id for p in seed_profiles]
    ev_rows = await session.execute(
        select(EvidenceReport, CrawledComment.raw_data)
        .outerjoin(CrawledComment, EvidenceReport.comment_id == CrawledComment.id)
        .where(EvidenceReport.accused_id.in_(accused_ids))
        .limit(200)
    )
    hint_records = []
    for ev, raw in ev_rows.all():
        raw = raw or {}
        if ev.permalink_snapshot and isinstance(ev.permalink_snapshot, dict):
            raw = {**raw, **(ev.permalink_snapshot.get("raw_network") or {})}
        hint_records.append(extract_network_hints(raw))

    network_hints = merge_network_hints(hint_records) if hint_records else extract_network_hints({})

    seed_summaries = [
        profile_to_dict(p, ["seed_profile"], in_db=True) for p in seed_profiles
    ]

    report: dict[str, Any] = {
        "username": seed_profiles[0].username,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed_profiles": seed_summaries,
        "linked_profiles": db_matches,
        "platform_candidates": platform_candidates,
        "network_hints": network_hints,
        "match_summary": {
            "database_links": len(db_matches),
            "platforms_confirmed": sorted(known_platforms),
            "candidates_to_verify": len(platform_candidates),
        },
    }

    now = datetime.now(timezone.utc)
    for p in seed_profiles:
        p.osint_data = report
        p.osint_updated_at = now

    await session.flush()
    return report
