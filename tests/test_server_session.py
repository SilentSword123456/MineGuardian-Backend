"""
Tests for serverSessionsManager.ServerSession.

The ServerSession constructor calls utils.getNewPort / utils.assignNewPort,
which touch the file system and real sockets.  Those calls are mocked so that
no actual process, file or network I/O is performed.
"""

import unittest
from unittest.mock import MagicMock, patch


def _make_session(server_id=1, name="test-server", command="java -jar server.jar"):
    """Return a ServerSession with all side-effectful setup patched out."""
    with patch("utils.getNewPort", side_effect=[25565, 25575]), \
         patch("utils.assignNewPort", side_effect=[25565, 25575]), \
         patch("utils.getConfig", return_value={"rconPassword": "secret"}), \
         patch("serverSessionsManager.ServersRepository.doesServerExist", return_value=True):
        import serverSessionsManager
        session = serverSessionsManager.ServerSession(server_id, name, command, working_dir="/fake/servers/test")
    return session


class ServerSessionInitTests(unittest.TestCase):
    def test_name_is_stored(self):
        s = _make_session(name="my-server")
        self.assertEqual(s.name, "my-server")

    def test_command_string_is_split_into_list(self):
        s = _make_session(command="java -jar server.jar nogui")
        self.assertEqual(s.command, ["java", "-jar", "server.jar", "nogui"])

    def test_command_list_is_stored_as_is(self):
        with patch("utils.getNewPort", side_effect=[25565, 25575]), \
             patch("utils.assignNewPort", side_effect=[25565, 25575]), \
             patch("serverSessionsManager.ServersRepository.doesServerExist", return_value=True):
            import serverSessionsManager
            s = serverSessionsManager.ServerSession(1, "s", ["java", "-jar", "server.jar"], working_dir="/fake/servers/s")
        self.assertEqual(s.command, ["java", "-jar", "server.jar"])

    def test_initial_state_is_not_running(self):
        s = _make_session()
        self.assertFalse(s._running)

    def test_log_history_starts_empty(self):
        s = _make_session()
        self.assertEqual(s.log_history, [])

    def test_listeners_start_empty(self):
        s = _make_session()
        self.assertEqual(s.listeners, [])
        self.assertEqual(s.status_listeners, [])

    def test_port_and_rcon_port_are_assigned(self):
        s = _make_session()
        self.assertEqual(s.port, 25565)
        self.assertEqual(s.rcon_port, 25575)


# ---------------------------------------------------------------------------
# Listener management
# ---------------------------------------------------------------------------

class AddRemoveListenerTests(unittest.TestCase):
    def setUp(self):
        self.session = _make_session()

    def test_add_listener_registers_callback(self):
        cb = MagicMock()
        self.session.add_listener(cb)
        self.assertIn(cb, self.session.listeners)

    def test_add_listener_does_not_duplicate(self):
        cb = MagicMock()
        self.session.add_listener(cb)
        self.session.add_listener(cb)
        self.assertEqual(self.session.listeners.count(cb), 1)

    def test_remove_listener_deregisters_callback(self):
        cb = MagicMock()
        self.session.add_listener(cb)
        self.session.remove_listener(cb)
        self.assertNotIn(cb, self.session.listeners)

    def test_remove_listener_is_noop_when_not_registered(self):
        cb = MagicMock()
        self.session.remove_listener(cb)  # Should not raise

    def test_add_status_listener_registers_callback(self):
        cb = MagicMock()
        self.session.add_status_listener(cb)
        self.assertIn(cb, self.session.status_listeners)

    def test_add_status_listener_does_not_duplicate(self):
        cb = MagicMock()
        self.session.add_status_listener(cb)
        self.session.add_status_listener(cb)
        self.assertEqual(self.session.status_listeners.count(cb), 1)


# ---------------------------------------------------------------------------
# _broadcast_status
# ---------------------------------------------------------------------------

class BroadcastStatusTests(unittest.TestCase):
    def setUp(self):
        self.session = _make_session()

    def test_calls_all_registered_status_listeners(self):
        cb1 = MagicMock()
        cb2 = MagicMock()
        self.session.add_status_listener(cb1)
        self.session.add_status_listener(cb2)

        self.session._broadcast_status(True)

        cb1.assert_called_once_with(True)
        cb2.assert_called_once_with(True)

    def test_passes_false_to_status_listeners(self):
        cb = MagicMock()
        self.session.add_status_listener(cb)
        self.session._broadcast_status(False)
        cb.assert_called_once_with(False)

    def test_does_not_raise_when_listener_raises(self):
        broken = MagicMock(side_effect=RuntimeError("oops"))
        self.session.add_status_listener(broken)
        # Should not propagate the exception
        self.session._broadcast_status(True)


# ---------------------------------------------------------------------------
# _updateHistory / _broadcast
# ---------------------------------------------------------------------------

