"""Dashboard WebSocket event payloads."""

from datetime import datetime, timezone
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


async def broadcast_crawl_activity(
    *,
    target_username: str,
    activity_type: str,
    message: str,
    detail: Optional[str] = None,
    platform: str = "instagram",
) -> None:
    """
    Real-time crawl activity stream — replaces the visible browser window.

    activity_type values:
      - crawl_started: Crawl begins for a target
      - navigating_profile: Loading the profile page
      - collecting_posts: Scrolling to find post URLs
      - opening_post: Navigating to an individual post
      - expanding_comments: Clicking "View all comments" buttons
      - comments_found: Parsed comments from a post
      - comment_abusive: A specific comment was classified as abusive
      - post_complete: Finished processing a post
      - crawl_finished: Crawl completed for the target
      - crawl_error: An error occurred
    """
    await ws_manager.broadcast_json(
        {
            "type": "crawl_activity",
            "data": {
                "target_username": target_username,
                "platform": platform,
                "activity_type": activity_type,
                "message": message,
                "detail": detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    )
