"""Live system performance metrics endpoint for dashboard monitoring widget."""

from fastapi import APIRouter, Depends

from auth.middleware import get_current_user
from database.models import User
from services.system_metrics_collector import collect_metrics

router = APIRouter()


@router.get("/system-stats")
async def get_system_stats(
    _user: User = Depends(get_current_user),
) -> dict:
    """Real-time system performance metrics (RAM, Swap, CPU, Disk, Bandwidth)."""
    return collect_metrics()
