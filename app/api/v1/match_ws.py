from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.api.deps import get_db, get_current_user_ws
from app.db.models.match import Match
from app.db.models.user import User
from app.db.models.match_move import MatchMove
from app.core.ws_manager import connection_manager
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.exc import IntegrityError

# piece: {"color": "RED"/"BLACK", "king": bool}
Board = List[List[Optional[Dict[str, Any]]]]


def role_to_color(role: str) -> str:
    # frontend mapea white->RED, black->BLACK
    return "RED" if role == "white" else "BLACK"


def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < 8 and 0 <= c < 8


def is_playable(r: int, c: int) -> bool:
    return (r + c) % 2 == 1


def forward_dir(color: str) -> int:
    # RED (abajo) sube: -1 ; BLACK (arriba) baja: +1
    return -1 if color == "RED" else +1


def initial_board() -> Board:
    b: Board = [[None for _ in range(8)] for _ in range(8)]
    for r in range(8):
        for c in range(8):
            if not is_playable(r, c):
                continue
            if r < 3:
                b[r][c] = {"color": "BLACK", "king": False}
            elif r > 4:
                b[r][c] = {"color": "RED", "king": False}
    return b


def dirs_for_piece(piece: Dict[str, Any]) -> List[Tuple[int, int]]:
    if piece.get("king"):
        return [(-1, -1), (-1, +1), (+1, -1), (+1, +1)]
    dr = forward_dir(piece["color"])
    return [(dr, -1), (dr, +1)]


def piece_captures(board: Board, r: int, c: int) -> List[Dict[str, Any]]:
    piece = board[r][c]
    if not piece:
        return []
    out = []
    for dr, dc in dirs_for_piece(piece):
        r2, c2 = r + 2 * dr, c + 2 * dc
        rm, cm = r + dr, c + dc
        if not in_bounds(r2, c2) or not is_playable(r2, c2):
            continue
        if board[r2][c2] is not None:
            continue
        mid = board[rm][cm]
        if mid and mid["color"] != piece["color"]:
            out.append({"from": [r, c], "to": [r2, c2], "capture": [rm, cm]})
    return out


def all_captures_for_color(board: Board, color: str) -> List[Dict[str, Any]]:
    caps = []
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p and p["color"] == color:
                caps.extend(piece_captures(board, r, c))
    return caps


def validate_and_apply_move(
    board: Board,
    color: str,
    move: Dict[str, Any],
    forced_from: Optional[Tuple[int, int]],
    must_capture: bool,
) -> Tuple[Board, bool, Tuple[int, int], Optional[Tuple[int, int]]]:
    """
    Returns:
      new_board, was_capture, new_pos, captured_pos
    """
    if not isinstance(move, dict):
        raise ValueError("Move must be an object")

    frm = move.get("from")
    to = move.get("to")
    if not (isinstance(frm, list)
            and isinstance(to, list)
            and len(frm) == 2
            and len(to) == 2):
        raise ValueError("Move must contain from/to as [row, col]")

    fr, fc = int(frm[0]), int(frm[1])
    tr, tc = int(to[0]), int(to[1])

    if not in_bounds(fr, fc) or not in_bounds(tr, tc):
        raise ValueError("Out of bounds")
    if not is_playable(fr, fc) or not is_playable(tr, tc):
        raise ValueError("Non-playable square")
    if forced_from and (fr, fc) != forced_from:
        raise ValueError(
            f"Must continue capture chain from {list(forced_from)}")

    piece = board[fr][fc]
    if not piece:
        raise ValueError("No piece at from")
    if piece["color"] != color:
        raise ValueError("Not your piece")
    if board[tr][tc] is not None:
        raise ValueError("Destination not empty")

    dr = tr - fr
    dc = tc - fc

    # Step move
    if abs(dr) == 1 and abs(dc) == 1:
        if must_capture:
            raise ValueError("Capture is mandatory")
        # direction constraint for men
        if not piece.get("king"):
            if dr != forward_dir(color):
                raise ValueError("Illegal direction for man")
        # apply
        new_board = [[(p.copy() if p else None) for p in row] for row in board]
        new_board[fr][fc] = None
        new_board[tr][tc] = piece.copy()
        # crowning
        if new_board[tr][tc]["color"] == "RED" and tr == 0:
            new_board[tr][tc]["king"] = True
        if new_board[tr][tc]["color"] == "BLACK" and tr == 7:
            new_board[tr][tc]["king"] = True
        return new_board, False, (tr, tc), None

    # Capture move
    if abs(dr) == 2 and abs(dc) == 2:
        # direction constraint for men
        if not piece.get("king"):
            if dr != 2 * forward_dir(color):
                raise ValueError("Illegal capture direction for man")

        mr = fr + dr // 2
        mc = fc + dc // 2
        mid = board[mr][mc]
        if not mid or mid["color"] == color:
            raise ValueError("No opponent piece to capture")

        new_board = [[(p.copy() if p else None) for p in row] for row in board]
        new_board[fr][fc] = None
        new_board[mr][mc] = None
        new_board[tr][tc] = piece.copy()

        # crowning (regla típica: si corona, el turno termina)
        kinged_now = False
        if (new_board[tr][tc]["color"] == "RED" and tr == 0 and
                not new_board[tr][tc].get("king")):
            new_board[tr][tc]["king"] = True
            kinged_now = True
        if (new_board[tr][tc]["color"] == "BLACK" and tr == 7 and
                not new_board[tr][tc].get("king")):
            new_board[tr][tc]["king"] = True
            kinged_now = True

        # (usar para cortar cadena)
        new_board[tr][tc]["_kinged_now"] = kinged_now
        return new_board, True, (tr, tc), (mr, mc)

    raise ValueError("Illegal move geometry")