class UpdateHistoryTests(unittest.TestCase):
    def setUp(self):
        self.session = _make_session()

    def test_appends_lines_to_history(self):
        self.session._updateHistory("line 1")
        self.session._updateHistory("line 2", source="user1")
        self.assertEqual(self.session.log_history, [
            {"line": "line 1", "source": "server"},
            {"line": "line 2", "source": "user1"}
        ])

    def test_history_is_capped_at_max_history(self):
        self.session.max_history = 3
        for i in range(5):
            self.session._updateHistory(f"line {i}")
        self.assertEqual(len(self.session.log_history), 3)
        # The oldest entries should be dropped
        self.assertNotIn({"line": "line 0", "source": "server"}, self.session.log_history)
        self.assertNotIn({"line": "line 1", "source": "server"}, self.session.log_history)
        self.assertIn({"line": "line 4", "source": "server"}, self.session.log_history)


class BroadcastTests(unittest.TestCase):
    def setUp(self):
        self.session = _make_session()

    def test_broadcast_updates_history(self):
        self.session._broadcast("hello")
        self.assertIn({"line": "hello", "source": "server"}, self.session.log_history)

    def test_broadcast_calls_all_listeners(self):
        cb1 = MagicMock()
        cb2 = MagicMock()
        self.session.add_listener(cb1)
        self.session.add_listener(cb2)
        self.session._broadcast("test line", source="custom")
        cb1.assert_called_once_with({"line": "test line", "source": "custom"})
        cb2.assert_called_once_with({"line": "test line", "source": "custom"})

    def test_broadcast_does_not_raise_when_listener_raises(self):
        broken = MagicMock(side_effect=RuntimeError("listener error"))
        self.session.add_listener(broken)
        self.session._broadcast("something")  # Should not raise


# ---------------------------------------------------------------------------
# running property
# ---------------------------------------------------------------------------

class RunningPropertyTests(unittest.TestCase):
    def setUp(self):
        self.session = _make_session()

    def test_running_setter_broadcasts_status_on_transition(self):
        cb = MagicMock()
        self.session.add_status_listener(cb)

        self.session.running = True
        cb.assert_called_once_with(True)

    def test_running_setter_does_not_broadcast_when_value_unchanged(self):
        self.session._running = True
        cb = MagicMock()
        self.session.add_status_listener(cb)

        self.session.running = True  # No change → no broadcast
        cb.assert_not_called()

    def test_running_setter_transitions_false_to_true_then_true_to_false(self):
        cb = MagicMock()
        self.session.add_status_listener(cb)

        self.session.running = True
        self.session.running = False

        self.assertEqual(cb.call_count, 2)
        cb.assert_any_call(True)
        cb.assert_any_call(False)


# ---------------------------------------------------------------------------
# is_running
# ---------------------------------------------------------------------------

