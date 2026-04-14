# MineGuardian Backend — Functionality Specification

This document describes the intended behaviour of every module, class, and function
in the codebase: its inputs, outputs, and any special edge cases the implementation
must honour.  Tests should be written (or verified) against this specification.

---

## Table of Contents

1. [Database/perms.py — Permission Enums](#1-databasepermspy--permission-enums)
2. [Database/repositories.py — Repository Layer](#2-databaserepositoriespy--repository-layer)
   - [UserRepository](#userrepository)
   - [FavoriteServersRepository](#favoriteserversrepository)
   - [PlayerRepository](#playerrepository)
   - [PlayersPrivilegesRepository](#playersprivilegesrepository)
   - [SettingsRepository](#settingsrepository)
   - [ServersRepository](#serversrepository)
   - [ServersUsersPermsRepository](#serversuserspermsrepository)
3. [rcon.py — RCON Client](#3-rconpy--rcon-client)
   - [RconClient](#rconclient)
4. [utils.py — Utility Functions](#4-utilspy--utility-functions)
5. [serverSessionsManager.py — ServerSession](#5-serversessionsmanagerpy--serversession)
6. [manageLocalServers.py — Server Installation](#6-managelocalserverspy--server-installation)
7. [services/server_services.py — Server Service Helpers](#7-servicesserver_servicespy--server-service-helpers)
8. [services/auth.py — Authentication API](#8-servicesauthpy--authentication-api)
9. [services/dbHandler.py — Database Handler API](#9-servicesdbhandlerpy--database-handler-api)
10. [services/servers.py — Server Management API](#10-servicesserverspy--server-management-api)

---

## 1. Database/perms.py — Permission Enums

Defines integer-valued enumerations used as permission IDs throughout the system.

### PlayersPermissions (Enum)
| Name                | Value |
|---------------------|-------|
| WhitelistedByDefault | 0    |
| OP                  | 1     |

### SettingsPermissions (Enum)
| Name     | Value |
|----------|-------|
| NotBlank | 0     |

### ServersPermissions (Enum)
| Name                      | Value |
|---------------------------|-------|
| AddPermissionToServer     | 1     |
| RemovePermissionFromServer| 2     |
| GetServerInfo             | 3     |
| StartServer               | 4     |
| StopServer                | 5     |

---

## 2. Database/repositories.py — Repository Layer

All repository methods operate against a SQLAlchemy session obtained from `db`.
They are pure database operations with no side effects outside the database.

---

### UserRepository

#### `createUser(username: str, password: str) -> bool`
- **Purpose:** Register a new user account.
- **Input:** `username` — the desired username (str); `password` — plaintext password (str).
- **Output:** `True` if the user was created; `False` if a user with the same username already exists.
- **Behaviour:**
  - Hashes `password` with SHA-256 before storing.
  - Rejects duplicate usernames (case-sensitive match).
  - Does **not** validate username/password length or character set (caller responsibility).

#### `removeUser(username: str) -> bool`
- **Purpose:** Delete a user account by username.
- **Input:** `username` — exact username to delete (str).
- **Output:** `True` if the user existed and was deleted; `False` if no such user exists.

#### `verify(username: str, password: str) -> bool`
- **Purpose:** Check username/password credentials.
- **Input:** `username` (str); `password` — plaintext password (str).
- **Output:** `True` if credentials are valid; `False` otherwise.
- **Behaviour:**
  - Hashes `password` with SHA-256 and compares against the stored hash.
  - Returns `False` if the username does not exist.

#### `getUserId(username: str) -> int`
- **Purpose:** Look up the numeric primary-key ID for a username.
- **Input:** `username` (str).
- **Output:** The integer user ID if found; `0` if the username does not exist.

#### `getUsername(userId: int) -> str`
- **Purpose:** Look up a username by numeric ID.
- **Input:** `userId` (int).
- **Output:** The username string if found; `''` (empty string) if the user does not exist.
- **Behaviour:** Calls `doseUserExist` first; returns `''` if the check fails.

#### `doseUserExist(userId: int) -> bool`  *(note: typo is intentional — matches source)*
- **Purpose:** Check whether a user with the given numeric ID exists.
- **Input:** `userId` (int).
- **Output:** `True` if found; `False` otherwise.

---

### FavoriteServersRepository

#### `addFavoriteServer(serverId: int, userId: int) -> bool`
- **Purpose:** Mark a server as a favourite for a user.
- **Input:** `serverId` (int) — the server's numeric ID; `userId` (int).
- **Output:** `True` if added; `False` if:
  - The user does not exist.
  - The server is already in the user's favourites list.

#### `removeFavoriteServer(userId: int, serverId: int) -> bool`
- **Purpose:** Remove a server from a user's favourites.
- **Input:** `userId` (int); `serverId` (int).
- **Output:** `True` if the entry existed and was removed; `False` if:
  - The user does not exist.
  - The server was not in the user's favourites.

#### `getFavoriteServers(userId: int) -> list[int]`
- **Purpose:** Return all favourite server IDs for a user.
- **Input:** `userId` (int).
- **Output:** A list of integer server IDs (may be empty).
- **Behaviour:** Returns `[]` if the user does not exist.

---

### PlayerRepository

#### `createPlayer(userId: int, name: str, uuid: str) -> bool`
- **Purpose:** Register a Minecraft player under a user account.
- **Input:** `userId` (int); `name` (str) — in-game name; `uuid` (str) — Minecraft UUID.
- **Output:** `True` if created; `False` if the user does not exist.

#### `removePlayer(userId: int, uuid: str) -> bool`
- **Purpose:** Delete a player record by UUID under a user account.
- **Input:** `userId` (int); `uuid` (str).
- **Output:** `True` if deleted; `False` if:
  - The user does not exist.
  - No player with that UUID exists under the user.

#### `getAllPlayersUUIDs(userId: int) -> list[str]`
- **Purpose:** Return all Minecraft UUIDs registered to a user.
- **Input:** `userId` (int).
- **Output:** A list of UUID strings (may be empty).
- **Behaviour:** Returns `[]` if the user does not exist.

#### `getPlayerId(userId: int, playerUUID: str) -> int`
- **Purpose:** Get the database primary key for a player.
- **Input:** `userId` (int); `playerUUID` (str).
- **Output:** The player's integer ID if found; `0` if:
  - The user does not exist.
  - No player with that UUID exists under the user.

---

### PlayersPrivilegesRepository

#### `addPrivilege(userId: int, playerUUID: str, privilegeId: int) -> bool`
- **Purpose:** Assign a privilege to a player.
- **Input:** `userId` (int); `playerUUID` (str); `privilegeId` (int — must be a valid `PlayersPermissions` value).
- **Output:** `True` if added; `False` if:
  - `privilegeId` is not a valid `PlayersPermissions` value.
  - The user does not exist.
  - The player UUID does not exist under the user (i.e. `getPlayerId` returns `0`).
  - The player already had the privilege.

#### `deletePrivilege(userId: int, playerUUID: str, privilegeId: int) -> bool`
- **Purpose:** Remove a privilege from a player.
- **Input:** `userId` (int); `playerUUID` (str); `privilegeId` (int).
- **Output:** `True` if one or more matching rows were deleted; `False` if:
  - The user does not exist.
  - The player UUID does not exist under the user.
  - No privilege row matching both `playerId` and `privilegeId` exists.

#### `getPlayerPrivileges(userId: int, playerUUID: str) -> list[PlayersPrivileges]`
- **Purpose:** Return all privilege rows for a player.
- **Input:** `userId` (int); `playerUUID` (str).
- **Output:** A list of `PlayersPrivileges` ORM objects (may be empty).
- **Behaviour:** Returns `[]` if the player ID resolves to `0`.

---

### SettingsRepository

#### `addSetting(userId: int, rule: int, approved: bool = False) -> bool`
- **Purpose:** Create a user setting.
- **Input:** `userId` (int); `rule` (int — must be a valid `SettingsPermissions` value); `approved` (bool, default `False`).
- **Output:** `True` if created; `False` if:
  - The user does not exist.
  - `rule` is not a valid `SettingsPermissions` value.
  - A setting with the same `(userId, rule)` pair already exists.

#### `removeSetting(userId: int, rule: int) -> bool`
- **Purpose:** Delete a user setting.
- **Input:** `userId` (int); `rule` (int).
- **Output:** `True` if deleted; `False` if:
  - The user does not exist.
  - No matching setting row exists.

#### `changeSetting(userId: int, rule: int, approved: bool = False) -> bool`
- **Purpose:** Update the `approved` flag of an existing setting.
- **Input:** `userId` (int); `rule` (int); `approved` (bool, default `False`).
- **Output:** `True` if updated; `False` if:
  - The user does not exist.
  - No matching setting row exists.

---

### ServersRepository

#### `addServer(userId: int, serverName: str) -> bool`
- **Purpose:** Register a server in the database under a user.
- **Input:** `userId` (int) — the owner's ID; `serverName` (str).
- **Output:** `True` if created; `False` if the user does not exist or there is already a server with the same name.

#### `removeServer(userId: int, serverName: str) -> bool`
- **Purpose:** Remove a server record.
- **Input:** `userId` (int); `serverName` (str).
- **Output:** `True` if deleted; `False` if:
  - The user does not exist.
  - No server with that name owned by the user exists.

#### `changeServerName(userId: int, currentServerName: str, newServerName: str) -> bool`
- **Purpose:** Rename a server.
- **Input:** `userId` (int); `currentServerName` (str); `newServerName` (str).
- **Output:** `True` if renamed; `False` if:
  - The user does not exist.
  - No server with `currentServerName` owned by the user exists.
  - A server with `newServerName` already exists under the same user.

#### `doseServerExist(serverId: int) -> bool`
- **Purpose:** Check whether a server with the given primary-key ID exists.
- **Input:** `serverId` (int).
- **Output:** `True` if found; `False` otherwise.

#### `getServerOwner(serverId: int) -> int`
- **Purpose:** Return the owner's user ID for a server.
- **Input:** `serverId` (int).
- **Output:** The owner's user ID (int); `0` if the server does not exist.

#### `getServerId(userId: int, serverName: str) -> int`
- **Purpose:** Look up a server's primary key given the owner ID and name.
- **Input:** `userId` (int); `serverName` (str).
- **Output:** The server's integer ID if found; `0` if:
  - The user does not exist.
  - No server with that name owned by the user exists.

---

### ServersUsersPermsRepository

#### `addPerm(userId: int, serverId: int, targetUserId: int, permId: int) -> bool`
- **Purpose:** Grant a permission on a server to a target user.
- **Input:** `userId` (int) — the granting user; `serverId` (int); `targetUserId` (int) — the user receiving the permission; `permId` (int — must be a valid `ServersPermissions` value).
- **Output:** `True` if granted; `False` if:
  - Either `userId` or `targetUserId` does not exist.
  - The server does not exist.
  - `userId` is neither the server owner **nor** holds `AddPermissionToServer` on the server.
  - `permId` is not a valid `ServersPermissions` value.

#### `removePerm(userId: int, serverId: int, targetUserId: int, permId: int) -> bool`
- **Purpose:** Revoke a permission on a server from a target user.
- **Input:** `userId` (int) — the revoking user; `serverId` (int); `targetUserId` (int); `permId` (int).
- **Output:** `True` if revoked; `False` if:
  - Either `userId` or `targetUserId` does not exist.
  - The server does not exist.
  - `userId` is neither the server owner **nor** holds `RemovePermissionFromServer`.
  - No matching permission row exists for the target user.

#### `getPerms(userId: int, serverId: int) -> list[int]`
- **Purpose:** Return all permission IDs held by a user on a server.
- **Input:** `userId` (int); `serverId` (int).
- **Output:** A list of integer permission IDs (may be empty).
- **Behaviour:** Returns `[]` if the user or server does not exist.

#### `doseUserHavePerm(userId: int, serverId: int, permId: int) -> bool`
- **Purpose:** Check whether a user holds a specific permission on a server.
- **Input:** `userId` (int); `serverId` (int); `permId` (int).
- **Output:** `True` if the user has the permission; `False` otherwise.
- **Behaviour:**
  - Returns `False` if the user does not exist.
  - Returns `False` if the server does not exist.
  - Returns `False` if `getPerms` returns an empty list.

---

## 3. rcon.py — RCON Client

Implements the [Minecraft RCON protocol](https://minecraft.wiki/w/RCON) over TCP.

### Error classes

| Class          | Meaning |
|----------------|---------|
| `RconAuthError`| Raised when RCON authentication fails (wrong password, or session invalidated). |
| `RconError`    | Raised for all other RCON communication failures (connection error, timeout, malformed packet, etc.). |

The two classes are **independent** — neither is a subclass of the other.

---

### RconClient

#### `__init__(host, port, password, timeout=5.0)`
- **Purpose:** Create a client instance (does **not** connect).
- **Inputs:** `host` (str, default `"127.0.0.1"`); `port` (int, default `25575`); `password` (str, default `""`); `timeout` (float seconds, default `5.0`).
- **State after:** `_sock` is `None`; `_req_id` counter starts at `0`.

#### `connect()`
- **Purpose:** Open a TCP connection and authenticate.
- **Behaviour:**
  1. Creates a `socket.socket` and calls `socket.connect((host, port))`.
  2. Sends a login packet (type `3`) with the password as payload.
  3. Reads the response packet.
  4. If the response ID is `−1` → raises `RconAuthError`.
  5. If the response ID does not match the sent request ID → raises `RconError`.
  6. If `socket.connect` raises `OSError` → raises `RconError` and sets `_sock = None`.
- **On success:** `_sock` is set to the connected socket.
- **On failure:** `disconnect()` is called to clean up, then the exception is re-raised.

#### `disconnect()`
- **Purpose:** Close the TCP connection.
- **Behaviour:**
  - If `_sock` is not `None`, calls `_sock.close()` and sets `_sock = None`.
  - If `_sock` is already `None`, does nothing (no exception).
  - `OSError` raised by `close()` is silently swallowed.

#### `send_command(command: str) -> str`
- **Purpose:** Send a console command and return the full text response.
- **Input:** `command` — the command string (str, must not be blank for meaningful output).
- **Output:** A string containing the server's response (may be empty string `""`).
- **Behaviour:**
  1. Raises `RconError` if not connected (`_sock is None`).
  2. Sends a command packet (type `2`).
  3. Reads packets in a loop (up to `max_packets = 100`) and skips any stray packets whose ID does not match the sent command ID.
  4. If no matching packet is found in `max_packets` iterations → raises `RconError`.
  5. If a packet with ID `−1` arrives → raises `RconAuthError` (session invalidated).
  6. After receiving the first matching packet, uses a short (0.1 s) timeout to collect any immediately buffered fragment packets with the same ID, then reassembles them in order.
  7. Returns the concatenated payload of all fragments as a single string.

#### `_next_id() -> int`
- **Purpose:** Produce the next sequential request ID.
- **Behaviour:**
  - Increments `_req_id` by 1.
  - Wraps back to `1` after reaching `2^30` (stays positive and fits in a signed 32-bit int).
  - Always returns a positive integer in the range `[1, 2^30]`.

#### `_send_packet(req_id, pkt_type, payload)`
- **Purpose:** Encode and send one RCON packet on the wire.
- **Wire format (little-endian):**
  ```
  Length  (int32) = 4 + 4 + len(payload_bytes) + 2
  ReqID   (int32)
  Type    (int32)
  Payload (UTF-8 bytes)
  0x00 0x00  (two null bytes)
  ```

#### `_recv_packet() -> (req_id: int, pkt_type: int, payload: str)`
- **Purpose:** Read and decode one RCON response packet from the socket.
- **Output:** A 3-tuple `(request_id, packet_type, payload_string)`.
- **Behaviour:**
  - Reads the 4-byte length prefix first.
  - Raises `RconError` if `length < 10` (too small to be valid).
  - Raises `RconError` if `length > 4096` (oversized / malicious).
  - Decodes payload bytes as UTF-8 with `errors="replace"`.

#### `_recv_exactly(num_bytes: int) -> bytes`
- **Purpose:** Read exactly `num_bytes` from the socket, reassembling fragmented chunks.
- **Behaviour:**
  - Loops until `len(buf) == num_bytes`.
  - If `recv()` returns `b""` (connection closed) → raises `RconError`.
  - If `socket.timeout` is raised → raises `RconError`.
  - If `OSError` is raised → raises `RconError`.

#### Context manager (`with RconClient(...) as rcon`)
- `__enter__` calls `connect()` and returns `self`.
- `__exit__` always calls `disconnect()`, even if the body raised.
- Does **not** suppress exceptions from the `with` body.

---

## 4. utils.py — Utility Functions

#### `getConfig() -> dict | None`
- **Purpose:** Read and return the parsed JSON from `config.json`.
- **Output:** A dict if the file exists and is valid JSON; `None` otherwise.
- **Extras:** Prints an error message and returns `None` on `JSONDecodeError` or if the file is missing.

#### `storeConfig(config: dict)`
- **Purpose:** Serialise `config` and overwrite `config.json` with indented JSON.
- **Input:** Any JSON-serialisable dict.

#### `generateFlaskKey()`
- **Purpose:** Generate and store a random Flask `SECRET_KEY` if none is set.
- **Behaviour:**
  - Reads config; does nothing if config is `None`.
  - Does nothing if `flaskConfig.SECRET_KEY` already has a non-empty value.
  - Otherwise generates a `secrets.token_urlsafe(32)` value, writes it to `config.flaskConfig.SECRET_KEY`, and calls `storeConfig`.

#### `generateJWTSecretKey()`
- **Purpose:** Generate and store a random JWT secret if none is set.
- **Behaviour:** Identical to `generateFlaskKey` but for `config["jwtSecretKey"]`; uses `secrets.token_urlsafe(64)`.

#### `generateRconPassword()`
- **Purpose:** Generate and store a random RCON password if none is set.
- **Behaviour:** Identical pattern; uses `secrets.token_urlsafe(24)` and stores in `config["rconPassword"]`.

#### `getMaxPlayers(serverPath: str | None = None) -> int`
- **Purpose:** Return the configured maximum player count for a server.
- **Input:** `serverPath` — filesystem path to the server directory (str or `None`).
- **Output:** Integer max player count.
- **Behaviour:**
  - Returns `20` (Minecraft default) if `serverPath` is `None` or falsy.
  - Checks `serverSessionsManager.serverInstances` first: if a running instance has a `working_dir` matching the absolute `serverPath` and has `max_players` set, returns that cached value.
  - Falls back to reading `server.properties` in `serverPath` and parsing the `max-players=` line.
  - Returns `20` if the file is missing or the key is absent.

#### `getOnlinePlayers(serverInstance) -> dict`
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

#### `getServerStats(serverInstance, force=False) -> dict`
- **Purpose:** Return CPU/memory/player stats for a server, with TTL caching.
- **Input:** `serverInstance` — a `ServerSession`; `force` (bool, default `False`) — bypass cache.
- **Output:** Dict with keys `cpu_usage_percent`, `memory_usage_mb`, `max_memory_mb`, `online_players`.
- **Behaviour:**
  - If `force=False` and cached stats are less than 5 seconds old, returns the cached value.
  - If a `_stats_lock` semaphore is present, acquires it (up to 10 s) before computing.
  - On lock timeout, returns cached stats or a zeroed fallback dict.
  - Calls `serverInstance.get_cpu_usage_percent()`, `get_memory_usage_mb()`, `getMaxMemoryMB()`, `getOnlinePlayers()`.

#### `getGlobalStats(serverInstances=None) -> dict`
- **Purpose:** Aggregate stats across all running server instances.
- **Input:** An iterable of `ServerSession` objects, or `None` (defaults to all `serverSessionsManager.serverInstances.values()`).
- **Output:** Aggregated dict: `{cpu_usage_percent, memory_usage_mb, max_memory_mb, online_players: {online, max, players}}`.
- **Behaviour:**
  - Skips instances where `is_running()` returns `False`.
  - Sums CPU %, memory MB, max memory MB, and player counts across all running instances.
  - Merges player name lists.
  - Returns zeroed struct when no servers are running.

#### `getLaunchCommand(path: str) -> str | None`
- **Purpose:** Read the server launch command from the start script (`launch.sh` on Unix, `launch.bat` on Windows).
- **Input:** `path` — server directory path.
- **Output:** The command string (stripped); `None` if the script does not exist or cannot be read.

#### `getMaxMemoryMB(serverPath: str | None) -> int`
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

#### `patchServerProperties(path: str, overrides: dict)`
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

#### `getNewPort(usedPorts: set | None = None, type: str = "server") -> int`
- **Purpose:** Find an available TCP port.
- **Input:** `usedPorts` — set of already-used port numbers (uses global `serverSessionsManager.usedPorts` if `None`); `type` — `"server"` (base 25565) or `"rcon"` (base 25575).
- **Output:** An integer port number that is both not in `usedPorts` and not bound by any OS process.
- **Raises `ValueError`** if `type` is not `"server"` or `"rcon"`.
- **Raises `RuntimeError`** if no available port can be found up to 65535.

---

## 5. serverSessionsManager.py — ServerSession

Module-level globals:
- `serverInstances: dict[str, ServerSession]` — maps server name → live `ServerSession` object.
- `usedPorts: set[int]` — all ports currently assigned to running instances.

---

### ServerSession

#### `__init__(name, command, working_dir=None)`
- **Purpose:** Initialise a server session and reserve TCP ports.
- **Inputs:** `name` (str); `command` (str or list); `working_dir` (str, path to the server folder).
- **Behaviour:**
  - If `command` is a `str`, splits it into a list via `str.split()`.
  - Calls `getNewPort` and `assignNewPort` to reserve a server port (`self.port`) and an RCON port (`self.rcon_port`).
  - Initial state: `_running = False`, `process = None`, `listeners = []`, `status_listeners = []`, `log_history = []`, `max_history = 100`.

#### `running` (property, getter)
- Returns the live running state by checking `is_running()`.
- If the live state differs from `_running`, sets `running = live` (triggering the setter).

#### `running` (property, setter)
- **Behaviour:** If the new value differs from `_running`, updates `_running` and calls `_broadcast_status(value)`.
- Does **not** broadcast if the value is unchanged.

#### `add_listener(callback)`
- Registers `callback` for log line events (called by `_broadcast`).
- Does **not** add duplicates (idempotent).

#### `remove_listener(callback)`
- Deregisters `callback`; no-op if not registered.

#### `add_status_listener(callback)`
- Registers `callback` for server running-state events (called by `_broadcast_status`).
- Does **not** add duplicates (idempotent).

#### `_broadcast_status(is_running: bool)`
- Calls each registered status listener with the new boolean state.
- Exceptions raised by listeners are caught and printed; they do **not** propagate.

#### `_broadcast(line: str)`
- Calls `_updateHistory(line)`, then calls each registered log listener with the line.
- Exceptions raised by listeners are caught and printed; they do **not** propagate.

#### `_updateHistory(line: str)`
- Appends `line` to `log_history`.
- If `len(log_history) > max_history`, drops the oldest entry (index 0).

#### `start() -> bool`
- **Purpose:** Launch the Minecraft server process.
- **Output:** `True` on success; `False` if already running or on start error.
- **Behaviour:**
  - Does nothing (prints message, returns `False`) if already running.
  - Launches `self.command` as a subprocess with stdin/stdout pipes.
  - Sets `running = True`, spawns `_read_output` and `_monitor_process_exit` green threads.

#### `stop(timeout=30) -> bool`
- **Purpose:** Gracefully stop the server; force-kill if it does not stop within `timeout` seconds.
- **Output:** `True` after stopping; `False` if not currently running.
- **Behaviour:**
  - Sends `"stop"` via `send_command`, then polls every second up to `timeout`.
  - If still alive after timeout, calls `process.terminate()`, waits 2 s, then `process.kill()`.
  - Always sets `running = False` and calls `cleanup()` before returning.

#### `is_running() -> bool`
- **Output:** `True` if `process` is set **and** `process.poll()` returns `None`; `False` otherwise.

#### `send_command(command: str) -> bool`
- **Purpose:** Write a command to the server's stdin.
- **Output:** `True` on success; `False` if:
  - Server is not running.
  - `command.strip()` is empty/blank.
  - An exception occurs writing to stdin.

#### `send_rcon_command(command: str) -> str | None`
- **Purpose:** Send a command via the persistent RCON connection (lazy connect / auto-reconnect).
- **Output:** The RCON response string; `None` if RCON is unavailable or fails after one reconnect attempt.

#### `get_process_info() -> dict`
- **Purpose:** Return a snapshot of the server's current state.
- **Output:** Dict with keys:
  - `server_id` (str) — the server name.
  - `is_running` (bool).
  - `pid` (int) — `0` when not running.
  - `uptime_seconds` (float) — `0.0` when not running.
  - `max_memory_mb` (int).
  - `max_players` (int).

#### `cleanup()`
- **Purpose:** Release resources held by this session.
- **Behaviour:**
  - If an RCON connection is open, disconnects it and sets `_rcon = None`.
  - Removes `self.port` and `self.rcon_port` from `serverSessionsManager.usedPorts`.
  - Safe to call when no RCON connection is open.

#### `get_memory_usage_mb() -> float`
- **Output:** Resident memory of the server process + all children in MB (rounded to 2 dp); `0.0` if process is not running or access is denied.

#### `get_cpu_usage_percent() -> float`
- **Output:** CPU usage % of the process + all children, normalised by CPU count; `0.0` if process is not running or access is denied.

---

## 6. manageLocalServers.py — Server Installation

#### `addAcceptEula(path: str)`
- **Purpose:** Create/overwrite `eula.txt` in `path` with `eula=true`.
- **Input:** `path` — server directory.
- **Output:** `None` (no return value).

#### `getAvailableVersions(serverSoftware: str) -> dict`
- **Purpose:** Return a list of downloadable Minecraft server versions.
- **Input:** `serverSoftware` — `"vanilla"` or `"spigot"`.
- **Output:**
  - `{"versions": ["latest", "1.21.1", ...]}` — release versions only (no snapshots/pre-releases), newest first. Always starts with `"latest"` as the first entry.
  - `{"error": <message>}` if:
    - `serverSoftware` is `"spigot"` (not yet implemented).
    - `serverSoftware` is anything other than `"vanilla"` or `"spigot"`.
    - A network error occurs while fetching the Mojang version manifest.

#### `installMinecraftServer(serverSoftware, serverVersion, serverName, acceptEula=False) -> bool | dict`
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

#### `uninstallMinecraftServer(serverName: str) -> bool | dict`
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

## 7. services/server_services.py — Server Service Helpers

#### `get_all_servers() -> list[dict]`
- **Purpose:** Return a list of all locally installed servers with their metadata.
- **Output:** A list of dicts, one per directory found in `servers/`. Each dict contains:
  - `server_id` (str) — directory name.
  - `id` (int) — sequential 1-based index.
  - `isRunning` (bool) — whether a running `ServerSession` exists for this server.
  - `max_memory_mb` (int) — from `getMaxMemoryMB`.
  - `online_players` (dict) — `{"max": <int>}`.

#### `get_server_instance(serverName: str) -> ServerSession`
- **Purpose:** Retrieve (or create) the `ServerSession` for a server, ready to start.
- **Input:** `serverName` (str).
- **Output:** A `ServerSession` instance.
- **Raises `ValueError`** if the server is already running (i.e. a session exists and `is_running()` is `True`).
- **Behaviour:**
  - Returns the existing session if it exists but is not running.
  - Calls `utils.setupServerInstance` to create a new session if none exists.

#### `stop_server(serverName: str)`
- **Purpose:** Stop a running server.
- **Input:** `serverName` (str).
- **Output:** `None` (delegates to `ServerSession.stop()`).
- **Raises `ValueError`** if no session exists for `serverName`.

---

## 8. services/auth.py — Authentication API

### `POST /login`
- **Purpose:** Authenticate a user and return a JWT access token.
- **Request body:** `{ "user_id": "<username>", "password": "<plaintext>" }`
- **Responses:**
  | Status | Condition | Body |
  |--------|-----------|------|
  | 200 | Credentials valid | `{ "access_token": "<JWT>" }` |
  | 400 | Missing `user_id` or `password` | `{ "message": "Missing user_id or password" }` |
  | 401 | Invalid credentials | `{ "message": "Invalid credentials" }` |
- **Extras:** Uses `UserRepository.verify` for credential check; uses `UserRepository.getUserId` to embed the user's numeric ID in the JWT identity claim.

---

## 9. services/dbHandler.py — Database Handler API

All protected endpoints require a valid JWT (`Authorization: Bearer <token>`).

### `POST /user`
- **Purpose:** Create a new user account.
- **Auth required:** No.
- **Request body:** `{ "username": "<str>", "password": "<str>" }`
- **Responses:**
  | Status | Condition | Body |
  |--------|-----------|------|
  | 200 | Always (unless 400) | `{ "status": true/false }` |
  | 400 | Missing body | `{ "error": "bad request" }` |

### `DELETE /user`
- **Auth required:** Yes.
- **Purpose:** Delete the authenticated user's own account.
- **Request body:** `{ "username": "<str>" }` — must match the authenticated user's own username.
- **Responses:**
  | Status | Condition | Body |
  |--------|-----------|------|
  | 200 | Deleted | `{ "status": true }` |
  | 400 | Missing body or `username` field | `{ "error": "bad request" }` |
  | 401 | No JWT | — |
  | 403 | `username` does not match the JWT's identity | `{ "error": "forbidden" }` |

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

## 10. services/servers.py — Server Management API

### `GET /servers`
- **Auth required:** No.
- **Purpose:** List all installed servers.
- **Response:** `200 { "servers": [{ "server_id", "id", "isRunning", "max_memory_mb", "online_players" }, ...] }`.

### `GET /servers/<serverName>`
- **Auth required:** Optional JWT.
- **Purpose:** Return live or cached info about a specific server.
- **Responses:**
  | Status | Condition | Body |
  |--------|-----------|------|
  | 200 | Found | `{ "name", "is_running", "pid", "uptime_seconds", "max_memory_mb", "online_players" }` |
  | 403 | JWT present and user lacks `GetServerInfo` permission | — |
  | 404 | Server name not found | — |
- **Extras:** If the server has a running `ServerSession`, values come from `serverInstance.get_process_info()`; otherwise defaults are used.

### `POST /servers/<serverName>/start`
- **Auth required:** No (TODO: should require StartServer perm).
- **Responses:** `200 { "message": "..." }` | `400` if server is already running (`ValueError`).

### `POST /servers/<serverName>/stop`
- **Auth required:** No (TODO: should require StopServer perm).
- **Responses:** `200 { "message": "..." }` | `400` if no instance exists (`ValueError`).

### `GET /servers/<serverName>/stats`
- **Auth required:** No.
- **Responses:**
  | Status | Condition |
  |--------|-----------|
  | 200 | Server is running; stats returned |
  | 404 | Server not found or not running |
  | 500 | Internal error collecting stats |

### `POST /manage/addServer`
- **Auth required:** Yes.
- **Request body:** `{ "serverName", "serverSoftware", "serverVersion", "acceptEula" (optional, default false) }`
- **Responses:**
  | Status | Condition | Body |
  |--------|-----------|------|
  | 200 | Success | `{ "status": true, "message": "..." }` |
  | 200 | EULA not accepted | `{ "status": true, "message": "<eula warning>" }` |
  | 400 | Missing required params | — |
  | 400 | Install error | — |
  | 500 | DB registration failed | — |

### `DELETE /servers/<serverName>/uninstall`
- **Auth required:** Yes.
- **Responses:** `200 { "status": true, "message": "..." }` | `400` on install error | `404` on DB removal failure.
- **Extras:** Only the server owner (or a user with `RemovePermissionFromServer`) can uninstall.

### `GET /manage/<software>/getAvailableVersions`
- **Auth required:** No.
- **Response:** `200 { "versions": ["latest", ...] }` | `400 { "message": "<error>" }`.

### `GET /servers/globalStats`
- **Auth required:** No.
- **Response:** `200` — aggregated stats dict (see `getGlobalStats`).
- **Extras:** Returns `500` on unexpected exception.
