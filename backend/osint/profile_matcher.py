"""Match accused profiles across platforms by username, avatar, and bio."""

from __future__ import annotations

from typing import Any

from database.models import AccusedProfile
from osint.bio_match import bio_similarity, display_name_similarity, username_similarity

PATROL_PLATFORMS = ("instagram", "facebook", "twitter", "threads")

PLATFORM_PROFILE_URL = {
    "instagram": "https://www.instagram.com/{u}/",
    "facebook": "https://www.facebook.com/{u}",
    "twitter": "https://twitter.com/{u}",
    "threads": "https://www.threads.net/@{u}",
}


def _match_confidence(signals: list[str]) -> float:
    weights = {
        "exact_username": 0.45,
        "similar_username": 0.25,
        "same_avatar_hash": 0.35,
        "similar_bio": 0.2,
        "same_display_name": 0.15,
        "username_candidate": 0.12,
    }
    score = sum(weights.get(s, 0.1) for s in signals)
    return min(1.0, round(score, 2))


def profile_to_dict(p: AccusedProfile, signals: list[str], in_db: bool = True) -> dict[str, Any]:
    return {
        "profile_id": str(p.id),
        "platform": p.platform.value,
        "username": p.username,
        "display_name": p.display_name,
        "bio": getattr(p, "bio", None),
        "profile_url": p.profile_url,
        "avatar_url": p.avatar_url,
        "avatar_hash": getattr(p, "avatar_hash", None),
        "confidence": _match_confidence(signals),
        "match_signals": signals,
        "in_database": in_db,
        "total_incidents": p.total_incidents,
    }


def find_database_matches(
    seed_profiles: list[AccusedProfile],
    all_profiles: list[AccusedProfile],
) -> list[dict[str, Any]]:
    """Find other DB profiles that may be the same person."""
    seed_ids = {p.id for p in seed_profiles}
    matches: list[dict[str, Any]] = []
    seen_ids: set = set()

    for seed in seed_profiles:
        for other in all_profiles:
            if other.id in seed_ids or other.id in seen_ids:
                continue
            signals: list[str] = []
            u_sim = username_similarity(seed.username, other.username)
            if u_sim >= 1.0:
                signals.append("exact_username")
            elif u_sim >= 0.7:
                signals.append("similar_username")

            seed_hash = getattr(seed, "avatar_hash", None)
            other_hash = getattr(other, "avatar_hash", None)
            if seed_hash and other_hash and seed_hash == other_hash:
                signals.append("same_avatar_hash")

            bio_sim = bio_similarity(getattr(seed, "bio", None), getattr(other, "bio", None))
            if bio_sim >= 0.45:
                signals.append("similar_bio")

            dn_sim = display_name_similarity(seed.display_name, other.display_name)
            if dn_sim >= 0.75:
                signals.append("same_display_name")

            if not signals:
                continue

            seen_ids.add(other.id)
            matches.append(profile_to_dict(other, signals))

    matches.sort(key=lambda x: x["confidence"], reverse=True)
    return matches


def generate_platform_candidates(username: str, known_platforms: set[str]) -> list[dict[str, Any]]:
    """Suggest profile URLs on platforms where we have not yet seen this handle."""
    u = username.lstrip("@")
    candidates: list[dict[str, Any]] = []
    for plat in PATROL_PLATFORMS:
        if plat in known_platforms:
            continue
        url = PLATFORM_PROFILE_URL[plat].format(u=u)
        candidates.append(
            {
                "platform": plat,
                "username": u,
                "profile_url": url,
                "confidence": 0.15,
                "match_signals": ["username_candidate"],
                "in_database": False,
                "note": "Manual verification required — handle may exist on this network",
            }
        )
    return candidates
