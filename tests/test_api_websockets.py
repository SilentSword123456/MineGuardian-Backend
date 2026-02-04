import unittest
from unittest.mock import MagicMock, patch
import queue
import time
import threading
from flask import Flask
from flask_socketio import SocketIO

# Import the app and socketio from api.py
# We might need to mock getConfig before importing api if it fails
with patch('utils.getConfig') as mock_config:
    mock_config.return_value = {
        'flaskConfig': {
            'SECRET_KEY': 'test_key',
            'SOCKETIO_CORS_ALLOWED_ORIGINS': '*'
        }
    }
    from api import app, socketio
    import api

class TestWebsocket(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = None
        # Reset global state in api.py
        api.roomClientCount = {}
        api.activeDisplayThreads = {}
        api.stopEvents = {}

    def tearDown(self):
        if self.client and self.client.is_connected():
            self.client.disconnect()
        # Stop any background threads started during tests
        for event in api.stopEvents.values():
            event.set()
        for thread in api.activeDisplayThreads.values():
            thread.join(timeout=1)

    @patch('setup.runningServers', {})
    def test_connect_no_server_name(self):
        client = socketio.test_client(app)
        self.assertFalse(client.is_connected())

    @patch('setup.runningServers', {})
    def test_connect_server_not_running(self):
        client = socketio.test_client(app, query_string='?serverName=missingServer')
        self.assertFalse(client.is_connected())

    def test_connect_success(self):
        mock_server = MagicMock()
        mock_server.running = True
        mock_server.output_queue = queue.Queue()
        
        with patch('setup.runningServers', {'testServer': mock_server}):
            self.client = socketio.test_client(app, query_string='?serverName=testServer')
            self.assertTrue(self.client.is_connected())
            
            received = self.client.get_received()
            messages = [m for m in received if m['name'] == 'message']
            self.assertEqual(len(messages), 1)
            self.assertEqual(self._get_arg_data(messages[0]), "Connected to server testServer")
            self.assertEqual(api.roomClientCount['testServer'], 1)

    def test_message_echo(self):
        mock_server = MagicMock()
        mock_server.running = True
        mock_server.output_queue = queue.Queue()
        
        with patch('setup.runningServers', {'testServer': mock_server}):
            self.client = socketio.test_client(app, query_string='?serverName=testServer')
            self.client.get_received() # clear connect messages
            
            self.client.emit('message', {'message': 'hello'})
            received = self.client.get_received()
            messages = [m for m in received if m['name'] == 'message']
            self.assertEqual(len(messages), 1)
            self.assertEqual(self._get_arg_data(messages[0]), "Server testServer received: hello")

    def test_console_command_success(self):
        mock_server = MagicMock()
        mock_server.running = True
        mock_server.output_queue = queue.Queue()
        
        with patch('setup.runningServers', {'testServer': mock_server}):
            self.client = socketio.test_client(app, query_string='?serverName=testServer')
            self.client.emit('console', {'message': 'help'})
            
            mock_server.send_command.assert_called_with('help')

    def test_console_command_server_not_running(self):
        mock_server = MagicMock()
        mock_server.running = True
        mock_server.output_queue = queue.Queue()
        
        # Connect to testServer, then it "stops" or we test another server
        with patch('setup.runningServers', {'testServer': mock_server}):
            self.client = socketio.test_client(app, query_string='?serverName=testServer')
            self.client.get_received()
            
            # Now simulate it's not in runningServers anymore
            with patch('setup.runningServers', {}):
                self.client.emit('console', {'message': 'help'})
                received = self.client.get_received()
                console_msgs = [m for m in received if m['name'] == 'console']
                self.assertEqual(len(console_msgs), 1)
                self.assertIn("is not running", self._get_arg_data(console_msgs[0]))

    def test_disconnect_cleanup(self):
        mock_server = MagicMock()
        mock_server.running = True
        mock_server.output_queue = queue.Queue()
        
        with patch('setup.runningServers', {'testServer': mock_server}):
            self.client = socketio.test_client(app, query_string='?serverName=testServer')
            self.client.get_received() # clear
            self.assertTrue(self.client.is_connected())
            self.assertEqual(api.roomClientCount['testServer'], 1)
            
            self.client.disconnect()
            self.assertEqual(api.roomClientCount['testServer'], 0)
            self.assertTrue(api.stopEvents['testServer'].is_set())

    def test_console_output_streaming(self):
        mock_server = MagicMock()
        mock_server.running = True
        q = queue.Queue()
        mock_server.output_queue = q
        
        with patch('setup.runningServers', {'testServer': mock_server}):
            self.client = socketio.test_client(app, query_string='?serverName=testServer')
            self.client.get_received() # clear connect messages
            
            q.put("Server started successfully")
            
            # Wait for background thread to pick it up and emit
            for _ in range(10):
                time.sleep(0.1)
                received = self.client.get_received()
                console_msgs = [m for m in received if m['name'] == 'console']
                actual_data = [self._get_arg_data(m) for m in console_msgs]
                
                if "Server started successfully" in actual_data:
                    break
            else:
                self.fail("Server started successfully message not received")

    def test_history_replay_on_connect(self):
        mock_server = MagicMock()
        mock_server.running = True
        mock_server.output_queue = queue.Queue()
        mock_server.console_history = ["Line 1", "Line 2", "Line 3"]
        
        with patch('setup.runningServers', {'testServer': mock_server}):
            self.client = socketio.test_client(app, query_string='?serverName=testServer')
            received = self.client.get_received()
            
            console_msgs = [m for m in received if m['name'] == 'console']
            actual_data = [self._get_arg_data(m) for m in console_msgs]
            
            self.assertIn("Line 1", actual_data)
            self.assertIn("Line 2", actual_data)
            self.assertIn("Line 3", actual_data)
            # Order should be preserved too
            line1_idx = actual_data.index("Line 1")
            line2_idx = actual_data.index("Line 2")
            line3_idx = actual_data.index("Line 3")
            self.assertTrue(line1_idx < line2_idx < line3_idx)

    def _get_arg_data(self, event):
        arg = event['args']
        if isinstance(arg, list):
            return arg[0]['data']
        return arg['data']

if __name__ == '__main__':
    unittest.main()
