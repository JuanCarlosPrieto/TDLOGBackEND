from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.api.deps import get_db, get_current_user
from app.core.security import (
    hash_password,
    verify_password,
    ALGO,
    create_access_token,
    create_refresh_token
)
from app.core.config import settings
from app.db.models.user import User
from app.schemas.auth import (
    RegisterIn,
    LoginIn,
    UserOut,
    AuthUserResponse,
    MessageResponse,
    UpdateUserIn,
    UserProfile
)


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

    access_token = create_access_token(sub=user.email)
    refresh_token = create_refresh_token(sub=user.email)

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
        email: str = payload.get("sub")
        if not email:
            raise ValueError("no sub")
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access = create_access_token(sub=user.email)
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
@router.get("/me", response_model=UserProfile)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", response_model=MessageResponse,)
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"detail": "logged out"}


@router.put("/update", response_model=UserProfile)
def update_me(
    body: UpdateUserIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # If username is being changed, check it is not used by another user
    if body.username and body.username != current_user.username:
        existing = (
            db.query(User)
            .filter(User.username == body.username,
                    User.userid != current_user.userid)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400,
                                detail="Username already in use")

    # Apply partial updates only if field is provided (not None)
    if body.username is not None:
        current_user.username = body.username

    if body.name is not None:
        current_user.name = body.name

    if body.surname is not None:
        current_user.surname = body.surname

    if body.birthdate is not None:
        current_user.birthdate = body.birthdate

    if body.country is not None:
        current_user.country = body.country

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user
