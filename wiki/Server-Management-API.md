# Server Management API

> **Source:** `services/servers.py`

---

## Table of Contents

- [Server Listing & Info](#server-listing--info)
- [Server Lifecycle](#server-lifecycle)
- [Server Stats](#server-stats)
- [Server Installation Management](#server-installation-management)

---

## Server Listing & Info

### `GET /servers`

- **Auth required:** No.
- **Purpose:** List all installed servers.
- **Response:** `200 { "servers": [{ "server_id", "id", "isRunning", "max_memory_mb", "online_players" }, ...] }`.

### `GET /servers/<serverName>`

- **Auth required:** Optional JWT.
- **Purpose:** Return live or cached info about a specific server.
- **Responses:**

| Status | Condition                                    | Body |
|--------|----------------------------------------------|------|
| 200    | Found                                        | `{ "name", "is_running", "pid", "uptime_seconds", "max_memory_mb", "online_players" }` |
| 403    | JWT present and user lacks `GetServerInfo` permission | — |
| 404    | Server name not found                        | — |

- **Extras:** If the server has a running `ServerSession`, values come from `serverInstance.get_process_info()`; otherwise defaults are used.

---

## Server Lifecycle

### `POST /servers/<serverName>/start`

- **Auth required:** No (TODO: should require StartServer perm).
- **Responses:** `200 { "message": "..." }` | `400` if server is already running (`ValueError`).

### `POST /servers/<serverName>/stop`

- **Auth required:** No (TODO: should require StopServer perm).
- **Responses:** `200 { "message": "..." }` | `400` if no instance exists (`ValueError`).

---

## Server Stats

### `GET /servers/<serverName>/stats`

- **Auth required:** No.
- **Responses:**

| Status | Condition                    |
|--------|------------------------------|
| 200    | Server is running; stats returned |
| 404    | Server not found or not running   |
| 500    | Internal error collecting stats   |

### `GET /servers/globalStats`

- **Auth required:** No.
- **Response:** `200` — aggregated stats dict (see [Utility Functions — `getGlobalStats`](Utility-Functions.md#getglobalstatsserverinstancesnone---dict)).
- **Extras:** Returns `500` on unexpected exception.

---

## Server Installation Management

### `POST /manage/addServer`

- **Auth required:** Yes.
- **Request body:** `{ "serverName", "serverSoftware", "serverVersion", "acceptEula" (optional, default false) }`
- **Responses:**

| Status | Condition             | Body |
|--------|-----------------------|------|
| 200    | Success               | `{ "status": true, "message": "..." }` |
| 200    | EULA not accepted     | `{ "status": true, "message": "<eula warning>" }` |
| 400    | Missing required params | — |
| 400    | Install error         | — |
| 500    | DB registration failed | — |

### `DELETE /servers/<serverName>/uninstall`

- **Auth required:** Yes.
- **Responses:** `200 { "status": true, "message": "..." }` | `400` on install error | `404` on DB removal failure.
- **Extras:** Only the server owner (or a user with `RemovePermissionFromServer`) can uninstall.

### `GET /manage/<software>/getAvailableVersions`

- **Auth required:** No.
- **Response:** `200 { "versions": ["latest", ...] }` | `400 { "message": "<error>" }`.

---

[← Back to Home](Home.md)
