import inspect
import unittest
from unittest.mock import MagicMock, patch

import api


class SocketIOSidContextTests(unittest.TestCase):
    def setUp(self):
        api._sid_server_context.clear()

    def tearDown(self):
        api._sid_server_context.clear()

    @patch("api.emit")
    @patch("api.get_jwt_identity", return_value=7)
    @patch("api.ServersUsersPermsRepository.doseUserHavePerm", return_value=True)
    def test_console_uses_sid_bound_server_context(self, _perm, _identity, emit_mock):
        sid = "sid-1"
        api._sid_server_context[sid] = {
            "user_id": 7,
            "server_id": 2,
            "server_name": "TestServer",
        }
        server_instance = MagicMock()
        server_instance.send_command.return_value = True

        with api.app.test_request_context("/"):
            with patch("api._current_sid", return_value=sid), \
                 patch.object(api.serverSessionsManager, "serverInstances", {"TestServer": server_instance}):
                inspect.unwrap(api.handle_console)({"message": "list"})

        server_instance.send_command.assert_called_once_with("list", 7)
        emit_mock.assert_any_call("console_ack", {
            "ok": True,
            "code": "SENT",
            "message": "Command forwarded",
        })

    @patch("api.emit")
    @patch("api.get_jwt_identity", return_value=7)
    def test_console_without_sid_context_emits_invalid_server_ack(self, _identity, emit_mock):
        with api.app.test_request_context("/"):
            with patch("api._current_sid", return_value="missing-sid"):
                inspect.unwrap(api.handle_console)({"message": "list"})

        emit_mock.assert_any_call("console_ack", {
            "ok": False,
            "code": "INVALID_SERVER",
            "message": "Invalid or unauthorized server access",
        })

    @patch("api.join_room")
    @patch("api.register_socketio_listeners")
    @patch("api.utils.getServerStats", return_value={"cpu_usage_percent": 0.0})
    @patch("api.ServersUsersPermsRepository.doseUserHavePerm", return_value=True)
    @patch("api.ServersRepository.getServerName", return_value="TestServer")
    @patch("api.ServersRepository.doesServerExist", return_value=True)
    @patch("services.auth.repositories.UserRepository.getUserId", return_value=7)
    @patch("services.auth.repositories.UserRepository.verify", return_value=True)
    def test_socketio_client_connect_and_console_ack_flow(
        self,
        _verify,
        _get_user_id,
        _exists,
        _name,
        _perm,
        _stats,
        _register_socketio,
        _join_room,
    ):
        flask_client = api.app.test_client()
        login_response = flask_client.post("/login", json={"user_id": "owner", "password": "pw"})
        self.assertEqual(login_response.status_code, 200)

        server_instance = MagicMock()
        server_instance.log_history = []
        server_instance.running = False
        server_instance.send_command.return_value = True

        with patch.object(api.serverSessionsManager, "serverInstances", {"TestServer": server_instance}), \
             patch("api.register_socketio_listeners"):
            socket_client = api.socketio.test_client(
                api.app,
                flask_test_client=flask_client,
                auth={"serverId": 2},
            )
            self.assertTrue(socket_client.is_connected())
            self.assertEqual(len(api._sid_server_context), 1)

            # Drop connect-time bootstrap events and focus on console ack.
            socket_client.get_received()
            socket_client.emit("console", {"message": "list"})
            received = socket_client.get_received()
            console_acks = [event for event in received if event.get("name") == "console_ack"]

            self.assertTrue(console_acks)
            ack = console_acks[-1]["args"][0]
            self.assertTrue(ack["ok"])
            self.assertEqual(ack["code"], "SENT")
            server_instance.send_command.assert_called_once_with("list", 7)

            socket_client.disconnect()

        self.assertEqual(api._sid_server_context, {})

    @patch("api.leave_room")
    def test_disconnect_clears_sid_context(self, leave_room_mock):
        sid = "sid-disconnect"
        api._sid_server_context[sid] = {
            "user_id": 7,
            "server_id": 2,
            "server_name": "TestServer",
        }

        with api.app.test_request_context("/"):
            with patch("api._current_sid", return_value=sid):
                api.handle_disconnect()

        self.assertNotIn(sid, api._sid_server_context)
        leave_room_mock.assert_called_once_with("TestServer")


if __name__ == "__main__":
    unittest.main()

