"""Tests for per-user room read markers and the cross-satellite unread-status
lookup, which drives an envelope icon (has messages / unread) in other
satellites (e.g. fertigungs-app's Werkercockpit and Gantt) that have no live
SSE connection of their own to the messenger.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.config import MESSENGER_SERVICE_TOKEN
from app.database import get_db
from app.main import app
from app.models import RoomMapping, RoomRead, RoomType, UserMapping
from app.routers import messages as messages_router
from app.services.encryption import encrypt_token


@pytest.fixture(autouse=True)
def mock_matrix_client(monkeypatch):
    monkeypatch.setattr(messages_router.matrix_client, "send_message", AsyncMock(return_value="$event1"))
    return messages_router.matrix_client


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_user(db_session, hub_user_id):
    user = UserMapping(
        hub_user_id=hub_user_id,
        matrix_user_id=f"@{hub_user_id}:hub.local",
        matrix_access_token_encrypted=encrypt_token(f"{hub_user_id}-secret"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_room(db_session, entity_type, entity_id, room_id="!room1:hub.local"):
    room = RoomMapping(
        matrix_room_id=room_id,
        room_type=RoomType.entity,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db_session.add(room)
    db_session.commit()
    db_session.refresh(room)
    return room


def test_unread_status_no_room_yet(client, db_session):
    resp = client.post(
        "/api/v1/rooms/unread-status",
        json={"hub_user_id": "alice", "entities": [{"entity_type": "project", "entity_id": 1}]},
        headers={"X-Service-Token": MESSENGER_SERVICE_TOKEN},
    )
    assert resp.status_code == 200, resp.text
    item = resp.json()["items"][0]
    assert item == {"entity_type": "project", "entity_id": 1, "has_messages": False, "unread": False}


def test_unread_status_requires_service_token(client, db_session):
    resp = client.post(
        "/api/v1/rooms/unread-status",
        json={"hub_user_id": "alice", "entities": []},
    )
    assert resp.status_code == 422


def test_unread_status_unread_then_read(client, db_session):
    room = _make_room(db_session, "project", 42)
    room.last_message_at = datetime.now(timezone.utc)
    db_session.commit()

    resp = client.post(
        "/api/v1/rooms/unread-status",
        json={"hub_user_id": "alice", "entities": [{"entity_type": "project", "entity_id": 42}]},
        headers={"X-Service-Token": MESSENGER_SERVICE_TOKEN},
    )
    item = resp.json()["items"][0]
    assert item["has_messages"] is True
    assert item["unread"] is True

    # alice reads the room
    db_session.add(RoomRead(
        hub_user_id="alice",
        matrix_room_id=room.matrix_room_id,
        last_read_at=datetime.now(timezone.utc) + timedelta(seconds=1),
    ))
    db_session.commit()

    resp = client.post(
        "/api/v1/rooms/unread-status",
        json={"hub_user_id": "alice", "entities": [{"entity_type": "project", "entity_id": 42}]},
        headers={"X-Service-Token": MESSENGER_SERVICE_TOKEN},
    )
    item = resp.json()["items"][0]
    assert item["has_messages"] is True
    assert item["unread"] is False

    # a different user who never read it still sees it as unread
    resp = client.post(
        "/api/v1/rooms/unread-status",
        json={"hub_user_id": "bob", "entities": [{"entity_type": "project", "entity_id": 42}]},
        headers={"X-Service-Token": MESSENGER_SERVICE_TOKEN},
    )
    item = resp.json()["items"][0]
    assert item["unread"] is True


def test_mark_room_read_endpoint(client, db_session):
    user = _make_user(db_session, "carol")
    room = _make_room(db_session, "project", 7)
    app.dependency_overrides[get_current_user] = lambda: user

    resp = client.post(f"/api/v1/rooms/{room.matrix_room_id}/read")
    assert resp.status_code == 200, resp.text

    row = (
        db_session.query(RoomRead)
        .filter(RoomRead.hub_user_id == "carol", RoomRead.matrix_room_id == room.matrix_room_id)
        .first()
    )
    assert row is not None


def test_sending_a_message_marks_room_read_for_sender_and_bumps_last_message_at(client, db_session):
    sender = _make_user(db_session, "dave")
    room = _make_room(db_session, "project", 9)
    app.dependency_overrides[get_current_user] = lambda: sender

    resp = client.post("/api/v1/messages/send", json={"room_id": room.matrix_room_id, "body": "hi"})
    assert resp.status_code == 200, resp.text

    db_session.refresh(room)
    assert room.last_message_at is not None

    read_row = (
        db_session.query(RoomRead)
        .filter(RoomRead.hub_user_id == "dave", RoomRead.matrix_room_id == room.matrix_room_id)
        .first()
    )
    assert read_row is not None
    assert read_row.last_read_at >= room.last_message_at
