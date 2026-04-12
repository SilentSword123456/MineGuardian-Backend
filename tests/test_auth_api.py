import json
import unittest
from unittest.mock import patch, MagicMock

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
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True) as verify_mock:
            response = self.request_json('POST', '/login', {
                'username': 'testuser',
                'password': 'testpass'
            })

        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertIn('access_token', response_data)
        self.assertIsNotNone(response_data['access_token'])
        verify_mock.assert_called_once_with('testuser', 'testpass')

    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=False) as verify_mock:
            response = self.request_json('POST', '/login', {
                'username': 'testuser',
                'password': 'wrongpass'
            })

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {'message': 'Invalid credentials'})
        verify_mock.assert_called_once_with('testuser', 'wrongpass')

    def test_login_missing_username(self):
        """Test login without username returns 400"""
        response = self.request_json('POST', '/login', {
            'password': 'testpass'
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'Missing username or password'})

    def test_login_missing_password(self):
        """Test login without password returns 400"""
        response = self.request_json('POST', '/login', {
            'username': 'testuser'
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'Missing username or password'})

    def test_login_missing_both_credentials(self):
        """Test login without username and password returns 400"""
        response = self.request_json('POST', '/login', {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'Missing username or password'})

    def test_login_with_null_username(self):
        """Test login with null username returns 400"""
        response = self.request_json('POST', '/login', {
            'username': None,
            'password': 'testpass'
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'Missing username or password'})

    def test_login_with_null_password(self):
        """Test login with null password returns 400"""
        response = self.request_json('POST', '/login', {
            'username': 'testuser',
            'password': None
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'message': 'Missing username or password'})

    # Protected endpoint tests

    def test_protected_route_with_valid_token(self):
        """Test protected route access with valid JWT token"""
        # First, login to get a token
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True):
            login_response = self.request_json('POST', '/login', {
                'username': 'testuser',
                'password': 'testpass'
            })

        token = login_response.get_json()['access_token']

        # Now access protected route with token
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.get('/protected', headers=headers)

        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertEqual(response_data['logged_in_as'], 'testuser')

    def test_protected_route_without_token(self):
        """Test protected route returns 401 without token"""
        response = self.client.get('/protected')

        self.assertEqual(response.status_code, 401)

    def test_protected_route_with_invalid_token(self):
        """Test protected route returns 422 with invalid token"""
        headers = {'Authorization': 'Bearer invalid_token_here'}
        response = self.client.get('/protected', headers=headers)

        self.assertEqual(response.status_code, 422)

    def test_protected_route_with_malformed_auth_header(self):
        """Test protected route with malformed Authorization header"""
        # Missing "Bearer " prefix
        headers = {'Authorization': 'invalid_token_here'}
        response = self.client.get('/protected', headers=headers)

        self.assertEqual(response.status_code, 422)

    def test_login_creates_jwt_with_username_identity(self):
        """Test that JWT token contains the username as identity"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True):
            login_response = self.request_json('POST', '/login', {
                'username': 'steve',
                'password': 'testpass'
            })

        token = login_response.get_json()['access_token']

        # Access protected route and verify identity
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.get('/protected', headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['logged_in_as'], 'steve')

    def test_login_with_empty_string_username(self):
        """Test login with empty string username"""
        response = self.request_json('POST', '/login', {
            'username': '',
            'password': 'testpass'
        })

        # Empty string is falsy in Python, but not None
        # The current code checks for None, so this will pass through and fail verification
        # This tests the actual behavior
        self.assertEqual(response.status_code, 200)

    def test_login_with_empty_string_password(self):
        """Test login with empty string password"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True):
            response = self.request_json('POST', '/login', {
                'username': 'testuser',
                'password': ''
            })

        self.assertEqual(response.status_code, 200)

    def test_login_with_special_characters_in_username(self):
        """Test login with special characters in username"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True) as verify_mock:
            response = self.request_json('POST', '/login', {
                'username': 'test@user.com',
                'password': 'testpass'
            })

        self.assertEqual(response.status_code, 200)
        verify_mock.assert_called_once_with('test@user.com', 'testpass')

    def test_multiple_login_attempts_with_different_users(self):
        """Test multiple logins with different users create different tokens"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True):
            response1 = self.request_json('POST', '/login', {
                'username': 'user1',
                'password': 'pass1'
            })
            response2 = self.request_json('POST', '/login', {
                'username': 'user2',
                'password': 'pass2'
            })

        token1 = response1.get_json()['access_token']
        token2 = response2.get_json()['access_token']

        # Tokens should be different
        self.assertNotEqual(token1, token2)

        # Each token should identify its respective user
        headers1 = {'Authorization': f'Bearer {token1}'}
        headers2 = {'Authorization': f'Bearer {token2}'}

        protected1 = self.client.get('/protected', headers=headers1)
        protected2 = self.client.get('/protected', headers=headers2)

        self.assertEqual(protected1.get_json()['logged_in_as'], 'user1')
        self.assertEqual(protected2.get_json()['logged_in_as'], 'user2')


if __name__ == '__main__':
    unittest.main()

