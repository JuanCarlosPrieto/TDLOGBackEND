from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, func
from sqlalchemy import Index
from app.db.session import Base


class AuthToken(Base):
    __tablename__ = "authtoken"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    userid = Column(BigInteger,
                    ForeignKey("users.userid", ondelete="CASCADE",
                               onupdate="CASCADE"), nullable=False, index=True)
    refreshtoken = Column(String(255), nullable=False, unique=True, index=True)
    expiresat = Column(DateTime, nullable=False)
    createdat = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_authtoken_user_expires", "userid", "expiresat"),
    )
