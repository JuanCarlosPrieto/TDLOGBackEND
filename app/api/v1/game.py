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

router = APIRouter(prefix="/game", tags=["game"])