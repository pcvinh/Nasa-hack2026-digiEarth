from __future__ import annotations

from fastapi import APIRouter, Request

from edt.api.errors import ApiError
from edt.api.models import Session, SessionInput, SessionList
from edt.sessions.store import StateTooLarge

router = APIRouter(tags=["sessions"])


def _store(request: Request):
    return request.app.state.sessions


@router.get("/sessions", response_model=SessionList, operation_id="listSessions")
def list_sessions(request: Request) -> dict:
    return {"items": _store(request).list()}


@router.post("/sessions", response_model=Session, status_code=201, operation_id="createSession")
def create_session(request: Request, body: SessionInput) -> dict:
    try:
        return _store(request).create(body.title, body.state)
    except StateTooLarge as e:
        raise ApiError(400, "invalid_input", str(e)) from e


@router.get("/sessions/{sessionId}", response_model=Session, operation_id="getSession")
def get_session(request: Request, sessionId: str) -> dict:  # noqa: N803
    s = _store(request).get(sessionId)
    if s is None:
        raise ApiError(404, "not_found", f"Unknown session '{sessionId}'.")
    return s


@router.put("/sessions/{sessionId}", response_model=Session, operation_id="updateSession")
def update_session(request: Request, sessionId: str, body: SessionInput) -> dict:  # noqa: N803
    try:
        s = _store(request).update(sessionId, body.title, body.state)
    except StateTooLarge as e:
        raise ApiError(400, "invalid_input", str(e)) from e
    if s is None:
        raise ApiError(404, "not_found", f"Unknown session '{sessionId}'.")
    return s
