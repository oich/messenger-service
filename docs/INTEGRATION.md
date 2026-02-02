# Messenger-Service: Integrationsdokumentation

Dieses Dokument beschreibt die Schnittstellen des Messenger-Service fuer andere Hub-Anwendungen (Satellites).

---

## Architektur-Ueberblick

```
                 +---------------------+
                 |     AESystek Hub    |
                 |  (hub-backend/      |
                 |   hub-frontend)     |
                 +--------+------------+
                          |  Hub JWT (SSO)
                          v
              +-----------+------------+
              |   Messenger-Service    |
              |                        |
              |  Backend (FastAPI)     |
              |  Frontend (Vue.js)     |
              |  Conduit (Matrix)      |
              |  PostgreSQL            |
              +-----------+------------+
                          ^
                          | HTTP / SSE
                          |
              +-----------+------------+
              |  Andere Satellites     |
              |  (Fertigungs-App,     |
              |   Admin-Dashboard...) |
              +------------------------+
```

Der Messenger-Service laeuft als Satellite im Docker-Netzwerk `hub_satellite_net`. Andere Anwendungen kommunizieren ueber HTTP-Requests mit dem Backend.

---

## Authentifizierung

### Hub SSO (fuer Benutzer)

Der Messenger akzeptiert Hub-JWT-Tokens direkt. Wenn `HUB_SECRET_KEY` konfiguriert ist, wird jeder Request mit einem Hub-Token automatisch authentifiziert. Der Benutzer wird bei erstem Zugriff automatisch auf Matrix provisioniert.

**Token-Format (Hub JWT):**
```json
{
  "sub": "benutzername",
  "role": "admin",
  "tenant_id": 1,
  "display_name": "Max Mustermann",
  "exp": 1769875698,
  "iss": "aesystek-hub"
}
```

### Service-Token (fuer Satellite-zu-Satellite)

Fuer Benachrichtigungen von anderen Anwendungen wird ein Service-Token verwendet:

```
Header: X-Service-Token: <MESSENGER_SERVICE_TOKEN>
```

Der Token wird ueber die Umgebungsvariable `MESSENGER_SERVICE_TOKEN` konfiguriert und muss in allen beteiligten Services identisch sein.

**Automatische Verteilung:** Der Hub verteilt `MESSENGER_SERVICE_URL` und `MESSENGER_SERVICE_TOKEN` automatisch an alle Satellites ueber `satellite_config_service.py` (`build_env_dict`). Die Werte sind auch in den `docker-compose.hub.yml` Dateien aller Satellites hinterlegt, sodass sie im Standalone-Betrieb den Dev-Fallback verwenden.

---

## Notification-API (Hauptschnittstelle fuer andere Apps)

### POST `/api/v1/notifications/send`

Sendet eine Benachrichtigung ueber den Messenger an Benutzer.

**Authentifizierung:** `X-Service-Token` Header

**Request:**
```json
{
  "source_app": "fertigungs-app",
  "event_type": "notification",
  "title": "Maschine gestoppt",
  "body": "Maschine CNC-01 hat einen Fehler gemeldet.",
  "target_type": "general",
  "entity_type": null,
  "entity_id": null,
  "target_user": null,
  "priority": "normal"
}
```

**Felder:**

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|-------------|
| `source_app` | string | ja | Name der sendenden Anwendung |
| `event_type` | string | ja | Event-Typ, z.B. `"notification"`, `"entity_event"` |
| `title` | string | ja | Titel der Benachrichtigung |
| `body` | string | nein | Detailtext |
| `target_type` | string | nein | Ziel: `"general"`, `"entity_room"`, `"dm"` (default: `"general"`) |
| `entity_type` | string | nein | Entity-Typ fuer `entity_room`, z.B. `"machine"`, `"project"` |
| `entity_id` | int | nein | Entity-ID fuer `entity_room` |
| `target_user` | string | nein | Hub-User-ID fuer Direktnachricht (`"dm"`) |
| `priority` | string | nein | `"normal"` oder `"urgent"` (default: `"normal"`) |

**Response (201):**
```json
{
  "id": 42,
  "source_app": "fertigungs-app",
  "event_type": "notification",
  "title": "Maschine gestoppt",
  "body": "Maschine CNC-01 hat einen Fehler gemeldet.",
  "priority": "normal",
  "status": "sent",
  "matrix_room_id": "!abc123:hub.local",
  "matrix_event_id": "$evt456",
  "created_at": "2026-01-31T12:00:00"
}
```

### Ziel-Typen (`target_type`)

#### `"general"` (Standard)
Nachricht geht in den allgemeinen Raum ("Allgemein") des Tenants.

```json
{
  "source_app": "admin-dashboard",
  "event_type": "notification",
  "title": "Wartungsfenster geplant",
  "body": "Am 05.02. von 18:00-20:00 Uhr.",
  "target_type": "general"
}
```

