"""Dashboard WebSocket event payloads."""

from typing import Any, Optional

from websocket.manager import ws_manager


async def broadcast_evidence_created(
    *,
    evidence_id: str,
    severity: str,
    platform: str,
    target_username: Optional[str],
    comment_preview: str,
    risk_score: int,
) -> None:
    await ws_manager.broadcast_json(
        {
            "type": "evidence_created",
            "data": {
                "evidence_id": evidence_id,
                "severity_level": severity,
                "platform": platform,
                "target_username": target_username,
                "comment_preview": comment_preview[:200],
                "risk_score": risk_score,
            },
        }
    )


async def broadcast_crawl_completed(
    *,
    target_username: str,
    comments_new: int,
    abusive_detected: int,
    success: bool,
) -> None:
    await ws_manager.broadcast_json(
        {
            "type": "crawl_completed",
            "data": {
                "target_username": target_username,
                "comments_new": comments_new,
                "abusive_detected": abusive_detected,
                "success": success,
            },
        }
    )


async def broadcast_stats_updated(stats: dict[str, Any]) -> None:
    await ws_manager.broadcast_json({"type": "stats_updated", "data": stats})
