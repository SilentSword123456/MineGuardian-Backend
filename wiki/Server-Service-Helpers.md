# Server Service Helpers

> **Source:** `services/server_services.py`

---

## Functions

### `get_all_servers() -> list[dict]`

- **Purpose:** Return a list of all locally installed servers with their metadata.
- **Output:** A list of dicts, one per directory found in `servers/`. Each dict contains:
  - `server_id` (str) — directory name.
  - `id` (int) — sequential 1-based index.
  - `isRunning` (bool) — whether a running `ServerSession` exists for this server.
  - `max_memory_mb` (int) — from `getMaxMemoryMB`.
  - `online_players` (dict) — `{"max": <int>}`.

### `get_server_instance(serverName: str) -> ServerSession`

- **Purpose:** Retrieve (or create) the `ServerSession` for a server, ready to start.
- **Input:** `serverName` (str).
- **Output:** A `ServerSession` instance.
- **Raises `ValueError`** if the server is already running (i.e. a session exists and `is_running()` is `True`).
- **Behaviour:**
  - Returns the existing session if it exists but is not running.
  - Calls `utils.setupServerInstance` to create a new session if none exists.

### `stop_server(serverName: str)`

- **Purpose:** Stop a running server.
- **Input:** `serverName` (str).
- **Output:** `None` (delegates to `ServerSession.stop()`).
- **Raises `ValueError`** if no session exists for `serverName`.

---

[← Back to Home](Home.md)
