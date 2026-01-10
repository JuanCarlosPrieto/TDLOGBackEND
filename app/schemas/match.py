from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel


class MatchBase(BaseModel):
    matchid: int
    startedat: datetime
    finishedat: Optional[datetime]
    whiteuser: Optional[int]
    blackuser: Optional[int]
    result: Literal["white", "black", "draw", "none"]
    reason: Literal["normal", "resign", "timeout", "agreement", "abandon",
                    "none"]
    status: Literal["waiting", "ongoing", "finished", "aborted"]

    class Config:
        orm_mode = True
        from_attributes = True


class FindMatchResponse(BaseModel):
    match: MatchBase
    role: Literal["white", "black"]
    waiting: bool
