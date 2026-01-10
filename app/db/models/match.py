from sqlalchemy import Enum, Column, BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.session import Base


match_status_enum = Enum(
    "waiting",
    "ongoing",
    "finished",
    "aborted",
    name="match_status"
)


match_result_enum = Enum(
    "white",
    "black",
    "draw",
    "none",
    name="match_result"
)


match_reason_enum = Enum(
    "normal",
    "resign",
    "timeout",
    "agreement",
    "abandon",
    "none",
    name="match_reason"
)


class Match(Base):
    __tablename__ = "matches"

    matchid = Column(BigInteger, primary_key=True, autoincrement=True)
    startedat = Column(DateTime, nullable=False, server_default=func.now())
    finishedat = Column(DateTime)
    whiteuser = Column(BigInteger, ForeignKey("users.userid"))
    blackuser = Column(BigInteger, ForeignKey("users.userid"))
    result = Column(match_result_enum, nullable=False, default="none")
    reason = Column(match_reason_enum, nullable=False, default="none")
    status = Column(match_status_enum, nullable=False, default="waiting")

    white = relationship("User", foreign_keys=[whiteuser])
    black = relationship("User", foreign_keys=[blackuser])