def compute_state_from_history(
    moves: List[Dict[str, Any]],
) -> Tuple[Board, str, Optional[Tuple[int, int]], bool]:
    """
    Simula el juego desde tablero inicial.
    Devuelve: board, next_role_to_play, forced_from, must_capture_for_next
    """
    board = initial_board()
    next_role = "white"
    forced_from: Optional[Tuple[int, int]] = None

    for m in moves:
        player = m["player"]
        mv = m["move"]
        color = role_to_color(player)

        # el historial debería ser consistente; si no,
        # igual lo simulamos “como está”
        if player != next_role:
            # en caso de inconsistencia, forzamos a
            # lo que dice DB (evita explotar)
            next_role = player
            forced_from = None

        must_cap = len(all_captures_for_color(board, color)) > 0

        board, was_cap, new_pos, _ = validate_and_apply_move(
            board=board,
            color=color,
            move=mv,
            forced_from=forced_from,
            must_capture=must_cap or (forced_from is not None),
        )

        # cortar cadena si se coronó en esta jugada (variante típica)
        kinged_now = False
        p = board[new_pos[0]][new_pos[1]]
        if p and p.pop("_kinged_now", False):
            kinged_now = True

        if was_cap and not kinged_now:
            more_caps = piece_captures(board, new_pos[0], new_pos[1])
            if more_caps:
                forced_from = new_pos
                next_role = player   # MISMO jugador continúa
                continue

        forced_from = None
        next_role = "black" if player == "white" else "white"

    # estado para el próximo jugador
    next_color = role_to_color(next_role)
    must_capture = len(all_captures_for_color(board, next_color)) > 0
    return board, next_role, forced_from, must_capture


router = APIRouter(prefix="/ws", tags=["websockets"])


def get_role(match: Match, userid: int) -> str:
    if match.whiteuser == userid:
        return "white"
    if match.blackuser == userid:
        return "black"
    return ""


def next_turn_player(last_player: str | None) -> str:
    # If no moves yet, white starts
    if last_player is None:
        return "white"
    return "black" if last_player == "white" else "white"


def is_users_turn(role: str, last_player: str | None) -> bool:
    if role not in ("white", "black"):
        return False
    return role == next_turn_player(last_player)


def piece_steps(board: Board, r: int, c: int) -> List[Dict[str, Any]]:
    piece = board[r][c]
    if not piece:
        return []
    out = []
    for dr, dc in dirs_for_piece(piece):
        r1, c1 = r + dr, c + dc
        if not in_bounds(r1, c1) or not is_playable(r1, c1):
            continue
        if board[r1][c1] is None:
            out.append({"from": [r, c], "to": [r1, c1]})
    return out


