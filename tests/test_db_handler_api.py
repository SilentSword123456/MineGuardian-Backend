import json
import unittest
from unittest.mock import patch

from api import app
from services import dbHandler as db_handler


class DbHandlerApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with patch.object(db_handler.UserRepository, 'verify', return_value=True), \
             patch.object(db_handler.UserRepository, 'getUserId', return_value='test'):
            login_response = self.request_json(
                'POST',
                '/login',
                {'user_id': 'test', 'password': 'test'},
                use_auth=False,
            )

        self.assertEqual(login_response.status_code, 200)
        self.jwt_token = login_response.get_json()['access_token']
        self.auth_headers = {'Authorization': f'Bearer {self.jwt_token}'}

    def request_json(self, method, path, payload=None, use_auth=True):
        data = None if payload is None else json.dumps(payload)
        headers = self.auth_headers if use_auth else None
        return self.client.open(path, method=method, data=data, headers=headers, content_type='application/json')

    def assert_bad_request(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'error': 'bad request'})

    def test_create_user(self):
        with patch.object(db_handler.UserRepository, 'createUser', return_value=True) as create_user:
            response = self.request_json('POST', '/user', {'username': 'test', 'password': 'test'}, use_auth=False)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        create_user.assert_called_once_with('test', 'test')

    def test_remove_user(self):
        with patch.object(db_handler.UserRepository, 'getUsername', return_value='test') as get_username, \
             patch.object(db_handler.UserRepository, 'removeUser', return_value=True) as remove_user:
            response = self.request_json('DELETE', '/user', {'username': 'test'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        get_username.assert_called_once_with('test')
        remove_user.assert_called_once_with('test')

    def test_remove_user_forbidden_on_username_mismatch(self):
        with patch.object(db_handler.UserRepository, 'getUsername', return_value='other-user'):
            response = self.request_json('DELETE', '/user', {'username': 'test'})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json(), {'error': 'forbidden'})

    def test_add_favorite_server(self):
        with patch.object(db_handler.FavoriteServersRepository, 'addFavoriteServer', return_value=True) as add_favorite_server:
            response = self.request_json('POST', '/favoriteServers', {'server_id': 99})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        add_favorite_server.assert_called_once_with(99, 'test')

    def test_remove_favorite_server(self):
        with patch.object(db_handler.FavoriteServersRepository, 'removeFavoriteServer', return_value=True) as remove_favorite_server:
            response = self.request_json('DELETE', '/favoriteServers', {'server_id': 99})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        remove_favorite_server.assert_called_once_with('test', 99)

    def test_get_favorite_servers(self):
        with patch.object(db_handler.FavoriteServersRepository, 'getFavoriteServers', return_value=[99, 100]) as get_favorite_servers:
            response = self.request_json('GET', '/favoriteServers')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'servers': [99, 100]})
        get_favorite_servers.assert_called_once_with('test')

    def test_add_player(self):
        with patch.object(db_handler.PlayerRepository, 'createPlayer', return_value=True) as create_player:
            response = self.request_json('POST', '/player', {'name': 'Steve', 'uuid': 'uuid-1'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        create_player.assert_called_once_with('test', 'Steve', 'uuid-1')

    def test_remove_player(self):
        with patch.object(db_handler.PlayerRepository, 'removePlayer', return_value=True) as remove_player:
            response = self.request_json('DELETE', '/player', {'uuid': 'uuid-1'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        remove_player.assert_called_once_with('test', 'uuid-1')

    def test_get_all_players_uuids(self):
        with patch.object(db_handler.PlayerRepository, 'getAllPlayersUUIDs', return_value=['uuid-1', 'uuid-2'], create=True) as get_all_players_uuids:
            response = self.request_json('GET', '/player')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'players': ['uuid-1', 'uuid-2']})
        get_all_players_uuids.assert_called_once_with('test')

    def test_add_player_privilege(self):
        with patch.object(db_handler.PlayersPrivilegesRepository, 'addPlayerPrivilege', return_value=True) as add_player_privilege:
            response = self.request_json('POST', '/playerPrivilege', {'player_uuid': 'uuid-1', 'privilege_id': 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        add_player_privilege.assert_called_once_with('test', 'uuid-1', 1)

    def test_delete_player_privilege(self):
        with patch.object(db_handler.PlayersPrivilegesRepository, 'deletePlayerPrivilege', return_value=True) as delete_player_privilege:
            response = self.request_json('DELETE', '/playerPrivilege', {'player_uuid': 'uuid-1', 'privilege_id': 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        delete_player_privilege.assert_called_once_with('test', 'uuid-1', 1)

    def test_get_player_privileges(self):
        expected_privileges = [{'id': 1, 'privilege_id': 0}]
        with patch.object(db_handler.PlayersPrivilegesRepository, 'getPlayerPrivileges', return_value=expected_privileges) as get_player_privileges:
            response = self.request_json('GET', '/playerPrivilege', {'player_uuid': 'uuid-1'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'privileges': expected_privileges})
        get_player_privileges.assert_called_once_with('test', 'uuid-1')

    def test_add_setting(self):
        with patch.object(db_handler.SettingsRepository, 'addSetting', return_value=True) as add_setting:
            response = self.request_json('POST', '/setting', {'rule': 0, 'approved': True})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        add_setting.assert_called_once_with('test', 0, True)

    def test_remove_setting(self):
        with patch.object(db_handler.SettingsRepository, 'removeSetting', return_value=True) as remove_setting:
            response = self.request_json('DELETE', '/setting', {'rule': 0})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        remove_setting.assert_called_once_with('test', 0)

    def test_change_setting_defaults_to_false(self):
        with patch.object(db_handler.SettingsRepository, 'changeSetting', return_value=True) as change_setting:
            response = self.request_json('PATCH', '/setting', {'rule': 0})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        change_setting.assert_called_once_with('test', 0, False)

    def test_missing_required_field_is_rejected(self):
        response = self.request_json('POST', '/favoriteServers', {})
        self.assert_bad_request(response)

    def test_invalid_integer_payload_is_rejected(self):
        response = self.request_json('POST', '/favoriteServers', {'server_id': 'abc'})
        self.assert_bad_request(response)


if __name__ == '__main__':
    unittest.main()

