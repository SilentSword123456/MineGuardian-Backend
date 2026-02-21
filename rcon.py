import socket
import struct


# Packet types (per minecraft.wiki/w/RCON)
_TYPE_LOGIN      = 3
_TYPE_COMMAND    = 2
_TYPE_RESPONSE   = 0
# Sentinel type: invalid packet type 0xC8 = 200. The server echoes it back
# as a Type-0 "Unknown request c8" response, marking the end of a
# potentially fragmented multi-packet reply.
# Reference: https://minecraft.wiki/w/RCON#Fragmented_response_packets
_TYPE_TERMINATOR = 200  # 0xC8

_AUTH_FAILURE_ID = -1


class RconAuthError(Exception):
    """Raised when RCON authentication fails (wrong password)."""
    pass


class RconError(Exception):
    """Raised for general RCON communication errors."""
    pass


class RconClient:
    """
    Minimal RCON client implementing the Minecraft RCON protocol.
    Reference: https://minecraft.wiki/w/RCON

    Packet layout (little-endian):
        [Length: int32][Request ID: int32][Type: int32][Payload: UTF-8 null-terminated][Pad: 0x00]

    Fragmented responses are handled by sending a sentinel packet (type 200 / 0xC8)
    immediately after every command packet. The server echoes it back as a Type-0
    packet with payload "Unknown request c8". All Type-0 packets received before
    that sentinel reply are fragments of the real response and are concatenated.

    Usage:
        with RconClient("127.0.0.1", 25575, "password") as rcon:
            response = rcon.send_command("list")
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 25575, password: str = "", timeout: float = 5.0):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._req_id = 0

    # ------------------------------------------------------------------ #
    #  Context manager support                                             #
    # ------------------------------------------------------------------ #

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False  # Do not suppress exceptions

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def connect(self):
        """Open a TCP connection to the RCON server and authenticate."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        try:
            self._sock.connect((self.host, self.port))
        except OSError as e:
            self._sock = None
            raise RconError(f"Could not connect to RCON at {self.host}:{self.port} — {e}") from e

        # Send login packet (type 3) with the password as payload
        req_id = self._next_id()
        self._send_packet(req_id, _TYPE_LOGIN, self.password)

        resp_id, resp_type, _ = self._recv_packet()

        if resp_id == _AUTH_FAILURE_ID:
            self.disconnect()
            raise RconAuthError("RCON authentication failed: wrong password.")

        if resp_id != req_id:
            self.disconnect()
            raise RconError(f"Unexpected response ID during login: expected {req_id}, got {resp_id}.")

    def send_command(self, command: str) -> str:
        """
        Send a command and return the full response, handling fragmented replies.

        After the command packet (Type 2), a sentinel packet with invalid type
        200 (0xC8) is sent immediately. The server echoes it back as a Type-0
        packet with payload "Unknown request c8". All Type-0 packets arriving
        before that sentinel reply are fragments of the real response and are
        concatenated in order.
        """
        if self._sock is None:
            raise RconError("Not connected. Call connect() first.")

        cmd_id = self._next_id()
        self._send_packet(cmd_id, _TYPE_COMMAND, command)

        # Send the sentinel immediately so we know when the response ends.
        sentinel_id = self._next_id()
        self._send_packet(sentinel_id, _TYPE_TERMINATOR, "")

        # Collect all response fragments until the sentinel reply arrives.
        fragments = []
        while True:
            resp_id, resp_type, payload = self._recv_packet()

            if resp_id == _AUTH_FAILURE_ID:
                raise RconAuthError("RCON session is no longer authenticated.")

            # The sentinel reply — server echoes a Type-0 packet with the sentinel's ID.
            if resp_id == sentinel_id:
                break

            # Any Type-0 packet matching the command's request ID is a response fragment.
            if resp_id == cmd_id and resp_type == _TYPE_RESPONSE:
                fragments.append(payload)

        return "".join(fragments)

    def disconnect(self):
        """Close the TCP connection."""
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            finally:
                self._sock = None

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _next_id(self) -> int:
        """Return the next request ID (1-based, wraps at 2^30 to stay positive)."""
        self._req_id = (self._req_id % (2 ** 30)) + 1
        return self._req_id

    def _send_packet(self, req_id: int, pkt_type: int, payload: str):
        """
        Encode and send one RCON packet.

        Wire format:
            Length (4 bytes LE)  = 4 (id) + 4 (type) + len(payload_bytes) + 2 (two null bytes)
            Request ID (4 bytes LE)
            Type (4 bytes LE)
            Payload (UTF-8 bytes)
            Null terminator (1 byte)
            Padding null (1 byte)
        """
        payload_bytes = payload.encode("utf-8")
        # Length field covers: req_id (4) + type (4) + payload + 2 null bytes
        length = 4 + 4 + len(payload_bytes) + 2
        packet = struct.pack("<iii", length, req_id, pkt_type) + payload_bytes + b"\x00\x00"
        self._sock.sendall(packet)

    def _recv_packet(self) -> tuple[int, int, str]:
        """
        Read one RCON response packet.
        Returns (request_id, type, payload_string).
        """
        # Read the 4-byte length prefix first
        raw_length = self._recv_exactly(4)
        (length,) = struct.unpack("<i", raw_length)

        if length < 10:  # Minimum valid packet body: 4+4+1+1 = 10 bytes
            raise RconError(f"Received malformed RCON packet (length={length}).")

        body = self._recv_exactly(length)

        req_id, pkt_type = struct.unpack("<ii", body[:8])
        # Payload is everything between the two fixed header ints and the two trailing null bytes
        payload = body[8:-2].decode("utf-8", errors="replace")

        return req_id, pkt_type, payload

    def _recv_exactly(self, num_bytes: int) -> bytes:
        """Read exactly num_bytes from the socket, blocking until available."""
        buf = b""
        while len(buf) < num_bytes:
            chunk = self._sock.recv(num_bytes - len(buf))
            if not chunk:
                raise RconError("Connection closed by server while reading packet.")
            buf += chunk
        return buf

