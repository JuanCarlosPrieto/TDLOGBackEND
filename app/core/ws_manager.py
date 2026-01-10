from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[int, Dict[int, WebSocket]] = {}

    async def connect(self, matchid: int, userid: int, websocket: WebSocket):
        await websocket.accept()
        self.rooms.setdefault(matchid, {})
        self.rooms[matchid][userid] = websocket

    def disconnect(self, matchid: int, userid: int):
        if matchid in self.rooms and userid in self.rooms[matchid]:
            del self.rooms[matchid][userid]
            if not self.rooms[matchid]:
                del self.rooms[matchid]

    async def send_to_user(self, matchid: int, userid: int, message: dict):
        websocket = self.rooms.get(matchid, {}).get(userid)
        if websocket:
            await websocket.send_json(message)

    async def broadcast(self, matchid: int, message: dict):
        room = self.rooms.get(matchid, {})
        for connection in room.values():
            await connection.send_json(message)

    async def close_match(self, matchid: int, code: int = 1000):
        room = self.rooms.get(matchid, {})
        for uid, ws in list(room.items()):
            try:
                await ws.close(code=code)
            except Exception:
                pass
            self.disconnect(matchid, uid)


connection_manager = ConnectionManager()
