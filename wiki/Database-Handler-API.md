# Database Handler API

> **Source:** `services/dbHandler.py`

All protected endpoints require a valid JWT (`Authorization: Bearer <token>`).

---

## Table of Contents

- [User Management](#user-management)
- [Favorite Servers](#favorite-servers)
- [Player Management](#player-management)
- [Player Privileges](#player-privileges)
- [Settings](#settings)

---

## User Management

### `POST /user`

- **Purpose:** Create a new user account.
- **Auth required:** No.
- **Request body:** `{ "username": "<str>", "password": "<str>" }`
- **Responses:**

| Status | Condition            | Body                      |
|--------|----------------------|---------------------------|
| 200    | Always (unless 400)  | `{ "status": true/false }` |
| 400    | Missing body         | `{ "error": "bad request" }` |

### `DELETE /user`

- **Auth required:** Yes.
- **Purpose:** Delete the authenticated user's own account.
- **Request body:** `{ "username": "<str>" }` — must match the authenticated user's own username.
- **Responses:**

| Status | Condition                                  | Body                      |
|--------|--------------------------------------------|---------------------------|
| 200    | Deleted                                    | `{ "status": true }`      |
| 400    | Missing body or `username` field           | `{ "error": "bad request" }` |
| 401    | No JWT                                     | —                         |
| 403    | `username` does not match the JWT's identity | `{ "error": "forbidden" }` |

---

## Favorite Servers

### `POST /favoriteServers`

- **Auth required:** Yes.
- **Request body:** `{ "server_id": <int> }`
- **Responses:** `200 { "status": true/false }` | `400` if body missing or `server_id` is not an integer.

### `DELETE /favoriteServers`

- **Auth required:** Yes.
- **Request body:** `{ "server_id": <int> }`
- **Responses:** `200 { "status": true/false }` | `400` if body missing or `server_id` is not an integer.

### `GET /favoriteServers`

- **Auth required:** Yes.
- **Response:** `200 { "servers": [<int>, ...] }` — list of server IDs.

---

## Player Management

### `POST /player`

- **Auth required:** Yes.
- **Request body:** `{ "name": "<str>", "uuid": "<str>" }`
- **Responses:** `200 { "status": true/false }` | `400` if any required field is missing.

### `DELETE /player`

- **Auth required:** Yes.
- **Request body:** `{ "uuid": "<str>" }`
- **Responses:** `200 { "status": true/false }` | `400` if body or `uuid` missing.

### `GET /player`

- **Auth required:** Yes.
- **Response:** `200 { "players": ["<uuid>", ...] }`.

---

## Player Privileges

### `POST /playerPrivilege`

- **Auth required:** Yes.
- **Request body:** `{ "player_uuid": "<str>", "privilege_id": <int> }`
- **Responses:** `200 { "status": true/false }` | `400` if fields missing or `privilege_id` not an integer.

### `DELETE /playerPrivilege`

- **Auth required:** Yes.
- **Request body:** `{ "player_uuid": "<str>", "privilege_id": <int> }`
- **Responses:** `200 { "status": true/false }` | `400` if fields missing or `privilege_id` not an integer.

### `GET /playerPrivilege`

- **Auth required:** Yes.
- **Request body:** `{ "player_uuid": "<str>" }`
- **Responses:** `200 { "privileges": [<PlayersPrivileges>, ...] }` | `400` if `player_uuid` missing.

---

## Settings

### `POST /setting`

- **Auth required:** Yes.
- **Request body:** `{ "rule": <int>, "approved": <bool> }`
- **Responses:** `200 { "status": true/false }` | `400` if `rule` missing or not an integer.

### `DELETE /setting`

- **Auth required:** Yes.
- **Request body:** `{ "rule": <int> }`
- **Responses:** `200 { "status": true/false }` | `400` if `rule` missing or not an integer.

### `PATCH /setting`

- **Auth required:** Yes.
- **Request body:** `{ "rule": <int>, "approved": <bool> }`
- **Responses:** `200 { "status": true/false }` | `400` if `rule` missing or not an integer.

---

[← Back to Home](Home.md)
