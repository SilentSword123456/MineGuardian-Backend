"""
Tests for rcon.py — RconClient and supporting error types.

Socket I/O is fully mocked so no real network connections are made.
"""

import struct
import socket
import unittest
from unittest.mock import MagicMock, patch, call

from rcon import RconClient, RconAuthError, RconError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_packet(req_id: int, pkt_type: int, payload: str) -> bytes:
    """Build a minimal RCON packet (mirrors RconClient._send_packet logic)."""
    payload_bytes = payload.encode("utf-8")
    length = 4 + 4 + len(payload_bytes) + 2
    return struct.pack("<iii", length, req_id, pkt_type) + payload_bytes + b"\x00\x00"


def _build_length_and_body(req_id: int, pkt_type: int, payload: str) -> tuple[bytes, bytes]:
    """Return (length_bytes, body_bytes) as the socket would deliver them."""
    payload_bytes = payload.encode("utf-8")
    length = 4 + 4 + len(payload_bytes) + 2
    length_bytes = struct.pack("<i", length)
    body = struct.pack("<ii", req_id, pkt_type) + payload_bytes + b"\x00\x00"
    return length_bytes, body


def _make_recv_chunks(*packets: tuple[int, int, str]) -> list[bytes]:
    """
    Return a list of raw bytes chunks (as socket.recv would deliver) for the
    given (req_id, pkt_type, payload) tuples.  Each packet contributes two
    entries: the 4-byte length prefix, then the body.
    """
    chunks: list[bytes] = []
    for req_id, pkt_type, payload in packets:
        length_bytes, body = _build_length_and_body(req_id, pkt_type, payload)
        chunks.append(length_bytes)
        chunks.append(body)
    return chunks


# ---------------------------------------------------------------------------
# _next_id
# ---------------------------------------------------------------------------

class NextIdTests(unittest.TestCase):
    def test_starts_at_one(self):
        client = RconClient.__new__(RconClient)
        client._req_id = 0
        self.assertEqual(client._next_id(), 1)

    def test_increments_sequentially(self):
        client = RconClient.__new__(RconClient)
        client._req_id = 0
        ids = [client._next_id() for _ in range(5)]
        self.assertEqual(ids, [1, 2, 3, 4, 5])

    def test_wraps_at_2_to_the_30(self):
        client = RconClient.__new__(RconClient)
        client._req_id = 2 ** 30  # already at the max
        self.assertEqual(client._next_id(), 1)

    def test_stays_positive_after_wrap(self):
        client = RconClient.__new__(RconClient)
        client._req_id = 2 ** 30 - 1
        first = client._next_id()   # 2**30
        second = client._next_id()  # wraps → 1
        self.assertEqual(first, 2 ** 30)
        self.assertEqual(second, 1)


# ---------------------------------------------------------------------------
# _send_packet
# ---------------------------------------------------------------------------

class SendPacketTests(unittest.TestCase):
    def setUp(self):
        self.client = RconClient.__new__(RconClient)
        self.mock_sock = MagicMock()
        self.client._sock = self.mock_sock

    def test_send_packet_encodes_correct_wire_format(self):
        self.client._send_packet(1, 3, "password")
        expected = _build_packet(1, 3, "password")
        self.mock_sock.sendall.assert_called_once_with(expected)

    def test_send_packet_with_empty_payload(self):
        self.client._send_packet(7, 2, "")
        expected = _build_packet(7, 2, "")
        self.mock_sock.sendall.assert_called_once_with(expected)

    def test_send_packet_with_utf8_payload(self):
        self.client._send_packet(2, 2, "say héllo")
        expected = _build_packet(2, 2, "say héllo")
        self.mock_sock.sendall.assert_called_once_with(expected)

    def test_length_field_is_correct(self):
        payload = "list"
        payload_bytes = payload.encode("utf-8")
        expected_length = 4 + 4 + len(payload_bytes) + 2
        self.client._send_packet(1, 2, payload)
        raw = self.mock_sock.sendall.call_args[0][0]
        (actual_length,) = struct.unpack("<i", raw[:4])
        self.assertEqual(actual_length, expected_length)


# ---------------------------------------------------------------------------
# _recv_packet / _recv_exactly
# ---------------------------------------------------------------------------

