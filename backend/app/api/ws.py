from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: dict[int, list[WebSocket]] = {}

    async def connect(self, audit_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(audit_id, []).append(websocket)

    def disconnect(self, audit_id: int, websocket: WebSocket):
        if audit_id in self.active:
            self.active[audit_id] = [
                ws for ws in self.active[audit_id] if ws is not websocket
            ]

    async def broadcast(self, audit_id: int, message: dict):
        for ws in self.active.get(audit_id, []):
            await ws.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/audits/{audit_id}")
async def audit_progress(websocket: WebSocket, audit_id: int):
    await manager.connect(audit_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(audit_id, websocket)
