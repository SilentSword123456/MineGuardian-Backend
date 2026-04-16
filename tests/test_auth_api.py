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

    def get_access_token_cookie(self, response):
        """Extract the accessToken value from the Set-Cookie header, or None."""
        for cookie in response.headers.getlist('Set-Cookie'):
            if cookie.startswith('accessToken='):
                return cookie.split(';')[0].split('=', 1)[1]
        return None

    def get_access_token_set_cookie_header(self, response):
        for cookie in response.headers.getlist('Set-Cookie'):
            if cookie.startswith('accessToken='):
                return cookie
        return None

    # Login endpoint tests

    def test_login_with_valid_credentials(self):
        """Test successful login sets accessToken cookie"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True) as verify_mock, \
             patch.object(auth.repositories.UserRepository, 'getUserId', return_value=1) as get_user_id_mock:
            response = self.request_json('POST', '/login', {
                'user_id': 'testuser',
                'password': 'testpass'
            })

        self.assertEqual(response.status_code, 200)
        token = self.get_access_token_cookie(response)
        self.assertIsNotNone(token)
        self.assertNotEqual(token, '')
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
        """Verified login should resolve user id and set accessToken cookie."""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True) as verify_mock, \
             patch.object(auth.repositories.UserRepository, 'getUserId', return_value=42) as get_user_id_mock:
            response = self.request_json('POST', '/login', {
                'user_id': 'steve',
                'password': 'testpass'
            })

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.get_access_token_cookie(response))
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
        """Test login with empty string password sets accessToken cookie"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True), \
             patch.object(auth.repositories.UserRepository, 'getUserId', return_value=2):
            response = self.request_json('POST', '/login', {
                'user_id': 'testuser',
                'password': ''
            })

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.get_access_token_cookie(response))

    def test_login_with_special_characters_in_username(self):
        """Test login with special characters in user_id sets accessToken cookie"""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True) as verify_mock, \
             patch.object(auth.repositories.UserRepository, 'getUserId', return_value=3) as get_user_id_mock:
            response = self.request_json('POST', '/login', {
                'user_id': 'test@user.com',
                'password': 'testpass'
            })

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.get_access_token_cookie(response))
        verify_mock.assert_called_once_with('test@user.com', 'testpass')
        get_user_id_mock.assert_called_once_with('test@user.com')

    def test_multiple_login_attempts_with_different_users(self):
        """Test multiple successful logins set different accessToken cookies."""
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True), \
             patch.object(auth.repositories.UserRepository, 'getUserId', side_effect=[11, 12]):
            response1 = self.request_json('POST', '/login', {
                'user_id': 'user1',
                'password': 'pass1'
            })
            response2 = self.request_json('POST', '/login', {
                'user_id': 'user2',
                'password': 'pass2'
            })

        token1 = self.get_access_token_cookie(response1)
        token2 = self.get_access_token_cookie(response2)

        self.assertIsNotNone(token1)
        self.assertIsNotNone(token2)
        # Tokens should be different
        self.assertNotEqual(token1, token2)

    def test_login_cookie_supports_cross_site_requests(self):
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True), \
             patch.object(auth.repositories.UserRepository, 'getUserId', return_value=55):
            response = self.request_json('POST', '/login', {
                'user_id': 'cross-site-user',
                'password': 'pass'
            })

        set_cookie = self.get_access_token_set_cookie_header(response)
        self.assertIsNotNone(set_cookie)
        self.assertIn('HttpOnly', set_cookie)
        self.assertIn('Secure', set_cookie)
        self.assertIn('SameSite=None', set_cookie)

    def test_login_allows_frontend_silentlab_origin(self):
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True), \
             patch.object(auth.repositories.UserRepository, 'getUserId', return_value=12):
            response = self.client.post(
                '/login',
                data=json.dumps({'user_id': 'testuser', 'password': 'testpass'}),
                content_type='application/json',
                headers={'Origin': 'https://frontend.silentlab.work'}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get('Access-Control-Allow-Origin'),
            'https://frontend.silentlab.work'
        )
        self.assertEqual(response.headers.get('Access-Control-Allow-Credentials'), 'true')

    def test_login_allows_workers_preview_origin(self):
        origin = 'https://preview-mineguardianui.andrei925-dumitru.workers.dev'
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True), \
             patch.object(auth.repositories.UserRepository, 'getUserId', return_value=13):
            response = self.client.post(
                '/login',
                data=json.dumps({'user_id': 'testuser', 'password': 'testpass'}),
                content_type='application/json',
                headers={'Origin': origin}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), origin)
        self.assertEqual(response.headers.get('Access-Control-Allow-Credentials'), 'true')

    def test_login_allows_untrusted_origin_temporarily(self):
        with patch.object(auth.repositories.UserRepository, 'verify', return_value=True), \
              patch.object(auth.repositories.UserRepository, 'getUserId', return_value=14):
            origin = 'https://example.com'
            response = self.client.post(
                '/login',
                data=json.dumps({'user_id': 'testuser', 'password': 'testpass'}),
                content_type='application/json',
                headers={'Origin': origin}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), origin)
        self.assertEqual(response.headers.get('Access-Control-Allow-Credentials'), 'true')



if __name__ == '__main__':
    unittest.main()
