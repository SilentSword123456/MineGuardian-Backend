import unittest
from unittest.mock import Mock, patch

from api import app
from services import servers as servers_module


class DummyServerInstance:
    def __init__(self, process_info=None, running=True, instance_id=1):
        self.id = instance_id
        self._running = running
        self._process_info = process_info or {
            'server_id': instance_id,
            'is_running': running,
            'pid': 1234 if running else 0,
            'uptime_seconds': 12.5 if running else 0.0,
            'max_memory_mb': 2048,
            'max_players': 20,
        }

    def get_process_info(self):
        return self._process_info

    def is_running(self):
        return self._running


class ServerRoutesTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _login(self, user_id=7):
        with patch('services.auth.repositories.UserRepository.verify', return_value=True), \
             patch('services.auth.repositories.UserRepository.getUserId', return_value=user_id):
            response = self.client.post('/login', json={'user_id': 'test-user', 'password': 'test'})
        self.assertEqual(response.status_code, 200)

    def test_health_endpoint(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'ok')

    def test_list_servers_requires_jwt(self):
        response = self.client.get('/servers')
        self.assertEqual(response.status_code, 401)

    def test_list_servers_returns_visible_servers(self):
        self._login()
        with patch.object(servers_module, 'getAllServers', return_value=[5]), \
             patch.object(servers_module.ServersRepository, 'getServerName', return_value='myCoolServer'), \
             patch.object(servers_module.serverSessionsManager, 'serverInstances', {}), \
             patch.object(servers_module.utils, 'getMaxMemoryMB', return_value=2048), \
             patch.object(servers_module.utils, 'getMaxPlayers', return_value=20):
            response = self.client.get('/servers')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            'servers': [{
                'name': 'myCoolServer',
                'server_id': 5,
                'isRunning': False,
                'max_memory_mb': 2048,
                'online_players': {'max': 20},
            }]
        })

    def test_general_server_info_when_not_running(self):
        self._login()
        with patch.object(servers_module.ServersRepository, 'doesServerExist', return_value=True), \
             patch.object(servers_module.ServersUsersPermsRepository, 'doseUserHavePerm', return_value=True), \
             patch.object(servers_module.ServersRepository, 'getServerName', return_value='myCoolServer'), \
             patch.object(servers_module.serverSessionsManager, 'serverInstances', {}), \
             patch.object(servers_module.utils, 'getMaxMemoryMB', return_value=1024), \
             patch.object(servers_module.utils, 'getMaxPlayers', return_value=20):
            response = self.client.get('/servers/9')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            'server_id': 9,
            'is_running': False,
            'pid': 0,
            'uptime_seconds': 0.0,
            'max_memory_mb': 1024,
            'max_players': 20,
        })

    def test_general_server_info_returns_403_without_permission(self):
        self._login()
        with patch.object(servers_module.ServersRepository, 'doesServerExist', return_value=True), \
             patch.object(servers_module.ServersUsersPermsRepository, 'doseUserHavePerm', return_value=False):
            response = self.client.get('/servers/9')
        self.assertEqual(response.status_code, 403)

    def test_general_server_info_when_running(self):
        self._login()
        server_instance = DummyServerInstance(process_info={
            'server_id': 9,
            'is_running': True,
            'pid': 4321,
            'uptime_seconds': 99.9,
            'max_memory_mb': 4096,
            'max_players': 15,
        })
        with patch.object(servers_module.ServersRepository, 'doesServerExist', return_value=True), \
             patch.object(servers_module.ServersUsersPermsRepository, 'doseUserHavePerm', return_value=True), \
             patch.object(servers_module.ServersRepository, 'getServerName', return_value='myCoolServer'), \
             patch.object(servers_module.serverSessionsManager, 'serverInstances', {'myCoolServer': server_instance}):
            response = self.client.get('/servers/9')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['pid'], 4321)

    def test_server_stats_endpoint(self):
        self._login()
        server_instance = DummyServerInstance(running=True)
        stats = {
            'cpu_usage_percent': 12.5,
            'memory_usage_mb': 512.0,
            'max_memory_mb': 2048,
            'online_players': {'online': 1, 'max': 20, 'players': ['Steve']},
        }
        with patch.object(servers_module.ServersRepository, 'doesServerExist', return_value=True), \
             patch.object(servers_module.ServersUsersPermsRepository, 'doseUserHavePerm', return_value=True), \
             patch.object(servers_module.ServersRepository, 'getServerName', return_value='myCoolServer'), \
             patch.object(servers_module.serverSessionsManager, 'serverInstances', {'myCoolServer': server_instance}), \
             patch.object(servers_module.utils, 'getServerStats', return_value=stats):
            response = self.client.get('/servers/9/stats')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), stats)

    def test_start_server_endpoint_starts_instance_and_registers_listener(self):
        self._login()
        server_instance = Mock()
        with patch.object(servers_module.ServersRepository, 'doesServerExist', return_value=True), \
             patch.object(servers_module.ServersUsersPermsRepository, 'doseUserHavePerm', return_value=True), \
             patch.object(servers_module.ServersRepository, 'getServerName', return_value='myCoolServer'), \
             patch.object(servers_module, 'get_server_instance', return_value=server_instance) as get_server_instance, \
             patch.object(servers_module.api, 'register_socketio_listener') as register_listener:
            response = self.client.post('/servers/9/start')

        self.assertEqual(response.status_code, 200)
        get_server_instance.assert_called_once_with(9)
        register_listener.assert_called_once_with('myCoolServer', server_instance)
        server_instance.start.assert_called_once_with()

    def test_stop_server_endpoint_calls_stop_service(self):
        self._login()
        with patch.object(servers_module.ServersRepository, 'doesServerExist', return_value=True), \
             patch.object(servers_module.ServersUsersPermsRepository, 'doseUserHavePerm', return_value=True), \
             patch.object(servers_module.ServersRepository, 'getServerName', return_value='myCoolServer'), \
             patch.object(servers_module, 'stop_server') as stop_server:
            response = self.client.post('/servers/9/stop')

        self.assertEqual(response.status_code, 200)
        stop_server.assert_called_once_with(9)

    def test_manage_add_server_requires_jwt(self):
        response = self.client.post('/manage/addServer', json={
            'serverName': 'jwt-server',
            'serverSoftware': 'vanilla',
            'serverVersion': 'latest',
        })
        self.assertEqual(response.status_code, 401)

    def test_manage_add_server_success(self):
        self._login()
        with patch.object(servers_module.manageLocalServers, 'installMinecraftServer', return_value=True) as install_server, \
             patch.object(servers_module.Database.repositories.ServersRepository, 'addServer', return_value=True) as add_server:
            response = self.client.post(
                '/manage/addServer',
                json={'serverName': 'myCoolServer', 'serverSoftware': 'vanilla', 'serverVersion': 'latest'},
            )

        self.assertEqual(response.status_code, 200)
        install_server.assert_called_once_with('vanilla', 'latest', 'myCoolServer', False)
        add_server.assert_called_once_with(7, 'myCoolServer')

    def test_manage_remove_server_success(self):
        self._login()
        with patch.object(servers_module.ServersRepository, 'getServerId', return_value=9), \
             patch.object(servers_module.ServersUsersPermsRepository, 'doseUserHavePerm', return_value=True), \
             patch.object(servers_module.manageLocalServers, 'uninstallMinecraftServer', return_value=True) as uninstall_server, \
             patch.object(servers_module.ServersRepository, 'removeServer', return_value=True):
            response = self.client.delete('/servers/myCoolServer/uninstall')

        self.assertEqual(response.status_code, 200)
        uninstall_server.assert_called_once_with('myCoolServer')

    def test_global_stats_endpoint(self):
        self._login()
        stats = {
            'cpu_usage_percent': 18.0,
            'memory_usage_mb': 1024.0,
            'max_memory_mb': 4096,
            'online_players': {'online': 7, 'max': 40, 'players': ['Steve', 'Alex']},
        }
        a = DummyServerInstance(instance_id=1)
        b = DummyServerInstance(instance_id=2)

        with patch.object(servers_module, 'getAllServers', return_value=[2]), \
             patch.object(servers_module.serverSessionsManager, 'serverInstances', {'a': a, 'b': b}), \
             patch.object(servers_module.utils, 'getGlobalStats', return_value=stats) as get_global_stats:
            response = self.client.get('/servers/globalStats')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), stats)
        get_global_stats.assert_called_once()
        called_instances = get_global_stats.call_args.args[0]
        self.assertEqual(len(called_instances), 1)
        self.assertEqual(called_instances[0].id, 2)

    def test_get_available_versions_success(self):
        versions = {'versions': ['latest', '1.21.1', '1.20.4']}
        with patch.object(servers_module.manageLocalServers, 'getAvailableVersions', return_value=versions):
            response = self.client.get('/manage/vanilla/getAvailableVersions')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), versions)

    def test_get_available_versions_returns_400_on_error(self):
        with patch.object(servers_module.manageLocalServers, 'getAvailableVersions', return_value={'error': 'Not supported'}):
            response = self.client.get('/manage/spigot/getAvailableVersions')
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()

