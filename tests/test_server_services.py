"""
Tests for services/server_services.py — get_all_servers, get_server_instance, stop_server.
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# Stub out the `api` module before importing server_services, as servers.py
# (which server_services imports indirectly) also imports `api`.
api_stub = types.ModuleType("api")
api_stub.register_socketio_listener = lambda *a, **kw: None
api_stub.socketio = types.SimpleNamespace(emit=lambda *a, **kw: None)
if "api" not in sys.modules:
    sys.modules["api"] = api_stub

from services.server_services import get_all_servers, get_server_instance, stop_server


class GetAllServersTests(unittest.TestCase):
    def test_returns_list_of_server_dicts(self):
        server_names = ["alpha", "beta"]
        with patch("services.server_services.os.listdir", return_value=server_names), \
             patch("services.server_services.os.path.join", side_effect=lambda *a: "/".join(a)), \
             patch("services.server_services.serverSessionsManager.serverInstances", {}), \
             patch("services.server_services.utils.getMaxMemoryMB", return_value=1024), \
             patch("services.server_services.utils.getMaxPlayers", return_value=20):
            servers = get_all_servers()

        self.assertEqual(len(servers), 2)
        names = [s["server_id"] for s in servers]
        self.assertIn("alpha", names)
        self.assertIn("beta", names)

    def test_marks_server_as_running_when_instance_is_running(self):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        with patch("services.server_services.os.listdir", return_value=["running-server"]), \
             patch("services.server_services.os.path.join", side_effect=lambda *a: "/".join(a)), \
             patch("services.server_services.serverSessionsManager.serverInstances", {"running-server": mock_instance}), \
             patch("services.server_services.utils.getMaxMemoryMB", return_value=2048), \
             patch("services.server_services.utils.getMaxPlayers", return_value=20):
            servers = get_all_servers()

        self.assertEqual(len(servers), 1)
        self.assertTrue(servers[0]["isRunning"])

    def test_marks_server_as_not_running_when_no_instance(self):
        with patch("services.server_services.os.listdir", return_value=["stopped-server"]), \
             patch("services.server_services.os.path.join", side_effect=lambda *a: "/".join(a)), \
             patch("services.server_services.serverSessionsManager.serverInstances", {}), \
             patch("services.server_services.utils.getMaxMemoryMB", return_value=1024), \
             patch("services.server_services.utils.getMaxPlayers", return_value=20):
            servers = get_all_servers()

        self.assertFalse(servers[0]["isRunning"])

    def test_includes_max_memory_and_online_players(self):
        with patch("services.server_services.os.listdir", return_value=["myserver"]), \
             patch("services.server_services.os.path.join", side_effect=lambda *a: "/".join(a)), \
             patch("services.server_services.serverSessionsManager.serverInstances", {}), \
             patch("services.server_services.utils.getMaxMemoryMB", return_value=4096), \
             patch("services.server_services.utils.getMaxPlayers", return_value=30):
            servers = get_all_servers()

        self.assertEqual(servers[0]["max_memory_mb"], 4096)
        self.assertEqual(servers[0]["online_players"]["max"], 30)


class GetServerInstanceTests(unittest.TestCase):
    def test_raises_value_error_when_server_already_running(self):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        with patch("services.server_services.serverSessionsManager.serverInstances", {"my-server": mock_instance}):
            with self.assertRaises(ValueError) as ctx:
                get_server_instance("my-server")
        self.assertIn("already running", str(ctx.exception))

    def test_returns_existing_instance_when_not_running(self):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        with patch("services.server_services.serverSessionsManager.serverInstances", {"my-server": mock_instance}):
            result = get_server_instance("my-server")
        self.assertIs(result, mock_instance)

    def test_creates_new_instance_when_server_not_in_instances(self):
        mock_new_instance = MagicMock()
        with patch("services.server_services.serverSessionsManager.serverInstances", {}), \
             patch("services.server_services.utils.setupServerInstance", return_value=mock_new_instance) as mock_setup, \
             patch("services.server_services.os.path.join", return_value="/fake/servers/new-server"):
            result = get_server_instance("new-server")

        self.assertIs(result, mock_new_instance)
        mock_setup.assert_called_once()


class StopServerTests(unittest.TestCase):
    def test_raises_value_error_when_no_instance(self):
        with patch("services.server_services.serverSessionsManager.serverInstances", {}):
            with self.assertRaises(ValueError) as ctx:
                stop_server("ghost-server")
        self.assertIn("ghost-server", str(ctx.exception))

    def test_calls_stop_on_server_instance(self):
        mock_instance = MagicMock()
        with patch("services.server_services.serverSessionsManager.serverInstances", {"running-server": mock_instance}):
            stop_server("running-server")
        mock_instance.stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
