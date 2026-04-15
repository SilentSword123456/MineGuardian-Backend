# Server Session Manager

> **Source:** `serverSessionsManager.py`

---

## Module-Level Globals

- `serverInstances: dict[str, ServerSession]` — maps server name → live `ServerSession` object.
- `usedPorts: set[int]` — all ports currently assigned to running instances.

---

## ServerSession

### `__init__(name, command, working_dir=None)`

- **Purpose:** Initialise a server session and reserve TCP ports.
- **Inputs:** `name` (str); `command` (str or list); `working_dir` (str, path to the server folder).
- **Behaviour:**
  - If `command` is a `str`, splits it into a list via `str.split()`.
  - Calls `getNewPort` and `assignNewPort` to reserve a server port (`self.port`) and an RCON port (`self.rcon_port`).
  - Initial state: `_running = False`, `process = None`, `listeners = []`, `status_listeners = []`, `log_history = []`, `max_history = 100`.

### `running` (property, getter)

- Returns the live running state by checking `is_running()`.
- If the live state differs from `_running`, sets `running = live` (triggering the setter).

### `running` (property, setter)

- **Behaviour:** If the new value differs from `_running`, updates `_running` and calls `_broadcast_status(value)`.
- Does **not** broadcast if the value is unchanged.

---

## Listener Management

### `add_listener(callback)`

- Registers `callback` for log line events (called by `_broadcast`).
- Does **not** add duplicates (idempotent).

### `remove_listener(callback)`

- Deregisters `callback`; no-op if not registered.

### `add_status_listener(callback)`

- Registers `callback` for server running-state events (called by `_broadcast_status`).
- Does **not** add duplicates (idempotent).

### `_broadcast_status(is_running: bool)`

- Calls each registered status listener with the new boolean state.
- Exceptions raised by listeners are caught and printed; they do **not** propagate.

### `_broadcast(line: str)`

- Calls `_updateHistory(line)`, then calls each registered log listener with the line.
- Exceptions raised by listeners are caught and printed; they do **not** propagate.

### `_updateHistory(line: str)`

- Appends `line` to `log_history`.
- If `len(log_history) > max_history`, drops the oldest entry (index 0).

---

## Lifecycle

### `start() -> bool`

- **Purpose:** Launch the Minecraft server process.
- **Output:** `True` on success; `False` if already running or on start error.
- **Behaviour:**
  - Does nothing (prints message, returns `False`) if already running.
  - Launches `self.command` as a subprocess with stdin/stdout pipes.
  - Sets `running = True`, spawns `_read_output` and `_monitor_process_exit` green threads.

### `stop(timeout=30) -> bool`

- **Purpose:** Gracefully stop the server; force-kill if it does not stop within `timeout` seconds.
- **Output:** `True` after stopping; `False` if not currently running.
- **Behaviour:**
  - Sends `"stop"` via `send_command`, then polls every second up to `timeout`.
  - If still alive after timeout, calls `process.terminate()`, waits 2 s, then `process.kill()`.
  - Always sets `running = False` and calls `cleanup()` before returning.

### `is_running() -> bool`

- **Output:** `True` if `process` is set **and** `process.poll()` returns `None`; `False` otherwise.

---

## Commands

### `send_command(command: str) -> bool`

- **Purpose:** Write a command to the server's stdin.
- **Output:** `True` on success; `False` if:
  - Server is not running.
  - `command.strip()` is empty/blank.
  - An exception occurs writing to stdin.

### `send_rcon_command(command: str) -> str | None`

- **Purpose:** Send a command via the persistent RCON connection (lazy connect / auto-reconnect).
- **Output:** The RCON response string; `None` if RCON is unavailable or fails after one reconnect attempt.

---

## Diagnostics

### `get_process_info() -> dict`

- **Purpose:** Return a snapshot of the server's current state.
- **Output:** Dict with keys:
  - `server_id` (str) — the server name.
  - `is_running` (bool).
  - `pid` (int) — `0` when not running.
  - `uptime_seconds` (float) — `0.0` when not running.
  - `max_memory_mb` (int).
  - `max_players` (int).

### `get_memory_usage_mb() -> float`

- **Output:** Resident memory of the server process + all children in MB (rounded to 2 dp); `0.0` if process is not running or access is denied.

### `get_cpu_usage_percent() -> float`

- **Output:** CPU usage % of the process + all children, normalised by CPU count; `0.0` if process is not running or access is denied.

---

## Cleanup

### `cleanup()`

- **Purpose:** Release resources held by this session.
- **Behaviour:**
  - If an RCON connection is open, disconnects it and sets `_rcon = None`.
  - Removes `self.port` and `self.rcon_port` from `serverSessionsManager.usedPorts`.
  - Safe to call when no RCON connection is open.

---

[← Back to Home](Home.md)
