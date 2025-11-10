from sqlalchemy import BigInteger, Column, Date, DateTime, String, func
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    userid = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100))
    surname = Column(String(100))
    password_hash = Column(String(255), nullable=False)
    birthdate = Column(Date)
    country = Column(String(80))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