#### `"entity_room"`
Nachricht geht in einen Entity-spezifischen Raum (wird automatisch erstellt).

```json
{
  "source_app": "fertigungs-app",
  "event_type": "entity_event",
  "title": "Auftrag #1234 abgeschlossen",
  "body": "Alle 50 Teile gefertigt.",
  "target_type": "entity_room",
  "entity_type": "production_order",
  "entity_id": 1234
}
```

#### `"dm"`
Direktnachricht an einen bestimmten Benutzer.

```json
{
  "source_app": "fertigungs-app",
  "event_type": "dm_notification",
  "title": "Freigabe erforderlich",
  "body": "Bitte Auftrag #5678 pruefen und freigeben.",
  "target_type": "dm",
  "target_user": "mueller"
}
```

---

## Python Client Library

Fuer Satellites steht eine fertige Client-Bibliothek bereit.

### Installation

```bash
pip install -e /path/to/shared/hub_messenger_client
```

Oder als Abhaengigkeit in `requirements.txt`:
```
hub-messenger-client @ file:///code/shared/hub_messenger_client
```

### Umgebungsvariablen

```bash
MESSENGER_SERVICE_URL=http://messenger-service-backend-1:8000
MESSENGER_SERVICE_TOKEN=messenger-service-token-dev
```

### Verwendung (Synchron)

```python
from hub_messenger_client import MessengerClient

client = MessengerClient()

# Allgemeine Benachrichtigung
client.notify(
    source_app="fertigungs-app",
    title="Schicht gestartet",
    body="Fruehschicht hat begonnen.",
)

# Entity-Benachrichtigung (z.B. an Maschinen-Raum)
client.notify_entity(
    source_app="fertigungs-app",
    entity_type="machine",
    entity_id=42,
    title="Maschine CNC-01 gestoppt",
    body="Fehlercode E-401: Kuehlmittel niedrig",
    priority="urgent",
)

# Direktnachricht an einen Benutzer
client.notify_user(
    source_app="fertigungs-app",
    target_user="mueller",
    title="Aufgabe zugewiesen",
    body="Bitte Maschine CNC-01 pruefen.",
)
```

### Verwendung (Asynchron)

```python
from hub_messenger_client import MessengerClient

client = MessengerClient()

await client.anotify(
    source_app="fertigungs-app",
    title="Async Benachrichtigung",
)

await client.anotify_entity(
    source_app="fertigungs-app",
    entity_type="machine",
    entity_id=42,
    title="Maschine Fehler",
    priority="urgent",
)

await client.anotify_user(
    source_app="fertigungs-app",
    target_user="mueller",
    title="Direktnachricht",
)
```

---

## SSE-Stream (Echtzeit-Events)

### GET `/api/v1/events/stream`

Server-Sent Events Stream fuer Echtzeit-Benachrichtigungen.

**Authentifizierung:** Query-Parameter `token=<JWT>` (EventSource-kompatibel)

```javascript
const es = new EventSource(
  `https://messenger:8085/api/v1/events/stream?token=${hubToken}`
)

es.onmessage = (e) => {
  const event = JSON.parse(e.data)
  // event.type: "new_message", "notification", "keepalive", "connected"
  console.log(event)
}
```

**Event-Typen:**

```json
// Neue Nachricht
{
  "type": "new_message",
  "room_id": "!abc:hub.local",
  "event_id": "$evt123",
  "sender": "@user:hub.local",
  "sender_display_name": "Max Mustermann",
  "body": "Hallo!",
  "msg_type": "m.text"
}

// Benachrichtigung (von anderer App)
{
  "type": "notification",
  "source_app": "fertigungs-app",
  "event_type": "entity_event",
  "title": "Maschine gestoppt",
  "body": "Fehlercode E-401",
  "priority": "urgent",
  "room_id": "!xyz:hub.local"
}

// Keepalive (alle 20 Sekunden)
{ "type": "keepalive" }

