from app.db.session import Base
from sqlalchemy.orm import relationship
from sqlalchemy import (
    Enum,
    Column,
    BigInteger,
    JSON,
    DateTime,
    ForeignKey,
    func)
from sqlalchemy import UniqueConstraint

__table_args__ = (
    UniqueConstraint("matchid", "move_number", name="uq_match_move_number"),
)


match_move_player_enum = Enum(
    "white",
    "black",
    name="match_move_player"
)


class MatchMove(Base):
    __tablename__ = "match_moves"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    matchid = Column(BigInteger, ForeignKey("matches.matchid"), nullable=False)
    move_number = Column(BigInteger, nullable=False)
    player = Column(match_move_player_enum, nullable=False)
    move = Column(JSON, nullable=False)
    createdat = Column(DateTime, nullable=False, server_default=func.now())

    match = relationship("Match", foreign_keys=[matchid])
