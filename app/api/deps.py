from sqlalchemy import select
from fastapi import Depends, HTTPException, status, Cookie, WebSocket
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.security import ALGO


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db)
) -> User:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(access_token, settings.JWT_SECRET,
                             algorithms=[ALGO])
        email: str = payload.get("sub")
        if not email:
            raise ValueError("no sub")
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_user_ws(
    websocket: WebSocket,
    db: Session = Depends(get_db),
) -> User:
    token = websocket.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401,
                            detail="Missing access token cookie")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGO])
        email = payload.get("sub")
        if not email:
            raise ValueError("no sub")
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.execute(
        select(User).where(User.email == email)).scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
