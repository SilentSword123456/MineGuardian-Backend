# Utility Functions

> **Source:** `utils.py`

---

## Configuration

### `getConfig() -> dict | None`

- **Purpose:** Read and return the parsed JSON from `config.json`.
- **Output:** A dict if the file exists and is valid JSON; `None` otherwise.
- **Extras:** Prints an error message and returns `None` on `JSONDecodeError` or if the file is missing.

### `storeConfig(config: dict)`

- **Purpose:** Serialise `config` and overwrite `config.json` with indented JSON.
- **Input:** Any JSON-serialisable dict.

### `generateFlaskKey()`

- **Purpose:** Generate and store a random Flask `SECRET_KEY` if none is set.
- **Behaviour:**
  - Reads config; does nothing if config is `None`.
  - Does nothing if `flaskConfig.SECRET_KEY` already has a non-empty value.
  - Otherwise generates a `secrets.token_urlsafe(32)` value, writes it to `config.flaskConfig.SECRET_KEY`, and calls `storeConfig`.

### `generateJWTSecretKey()`

- **Purpose:** Generate and store a random JWT secret if none is set.
- **Behaviour:** Identical to `generateFlaskKey` but for `config["jwtSecretKey"]`; uses `secrets.token_urlsafe(64)`.

### `generateRconPassword()`

- **Purpose:** Generate and store a random RCON password if none is set.
- **Behaviour:** Identical pattern; uses `secrets.token_urlsafe(24)` and stores in `config["rconPassword"]`.

---

## Server Information

### `getMaxPlayers(serverPath: str | None = None) -> int`

- **Purpose:** Return the configured maximum player count for a server.
- **Input:** `serverPath` — filesystem path to the server directory (str or `None`).
- **Output:** Integer max player count.
- **Behaviour:**
  - Returns `20` (Minecraft default) if `serverPath` is `None` or falsy.
  - Checks `serverSessionsManager.serverInstances` first: if a running instance has a `working_dir` matching the absolute `serverPath` and has `max_players` set, returns that cached value.
  - Falls back to reading `server.properties` in `serverPath` and parsing the `max-players=` line.
  - Returns `20` if the file is missing or the key is absent.

### `getOnlinePlayers(serverInstance) -> dict`

- **Purpose:** Query a running server for live player data via RCON.
- **Input:** A `ServerSession` instance or `None`.
- **Output:** A dict with at minimum `{"max": <int>}`. When the server is running and RCON succeeds: `{"online": <int>, "max": <int>, "players": [<str>, ...]}`.
- **Behaviour:**
  - Returns `{"max": getMaxPlayers(...)}` if `serverInstance` is `None` or not running.
  - Calls `serverInstance.send_rcon_command("list")`.
  - Returns `{"max": ...}` if the RCON call returns `None`.
  - Parses the vanilla list output `"There are X of a max of Y players online: name1, name2"`.
  - Returns `{"max": ...}` on any parsing/RCON exception (never raises).
  - Player list is empty (`[]`) when online count is 0.

### `getServerStats(serverInstance, force=False) -> dict`

- **Purpose:** Return CPU/memory/player stats for a server, with TTL caching.
- **Input:** `serverInstance` — a `ServerSession`; `force` (bool, default `False`) — bypass cache.
- **Output:** Dict with keys `cpu_usage_percent`, `memory_usage_mb`, `max_memory_mb`, `online_players`.
- **Behaviour:**
  - If `force=False` and cached stats are less than 5 seconds old, returns the cached value.
  - If a `_stats_lock` semaphore is present, acquires it (up to 10 s) before computing.
  - On lock timeout, returns cached stats or a zeroed fallback dict.
  - Calls `serverInstance.get_cpu_usage_percent()`, `get_memory_usage_mb()`, `getMaxMemoryMB()`, `getOnlinePlayers()`.

### `getGlobalStats(serverInstances=None) -> dict`

- **Purpose:** Aggregate stats across all running server instances.
- **Input:** An iterable of `ServerSession` objects, or `None` (defaults to all `serverSessionsManager.serverInstances.values()`).
- **Output:** Aggregated dict: `{cpu_usage_percent, memory_usage_mb, max_memory_mb, online_players: {online, max, players}}`.
- **Behaviour:**
  - Skips instances where `is_running()` returns `False`.
  - Sums CPU %, memory MB, max memory MB, and player counts across all running instances.
  - Merges player name lists.
  - Returns zeroed struct when no servers are running.

---

## Server Files & Ports

### `getLaunchCommand(path: str) -> str | None`

- **Purpose:** Read the server launch command from the start script (`launch.sh` on Unix, `launch.bat` on Windows).
- **Input:** `path` — server directory path.
- **Output:** The command string (stripped); `None` if the script does not exist or cannot be read.

### `getMaxMemoryMB(serverPath: str | None) -> int`

- **Purpose:** Determine the maximum heap size in MB from a server's launch command.
- **Input:** `serverPath` — path to server directory or `None`.
- **Output:** Integer MB value.
- **Behaviour:**
  - Returns `-1` if `serverPath` is `None`.
  - Returns the cached `max_memory_mb` value from a running `ServerSession` whose `working_dir` matches.
  - Reads `getLaunchCommand(serverPath)` and parses the `-Xmx` JVM flag:
    - Suffix `M` → value in MB directly.
    - Suffix `G` → value × 1024.
    - No suffix → treats as bytes, divides by 1,048,576.
  - Returns `1024` as default if no `-Xmx` flag found.
  - Returns `-1` if `getLaunchCommand` returns `None`.

### `patchServerProperties(path: str, overrides: dict)`

- **Purpose:** Create or update `server.properties` in the given server directory with the supplied key=value pairs.
- **Input:** `path` — server directory (str); `overrides` — dict of property key→value pairs.
- **Raises `ValueError`** if:
  - `path` is empty/`None`.
  - `path` (resolved to absolute) is not inside the `servers/` directory — prevents path-traversal attacks.
  - The resolved directory does not exist on disk.
- **Behaviour:**
  - Reads existing `server.properties` if present, preserving comments and unrelated keys.
  - Updates matching keys in-place.
  - Appends any keys from `overrides` that were not already in the file.
  - Overwrites the file atomically.

### `getNewPort(usedPorts: set | None = None, type: str = "server") -> int`

- **Purpose:** Find an available TCP port.
- **Input:** `usedPorts` — set of already-used port numbers (uses global `serverSessionsManager.usedPorts` if `None`); `type` — `"server"` (base 25565) or `"rcon"` (base 25575).
- **Output:** An integer port number that is both not in `usedPorts` and not bound by any OS process.
- **Raises `ValueError`** if `type` is not `"server"` or `"rcon"`.
- **Raises `RuntimeError`** if no available port can be found up to 65535.

---

[← Back to Home](Home.md)
