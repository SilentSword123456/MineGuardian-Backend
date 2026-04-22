import json
import unittest
from unittest.mock import patch

from api import app
from services import dbHandler as db_handler


class DbHandlerApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with patch.object(db_handler.UserRepository, 'verify', return_value=True), \
             patch.object(db_handler.UserRepository, 'getUserId', return_value=1):
            login_response = self.client.open(
                '/login',
                method='POST',
                data=json.dumps({'user_id': 'test', 'password': 'test'}),
                content_type='application/json',
            )

        self.assertEqual(login_response.status_code, 200)
        # JWT is stored in cookies (JWT_TOKEN_LOCATION=["cookies"] in api.py).
        # The Flask test client persists cookies automatically across requests.

    def request_json(self, method, path, payload=None, use_auth=True):
        data = None if payload is None else json.dumps(payload)
        client = self.client if use_auth else app.test_client()
        return client.open(path, method=method, data=data, content_type='application/json')

    def assert_bad_request(self, response, message='bad request'):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['error'], message)

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
        get_username.assert_called_once_with(1)
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
        add_favorite_server.assert_called_once_with(99, 1)

    def test_remove_favorite_server(self):
        with patch.object(db_handler.FavoriteServersRepository, 'removeFavoriteServer', return_value=True) as remove_favorite_server:
            response = self.request_json('DELETE', '/favoriteServers', {'server_id': 99})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        remove_favorite_server.assert_called_once_with(1, 99)

    def test_get_favorite_servers(self):
        with patch.object(db_handler.FavoriteServersRepository, 'getFavoriteServers', return_value=[99, 100]) as get_favorite_servers:
            response = self.request_json('GET', '/favoriteServers')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'servers': [99, 100]})
        get_favorite_servers.assert_called_once_with(1)

    def test_add_player(self):
        with patch.object(db_handler.PlayerRepository, 'createPlayer', return_value=True) as create_player:
            response = self.request_json('POST', '/player', {'name': 'Steve', 'uuid': 'uuid-1'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        create_player.assert_called_once_with(1, 'Steve', 'uuid-1')

    def test_remove_player(self):
        with patch.object(db_handler.PlayerRepository, 'removePlayer', return_value=True) as remove_player:
            response = self.request_json('DELETE', '/player', {'uuid': 'uuid-1'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        remove_player.assert_called_once_with(1, 'uuid-1')

    def test_get_all_players_uuids(self):
        with patch.object(db_handler.PlayerRepository, 'getAllPlayersUUIDs', return_value=['uuid-1', 'uuid-2']) as get_all_players_uuids:
            response = self.request_json('GET', '/player')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'players': ['uuid-1', 'uuid-2']})
        get_all_players_uuids.assert_called_once_with(1)

    def test_add_player_privilege(self):
        with patch.object(db_handler.PlayersPrivilegesRepository, 'addPrivilege', return_value=True) as add_player_privilege:
            response = self.request_json('POST', '/playerPrivilege', {'player_uuid': 'uuid-1', 'privilege_id': 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        add_player_privilege.assert_called_once_with(1, 'uuid-1', 1)

    def test_delete_player_privilege(self):
        with patch.object(db_handler.PlayersPrivilegesRepository, 'deletePrivilege', return_value=True) as delete_player_privilege:
            response = self.request_json('DELETE', '/playerPrivilege', {'player_uuid': 'uuid-1', 'privilege_id': 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        delete_player_privilege.assert_called_once_with(1, 'uuid-1', 1)

    def test_add_player_privilege_invalid_integer_payload_is_rejected(self):
        response = self.request_json('POST', '/playerPrivilege', {'player_uuid': 'uuid-1', 'privilege_id': 'abc'})
        self.assert_bad_request(response)

    def test_delete_player_privilege_invalid_integer_payload_is_rejected(self):
        response = self.request_json('DELETE', '/playerPrivilege', {'player_uuid': 'uuid-1', 'privilege_id': 'abc'})
        self.assert_bad_request(response)

    def test_get_player_privileges(self):
        expected_privileges = [{'id': 1, 'privilege_id': 0}]
        with patch.object(db_handler.PlayersPrivilegesRepository, 'getPlayerPrivileges', return_value=expected_privileges) as get_player_privileges:
            response = self.request_json('GET', '/playerPrivilege', {'player_uuid': 'uuid-1'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'privileges': expected_privileges})
        get_player_privileges.assert_called_once_with(1, 'uuid-1')

    def test_add_setting(self):
        with patch.object(db_handler.SettingsRepository, 'addSetting', return_value=True) as add_setting:
            response = self.request_json('POST', '/setting', {'rule': 0, 'approved': True})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        add_setting.assert_called_once_with(1, 0, True)

    def test_remove_setting(self):
        with patch.object(db_handler.SettingsRepository, 'removeSetting', return_value=True) as remove_setting:
            response = self.request_json('DELETE', '/setting', {'rule': 0})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        remove_setting.assert_called_once_with(1, 0)

    def test_change_setting_defaults_to_false(self):
        with patch.object(db_handler.SettingsRepository, 'changeSetting', return_value=True) as change_setting:
            response = self.request_json('PATCH', '/setting', {'rule': 0})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        change_setting.assert_called_once_with(1, 0, False)

    def test_missing_required_field_is_rejected(self):
        response = self.request_json('POST', '/favoriteServers', {})
        self.assert_bad_request(response)

    def test_invalid_integer_payload_is_rejected(self):
        response = self.request_json('POST', '/favoriteServers', {'server_id': 'abc'})
        self.assert_bad_request(response)

    def test_create_user_does_not_require_auth(self):
        """POST /user should succeed without a JWT token."""
        with patch.object(db_handler.UserRepository, 'createUser', return_value=True):
            response = self.request_json('POST', '/user', {'username': 'noauth', 'password': 'pw'}, use_auth=False)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['status'])

    def test_remove_user_requires_auth(self):
        """DELETE /user without JWT should return 401."""
        response = self.request_json('DELETE', '/user', {'username': 'test'}, use_auth=False)
        self.assertEqual(response.status_code, 401)

    def test_get_favorite_servers_requires_auth(self):
        """GET /favoriteServers without JWT should return 401."""
        response = app.test_client().get('/favoriteServers')
        self.assertEqual(response.status_code, 401)

    def test_add_player_missing_name_is_rejected(self):
        """POST /player without 'name' should return 400."""
        response = self.request_json('POST', '/player', {'uuid': 'some-uuid'})
        self.assert_bad_request(response)

    def test_add_player_missing_uuid_is_rejected(self):
        """POST /player without 'uuid' should return 400."""
        response = self.request_json('POST', '/player', {'name': 'Steve'})
        self.assert_bad_request(response)

    def test_get_player_privileges_missing_uuid_is_rejected(self):
        """GET /playerPrivilege without 'player_uuid' should return 400."""
        response = self.request_json('GET', '/playerPrivilege', {})
        self.assert_bad_request(response)

    def test_add_setting_missing_rule_is_rejected(self):
        """POST /setting without 'rule' should return 400."""
        response = self.request_json('POST', '/setting', {'approved': True})
        self.assert_bad_request(response)

    def test_remove_setting_missing_rule_is_rejected(self):
        """DELETE /setting without 'rule' should return 400."""
        response = self.request_json('DELETE', '/setting', {})
        self.assert_bad_request(response)

    def test_change_setting_with_approved_true(self):
        """PATCH /setting with approved=True should pass approved=True to changeSetting."""
        with patch.object(db_handler.SettingsRepository, 'changeSetting', return_value=True) as change_setting:
            response = self.request_json('PATCH', '/setting', {'rule': 0, 'approved': True})

        self.assertEqual(response.status_code, 200)
        change_setting.assert_called_once_with(1, 0, True)

    def test_remove_favorite_server_returns_400_on_invalid_id(self):
        """DELETE /favoriteServers with non-integer server_id should return 400."""
        response = self.request_json('DELETE', '/favoriteServers', {'server_id': 'not-a-number'})
        self.assert_bad_request(response)

    def assert_validation_error(self, response):
        self.assertEqual(response.status_code, 422)
        data = response.get_json()
        self.assertEqual(data.get('message'), 'Validation error')

    def test_add_user_permission_for_server(self):
        """POST /userPermission should call ServersUsersPermsRepository.addPerm."""
        with patch.object(db_handler.ServersUsersPermsRepository, 'addPerm', return_value=True) as add_perm:
            response = self.request_json('POST', '/userPermission', {'user_id': 2, 'server_id': 1, 'perm_id': 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        add_perm.assert_called_once_with(1, 1, 2, 1)

    def test_remove_user_permission_for_server(self):
        """DELETE /userPermission should call ServersUsersPermsRepository.removePerm."""
        with patch.object(db_handler.ServersUsersPermsRepository, 'removePerm', return_value=True) as remove_perm:
            response = self.request_json('DELETE', '/userPermission', {'user_id': 2, 'server_id': 1, 'perm_id': 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': True})
        remove_perm.assert_called_once_with(1, 1, 2, 1)

    def test_add_user_permission_missing_fields_rejected(self):
        """POST /userPermission with missing fields should return 422."""
        response = self.request_json('POST', '/userPermission', {'user_id': 2})
        self.assert_validation_error(response)

    def test_remove_user_permission_invalid_types_rejected(self):
        """DELETE /userPermission with non-integer fields should return 422."""
        response = self.request_json('DELETE', '/userPermission', {'user_id': 'abc', 'server_id': 1, 'perm_id': 1})
        self.assert_validation_error(response)

    def test_add_user_permission_repository_failure_returns_401(self):
        """POST /userPermission should return 401 if addPerm returns False."""
        with patch.object(db_handler.ServersUsersPermsRepository, 'addPerm', return_value=False):
            response = self.request_json('POST', '/userPermission', {'user_id': 2, 'server_id': 1, 'perm_id': 1})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()['error'], 'Failed to add permission to the records.')

    def test_remove_user_permission_repository_failure_returns_401(self):
        """DELETE /userPermission should return 401 if removePerm returns False."""
        with patch.object(db_handler.ServersUsersPermsRepository, 'removePerm', return_value=False):
            response = self.request_json('DELETE', '/userPermission', {'user_id': 2, 'server_id': 1, 'perm_id': 1})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()['error'], 'Failed to remove permission from the records.')

    def test_get_default_servers_permissions(self):
        """GET /getDefaultServersPermissions should return all server permissions mapping."""
        response = app.test_client().get('/getDefaultServersPermissions')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('AddPermissionToServer', data)
        self.assertEqual(data['AddPermissionToServer'], 1)
        self.assertIn('ViewServer', data)
        self.assertEqual(data['ViewServer'], 6)

    def test_get_users_with_perms_on_server(self):
        """GET /servers/1/permissions should call ServersUsersPermsRepository.getUsersWithPermsOnServer."""
        mock_perms = {2: [1]}
        with patch('services.dbHandler.ServersRepository.getServerOwner', return_value=1), \
             patch('services.dbHandler.ServersUsersPermsRepository.getUsersWithPermsOnServer', return_value=mock_perms) as get_perms:
            response = self.request_json('GET', '/servers/1/permissions')

        self.assertEqual(response.status_code, 200)
        # Marshmallow/APIFlask might convert keys to strings in JSON
        self.assertEqual(response.get_json(), {'permissions': {'2': [1]}})
        get_perms.assert_called_once_with(1)

    def test_get_users_with_perms_on_server_unauthorized(self):
        """GET /servers/1/permissions should return 401 if user is not authorized."""
        with patch('services.dbHandler.ServersRepository.getServerOwner', return_value=2), \
             patch('services.dbHandler.ServersUsersPermsRepository.doseUserHavePerm', return_value=False):
            response = self.request_json('GET', '/servers/1/permissions')
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()['error'], 'Unauthorized')

    def test_get_users_with_perms_on_server_invalid_id_rejected(self):
        """GET /servers/abc/permissions with invalid server_id should return 404 (not matched)."""
        response = self.request_json('GET', '/servers/abc/permissions')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()