class RecvPacketTests(unittest.TestCase):
    def _make_client_with_recv(self, *packets):
        client = RconClient.__new__(RconClient)
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = _make_recv_chunks(*packets)
        client._sock = mock_sock
        return client

    def test_recv_packet_parses_single_packet(self):
        client = self._make_client_with_recv((42, 2, "hello"))
        req_id, pkt_type, payload = client._recv_packet()
        self.assertEqual(req_id, 42)
        self.assertEqual(pkt_type, 2)
        self.assertEqual(payload, "hello")

    def test_recv_packet_parses_empty_payload(self):
        client = self._make_client_with_recv((1, 0, ""))
        req_id, pkt_type, payload = client._recv_packet()
        self.assertEqual(req_id, 1)
        self.assertEqual(pkt_type, 0)
        self.assertEqual(payload, "")

    def test_recv_packet_raises_on_too_short_length(self):
        """length < 10 should raise RconError."""
        client = RconClient.__new__(RconClient)
        mock_sock = MagicMock()
        # Deliver a length of 5 (below minimum of 10)
        mock_sock.recv.side_effect = [struct.pack("<i", 5), b""]
        client._sock = mock_sock
        with self.assertRaises(RconError):
            client._recv_packet()

    def test_recv_packet_raises_on_oversized_length(self):
        """length > 4096 should raise RconError."""
        client = RconClient.__new__(RconClient)
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = [struct.pack("<i", 5000), b""]
        client._sock = mock_sock
        with self.assertRaises(RconError):
            client._recv_packet()

    def test_recv_exactly_raises_rcon_error_on_connection_closed(self):
        """recv returning empty bytes should raise RconError."""
        client = RconClient.__new__(RconClient)
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b""
        client._sock = mock_sock
        with self.assertRaises(RconError, msg="Connection closed by server while reading packet."):
            client._recv_exactly(4)

    def test_recv_exactly_raises_on_timeout(self):
        """socket.timeout during recv should be wrapped as RconError."""
        client = RconClient.__new__(RconClient)
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = socket.timeout
        client._sock = mock_sock
        with self.assertRaises(RconError):
            client._recv_exactly(4)

    def test_recv_exactly_raises_on_oserror(self):
        """Generic OSError during recv should be wrapped as RconError."""
        client = RconClient.__new__(RconClient)
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = OSError("broken pipe")
        client._sock = mock_sock
        with self.assertRaises(RconError):
            client._recv_exactly(4)

    def test_recv_exactly_reassembles_fragmented_chunks(self):
        """recv returning partial data should keep reading until buffer is full."""
        client = RconClient.__new__(RconClient)
        mock_sock = MagicMock()
        # Deliver 4 bytes across 4 one-byte chunks
        mock_sock.recv.side_effect = [b"\x01", b"\x02", b"\x03", b"\x04"]
        client._sock = mock_sock
        result = client._recv_exactly(4)
        self.assertEqual(result, b"\x01\x02\x03\x04")


# ---------------------------------------------------------------------------
# connect
# ---------------------------------------------------------------------------

class ConnectTests(unittest.TestCase):
    def _mock_connect(self, client, auth_response_id, auth_response_type=2):
        """Patch socket.socket so connect() uses our mock."""
        mock_sock = MagicMock()
        length_bytes, body = _build_length_and_body(auth_response_id, auth_response_type, "")
        mock_sock.recv.side_effect = [length_bytes, body]
        return mock_sock

    @patch("rcon.socket.socket")
    def test_connect_succeeds_when_server_echoes_request_id(self, MockSocket):
        client = RconClient("127.0.0.1", 25575, "secret")
        mock_sock = MagicMock()
        MockSocket.return_value = mock_sock

        # The auth response should echo back the first req_id (which will be 1).
        mock_sock.recv.side_effect = _make_recv_chunks((1, 2, ""))

        client.connect()  # Should not raise
        self.assertIsNotNone(client._sock)

    @patch("rcon.socket.socket")
    def test_connect_raises_rcon_auth_error_on_failure_id(self, MockSocket):
        client = RconClient("127.0.0.1", 25575, "wrong")
        mock_sock = MagicMock()
        MockSocket.return_value = mock_sock

        # Server returns AUTH_FAILURE_ID (-1)
        mock_sock.recv.side_effect = _make_recv_chunks((-1, 2, ""))

        with self.assertRaises(RconAuthError):
            client.connect()

    @patch("rcon.socket.socket")
    def test_connect_raises_rcon_error_when_socket_connect_fails(self, MockSocket):
        client = RconClient("127.0.0.1", 25575, "pass")
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = OSError("Connection refused")
        MockSocket.return_value = mock_sock

        with self.assertRaises(RconError):
            client.connect()
        # Socket should be cleaned up
        self.assertIsNone(client._sock)

    @patch("rcon.socket.socket")
    def test_connect_raises_rcon_error_on_unexpected_response_id(self, MockSocket):
        client = RconClient("127.0.0.1", 25575, "pass")
        mock_sock = MagicMock()
        MockSocket.return_value = mock_sock

        # Return a completely different ID
        mock_sock.recv.side_effect = _make_recv_chunks((999, 2, ""))

        with self.assertRaises(RconError):
            client.connect()


# ---------------------------------------------------------------------------
# disconnect
# ---------------------------------------------------------------------------

class DisconnectTests(unittest.TestCase):
    def test_disconnect_closes_socket_and_clears_reference(self):
        client = RconClient.__new__(RconClient)
        mock_sock = MagicMock()
        client._sock = mock_sock

        client.disconnect()

        mock_sock.close.assert_called_once()
        self.assertIsNone(client._sock)

    def test_disconnect_when_not_connected_is_a_noop(self):
        client = RconClient.__new__(RconClient)
        client._sock = None
        client.disconnect()  # Should not raise

    def test_disconnect_swallows_oserror_on_close(self):
        client = RconClient.__new__(RconClient)
        mock_sock = MagicMock()
        mock_sock.close.side_effect = OSError("already closed")
        client._sock = mock_sock

        client.disconnect()  # Should not raise
        self.assertIsNone(client._sock)


