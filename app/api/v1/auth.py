from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.api.deps import get_db, get_current_user
from app.core.security import hash_password, verify_password, ALGO
from app.core.security import create_access_token, create_refresh_token
from app.core.config import settings
from app.db.models.user import User
from app.schemas.auth import RegisterIn, LoginIn, UserOut, AuthUserResponse
from app.schemas.auth import MessageResponse

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- Register ----------
@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter((User.username == body.username) |
                             (User.email == body.email)).first():
        raise HTTPException(status_code=400,
                            detail="Usuario o email ya existe")

    print(body.password)
    user = User(
        email=body.email,
        username=body.username,
        name=body.name,
        surname=body.surname,
        password_hash=hash_password(body.password),
        birthdate=body.birthdate,
        country=body.country,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------- Login (access + refresh) ----------
@router.post("/login", response_model=AuthUserResponse)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(sub=user.username)
    refresh_token = create_refresh_token(sub=user.username)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )

    return {"user": user}


# ---------- Refresh ----------
@router.post("/refresh", response_model=MessageResponse)
def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET,
                             algorithms=[ALGO])
        if payload.get("type") != "refresh":
            raise ValueError("not refresh")
        username: str = payload.get("sub")
        if not username:
            raise ValueError("no sub")
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access = create_access_token(sub=user.username)
    response.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return {"detail": "access token refreshed"}


# ---------- Perfil rápido ----------
@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", response_model=MessageResponse,)
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"detail": "logged out"}
