"""Tests for get_or_create_entity_room's create/get/rename/source_url logic.

This is the core of the Projekt-Chat / Reklamations-Chat feature: multiple
satellites can share one entity room, but only a caller passing
update_display_name=True may rename it (a "secondary" satellite must not
clobber the authoritative name). matrix_client is mocked - these tests
exercise the DB/business logic, not the Matrix HTTP calls.
"""

from unittest.mock import AsyncMock

import pytest

from app.models import RoomMapping, RoomType
from app.services import room_manager


@pytest.fixture(autouse=True)
def mock_matrix_client(monkeypatch):
    monkeypatch.setattr(room_manager.matrix_client, "create_room", AsyncMock(return_value="!newroom:hub.local"))
    monkeypatch.setattr(room_manager.matrix_client, "join_room", AsyncMock(return_value=None))
    return room_manager.matrix_client


@pytest.mark.asyncio
async def test_creates_room_on_first_call(db_session):
    mapping = await room_manager.get_or_create_entity_room(
        entity_type="project",
        entity_id=42,
        display_name="1234.5678 - Testprojekt",
        admin_token="bot-token",
        db=db_session,
    )

    assert mapping.matrix_room_id == "!newroom:hub.local"
    assert mapping.room_type == RoomType.entity
    assert mapping.entity_type == "project"
    assert mapping.entity_id == 42
    assert mapping.display_name == "1234.5678 - Testprojekt"
    room_manager.matrix_client.create_room.assert_awaited_once()


@pytest.mark.asyncio
async def test_second_call_returns_same_room_idempotent(db_session):
    first = await room_manager.get_or_create_entity_room(
        entity_type="project", entity_id=42, display_name="A",
        admin_token="bot-token", db=db_session,
    )
    room_manager.matrix_client.create_room.reset_mock()

    second = await room_manager.get_or_create_entity_room(
        entity_type="project", entity_id=42, display_name="A",
        admin_token="bot-token", db=db_session,
    )

    assert second.id == first.id
    assert second.matrix_room_id == first.matrix_room_id
    room_manager.matrix_client.create_room.assert_not_awaited()
    # Idempotent get always re-ensures the bot is a member (may have been
    # created before bot provisioning).
    room_manager.matrix_client.join_room.assert_awaited_once()


@pytest.mark.asyncio
async def test_display_name_not_overwritten_without_update_flag(db_session):
    """A secondary satellite (e.g. engineering-app) opening an existing room
    with a different name must NOT rename it."""
    await room_manager.get_or_create_entity_room(
        entity_type="project", entity_id=42, display_name="1234.5678 - Original",
        admin_token="bot-token", db=db_session, update_display_name=True,
    )

    mapping = await room_manager.get_or_create_entity_room(
        entity_type="project", entity_id=42, display_name="Projekt #42",
        admin_token="bot-token", db=db_session,
        # update_display_name defaults to False
    )

    assert mapping.display_name == "1234.5678 - Original"


@pytest.mark.asyncio
async def test_display_name_updated_with_update_flag(db_session):
    """The authoritative caller (fertigungs-app) renaming an existing room
    (e.g. after the project was renamed) must take effect."""
    await room_manager.get_or_create_entity_room(
        entity_type="project", entity_id=42, display_name="1234.5678 - Alt",
        admin_token="bot-token", db=db_session, update_display_name=True,
    )

    mapping = await room_manager.get_or_create_entity_room(
        entity_type="project", entity_id=42, display_name="1234.5678 - Neu",
        admin_token="bot-token", db=db_session, update_display_name=True,
    )

    assert mapping.display_name == "1234.5678 - Neu"


@pytest.mark.asyncio
async def test_source_url_set_on_create_and_synced_later(db_session):
    mapping = await room_manager.get_or_create_entity_room(
        entity_type="project", entity_id=42, display_name="A",
        admin_token="bot-token", db=db_session,
        source_url="https://fertigung.example/gantt?openProject=42",
    )
    assert mapping.source_url == "https://fertigung.example/gantt?openProject=42"

    # A later call (e.g. from engineering-app, no source_url) must not clear it.
    mapping = await room_manager.get_or_create_entity_room(
        entity_type="project", entity_id=42, display_name="A",
        admin_token="bot-token", db=db_session,
    )
    assert mapping.source_url == "https://fertigung.example/gantt?openProject=42"


@pytest.mark.asyncio
async def test_different_entities_get_separate_rooms(db_session):
    room_manager.matrix_client.create_room = AsyncMock(side_effect=["!room1:hub.local", "!room2:hub.local"])

    a = await room_manager.get_or_create_entity_room(
        entity_type="project", entity_id=1, display_name="A", admin_token="t", db=db_session,
    )
    b = await room_manager.get_or_create_entity_room(
        entity_type="project", entity_id=2, display_name="B", admin_token="t", db=db_session,
    )

    assert a.matrix_room_id != b.matrix_room_id
    assert db_session.query(RoomMapping).count() == 2


@pytest.mark.asyncio
async def test_same_entity_id_different_entity_type_is_separate_room(db_session):
    """entity_id alone isn't unique across entity types (a project #1 and a
    complaint #1 must not collide)."""
    room_manager.matrix_client.create_room = AsyncMock(side_effect=["!proj:hub.local", "!compl:hub.local"])

    project_room = await room_manager.get_or_create_entity_room(
        entity_type="project", entity_id=1, display_name="Projekt", admin_token="t", db=db_session,
    )
    complaint_room = await room_manager.get_or_create_entity_room(
        entity_type="complaint", entity_id=1, display_name="Reklamation", admin_token="t", db=db_session,
    )

    assert project_room.matrix_room_id != complaint_room.matrix_room_id
