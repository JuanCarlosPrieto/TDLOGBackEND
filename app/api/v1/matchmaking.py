from fastapi import APIRouter, Depends
from app.api.deps import get_db, get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.schemas.match import FindMatchResponse
from app.db.models.match import Match
from app.db.models.user import User
from random import random

router = APIRouter(prefix="/matchmaking", tags=["matchmaking"])


@router.post("/find", response_model=FindMatchResponse)
def find_or_create_match(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy import delete, text

    stmt_ongoing = (
        select(Match)
        .where(
            Match.status == "ongoing",
            or_(Match.whiteuser == current_user.userid,
                Match.blackuser == current_user.userid)
        )
        .order_by(Match.startedat.desc())
        .limit(1)
    )

    ongoing = db.execute(stmt_ongoing).scalars().first()
    if ongoing:
        my_role = ("white" if ongoing.whiteuser == current_user.userid
                   else "black")
        return FindMatchResponse(match=ongoing, role=my_role, waiting=False)

    WAIT_MINUTES = 1

    db.execute(
        delete(Match).where(
            Match.status == "waiting",
            Match.startedat < func.date_sub(
                func.now(),
                text(f"INTERVAL {WAIT_MINUTES} MINUTE")
            )
        )
    )
    db.commit()

    stmt = (
        select(Match)
        .where(Match.status == "waiting",
               or_(Match.whiteuser.is_(None),
                   Match.whiteuser != current_user.userid),
               or_(Match.blackuser.is_(None),
                   Match.blackuser != current_user.userid))
        .order_by(Match.startedat.asc())
        .limit(1)
    )

    waiting_match = db.execute(stmt).scalars().first()

    if waiting_match:
        my_role = ""
        if waiting_match.whiteuser is None:
            waiting_match.whiteuser = current_user.userid
            my_role = "white"
        elif waiting_match.blackuser is None:
            waiting_match.blackuser = current_user.userid
            my_role = "black"

        waiting_match.status = "ongoing"
        db.commit()
        db.refresh(waiting_match)
        return FindMatchResponse(match=waiting_match,
                                 role=my_role,
                                 waiting=False)

    stmt_own = (
        select(Match)
        .where(
            Match.status == "waiting",
            ((Match.whiteuser == current_user.userid) |
             (Match.blackuser == current_user.userid))
        )
        .order_by(Match.startedat.asc())
        .limit(1)
    )
    own_waiting_match = db.execute(stmt_own).scalars().first()

    if own_waiting_match:
        my_role = ("white"
                   if
                   own_waiting_match.whiteuser == current_user.userid
                   else
                   "black")
        return FindMatchResponse(match=own_waiting_match,
                                 role=my_role,
                                 waiting=True)

    # Select white or black randomly
    my_role = ""
    isWhite = random() < 0.5
    new_match = Match(
        startedat=func.now(),
        status="waiting"
    )

    if isWhite:
        new_match.whiteuser = current_user.userid
        my_role = "white"
    else:
        new_match.blackuser = current_user.userid
        my_role = "black"

    db.add(new_match)
    db.commit()
    db.refresh(new_match)

    return FindMatchResponse(match=new_match,
                             role=my_role,
                             waiting=True)


@router.post("/{matchid}/resign")
def resign_match(
    matchid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = (
        select(Match)
        .where(
            Match.matchid == matchid,
            Match.status == "ongoing",
            or_(Match.whiteuser == current_user.userid,
                Match.blackuser == current_user.userid)
        )
    )

    match = db.execute(stmt).scalars().first()
    if not match:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Match not found")

    if match.status != "ongoing":
        raise HTTPException(status_code=400, detail="Match is not ongoing")

    if match.whiteuser == current_user.userid:
        match.result = "black"
    else:
        match.result = "white"

    match.reason = "resign"
    match.status = "finished"
    match.finishedat = func.now()

    db.commit()
    db.refresh(match)

    return match
