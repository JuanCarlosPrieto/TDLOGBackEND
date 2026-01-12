from operator import or_
from fastapi import APIRouter, Depends
from fastapi import HTTPException
from fastapi.temp_pydantic_v1_params import Query
from requests import Session
from sqlalchemy import func, select
from app.api.deps import get_current_user, get_db
from app.db.models.match import Match
from app.db.models.match_move import MatchMove
from app.db.models.user import User
from app.schemas.match_history import (
    MatchSummaryOut,
    MatchDetailOut,
    MatchMoveOut,
    MatchMovesPageOut
)

router = APIRouter(prefix="/match_history", tags=["match_history"])


def assert_user_in_match(match: Match, userid: int) -> None:
    if userid != match.whiteuser and userid != match.blackuser:
        raise HTTPException(status_code=403, detail="User not in match")


def get_my_role(match: Match, userid: int) -> str:
    return "white" if userid == match.whiteuser else "black"


def get_opponent(match: Match, userid: int) -> int:
    return match.blackuser if userid == match.whiteuser else match.whiteuser


@router.get("/history", response_model=list[MatchSummaryOut])
def list_my_matches(
    status: str | None = Query(default="finished",
                               description="finished|playing|"
                               "waiting|aborted|all"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    userid = current_user.userid

    filters = [or_(Match.whiteuser == userid, Match.blackuser == userid)]
    if status and status != "all":
        filters.append(Match.status == status)

    moves_count_sq = (
        select(MatchMove.matchid,
               func.count(MatchMove.id).label("moves_count"))
        .group_by(MatchMove.matchid)
        .subquery()
    )

    stmt = (
        select(Match, func.coalesce(moves_count_sq.c.moves_count, 0))
        .outerjoin(moves_count_sq, moves_count_sq.c.matchid == Match.matchid)
        .where(*filters)
        .order_by(Match.matchid.desc())
        .limit(limit)
        .offset(offset)
    )

    rows = db.execute(stmt).all()

    out: list[MatchSummaryOut] = []
    for match, moves_count in rows:
        my_role = get_my_role(match, userid)
        opponent = get_opponent(match, userid)

        out.append(
            MatchSummaryOut(
                matchid=match.matchid,
                whiteuser=match.whiteuser,
                blackuser=match.blackuser,
                status=match.status,
                winner=getattr(match, "winner", None),
                created_at=getattr(match, "created_at", None),
                started_at=getattr(match, "started_at", None),
                ended_at=getattr(match, "ended_at", None),
                my_role=my_role,
                opponent_userid=opponent,
                moves_count=int(moves_count or 0),
            )
        )

    return out


@router.get("/{matchid}", response_model=MatchDetailOut)
def get_match_detail(
    matchid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = db.get(Match, matchid)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    assert_user_in_match(match, current_user.userid)
    return match


@router.get("/{matchid}/moves", response_model=MatchMovesPageOut)
def get_match_moves(
    matchid: int,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = db.get(Match, matchid)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    assert_user_in_match(match, current_user.userid)

    total = db.execute(
        select(func.count(MatchMove.id)).where(MatchMove.matchid == matchid)
    ).scalar_one()

    stmt = (
        select(MatchMove)
        .where(MatchMove.matchid == matchid)
        .order_by(MatchMove.move_number.asc())
        .limit(limit)
        .offset(offset)
    )
    moves = db.execute(stmt).scalars().all()

    return MatchMovesPageOut(
        matchid=matchid,
        total=int(total),
        items=[MatchMoveOut.model_validate(m) for m in moves],
    )
