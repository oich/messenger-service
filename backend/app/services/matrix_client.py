"""Wrapper around Matrix Client-Server API using httpx.

Uses direct HTTP calls to Conduit's CS API instead of matrix-nio
for simpler dependency management and better async support.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import httpx

from app.config import MATRIX_HOMESERVER_URL, MATRIX_SERVER_NAME

logger = logging.getLogger("matrix_client")


class MatrixClientError(Exception):
    pass


class MatrixClient:
    """Async HTTP client for Matrix Client-Server API."""

    def __init__(self, homeserver_url: str = MATRIX_HOMESERVER_URL):
        self.homeserver_url = homeserver_url.rstrip("/")
        self._http: Optional[httpx.AsyncClient] = None

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.homeserver_url,
                timeout=30.0,
            )
        return self._http

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    def _auth_headers(self, access_token: str) -> dict:
        return {"Authorization": f"Bearer {access_token}"}

    # --- Authentication ---

    async def register_user(
        self, username: str, password: str, admin: bool = False
    ) -> Dict[str, Any]:
        """Register a new Matrix user via the admin API."""
        client = await self._client()
        body = {
            "username": username,
            "password": password,
            "admin": admin,
            "auth": {"type": "m.login.dummy"},
        }
        resp = await client.post("/_matrix/client/v3/register", json=body)
        if resp.status_code == 200:
            return resp.json()
        # User may already exist
        if resp.status_code == 400:
            data = resp.json()
            if data.get("errcode") == "M_USER_IN_USE":
                return await self.login(username, password)
            raise MatrixClientError(f"Register failed: {data}")
        raise MatrixClientError(f"Register failed: {resp.status_code} {resp.text}")

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and get access token."""
        client = await self._client()
        body = {
            "type": "m.login.password",
            "identifier": {"type": "m.id.user", "user": username},
            "password": password,
        }
        resp = await client.post("/_matrix/client/v3/login", json=body)
        if resp.status_code == 200:
            return resp.json()
        raise MatrixClientError(f"Login failed: {resp.status_code} {resp.text}")

    # --- Rooms ---

    async def create_room(
        self,
        access_token: str,
        name: str,
        topic: Optional[str] = None,
        invite: Optional[List[str]] = None,
        is_direct: bool = False,
        preset: str = "private_chat",
    ) -> str:
        """Create a room, returns room_id."""
        client = await self._client()
        body: Dict[str, Any] = {
            "name": name,
            "preset": preset,
            "visibility": "private",
        }
        if topic:
            body["topic"] = topic
        if invite:
            body["invite"] = invite
        if is_direct:
            body["is_direct"] = True
        resp = await client.post(
            "/_matrix/client/v3/createRoom",
            json=body,
            headers=self._auth_headers(access_token),
        )
        if resp.status_code == 200:
            return resp.json()["room_id"]
        raise MatrixClientError(f"Create room failed: {resp.status_code} {resp.text}")

    async def join_room(self, access_token: str, room_id: str) -> None:
        """Join a room."""
        client = await self._client()
        resp = await client.post(
            f"/_matrix/client/v3/join/{room_id}",
            json={},
            headers=self._auth_headers(access_token),
        )
        if resp.status_code != 200:
            raise MatrixClientError(f"Join room failed: {resp.status_code} {resp.text}")

    async def invite_user(
        self, access_token: str, room_id: str, user_id: str
    ) -> None:
        """Invite a user to a room."""
        client = await self._client()
        resp = await client.post(
            f"/_matrix/client/v3/rooms/{room_id}/invite",
            json={"user_id": user_id},
            headers=self._auth_headers(access_token),
        )
        if resp.status_code not in (200, 403):
            raise MatrixClientError(f"Invite failed: {resp.status_code} {resp.text}")

    async def list_joined_rooms(self, access_token: str) -> List[str]:
        """List all rooms the user has joined."""
        client = await self._client()
        resp = await client.get(
            "/_matrix/client/v3/joined_rooms",
            headers=self._auth_headers(access_token),
        )
        if resp.status_code == 200:
            return resp.json().get("joined_rooms", [])
        raise MatrixClientError(f"List rooms failed: {resp.status_code} {resp.text}")

    # --- Messages ---

    async def send_message(
        self,
        access_token: str,
        room_id: str,
        body: str,
        msg_type: str = "m.text",
        txn_id: Optional[str] = None,
    ) -> str:
        """Send a message to a room, returns event_id."""
        import uuid

        client = await self._client()
        if not txn_id:
            txn_id = str(uuid.uuid4())
        content = {"msgtype": msg_type, "body": body}
        resp = await client.put(
            f"/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txn_id}",
            json=content,
            headers=self._auth_headers(access_token),
        )
        if resp.status_code == 200:
            return resp.json()["event_id"]
        raise MatrixClientError(f"Send failed: {resp.status_code} {resp.text}")

    async def get_room_messages(
        self,
        access_token: str,
        room_id: str,
        limit: int = 50,
        from_token: Optional[str] = None,
        direction: str = "b",  # b=backwards, f=forwards
    ) -> Dict[str, Any]:
        """Get message history for a room."""
        client = await self._client()
        params: Dict[str, Any] = {"dir": direction, "limit": limit}
        if from_token:
            params["from"] = from_token
        resp = await client.get(
            f"/_matrix/client/v3/rooms/{room_id}/messages",
            params=params,
            headers=self._auth_headers(access_token),
        )
        if resp.status_code == 200:
            return resp.json()
        raise MatrixClientError(f"Get messages failed: {resp.status_code} {resp.text}")

    # --- File upload ---

    async def upload_file(
        self,
        access_token: str,
        file_data: bytes,
        content_type: str,
        filename: str,
    ) -> str:
        """Upload a file to Matrix content repository, returns mxc:// URI."""
        client = await self._client()
        headers = {
            **self._auth_headers(access_token),
            "Content-Type": content_type,
        }
        params = {"filename": filename}
        # Try v3 first, then r0 for older Conduit versions
        for media_path in ["/_matrix/media/v3/upload", "/_matrix/media/r0/upload"]:
            resp = await client.post(
                media_path,
                content=file_data,
                headers=headers,
                params=params,
                timeout=httpx.Timeout(60.0),
            )
            if resp.status_code == 200:
                content_uri = resp.json().get("content_uri")
                logger.info("File uploaded: %s via %s", content_uri, media_path)
                return content_uri
            logger.debug("Upload via %s failed: %d %s", media_path, resp.status_code, resp.text[:200])

        raise MatrixClientError(f"Upload failed: {resp.status_code} {resp.text}")

    async def send_message_event(
        self,
        access_token: str,
        room_id: str,
        content: Dict[str, Any],
        txn_id: Optional[str] = None,
    ) -> str:
        """Send a message event with arbitrary content to a room, returns event_id."""
        import uuid

        client = await self._client()
        if not txn_id:
            txn_id = str(uuid.uuid4())
        resp = await client.put(
            f"/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txn_id}",
            json=content,
            headers=self._auth_headers(access_token),
        )
        if resp.status_code == 200:
            return resp.json()["event_id"]
        raise MatrixClientError(f"Send event failed: {resp.status_code} {resp.text}")

    # --- Sync ---

    async def sync(
        self,
        access_token: str,
        since: Optional[str] = None,
        timeout: int = 30000,
        filter_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Long-poll sync endpoint."""
        client = await self._client()
        params: Dict[str, Any] = {"timeout": timeout}
        if since:
            params["since"] = since
        if filter_str:
            params["filter"] = filter_str
        resp = await client.get(
            "/_matrix/client/v3/sync",
            params=params,
            headers=self._auth_headers(access_token),
            timeout=httpx.Timeout(timeout / 1000 + 10),
        )
        if resp.status_code == 200:
            return resp.json()
        raise MatrixClientError(f"Sync failed: {resp.status_code} {resp.text}")

    # --- Profile ---

    async def set_display_name(
        self, access_token: str, user_id: str, display_name: str
    ) -> None:
        client = await self._client()
        resp = await client.put(
            f"/_matrix/client/v3/profile/{user_id}/displayname",
            json={"displayname": display_name},
            headers=self._auth_headers(access_token),
        )
        if resp.status_code != 200:
            logger.warning("Set display name failed: %s %s", resp.status_code, resp.text)

    # --- Server info ---

    async def server_versions(self) -> Dict[str, Any]:
        """Check server health via /_matrix/client/versions."""
        client = await self._client()
        resp = await client.get("/_matrix/client/versions")
        if resp.status_code == 200:
            return resp.json()
        raise MatrixClientError(f"Versions check failed: {resp.status_code}")


# Singleton instance
matrix_client = MatrixClient()