def all_steps_for_color(board: Board, color: str) -> List[Dict[str, Any]]:
    steps = []
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p and p["color"] == color:
                steps.extend(piece_steps(board, r, c))
    return steps


def has_any_legal_move(board: Board, color: str) -> bool:
    caps = all_captures_for_color(board, color)
    if caps:
        return True  # capture exists => at least one legal move
    steps = all_steps_for_color(board, color)
    return len(steps) > 0


def opposite_role(role: str) -> str:
    return "black" if role == "white" else "white"


def compute_game_over(board: Board, next_role: str) -> Tuple[bool, str, str]:
    """
    Returns: (is_over, result, reason)
    result in {'white','black','draw','none'}
    reason in {'normal', ...}
    """
    next_color = role_to_color(next_role)

    # If next player cannot move => they lose => other wins
    if not has_any_legal_move(board, next_color):
        winner = opposite_role(next_role)
        return True, winner, "normal"

    return False, "none", "none"


@router.websocket("/match/{matchid}")
async def match_socket(
    websocket: WebSocket,
    matchid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ws),
):
    """
    Game websocket per match.
    Expected messages from client:
      { "type": "move", "payload": { "move": {...} } }
      { "type": "ping", "payload": {} }
    """

    # 1) Validate match exists
    match = db.execute(
        select(Match).where(Match.matchid == matchid)
    ).scalars().first()

    if not match:
        await websocket.close(code=1008)
        return

    # 2) Validate user belongs to match
    role = get_role(match, current_user.userid)
    if not role:
        await websocket.close(code=1008)
        return

    # 3) Connect to room
    await connection_manager.connect(matchid, current_user.userid, websocket)

    try:
        # 4) Initial sync (history + next turn)
        moves = db.execute(
            select(MatchMove)
            .where(MatchMove.matchid == matchid)
            .order_by(MatchMove.move_number.asc())
        ).scalars().all()

        last_player = moves[-1].player if moves else None
        next_turn = next_turn_player(last_player)

        hist_moves = [{"player": m.player, "move": m.move} for m in moves]
        (_, next_turn, forced_from, must_capture) = (
            compute_state_from_history(hist_moves)
        )

        await websocket.send_json({
            "type": "sync",
            "payload": {
                "matchid": matchid,
                "status": match.status,
                "your_role": role,
                "next_turn": next_turn,
                "forced_from": list(forced_from) if forced_from else None,
                "must_capture": must_capture,
                "moves": [
                    {
                        "id": m.id,
                        "matchid": m.matchid,
                        "move_number": m.move_number,
                        "player": m.player,
                        "move": m.move,
                        "createdat": m.createdat.isoformat()
                        if m.createdat else None
                    } for m in moves
                ]
            }
        })
        db.rollback()

        if match.status != "ongoing":
            await websocket.close(code=1000)
            return

        # 5) Message loop
        while True:
            data = await websocket.receive_json()
            db.rollback()

            msg_type = data.get("type")
            payload = data.get("payload") or {}

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "payload": {}})
                continue

            if msg_type != "move":
                await websocket.send_json({
                    "type": "error",
                    "payload": {"detail": "Unknown message type"}
                })
                continue

            # 6) Re-read match state
            match = db.execute(
                select(Match).where(Match.matchid == matchid)
            ).scalars().first()

            if not match or match.status != "ongoing":
                await websocket.send_json({
                    "type": "error",
                    "payload": {"detail": "Match not ongoing"}
                })
                continue

            # 7) Build authoritative state from history
            history = db.execute(
                select(MatchMove)
                .where(MatchMove.matchid == matchid)
                .order_by(MatchMove.move_number.asc())
            ).scalars().all()

            hist_moves = [{"player": mm.player, "move": mm.move}
                          for mm in history]
            board, next_role, forced_from, must_capture = \
                compute_state_from_history(hist_moves)

            if role != next_role:
                await websocket.send_json({
                    "type": "error",
                    "payload": {
                        "detail": "Not your turn",
                        "next_turn": next_role,
                        "forced_from": list(forced_from)
                        if forced_from else None,
                        "must_capture": must_capture
                    }
                })
                continue

            move_content = payload.get("move")
            if not isinstance(move_content, dict):
                await websocket.send_json({
                    "type": "error",
                    "payload": {"detail": "Invalid move payload"}
                })
                continue

            # 8) Validate move against rules + apply (server-side)
            color = role_to_color(role)
            try:
                new_board, was_cap, new_pos, _ = validate_and_apply_move(
                    board=board,
                    color=color,
                    move=move_content,
                    forced_from=forced_from,
                    must_capture=must_capture or (forced_from is not None),
                )
            except ValueError as e:
                await websocket.send_json({
                    "type": "error",
                    "payload": {
                        "detail": str(e),
                        "next_turn": next_role,
                        "forced_from": (
                            list(forced_from) if forced_from else None
                        ),
                        "must_capture": must_capture
                    }
                })
                continue

            # Determine continuation after this move
            kinged_now = False
            p = new_board[new_pos[0]][new_pos[1]]
            if p and p.pop("_kinged_now", False):
                kinged_now = True

            must_continue = False
            new_forced_from: Optional[Tuple[int, int]] = None
            if was_cap and not kinged_now:
                if piece_captures(new_board, new_pos[0], new_pos[1]):
                    must_continue = True
                    new_forced_from = new_pos

            # 9) Save move with safe move_number (LOCK + atomic max)
            move_to_store = dict(move_content)
            move_to_store["was_capture"] = was_cap

            try:
                move_to_store = dict(move_content)
                move_to_store["was_capture"] = was_cap

                with db.begin_nested():
                    locked_match = db.execute(
                        select(Match)
                        .where(Match.matchid == matchid)
                        .with_for_update()
                    ).scalar_one()

                    if locked_match.status != "ongoing":
                        raise ValueError("Match not ongoing")

                    last_no = db.execute(
                        select(func.coalesce(func.max(MatchMove.move_number),
                                             0))
                        .where(MatchMove.matchid == matchid)
                    ).scalar_one()

                    next_number = int(last_no) + 1

                    new_move = MatchMove(
                        matchid=matchid,
                        move_number=next_number,
                        player=role,
                        move=move_to_store
                    )
                    db.add(new_move)

                db.commit()
                db.refresh(new_move)

            except IntegrityError:
                # If UNIQUE(matchid, move_number) triggers, you can retry once
                db.rollback()
                await websocket.send_json({
                    "type": "error",
                    "payload":
                    {"detail": "Move numbering conflict. Please resend."}
                })
                continue

            except Exception as e:
                db.rollback()
                await websocket.send_json({
                    "type": "error",
                    "payload": {"detail": f"DB error while saving move: {e}"}
                })
                continue

            # 10) next_turn depends on chain
            if must_continue:
                next_turn = role
            else:
                next_turn = (
                    "black" if role == "white" else "white"
                )

            # 11) If chain ended, check game-over for the next player
            match_finished = False
            finish_payload = None

            if not must_continue:
                (is_over, result, reason
                 ) = compute_game_over(new_board, next_turn)

                if is_over:
                    match_finished = True
                    match.status = "finished"
                    match.result = result  # 'white' or 'black' (or draw later)
                    match.reason = reason          # 'normal'
                    match.finishedat = func.now()
                    db.commit()
                    db.refresh(match)

                    finish_payload = {
                        "matchid": matchid,
                        "status": match.status,
                        "result": match.result,
                        "reason": match.reason,
                        "finishedat": match.finishedat.isoformat()
                        if match.finishedat else None,
                    }

            await connection_manager.broadcast(matchid, {
                "type": "move",
                "payload": {
                    "id": new_move.id,
                    "matchid": new_move.matchid,
                    "move_number": new_move.move_number,
                    "player": new_move.player,
                    "move": new_move.move,
                    "createdat": (new_move.createdat.isoformat()
                                  if new_move.createdat else None),
                    "next_turn": next_turn,
                    "must_continue": must_continue,
                    "forced_from": (list(new_forced_from)
                                    if new_forced_from else None)
                }
            })

            if match_finished and finish_payload:
                await connection_manager.broadcast(matchid, {
                    "type": "match_finished",
                    "payload": finish_payload
                })
                # close everyone after notifying
                await connection_manager.close_match(matchid, code=1000)

    except WebSocketDisconnect:
        connection_manager.disconnect(matchid, current_user.userid)

    except Exception as e:
        connection_manager.disconnect(matchid, current_user.userid)
        print("WS fatal error:", repr(e))
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