// Verbindung hergestellt
{ "type": "connected" }
```

### GET `/api/v1/events/poll`

Polling-Fallback wenn SSE nicht moeglich ist.

**Authentifizierung:** Query-Parameter `token=<JWT>`

**Response:**
```json
[
  { "type": "new_message", "room_id": "...", "body": "..." },
  { "type": "notification", "title": "...", "body": "..." }
]
```

---

## Weitere API-Endpunkte

### Health-Check

**GET `/api/v1/health`** (keine Auth)

```json
{
  "status": "healthy",
  "service": "messenger-service",
  "conduit": "reachable"
}
```

### Benutzer-Info

**GET `/api/v1/users/me`** (Hub-JWT Auth)

```json
{
  "hub_user_id": "admin",
  "display_name": "Administrator",
  "matrix_user_id": "@admin:hub.local",
  "role": "admin",
  "external_client_enabled": false
}
```

### Benutzerliste (fuer DM-Auswahl)

**GET `/api/v1/users?q=suchbegriff`** (Hub-JWT Auth)

```json
[
  { "hub_user_id": "mueller", "display_name": "Max Mueller" },
  { "hub_user_id": "schmidt", "display_name": "Anna Schmidt" }
]
```

### Raeume

**GET `/api/v1/rooms`** (Hub-JWT Auth) - Raumliste des Benutzers

**POST `/api/v1/rooms`** (Hub-JWT Auth) - Raum erstellen
```json
{
  "name": "Projekt Alpha",
  "topic": "Diskussion zum Projekt",
  "invite_users": ["mueller", "schmidt"]
}
```

**POST `/api/v1/rooms/dm/{hub_user_id}`** (Hub-JWT Auth) - DM erstellen/oeffnen

### Nachrichten

**POST `/api/v1/messages/send`** (Hub-JWT Auth)
```json
{
  "room_id": "!abc:hub.local",
  "body": "Hallo Welt!",
  "msg_type": "m.text"
}
```

**GET `/api/v1/messages/history/{room_id}?limit=50`** (Hub-JWT Auth)

**POST `/api/v1/messages/upload`** (Hub-JWT Auth, multipart/form-data)
- Felder: `room_id`, `file`, `body` (optional)

---

## Konfiguration

### Umgebungsvariablen (Backend)

| Variable | Beschreibung | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL Connection-String | *pflicht* |
| `SECRET_KEY` | JWT-Signing-Key (lokal) | `messenger-dev-secret` |
| `HUB_SECRET_KEY` | Hub-SSO-Secret (aktiviert SSO) | *leer* |
| `MATRIX_HOMESERVER_URL` | Conduit-URL | `http://conduit:6167` |
| `MATRIX_SERVER_NAME` | Matrix Server-Name | `hub.local` |
| `MESSENGER_SERVICE_TOKEN` | Token fuer Cross-App-Notifications | `messenger-service-token-dev` |
| `LOG_LEVEL` | Log-Level | `info` |

### Netzwerk

Der Service laeuft im Docker-Netzwerk `hub_satellite_net`. Andere Satellites im gleichen Netzwerk erreichen das Backend unter:

```
http://messenger-service-backend-1:8000
```

Von aussen (Browser) ist der Messenger ueber den Hub-Proxy erreichbar:

```
https://<hub-host>:8085
```

Fuer externe Matrix-Clients (FluffyChat, Element) stehen zwei Ports bereit:

```
https://<hub-host>:8448   (HTTPS, erfordert Zertifikats-Vertrauen)
http://<hub-host>:8008    (HTTP, nur fuer lokale Netzwerk-Clients)
```

Port 8008 ist plain HTTP und gedacht fuer Clients im gleichen LAN, die kein Self-Signed-Zertifikat akzeptieren.

---

## Rollen-Mapping

Hub-Rollen werden auf Messenger-Rollen gemappt:

| Hub-Rolle | Messenger-Rolle |
|-----------|----------------|
| `super_admin` | `admin` |
| `admin` | `admin` |
| `manager` | `user` |
| `user` | `user` |
| `terminal` | `user` |
| `viewer` | `viewer` |

Admin-Benutzer haben Zugriff auf das Admin-Panel (`/admin`) und die Admin-API (`/api/v1/admin/*`).

---

## Integrationsbeispiel: Satellite einbinden

### 1. Docker-Compose erweitern

```yaml
# Im docker-compose.yml des Satellites:
services:
  meine-app:
    environment:
      - MESSENGER_SERVICE_URL=http://messenger-service-backend-1:8000
      - MESSENGER_SERVICE_TOKEN=${MESSENGER_SERVICE_TOKEN:-messenger-service-token-dev}
    networks:
      - default
      - hub_satellite_net

networks:
  hub_satellite_net:
    external: true
```

### 2. Client-Library einbinden

```bash
# In requirements.txt:
hub-messenger-client @ file:///code/shared/hub_messenger_client

# Oder direkt:
pip install -e /pfad/zu/shared/hub_messenger_client
```

### 3. Benachrichtigungen senden

```python
from hub_messenger_client import MessengerClient

messenger = MessengerClient()

# Bei einem Event in der Anwendung:
messenger.notify(
    source_app="meine-app",
    title="Vorgang abgeschlossen",
    body="Der Vorgang wurde erfolgreich bearbeitet.",
)
```

### 4. SSE im Frontend empfangen (optional)

```javascript
// Im Hub-Frontend oder einer Satellite-Webapp:
const token = localStorage.getItem('hub_token')
const es = new EventSource(
  `${MESSENGER_URL}/api/v1/events/stream?token=${token}`
)

es.onmessage = (e) => {
  const data = JSON.parse(e.data)
  if (data.type === 'notification' && data.source_app === 'meine-app') {
    showToast(data.title, data.body)
  }
}
```
