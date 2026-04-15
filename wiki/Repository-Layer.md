# Repository Layer

> **Source:** `Database/repositories.py`

All repository methods operate against a SQLAlchemy session obtained from `db`. They are pure database operations with no side effects outside the database.

---

## Table of Contents

- [UserRepository](#userrepository)
- [FavoriteServersRepository](#favoriteserversrepository)
- [PlayerRepository](#playerrepository)
- [PlayersPrivilegesRepository](#playersprivilegesrepository)
- [SettingsRepository](#settingsrepository)
- [ServersRepository](#serversrepository)
- [ServersUsersPermsRepository](#serversuserspermsrepository)

---

## UserRepository

### `createUser(username: str, password: str) -> bool`

- **Purpose:** Register a new user account.
- **Input:** `username` — the desired username (str); `password` — plaintext password (str).
- **Output:** `True` if the user was created; `False` if a user with the same username already exists.
- **Behaviour:**
  - Hashes `password` with SHA-256 before storing.
  - Rejects duplicate usernames (case-sensitive match).
  - Does **not** validate username/password length or character set (caller responsibility).

### `removeUser(username: str) -> bool`

- **Purpose:** Delete a user account by username.
- **Input:** `username` — exact username to delete (str).
- **Output:** `True` if the user existed and was deleted; `False` if no such user exists.

### `verify(username: str, password: str) -> bool`

- **Purpose:** Check username/password credentials.
- **Input:** `username` (str); `password` — plaintext password (str).
- **Output:** `True` if credentials are valid; `False` otherwise.
- **Behaviour:**
  - Hashes `password` with SHA-256 and compares against the stored hash.
  - Returns `False` if the username does not exist.

### `getUserId(username: str) -> int`

- **Purpose:** Look up the numeric primary-key ID for a username.
- **Input:** `username` (str).
- **Output:** The integer user ID if found; `0` if the username does not exist.

### `getUsername(userId: int) -> str`

- **Purpose:** Look up a username by numeric ID.
- **Input:** `userId` (int).
- **Output:** The username string if found; `''` (empty string) if the user does not exist.
- **Behaviour:** Calls `doseUserExist` first; returns `''` if the check fails.

### `doseUserExist(userId: int) -> bool`

*(note: typo is intentional — matches source)*

- **Purpose:** Check whether a user with the given numeric ID exists.
- **Input:** `userId` (int).
- **Output:** `True` if found; `False` otherwise.

---

## FavoriteServersRepository

### `addFavoriteServer(serverId: int, userId: int) -> bool`

- **Purpose:** Mark a server as a favourite for a user.
- **Input:** `serverId` (int) — the server's numeric ID; `userId` (int).
- **Output:** `True` if added; `False` if:
  - The user does not exist.
  - The server is already in the user's favourites list.

### `removeFavoriteServer(userId: int, serverId: int) -> bool`

- **Purpose:** Remove a server from a user's favourites.
- **Input:** `userId` (int); `serverId` (int).
- **Output:** `True` if the entry existed and was removed; `False` if:
  - The user does not exist.
  - The server was not in the user's favourites.

### `getFavoriteServers(userId: int) -> list[int]`

- **Purpose:** Return all favourite server IDs for a user.
- **Input:** `userId` (int).
- **Output:** A list of integer server IDs (may be empty).
- **Behaviour:** Returns `[]` if the user does not exist.

---

## PlayerRepository

### `createPlayer(userId: int, name: str, uuid: str) -> bool`

- **Purpose:** Register a Minecraft player under a user account.
- **Input:** `userId` (int); `name` (str) — in-game name; `uuid` (str) — Minecraft UUID.
- **Output:** `True` if created; `False` if the user does not exist.

### `removePlayer(userId: int, uuid: str) -> bool`

- **Purpose:** Delete a player record by UUID under a user account.
- **Input:** `userId` (int); `uuid` (str).
- **Output:** `True` if deleted; `False` if:
  - The user does not exist.
  - No player with that UUID exists under the user.

### `getAllPlayersUUIDs(userId: int) -> list[str]`

- **Purpose:** Return all Minecraft UUIDs registered to a user.
- **Input:** `userId` (int).
- **Output:** A list of UUID strings (may be empty).
- **Behaviour:** Returns `[]` if the user does not exist.

### `getPlayerId(userId: int, playerUUID: str) -> int`

- **Purpose:** Get the database primary key for a player.
- **Input:** `userId` (int); `playerUUID` (str).
- **Output:** The player's integer ID if found; `0` if:
  - The user does not exist.
  - No player with that UUID exists under the user.

---

## PlayersPrivilegesRepository

### `addPrivilege(userId: int, playerUUID: str, privilegeId: int) -> bool`

- **Purpose:** Assign a privilege to a player.
- **Input:** `userId` (int); `playerUUID` (str); `privilegeId` (int — must be a valid `PlayersPermissions` value).
- **Output:** `True` if added; `False` if:
  - `privilegeId` is not a valid `PlayersPermissions` value.
  - The user does not exist.
  - The player UUID does not exist under the user (i.e. `getPlayerId` returns `0`).
  - The player already had the privilege.

### `deletePrivilege(userId: int, playerUUID: str, privilegeId: int) -> bool`

- **Purpose:** Remove a privilege from a player.
- **Input:** `userId` (int); `playerUUID` (str); `privilegeId` (int).
- **Output:** `True` if one or more matching rows were deleted; `False` if:
  - The user does not exist.
  - The player UUID does not exist under the user.
  - No privilege row matching both `playerId` and `privilegeId` exists.

### `getPlayerPrivileges(userId: int, playerUUID: str) -> list[PlayersPrivileges]`

- **Purpose:** Return all privilege rows for a player.
- **Input:** `userId` (int); `playerUUID` (str).
- **Output:** A list of `PlayersPrivileges` ORM objects (may be empty).
- **Behaviour:** Returns `[]` if the player ID resolves to `0`.

---

## SettingsRepository

### `addSetting(userId: int, rule: int, approved: bool = False) -> bool`

- **Purpose:** Create a user setting.
- **Input:** `userId` (int); `rule` (int — must be a valid `SettingsPermissions` value); `approved` (bool, default `False`).
- **Output:** `True` if created; `False` if:
  - The user does not exist.
  - `rule` is not a valid `SettingsPermissions` value.
  - A setting with the same `(userId, rule)` pair already exists.

### `removeSetting(userId: int, rule: int) -> bool`

- **Purpose:** Delete a user setting.
- **Input:** `userId` (int); `rule` (int).
- **Output:** `True` if deleted; `False` if:
  - The user does not exist.
  - No matching setting row exists.

### `changeSetting(userId: int, rule: int, approved: bool = False) -> bool`

- **Purpose:** Update the `approved` flag of an existing setting.
- **Input:** `userId` (int); `rule` (int); `approved` (bool, default `False`).
- **Output:** `True` if updated; `False` if:
  - The user does not exist.
  - No matching setting row exists.

---

## ServersRepository

### `addServer(userId: int, serverName: str) -> bool`

- **Purpose:** Register a server in the database under a user.
- **Input:** `userId` (int) — the owner's ID; `serverName` (str).
- **Output:** `True` if created; `False` if the user does not exist or there is already a server with the same name.

### `removeServer(userId: int, serverName: str) -> bool`

- **Purpose:** Remove a server record.
- **Input:** `userId` (int); `serverName` (str).
- **Output:** `True` if deleted; `False` if:
  - The user does not exist.
  - No server with that name owned by the user exists.

### `changeServerName(userId: int, currentServerName: str, newServerName: str) -> bool`

- **Purpose:** Rename a server.
- **Input:** `userId` (int); `currentServerName` (str); `newServerName` (str).
- **Output:** `True` if renamed; `False` if:
  - The user does not exist.
  - No server with `currentServerName` owned by the user exists.
  - A server with `newServerName` already exists under the same user.

### `doseServerExist(serverId: int) -> bool`

- **Purpose:** Check whether a server with the given primary-key ID exists.
- **Input:** `serverId` (int).
- **Output:** `True` if found; `False` otherwise.

### `getServerOwner(serverId: int) -> int`

- **Purpose:** Return the owner's user ID for a server.
- **Input:** `serverId` (int).
- **Output:** The owner's user ID (int); `0` if the server does not exist.

### `getServerId(userId: int, serverName: str) -> int`

- **Purpose:** Look up a server's primary key given the owner ID and name.
- **Input:** `userId` (int); `serverName` (str).
- **Output:** The server's integer ID if found; `0` if:
  - The user does not exist.
  - No server with that name owned by the user exists.

---

## ServersUsersPermsRepository

### `addPerm(userId: int, serverId: int, targetUserId: int, permId: int) -> bool`

- **Purpose:** Grant a permission on a server to a target user.
- **Input:** `userId` (int) — the granting user; `serverId` (int); `targetUserId` (int) — the user receiving the permission; `permId` (int — must be a valid `ServersPermissions` value).
- **Output:** `True` if granted; `False` if:
  - Either `userId` or `targetUserId` does not exist.
  - The server does not exist.
  - `userId` is neither the server owner **nor** holds `AddPermissionToServer` on the server.
  - `permId` is not a valid `ServersPermissions` value.

### `removePerm(userId: int, serverId: int, targetUserId: int, permId: int) -> bool`

- **Purpose:** Revoke a permission on a server from a target user.
- **Input:** `userId` (int) — the revoking user; `serverId` (int); `targetUserId` (int); `permId` (int).
- **Output:** `True` if revoked; `False` if:
  - Either `userId` or `targetUserId` does not exist.
  - The server does not exist.
  - `userId` is neither the server owner **nor** holds `RemovePermissionFromServer`.
  - No matching permission row exists for the target user.

### `getPerms(userId: int, serverId: int) -> list[int]`

- **Purpose:** Return all permission IDs held by a user on a server.
- **Input:** `userId` (int); `serverId` (int).
- **Output:** A list of integer permission IDs (may be empty).
- **Behaviour:** Returns `[]` if the user or server does not exist.

### `doseUserHavePerm(userId: int, serverId: int, permId: int) -> bool`

- **Purpose:** Check whether a user holds a specific permission on a server.
- **Input:** `userId` (int); `serverId` (int); `permId` (int).
- **Output:** `True` if the user has the permission; `False` otherwise.
- **Behaviour:**
  - Returns `False` if the user does not exist.
  - Returns `False` if the server does not exist.
  - Returns `False` if `getPerms` returns an empty list.

---

[← Back to Home](Home.md)
