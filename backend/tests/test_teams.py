"""Tests for fixed/named teams: admin-only CRUD, visible to any authenticated
user (needed for the invite-a-team picker), and bulk-invite into a room.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.auth import get_admin_user, get_current_user
from app.database import get_db
from app.main import app
from app.models import UserMapping
from app.routers import rooms as rooms_router
from app.services.encryption import encrypt_token


@pytest.fixture(autouse=True)
def mock_matrix_client(monkeypatch):
    monkeypatch.setattr(rooms_router.matrix_client, "invite_user", AsyncMock(return_value=None))
    monkeypatch.setattr(rooms_router.matrix_client, "join_room", AsyncMock(return_value=None))
    monkeypatch.setattr(rooms_router.matrix_client, "get_room_members", AsyncMock(return_value=[]))
    return rooms_router.matrix_client


def _make_user(db_session, hub_user_id, role="user", display_name=None):
    user = UserMapping(
        hub_user_id=hub_user_id,
        matrix_user_id=f"@{hub_user_id}:hub.local",
        matrix_access_token_encrypted=encrypt_token(f"{hub_user_id}-secret"),
        role=role,
        display_name=display_name or hub_user_id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _as_user(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _as_admin(admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_admin_user] = lambda: admin_user


def test_non_admin_cannot_create_team(client, db_session):
    user = _make_user(db_session, "worker1")
    _as_user(user)

    resp = client.post("/api/v1/teams", json={"name": "Schicht A", "member_hub_user_ids": []})
    assert resp.status_code == 403


def test_admin_can_create_and_any_user_can_list(client, db_session):
    admin = _make_user(db_session, "boss", role="admin")
    member = _make_user(db_session, "worker2", display_name="Worker Two")
    _as_admin(admin)

    resp = client.post(
        "/api/v1/teams",
        json={"name": "Konstruktion", "member_hub_user_ids": ["worker2"]},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Konstruktion"
    assert body["members"] == [{"hub_user_id": "worker2", "display_name": "Worker Two"}]

    # A regular (non-admin) user can still list teams - needed for the
    # invite-a-team picker available to anyone who can already invite.
    other_user = _make_user(db_session, "worker3")
    _as_user(other_user)
    resp = client.get("/api/v1/teams")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_duplicate_team_name_rejected(client, db_session):
    admin = _make_user(db_session, "boss2", role="admin")
    _as_admin(admin)

    client.post("/api/v1/teams", json={"name": "Dup", "member_hub_user_ids": []})
    resp = client.post("/api/v1/teams", json={"name": "Dup", "member_hub_user_ids": []})
    assert resp.status_code == 409


def test_invite_team_bulk_invites_all_members_and_skips_existing(client, db_session):
    admin = _make_user(db_session, "boss3", role="admin")
    m1 = _make_user(db_session, "member1")
    m2 = _make_user(db_session, "member2")
    _as_admin(admin)

    team_resp = client.post(
        "/api/v1/teams",
        json={"name": "Team X", "member_hub_user_ids": ["member1", "member2"]},
    )
    team_id = team_resp.json()["id"]

    # member1 is already in the room -> should be skipped, not re-invited.
    rooms_router.matrix_client.get_room_members.return_value = ["@member1:hub.local"]

    resp = client.post(
        "/api/v1/rooms/!someroom:hub.local/invite-team",
        json={"team_id": team_id},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["already_member"] == ["member1"]
    assert body["invited"] == ["member2"]
    assert body["failed"] == []
    rooms_router.matrix_client.invite_user.assert_awaited_once()


def test_invite_team_unknown_team_404(client, db_session):
    admin = _make_user(db_session, "boss4", role="admin")
    _as_admin(admin)

    resp = client.post(
        "/api/v1/rooms/!someroom:hub.local/invite-team",
        json={"team_id": 9999},
    )
    assert resp.status_code == 404
