# RCON Client

> **Source:** `rcon.py`

Implements the [Minecraft RCON protocol](https://minecraft.wiki/w/RCON) over TCP.

---

## Error Classes

| Class           | Meaning |
|-----------------|---------|
| `RconAuthError` | Raised when RCON authentication fails (wrong password, or session invalidated). |
| `RconError`     | Raised for all other RCON communication failures (connection error, timeout, malformed packet, etc.). |

The two classes are **independent** — neither is a subclass of the other.

---

## RconClient

### `__init__(host, port, password, timeout=5.0)`

- **Purpose:** Create a client instance (does **not** connect).
- **Inputs:** `host` (str, default `"127.0.0.1"`); `port` (int, default `25575`); `password` (str, default `""`); `timeout` (float seconds, default `5.0`).
- **State after:** `_sock` is `None`; `_req_id` counter starts at `0`.

### `connect()`

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

### `disconnect()`

- **Purpose:** Close the TCP connection.
- **Behaviour:**
  - If `_sock` is not `None`, calls `_sock.close()` and sets `_sock = None`.
  - If `_sock` is already `None`, does nothing (no exception).
  - `OSError` raised by `close()` is silently swallowed.

### `send_command(command: str) -> str`

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

---

## Internal Methods

### `_next_id() -> int`

- **Purpose:** Produce the next sequential request ID.
- **Behaviour:**
  - Increments `_req_id` by 1.
  - Wraps back to `1` after reaching `2^30` (stays positive and fits in a signed 32-bit int).
  - Always returns a positive integer in the range `[1, 2^30]`.

### `_send_packet(req_id, pkt_type, payload)`

- **Purpose:** Encode and send one RCON packet on the wire.
- **Wire format (little-endian):**
  ```
  Length  (int32) = 4 + 4 + len(payload_bytes) + 2
  ReqID   (int32)
  Type    (int32)
  Payload (UTF-8 bytes)
  0x00 0x00  (two null bytes)
  ```

### `_recv_packet() -> (req_id: int, pkt_type: int, payload: str)`

- **Purpose:** Read and decode one RCON response packet from the socket.
- **Output:** A 3-tuple `(request_id, packet_type, payload_string)`.
- **Behaviour:**
  - Reads the 4-byte length prefix first.
  - Raises `RconError` if `length < 10` (too small to be valid).
  - Raises `RconError` if `length > 4096` (oversized / malicious).
  - Decodes payload bytes as UTF-8 with `errors="replace"`.

### `_recv_exactly(num_bytes: int) -> bytes`

- **Purpose:** Read exactly `num_bytes` from the socket, reassembling fragmented chunks.
- **Behaviour:**
  - Loops until `len(buf) == num_bytes`.
  - If `recv()` returns `b""` (connection closed) → raises `RconError`.
  - If `socket.timeout` is raised → raises `RconError`.
  - If `OSError` is raised → raises `RconError`.

---

## Context Manager

```python
with RconClient(...) as rcon:
    response = rcon.send_command("list")
```

- `__enter__` calls `connect()` and returns `self`.
- `__exit__` always calls `disconnect()`, even if the body raised.
- Does **not** suppress exceptions from the `with` body.

---

[← Back to Home](Home.md)
