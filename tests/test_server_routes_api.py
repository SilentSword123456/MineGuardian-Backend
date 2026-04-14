import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from Database.perms import ServersPermissions
from Database.repositories import ServersRepository, ServersUsersPermsRepository, UserRepository

from api import app
from services import servers as servers_module


class DummyServerInstance:
    def __init__(self, process_info=None, running=True):
        self._process_info = process_info or {
            'server_id': 'myCoolServer',
            'is_running': True,
            'pid': 1234,
            'uptime_seconds': 12.5,
            'max_memory_mb': 2048,
            'max_players': 20,
        }
        self._running = running

    def get_process_info(self):
        return self._process_info

    def is_running(self):
        return self._running


class ServerRoutesTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self._workflow_username = None
        self._workflow_password = None
        self._workflow_server_name = None
        self._workflow_headers = None

    def tearDown(self):
        self._cleanup_workflow_artifacts()

    def _get_auth_headers(self):
        with patch('services.auth.repositories.UserRepository.verify', return_value=True), \
                patch('services.auth.repositories.UserRepository.getUserId', return_value=7):
            response = self.client.post('/login', json={'user_id': 'test-user', 'password': 'test'})

        self.assertEqual(response.status_code, 200)
        token = response.get_json()['access_token']
        return {'Authorization': f'Bearer {token}'}

    def _workflow_server_root(self):
        return Path(__file__).resolve().parent.parent / 'servers' / self._workflow_server_name

    def _create_workflow_server_folder(self):
        server_root = self._workflow_server_root()
        server_root.mkdir(parents=True, exist_ok=True)

        with (server_root / 'launch.bat').open('w', encoding='utf-8') as handle:
            handle.write('java -Xmx2048M -jar server.jar nogui')

        with (server_root / 'server.properties').open('w', encoding='utf-8') as handle:
            handle.write('max-players=20\n')

    def _cleanup_workflow_artifacts(self):
        if self._workflow_server_name:
            shutil.rmtree(self._workflow_server_root(), ignore_errors=True)
            with app.app_context():
                workflow_user_id = UserRepository.getUserId(self._workflow_username) if self._workflow_username else 0
                if workflow_user_id:
                    ServersRepository.removeServer(workflow_user_id, self._workflow_server_name)

        if self._workflow_username:
            with app.app_context():
                workflow_user_id = UserRepository.getUserId(self._workflow_username)
                if workflow_user_id:
                    UserRepository.removeUser(self._workflow_username)

    def test_health_endpoint(self):
        response = self.client.get('/health')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('timestamp', data)

    def test_list_servers(self):
        servers = [{'name': 'myCoolServer', 'id': 1, 'isRunning': False, 'max_memory_mb': 2048}]
        with patch.object(servers_module, 'get_all_servers', return_value=servers):
            response = self.client.get('/servers')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'servers': servers})

    def test_general_server_info_when_server_is_not_running(self):
        servers = [{'server_id': 'myCoolServer', 'max_memory_mb': 2048, 'online_players': {'max': 20}}]
        with patch.object(servers_module, 'get_all_servers', return_value=servers), \
                patch.object(servers_module.serverSessionsManager, 'serverInstances', {}):
            response = self.client.get('/servers/myCoolServer')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            'name': 'myCoolServer',
            'is_running': False,
            'pid': 0,
            'uptime_seconds': 0.0,
            'max_memory_mb': 2048,
            'online_players': {'max': 20},
        })

    def test_general_server_info_when_server_is_running(self):
        servers = [{'server_id': 'myCoolServer', 'max_memory_mb': 4096, 'online_players': {'max': 10}}]
        server_instance = DummyServerInstance(process_info={
            'server_id': 'myCoolServer',
            'is_running': True,
            'pid': 4321,
            'uptime_seconds': 99.9,
            'max_memory_mb': 4096,
            'max_players': 15,
        })

        with patch.object(servers_module, 'get_all_servers', return_value=servers), \
                patch.object(servers_module.serverSessionsManager, 'serverInstances', {'myCoolServer': server_instance}):
            response = self.client.get('/servers/myCoolServer')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            'name': 'myCoolServer',
            'is_running': True,
            'pid': 4321,
            'uptime_seconds': 99.9,
            'max_memory_mb': 4096,
            'online_players': {'max': 15},
        })

    def test_server_not_found(self):
        with patch.object(servers_module, 'get_all_servers', return_value=[]):
            response = self.client.get('/servers/NotARealServer')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {'detail': {}, 'message': 'Server not found'})

    def test_server_stats_endpoint(self):
        server_instance = DummyServerInstance(running=True)
        stats = {
            'cpu_usage_percent': 12.5,
            'memory_usage_mb': 512.0,
            'max_memory_mb': 2048,
            'online_players': {'online': 1, 'max': 20, 'players': ['Steve']},
        }

        with patch.object(servers_module.serverSessionsManager, 'serverInstances', {'myCoolServer': server_instance}), \
                patch.object(servers_module.utils, 'getServerStats', return_value=stats):
            response = self.client.get('/servers/myCoolServer/stats')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), stats)

    def test_server_stats_endpoint_returns_404_when_server_not_running(self):
        server_instance = DummyServerInstance(running=False)

        with patch.object(servers_module.serverSessionsManager, 'serverInstances', {'myCoolServer': server_instance}):
            response = self.client.get('/servers/myCoolServer/stats')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {'detail': {}, 'message': "Server 'myCoolServer' is not running"})

    def test_start_server_endpoint_starts_instance_and_registers_listener(self):
        server_instance = Mock()

        with patch.object(servers_module, 'get_server_instance', return_value=server_instance) as get_server_instance, \
                patch.object(servers_module.api, 'register_socketio_listener') as register_listener:
            response = self.client.post('/servers/myCoolServer/start')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'message': "Server 'myCoolServer' started successfully"})
        get_server_instance.assert_called_once_with('myCoolServer')
        register_listener.assert_called_once_with('myCoolServer', server_instance)
        server_instance.start.assert_called_once_with()

    def test_stop_server_endpoint_calls_stop_service(self):
        with patch.object(servers_module, 'stop_server') as stop_server:
            response = self.client.post('/servers/myCoolServer/stop')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'message': "Server 'myCoolServer' stopped successfully"})
        stop_server.assert_called_once_with('myCoolServer')

    def test_manage_add_server_requires_jwt(self):
        response = self.client.post('/manage/addServer', json={
            'serverName': 'jwt-server',
            'serverSoftware': 'vanilla',
            'serverVersion': 'latest',
        })

        self.assertEqual(response.status_code, 401)

    def test_manage_add_server_success(self):
        headers = self._get_auth_headers()

        with patch.object(servers_module.manageLocalServers, 'installMinecraftServer', return_value=True) as install_server, \
                patch.object(servers_module.Database.repositories.ServersRepository, 'addServer', return_value=True) as add_server:
            response = self.client.post(
                '/manage/addServer',
                json={'serverName': 'myCoolServer', 'serverSoftware': 'vanilla', 'serverVersion': 'latest'},
                headers=headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True, 'message': "Server 'myCoolServer' installed and registered successfully"})
        install_server.assert_called_once_with('vanilla', 'latest', 'myCoolServer', False)
        add_server.assert_called_once_with(7, 'myCoolServer')

    def test_manage_remove_server_requires_jwt(self):
        response = self.client.delete('/servers/myCoolServer/uninstall')

        self.assertEqual(response.status_code, 401)

    def test_manage_remove_server_success(self):
        self._workflow_username = f'workflow-user-{uuid.uuid4().hex[:8]}'
        self._workflow_password = f'workflow-pass-{uuid.uuid4().hex[:8]}'
        self._workflow_server_name = f'workflow-server-{uuid.uuid4().hex[:8]}'

        try:
            create_response = self.client.post('/user', json={
                'username': self._workflow_username,
                'password': self._workflow_password,
            })
            self.assertEqual(create_response.status_code, 200)
            self.assertTrue(create_response.get_json()['status'])

            login_response = self.client.post('/login', json={
                'user_id': self._workflow_username,
                'password': self._workflow_password,
            })
            self.assertEqual(login_response.status_code, 200)
            token = login_response.get_json()['access_token']
            headers = {'Authorization': f'Bearer {token}'}
            self._workflow_headers = headers

            with patch.object(servers_module.manageLocalServers, 'installMinecraftServer', side_effect=lambda *args, **kwargs: self._create_workflow_server_folder() or True) as install_server:
                add_response = self.client.post(
                    '/manage/addServer',
                    json={
                        'serverName': self._workflow_server_name,
                        'serverSoftware': 'vanilla',
                        'serverVersion': 'latest',
                    },
                    headers=headers,
                )

            self.assertEqual(add_response.status_code, 200)
            self.assertEqual(add_response.get_json(), {'status': True, 'message': f"Server '{self._workflow_server_name}' installed and registered successfully"})
            install_server.assert_called_once_with('vanilla', 'latest', self._workflow_server_name, False)

            with app.app_context():
                workflow_user_id = UserRepository.getUserId(self._workflow_username)
                workflow_server_id = ServersRepository.getServerId(workflow_user_id, self._workflow_server_name)
                self.assertTrue(
                    ServersUsersPermsRepository.addPerm(
                        workflow_user_id,
                        workflow_server_id,
                        workflow_user_id,
                        ServersPermissions.RemovePermissionFromServer.value,
                    )
                )

            info_response = self.client.get(f'/servers/{self._workflow_server_name}')
            self.assertEqual(info_response.status_code, 200)
            self.assertEqual(info_response.get_json()['name'], self._workflow_server_name)

            with patch.object(servers_module.manageLocalServers, 'uninstallMinecraftServer', side_effect=lambda server_name: shutil.rmtree(Path(__file__).resolve().parent.parent / 'servers' / server_name, ignore_errors=True) or True) as uninstall_server:
                remove_response = self.client.delete(f'/servers/{self._workflow_server_name}/uninstall', headers=headers)

            self.assertEqual(remove_response.status_code, 200)
            self.assertEqual(remove_response.get_json(), {'status': True, 'message': f"Server '{self._workflow_server_name}' uninstalled and removed successfully"})
            uninstall_server.assert_called_once_with(self._workflow_server_name)

            with app.app_context():
                workflow_user_id = UserRepository.getUserId(self._workflow_username)
                self.assertNotEqual(workflow_user_id, 0)
                self.assertEqual(ServersRepository.getServerId(workflow_user_id, self._workflow_server_name), 0)
        finally:
            self._cleanup_workflow_artifacts()

    def test_global_stats_endpoint(self):
        stats = {
            'cpu_usage_percent': 18.0,
            'memory_usage_mb': 1024.0,
            'max_memory_mb': 4096,
            'online_players': {'online': 7, 'max': 40, 'players': ['Steve', 'Alex']},
        }

        with patch.object(servers_module.utils, 'getGlobalStats', return_value=stats):
            response = self.client.get('/servers/globalStats')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), stats)


if __name__ == "__main__":
    unittest.main()


