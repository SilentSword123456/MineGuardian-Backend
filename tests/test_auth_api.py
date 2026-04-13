import json
import unittest
from unittest.mock import patch

from api import app
from services import auth


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def request_json(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload)
        return self.client.open(path, method=method, data=data, content_type='application/json')

    # Login endpoint tests

    def test_login_with_valid_credentials(self):
        """Test successful login returns access token"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True) as verify_mock, \
             patch.object(auth.repositories.UserRepository, 'getUserId', return_value='user-1') as get_user_id_mock:
            response = self.request_json('POST', '/login', {
                'user_id': 'testuser',
                'password': 'testpass'
            })

        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertIn('access_token', response_data)
        self.assertIsNotNone(response_data['access_token'])
        verify_mock.assert_called_once_with('testuser', 'testpass')
        get_user_id_mock.assert_called_once_with('testuser')

    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=False) as verify_mock, \
             patch.object(auth.repositories.UserRepository, 'getUserId') as get_user_id_mock:
            response = self.request_json('POST', '/login', {
                'user_id': 'testuser',
                'password': 'wrongpass'
            })

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {'message': 'Invalid credentials'})
        verify_mock.assert_called_once_with('testuser', 'wrongpass')
        get_user_id_mock.assert_not_called()

    def test_login_missing_username(self):
        """Test login without user_id returns 400"""
        response = self.request_json('POST', '/login', {
            'password': 'testpass'
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'Missing user_id or password'})

    def test_login_missing_password(self):
        """Test login without password returns 400"""
        response = self.request_json('POST', '/login', {
            'user_id': 'testuser'
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'Missing user_id or password'})

    def test_login_missing_both_credentials(self):
        """Test login without user_id and password returns 400"""
        response = self.request_json('POST', '/login', {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'Missing user_id or password'})

    def test_login_with_null_username(self):
        """Test login with null user_id returns 400"""
        response = self.request_json('POST', '/login', {
            'user_id': None,
            'password': 'testpass'
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'Missing user_id or password'})

    def test_login_with_null_password(self):
        """Test login with null password returns 400"""
        response = self.request_json('POST', '/login', {
            'user_id': 'testuser',
            'password': None
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'Missing user_id or password'})

    def test_login_calls_get_user_id_for_verified_user(self):
        """Verified login should resolve user id and return an access token."""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True) as verify_mock, \
             patch.object(auth.repositories.UserRepository, 'getUserId', return_value='user-42') as get_user_id_mock:
            response = self.request_json('POST', '/login', {
                'user_id': 'steve',
                'password': 'testpass'
            })

        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.get_json())
        verify_mock.assert_called_once_with('steve', 'testpass')
        get_user_id_mock.assert_called_once_with('steve')

    def test_login_with_empty_string_username(self):
        """Test login with empty string user_id"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=False) as verify_mock:
            response = self.request_json('POST', '/login', {
                'user_id': '',
                'password': 'testpass'
            })

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {'message': 'Invalid credentials'})
        verify_mock.assert_called_once_with('', 'testpass')

    def test_login_with_empty_string_password(self):
        """Test login with empty string password"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True), \
             patch.object(auth.repositories.UserRepository, 'getUserId', return_value='empty-pwd-user'):
            response = self.request_json('POST', '/login', {
                'user_id': 'testuser',
                'password': ''
            })

        self.assertEqual(response.status_code, 200)

    def test_login_with_special_characters_in_username(self):
        """Test login with special characters in user_id"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True) as verify_mock, \
             patch.object(auth.repositories.UserRepository, 'getUserId', return_value='special-user-id') as get_user_id_mock:
            response = self.request_json('POST', '/login', {
                'user_id': 'test@user.com',
                'password': 'testpass'
            })

        self.assertEqual(response.status_code, 200)
        verify_mock.assert_called_once_with('test@user.com', 'testpass')
        get_user_id_mock.assert_called_once_with('test@user.com')

    def test_multiple_login_attempts_with_different_users(self):
        """Test multiple successful logins issue different tokens."""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True), \
             patch.object(auth.repositories.UserRepository, 'getUserId', side_effect=['user1-id', 'user2-id']):
            response1 = self.request_json('POST', '/login', {
                'user_id': 'user1',
                'password': 'pass1'
            })
            response2 = self.request_json('POST', '/login', {
                'user_id': 'user2',
                'password': 'pass2'
            })

        token1 = response1.get_json()['access_token']
        token2 = response2.get_json()['access_token']

        # Tokens should be different
        self.assertNotEqual(token1, token2)



if __name__ == '__main__':
    unittest.main()

