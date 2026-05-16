"""WebSocket endpoint for live dashboard updates."""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from auth.jwt_handler import decode_access_token
from websocket.manager import ws_manager

router = APIRouter()


@router.websocket("/dashboard")
async def dashboard_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    try:
        decode_access_token(token)
    except Exception:
        await websocket.close(code=4401)
        return

    await ws_manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected", "data": {"channel": "dashboard"}})
        while True:
            # Keep connection alive; client may send ping
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
