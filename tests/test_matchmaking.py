import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.v1.matchmaking import router
from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.match import Match

app = FastAPI()
app.include_router(router)

mock_user = MagicMock(spec=User)
mock_user.userid = 1

mock_db = MagicMock()

def override_get_db():
    try:
        yield mock_db
    finally:
        pass

def override_get_current_user():
    return mock_user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

def test_create_new_match_if_none_available():
    mock_db.execute.return_value.scalars.return_value.first.return_value = None

    response = client.post("/matchmaking/find")

    assert response.status_code == 200
    data = response.json()
    
    assert data["waiting"] is True
    mock_db.add.assert_called()
    mock_db.commit.assert_called()

def test_join_existing_match():
    existing_match = MagicMock(spec=Match)
    existing_match.status = "waiting"
    existing_match.whiteuser = 999 
    existing_match.blackuser = None
    existing_match.startedat = "2023-01-01"

    mock_db.execute.return_value.scalars.return_value.first.side_effect = [existing_match, None]

    response = client.post("/matchmaking/find")

    assert response.status_code == 200
    data = response.json()

    assert data["waiting"] is False
    assert data["role"] == "black"
    assert existing_match.status == "ongoing"
    mock_db.commit.assert_called()

def test_return_own_waiting_match():
    my_match = MagicMock(spec=Match)
    my_match.status = "waiting"
    my_match.whiteuser = 1
    my_match.blackuser = None

    mock_db.execute.return_value.scalars.return_value.first.side_effect = [None, my_match]

    response = client.post("/matchmaking/find")

    assert response.status_code == 200
    data = response.json()

    assert data["waiting"] is True
    assert data["role"] == "white"
    mock_db.add.assert_not_called()