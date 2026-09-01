"""End-to-end test for POST /api/v1/rooms/entity: this is exactly the flow
that broke in production (room created but the requesting human user was
never invited, causing 403s from Matrix on /members). Verifies the full
chain: room creation, MESSENGER_SERVICE_TOKEN auth, and that every
hub_user_id gets invited + joined (not just the bot).
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import MESSENGER_SERVICE_TOKEN
from app.database import get_db
from app.main import app
from app.models import UserMapping
from app.services import room_manager
from app.services.encryption import encrypt_token


@pytest.fixture(autouse=True)
def mock_matrix_client(monkeypatch):
    monkeypatch.setattr(room_manager.matrix_client, "create_room", AsyncMock(return_value="!room1:hub.local"))
    monkeypatch.setattr(room_manager.matrix_client, "join_room", AsyncMock(return_value=None))
    monkeypatch.setattr(room_manager.matrix_client, "invite_user", AsyncMock(return_value=None))
    return room_manager.matrix_client


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_bot(db_session):
    bot = UserMapping(
        hub_user_id="notification_bot",
        matrix_user_id="@notification_bot:hub.local",
        matrix_access_token_encrypted=encrypt_token("bot-secret"),
        is_bot=True,
    )
    db_session.add(bot)
    db_session.commit()
    return bot


def test_rejects_missing_service_token(client, db_session):
    _make_bot(db_session)
    resp = client.post("/api/v1/rooms/entity", json={
        "entity_type": "project", "entity_id": 1, "display_name": "Test",
    })
    assert resp.status_code == 422  # X-Service-Token header is required


def test_rejects_wrong_service_token(client, db_session):
    _make_bot(db_session)
    resp = client.post(
        "/api/v1/rooms/entity",
        json={"entity_type": "project", "entity_id": 1, "display_name": "Test"},
        headers={"X-Service-Token": "wrong-token"},
    )
    assert resp.status_code == 403


def test_fails_gracefully_without_bot_provisioned(client, db_session):
    resp = client.post(
        "/api/v1/rooms/entity",
        json={"entity_type": "project", "entity_id": 1, "display_name": "Test"},
        headers={"X-Service-Token": MESSENGER_SERVICE_TOKEN},
    )
    assert resp.status_code == 503


def test_creates_room_and_invites_all_requested_users(client, db_session):
    _make_bot(db_session)
    # An already-provisioned user - provision_matrix_user should NOT be
    # invoked for this one, only ensure_user_in_room.
    existing_user = UserMapping(
        hub_user_id="aeic",
        matrix_user_id="@aeic:hub.local",
        matrix_access_token_encrypted=encrypt_token("aeic-secret"),
    )
    db_session.add(existing_user)
    db_session.commit()

    resp = client.post(
        "/api/v1/rooms/entity",
        json={
            "entity_type": "project",
            "entity_id": 42,
            "display_name": "1234.5678 - Testprojekt",
            "hub_user_ids": ["aeic"],
            "update_display_name": True,
        },
        headers={"X-Service-Token": MESSENGER_SERVICE_TOKEN},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["matrix_room_id"] == "!room1:hub.local"
    assert body["display_name"] == "1234.5678 - Testprojekt"
    assert body["deep_link_path"] == "/room/%21room1%3Ahub.local"

    # The requesting human user (not just the bot) must have been
    # invited+joined - this is the exact bug that broke Projekt-Chat.
    room_manager.matrix_client.invite_user.assert_awaited_once()
    room_manager.matrix_client.join_room.assert_awaited()
    invite_call = room_manager.matrix_client.invite_user.await_args
    assert invite_call.args[2] == "@aeic:hub.local"


def test_missing_hub_user_ids_still_creates_room(client, db_session):
    """Backward-compatible: a caller that only wants the room (no invite
    list, e.g. a notification-only use case) still gets a working room."""
    _make_bot(db_session)

    resp = client.post(
        "/api/v1/rooms/entity",
        json={"entity_type": "machine", "entity_id": 7, "display_name": "Maschine 7"},
        headers={"X-Service-Token": MESSENGER_SERVICE_TOKEN},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["matrix_room_id"] == "!room1:hub.local"
