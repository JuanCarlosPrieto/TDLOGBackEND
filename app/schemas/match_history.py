from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel, ConfigDict


class MatchSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    matchid: int
    whiteuser: int | None
    blackuser: int | None

    status: str
    winner: Optional[int]

    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    my_role: Optional[str] = None
    opponent_userid: Optional[int] = None
    moves_count: Optional[int] = None


class MatchDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    matchid: int
    whiteuser: int
    blackuser: int
    status: str
    winner: Optional[int]
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class MatchMoveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matchid: int
    move_number: int
    player: str
    move: Any
    created_at: Optional[datetime] = None


class MatchMovesPageOut(BaseModel):
    matchid: int
    total: int
    items: List[MatchMoveOut]
