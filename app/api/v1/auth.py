from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.security import hash_password, verify_password
from app.core.security import create_access_token, create_refresh_token
from app.core.config import settings
from app.db.models.user import User
from app.db.models.authtoken import AuthToken
from app.schemas.auth import RegisterIn, LoginIn, UserOut, TokenPair

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
@router.post("/login", response_model=TokenPair)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    access = create_access_token(user.username)

    # Crear refresh y guardarlo en DB
    refresh = create_refresh_token()
    expires_at = datetime.now(timezone.utc) +\
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(AuthToken(userid=user.userid, refreshtoken=refresh,
                     expiresat=expires_at))
    db.commit()

    return {"access_token": access, "refresh_token": refresh}


# ---------- Refresh ----------
@router.post("/refresh", response_model=TokenPair)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    token_row = (
        db.query(AuthToken)
        .filter(AuthToken.refreshtoken == refresh_token)
        .first()
    )
    if not token_row:
        raise HTTPException(status_code=401, detail="Refresh token inválido")
    if datetime.now(timezone.utc) >\
            token_row.expiresat.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expirado")

    user = db.query(User).filter(User.userid == token_row.userid).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    # Rotación simple: emitir nuevo refresh y borrar el anterior
    db.delete(token_row)
    new_refresh = create_refresh_token()
    new_expires = datetime.now(timezone.utc) +\
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(AuthToken(userid=user.userid, refreshtoken=new_refresh,
                     expiresat=new_expires))
    db.commit()

    new_access = create_access_token(user.username)
    return {"access_token": new_access, "refresh_token": new_refresh}


# ---------- Perfil rápido ----------
@router.get("/me", response_model=UserOut)
def me(authorization: str = Header(...), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    return user
