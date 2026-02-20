import unittest
import queue
from unittest.mock import MagicMock, patch
from api import app, socketio
import api

class TestWebsocketErrors(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = None
        api.roomClientCount = {}
        api.activeDisplayThreads = {}
        api.stopEvents = {}

    def tearDown(self):
        if self.client and self.client.is_connected():
            self.client.disconnect()
        for event in api.stopEvents.values():
            event.set()

    def test_message_without_message_key(self):
        mock_server = MagicMock()
        mock_server.running = True
        mock_server.output_queue = queue.Queue()
        
        with patch('setup.runningServers', {'testServer': mock_server}):
            self.client = socketio.test_client(app, query_string='?serverName=testServer')
            # This should not crash the server
            self.client.emit('message', {})
            received = self.client.get_received()
            # If it crashed, we might not get anything or the server might have logged an error
            # In test_client, exceptions usually bubble up or are logged.

    def test_console_without_message_key(self):
        mock_server = MagicMock()
        mock_server.running = True
        mock_server.output_queue = queue.Queue()
        
        with patch('setup.runningServers', {'testServer': mock_server}):
            self.client = socketio.test_client(app, query_string='?serverName=testServer')
            # This should not crash the server
            self.client.emit('console', {})
            
    def test_message_with_non_dict_data(self):
        mock_server = MagicMock()
        mock_server.running = True
        mock_server.output_queue = queue.Queue()
        
        with patch('setup.runningServers', {'testServer': mock_server}):
            self.client = socketio.test_client(app, query_string='?serverName=testServer')
            self.client.emit('message', "not a dict")

if __name__ == '__main__':
    unittest.main()
