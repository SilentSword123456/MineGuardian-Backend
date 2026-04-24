import sys
import types
import inspect
import unittest
from unittest.mock import patch

from flask import Flask

# `services.servers` imports `api` at import time, so provide a tiny stub first.
api_stub = types.ModuleType('api')
api_stub.register_socketio_listeners = lambda *args, **kwargs: None
api_stub.socketio = types.SimpleNamespace(emit=lambda *args, **kwargs: None)
if 'api' not in sys.modules:
    sys.modules['api'] = api_stub

import services.servers as servers_module


class ServersAPITestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)

    def _call_in_request_context(self, method, path, json_data=None):
        return self.app.test_request_context(path, method=method.upper(), json=json_data)


class AddServerTests(ServersAPITestCase):
    @patch('services.servers.manageLocalServers.installMinecraftServer')
    @patch('services.servers.Database.repositories.ServersRepository.addServer')
    @patch('services.servers.get_jwt_identity', return_value=7)
    def test_add_server_installs_and_registers(self, mock_identity, mock_add_server, mock_install):
        mock_install.return_value = {'status': 'ok'}
        mock_add_server.return_value = True

        with self._call_in_request_context(
            'post',
            '/manage/addServer',
            json_data={'serverName': 'demo', 'serverSoftware': 'vanilla', 'serverVersion': '1.20'},
        ):
            response = inspect.unwrap(servers_module.add_server)()

        self.assertEqual(response[1], 200)
        self.assertTrue(response[0]['status'])
        mock_install.assert_called_once_with('vanilla', '1.20', 'demo', False)
        mock_add_server.assert_called_once_with(7, 'demo')


class RemoveServerTests(ServersAPITestCase):
    @patch('services.servers.ServersRepository.doesServerExist', return_value=True)
    @patch('services.servers.ServersRepository.getServerName', return_value='demo')
    @patch('services.servers.ServersUsersPermsRepository.doesUserHavePerm')
    @patch('services.servers.manageLocalServers.uninstallMinecraftServer')
    @patch('services.servers.ServersRepository.removeServer')
    @patch('services.servers.get_jwt_identity', return_value=3)
    def test_remove_server_returns_403_without_permission(self, mock_identity, mock_remove, mock_uninstall, mock_has_perm, mock_get_server_name, mock_exists):
        mock_has_perm.return_value = False

        with self._call_in_request_context('delete', '/servers/12/uninstall'):
            with self.assertRaises(Exception) as ctx:
                inspect.unwrap(servers_module.remove_server)('12')

        self.assertIn('HTTPError', type(ctx.exception).__name__)
        self.assertFalse(mock_uninstall.called)
        self.assertFalse(mock_remove.called)

    @patch('services.servers.ServersRepository.doesServerExist', return_value=True)
    @patch('services.servers.ServersRepository.getServerName', return_value='demo')
    @patch('services.servers.ServersUsersPermsRepository.doesUserHavePerm')
    @patch('services.servers.manageLocalServers.uninstallMinecraftServer')
    @patch('services.servers.ServersRepository.removeServer')
    @patch('services.servers.get_jwt_identity', return_value=3)
    def test_remove_server_uninstalls_and_removes_when_permitted(self, mock_identity, mock_remove, mock_uninstall, mock_has_perm, mock_get_server_name, mock_exists):
        mock_has_perm.return_value = True
        mock_uninstall.return_value = {'status': 'ok'}
        mock_remove.return_value = True

        with self._call_in_request_context('delete', '/servers/12/uninstall'):
            response = inspect.unwrap(servers_module.remove_server)('12')

        self.assertEqual(response[1], 200)
        self.assertTrue(response[0]['status'])
        mock_uninstall.assert_called_once_with('demo')
        mock_remove.assert_called_once_with(3, 'demo')


if __name__ == '__main__':
    unittest.main()