# ---------------------------------------------------------------------------
# send_command
# ---------------------------------------------------------------------------

class SendCommandTests(unittest.TestCase):
    def _make_connected_client(self, *response_packets):
        """Return a client with a mock socket that feeds the given response packets."""
        client = RconClient.__new__(RconClient)
        client._req_id = 0
        client.timeout = 5.0
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = _make_recv_chunks(*response_packets) + [socket.timeout()]
        client._sock = mock_sock
        return client, mock_sock

    def test_send_command_raises_when_not_connected(self):
        client = RconClient.__new__(RconClient)
        client._req_id = 0
        client._sock = None
        with self.assertRaises(RconError):
            client.send_command("list")

    def test_send_command_returns_response_payload(self):
        # First _next_id() will return 1 → that's the cmd_id
        client, mock_sock = self._make_connected_client((1, 0, "players: Steve"))
        mock_sock.settimeout = MagicMock()

        result = client.send_command("list")
        self.assertEqual(result, "players: Steve")

    def test_send_command_reassembles_multi_fragment_response(self):
        client = RconClient.__new__(RconClient)
        client._req_id = 0
        client.timeout = 5.0
        mock_sock = MagicMock()
        client._sock = mock_sock

        # First response packet (main), then a fragment, then timeout
        mock_sock.recv.side_effect = (
            _make_recv_chunks((1, 0, "hello "), (1, 0, "world"))
            + [socket.timeout()]
        )
        mock_sock.settimeout = MagicMock()

        result = client.send_command("list")
        self.assertEqual(result, "hello world")

    def test_send_command_raises_rcon_auth_error_on_session_invalid(self):
        """AUTH_FAILURE_ID in a command response should raise RconAuthError."""
        client, mock_sock = self._make_connected_client((-1, 0, ""))
        mock_sock.settimeout = MagicMock()

        with self.assertRaises(RconAuthError):
            client.send_command("list")

    def test_send_command_raises_rcon_error_when_no_matching_packet_received(self):
        """If no packet with the matching cmd_id arrives within max_packets, raise."""
        client = RconClient.__new__(RconClient)
        client._req_id = 0
        client.timeout = 5.0
        mock_sock = MagicMock()
        client._sock = mock_sock

        # Return 100 packets all with wrong req_id (999)
        mock_sock.recv.side_effect = _make_recv_chunks(*[(999, 0, "")] * 100)
        mock_sock.settimeout = MagicMock()

        with self.assertRaises(RconError):
            client.send_command("list")

    def test_send_command_skips_stray_packets_before_matching(self):
        """Stray packets (wrong req_id) should be skipped."""
        client = RconClient.__new__(RconClient)
        client._req_id = 0
        client.timeout = 5.0
        mock_sock = MagicMock()
        client._sock = mock_sock

        # Stray packet with req_id=99, then correct packet with req_id=1
        mock_sock.recv.side_effect = (
            _make_recv_chunks((99, 0, "stray"), (1, 0, "correct"))
            + [socket.timeout()]
        )
        mock_sock.settimeout = MagicMock()

        result = client.send_command("list")
        self.assertEqual(result, "correct")


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class ContextManagerTests(unittest.TestCase):
    @patch.object(RconClient, "connect")
    @patch.object(RconClient, "disconnect")
    def test_context_manager_calls_connect_and_disconnect(self, mock_disconnect, mock_connect):
        client = RconClient("127.0.0.1", 25575, "pass")
        with client as ctx:
            self.assertIs(ctx, client)
            mock_connect.assert_called_once()
        mock_disconnect.assert_called_once()

    @patch.object(RconClient, "connect")
    @patch.object(RconClient, "disconnect")
    def test_context_manager_calls_disconnect_on_exception(self, mock_disconnect, mock_connect):
        client = RconClient("127.0.0.1", 25575, "pass")
        with self.assertRaises(ValueError):
            with client:
                raise ValueError("test error")
        mock_disconnect.assert_called_once()

    @patch.object(RconClient, "connect", side_effect=RconError("fail"))
    @patch.object(RconClient, "disconnect")
    def test_context_manager_propagates_connect_error(self, mock_disconnect, mock_connect):
        client = RconClient("127.0.0.1", 25575, "pass")
        with self.assertRaises(RconError):
            with client:
                pass


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------

class RconErrorTypesTests(unittest.TestCase):
    def test_rcon_auth_error_is_exception(self):
        err = RconAuthError("bad password")
        self.assertIsInstance(err, Exception)
        self.assertEqual(str(err), "bad password")

    def test_rcon_error_is_exception(self):
        err = RconError("socket closed")
        self.assertIsInstance(err, Exception)
        self.assertEqual(str(err), "socket closed")

    def test_rcon_auth_error_is_not_rcon_error(self):
        """The two error classes are independent."""
        self.assertNotIsInstance(RconAuthError("x"), RconError)
        self.assertNotIsInstance(RconError("x"), RconAuthError)


if __name__ == "__main__":
    unittest.main()
