from typing import Any, Dict
from pydantic import BaseModel, Field, List
from datetime import datetime


class MoveIn(BaseModel):
    move: Dict[str, Any] = Field(...,
                                 description="The move data in JSON format")


class MoveOut(BaseModel):
    id: int
    matchid: int
    move_number: int
    player: str
    move: Dict[str, Any]
    createdat: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class WSMessage(BaseModel):
    type: str
    payload: Dict[str, Any]


class SyncPayLoad(BaseModel):
    matchid: int
    status: str
    your_role: str
    moves: List[MoveOut]
