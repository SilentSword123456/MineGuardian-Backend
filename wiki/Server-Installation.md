# Server Installation

> **Source:** `manageLocalServers.py`

---

## Functions

### `addAcceptEula(path: str)`

- **Purpose:** Create/overwrite `eula.txt` in `path` with `eula=true`.
- **Input:** `path` — server directory.
- **Output:** `None` (no return value).

### `getAvailableVersions(serverSoftware: str) -> dict`

- **Purpose:** Return a list of downloadable Minecraft server versions.
- **Input:** `serverSoftware` — `"vanilla"` or `"spigot"`.
- **Output:**
  - `{"versions": ["latest", "1.21.1", ...]}` — release versions only (no snapshots/pre-releases), newest first. Always starts with `"latest"` as the first entry.
  - `{"error": <message>}` if:
    - `serverSoftware` is `"spigot"` (not yet implemented).
    - `serverSoftware` is anything other than `"vanilla"` or `"spigot"`.
    - A network error occurs while fetching the Mojang version manifest.

### `installMinecraftServer(serverSoftware, serverVersion, serverName, acceptEula=False) -> bool | dict`

- **Purpose:** Download and set up a Minecraft server.
- **Input:** `serverSoftware` (str); `serverVersion` (str, or `"latest"`); `serverName` (str); `acceptEula` (bool, default `False`).
- **Output:**
  - `True` — installed successfully and EULA accepted.
  - `{"warning": <message>}` — installed but EULA not accepted (server files exist but won't start until `eula.txt` is set).
  - `{"error": <message>}` if:
    - `serverSoftware` is not `"vanilla"` or `"spigot"`.
    - `serverSoftware` is `"spigot"` (not yet implemented).
    - A server with `serverName` already exists locally.
    - The requested `serverVersion` is not found in the Mojang manifest.
    - A network error occurs.
- **Extras:**
  - If `serverVersion == "latest"`, resolves to the current latest release version before downloading.

### `uninstallMinecraftServer(serverName: str) -> bool | dict`

- **Purpose:** Remove a server's files from disk and clean up its in-memory session.
- **Input:** `serverName` (str).
- **Output:**
  - `True` — uninstalled successfully.
  - `{"error": <message>}` if:
    - The server directory does not exist.
    - The server is currently running (must be stopped first).
    - A filesystem error occurs during deletion.
- **Behaviour:**
  - If the server has an entry in `serverSessionsManager.serverInstances`, calls `cleanup()` on it and removes it from the dict.
  - Recursively deletes all files and subdirectories, then removes the top-level server directory.

---

[← Back to Home](Home.md)