class IsRunningTests(unittest.TestCase):
    def setUp(self):
        self.session = _make_session()

    def test_returns_false_when_process_is_none(self):
        self.session.process = None
        self.assertFalse(self.session.is_running())

    def test_returns_true_when_process_is_alive(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # None means still running
        self.session.process = mock_proc
        self.assertTrue(self.session.is_running())

    def test_returns_false_when_process_has_exited(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0  # exit code 0 means exited
        self.session.process = mock_proc
        self.assertFalse(self.session.is_running())


# ---------------------------------------------------------------------------
# send_command
# ---------------------------------------------------------------------------

class SendCommandTests(unittest.TestCase):
    def setUp(self):
        self.session = _make_session()

    def test_returns_false_when_server_not_running(self):
        self.session._running = False
        self.session.process = None
        result = self.session.send_command("list")
        self.assertFalse(result)

    def test_returns_false_for_blank_command(self):
        self.session._running = True
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        self.session.process = mock_proc
        result = self.session.send_command("   ")
        self.assertFalse(result)

    def test_send_command_broadcasts_with_source(self):
        self.session._running = True
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        self.session.process = mock_proc
        
        cb = MagicMock()
        self.session.add_listener(cb)
        
        with patch("eventlet.tpool.execute"):
            self.session.send_command("list", source="admin")
            
        cb.assert_called_once_with({"line": "> list", "source": "admin"})
        self.assertIn({"line": "> list", "source": "admin"}, self.session.log_history)


# ---------------------------------------------------------------------------
# get_process_info
# ---------------------------------------------------------------------------

class GetProcessInfoTests(unittest.TestCase):
    def setUp(self):
        self.session = _make_session()

    def test_returns_not_running_info_when_stopped(self):
        self.session._running = False
        self.session.process = None
        with patch("utils.getMaxMemoryMB", return_value=1024), \
             patch("utils.getMaxPlayers", return_value=20):
            info = self.session.get_process_info()
        self.assertFalse(info["is_running"])
        self.assertEqual(info["pid"], 0)
        self.assertEqual(info["uptime_seconds"], 0.0)
        self.assertEqual(info["server_id"], self.session.id)

    def test_returns_server_id_matching_name(self):
        s = _make_session(server_id=55, name="my-cool-server")
        s._running = False
        s.process = None
        with patch("utils.getMaxMemoryMB", return_value=512), \
             patch("utils.getMaxPlayers", return_value=10):
            info = s.get_process_info()
        self.assertEqual(info["server_id"], 55)

    def test_returns_running_info_with_pid_when_running(self):
        self.session._running = True
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234
        self.session.process = mock_proc
        self.session.max_memory_mb = 2048
        self.session.max_players = 20
        self.session.started_at = 0.0

        with patch.object(self.session, "_ensure_psutil_proc", return_value=False):
            info = self.session.get_process_info()

        self.assertTrue(info["is_running"])
        self.assertEqual(info["pid"], 1234)


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

class CleanupTests(unittest.TestCase):
    def test_cleanup_releases_ports(self):
        import serverSessionsManager
        s = _make_session()
        serverSessionsManager.usedPorts.add(s.port)
        serverSessionsManager.usedPorts.add(s.rcon_port)

        s.cleanup()

        self.assertNotIn(s.port, serverSessionsManager.usedPorts)
        self.assertNotIn(s.rcon_port, serverSessionsManager.usedPorts)

    def test_cleanup_disconnects_open_rcon_connection(self):
        s = _make_session()
        mock_rcon = MagicMock()
        s._rcon = mock_rcon

        s.cleanup()

        mock_rcon.disconnect.assert_called_once()
        self.assertIsNone(s._rcon)

    def test_cleanup_is_safe_when_no_rcon_connection(self):
        s = _make_session()
        s._rcon = None
        s.cleanup()  # Should not raise


# ---------------------------------------------------------------------------
# Java version check in ServerSession.start()
# ---------------------------------------------------------------------------

class StartJavaVersionCheckTests(unittest.TestCase):
    def setUp(self):
        self.session = _make_session(command="java -jar server.jar")
        self.session.working_dir = "/fake/servers/test"

    def test_returns_false_when_required_java_not_installed(self):
        """start() must return False when the server needs Java 21 but only Java 17 is present."""
        with patch("shutil.which", return_value="/usr/bin/java"), \
             patch("utils.getMcVersion", return_value="1.21.4"), \
             patch("utils.getRequiredJavaVersion", return_value=21), \
             patch("utils.getInstalledJavaMajorVersions", return_value={17}):
            result = self.session.start()
        self.assertFalse(result)

    def test_returns_false_when_no_java_installed(self):
        """start() must return False when no Java is found (original path check)."""
        with patch("shutil.which", return_value=None):
            result = self.session.start()
        self.assertFalse(result)

    def test_proceeds_when_sufficient_java_installed(self):
        """start() should attempt to launch the process when Java is sufficient."""
        with patch("shutil.which", return_value="/usr/bin/java"), \
             patch("utils.getMcVersion", return_value="1.21.4"), \
             patch("utils.getRequiredJavaVersion", return_value=21), \
             patch("utils.getInstalledJavaMajorVersions", return_value={21}), \
             patch("subprocess.Popen") as mock_popen, \
             patch("eventlet.spawn"):
            mock_proc = MagicMock()
            mock_proc.pid = 9999
            mock_popen.return_value = mock_proc
            result = self.session.start()
        self.assertTrue(result)
        mock_popen.assert_called_once()

    def test_proceeds_when_higher_java_installed(self):
        """Java 25 satisfies a server that requires Java 21."""
        with patch("shutil.which", return_value="/usr/bin/java"), \
             patch("utils.getMcVersion", return_value="1.21.4"), \
             patch("utils.getRequiredJavaVersion", return_value=21), \
             patch("utils.getInstalledJavaMajorVersions", return_value={25}), \
             patch("subprocess.Popen") as mock_popen, \
             patch("eventlet.spawn"):
            mock_proc = MagicMock()
            mock_proc.pid = 9999
            mock_popen.return_value = mock_proc
            result = self.session.start()
        self.assertTrue(result)
        mock_popen.assert_called_once()

    def test_skips_java_version_check_when_no_metadata(self):
        """If mineguardian.json is absent, start() skips the version check."""
        with patch("shutil.which", return_value="/usr/bin/java"), \
             patch("utils.getMcVersion", return_value=None), \
             patch("subprocess.Popen") as mock_popen, \
             patch("eventlet.spawn"):
            mock_proc = MagicMock()
            mock_proc.pid = 9999
            mock_popen.return_value = mock_proc
            result = self.session.start()
        self.assertTrue(result)
        mock_popen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
