"""Tests for services/server_services.py ID-based helpers."""

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

from services.server_services import getAllServers, get_server_instance, stop_server


class GetAllServersTests(unittest.TestCase):
    def test_returns_server_ids_with_view_permission(self):
        with patch("services.server_services.ServersUsersPermsRepository.getServersWithUserPerm", return_value=[11, 13]) as get_servers:
            servers = getAllServers(7)

        self.assertEqual(servers, [11, 13])
        get_servers.assert_called_once()

    def test_returns_empty_when_user_has_no_visible_servers(self):
        with patch("services.server_services.ServersUsersPermsRepository.getServersWithUserPerm", return_value=[]):
            self.assertEqual(getAllServers(77), [])


class GetServerInstanceTests(unittest.TestCase):
    def test_raises_value_error_when_server_already_running(self):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        with patch("services.server_services.ServersRepository.getServerName", return_value="my-server"), \
             patch("services.server_services.serverSessionsManager.serverInstances", {"my-server": mock_instance}):
            with self.assertRaises(ValueError) as ctx:
                get_server_instance(5)
        self.assertIn("already running", str(ctx.exception))

    def test_returns_existing_instance_when_not_running(self):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        with patch("services.server_services.ServersRepository.getServerName", return_value="my-server"), \
             patch("services.server_services.serverSessionsManager.serverInstances", {"my-server": mock_instance}):
            result = get_server_instance(5)
        self.assertIs(result, mock_instance)

    def test_creates_new_instance_when_server_not_in_instances(self):
        mock_new_instance = MagicMock()
        with patch("services.server_services.serverSessionsManager.serverInstances", {}), \
             patch("services.server_services.ServersRepository.getServerName", return_value="new-server"), \
             patch("services.server_services.utils.setupServerInstance", return_value=mock_new_instance) as mock_setup, \
             patch("services.server_services.os.path.join", return_value="/fake/servers/new-server"):
            result = get_server_instance(99)

        self.assertIs(result, mock_new_instance)
        mock_setup.assert_called_once_with("/fake/servers/new-server", "new-server", 99)


class StopServerTests(unittest.TestCase):
    def test_raises_value_error_when_no_instance(self):
        with patch("services.server_services.ServersRepository.getServerName", return_value="ghost-server"), \
             patch("services.server_services.serverSessionsManager.serverInstances", {}):
            with self.assertRaises(ValueError) as ctx:
                stop_server(777)
        self.assertIn("ghost-server", str(ctx.exception))

    def test_calls_stop_on_server_instance(self):
        mock_instance = MagicMock()
        with patch("services.server_services.ServersRepository.getServerName", return_value="running-server"), \
             patch("services.server_services.serverSessionsManager.serverInstances", {"running-server": mock_instance}):
            stop_server(41)
        mock_instance.stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
