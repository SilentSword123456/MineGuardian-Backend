"""
Tests for utils.py utility functions.

All file I/O and external calls are mocked so no real filesystem or
network operations are performed.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch, mock_open

import utils


# ---------------------------------------------------------------------------
# getConfig / storeConfig
# ---------------------------------------------------------------------------

class GetConfigTests(unittest.TestCase):
    def test_returns_none_when_config_file_missing(self):
        with patch("utils.os.path.isfile", return_value=False):
            result = utils.getConfig()
        self.assertIsNone(result)

    def test_returns_parsed_json_when_file_exists(self):
        config_data = {"jwtSecretKey": "abc", "rconPassword": "xyz"}
        with patch("utils.os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps(config_data))):
            result = utils.getConfig()
        self.assertEqual(result, config_data)

    def test_returns_none_on_json_decode_error(self):
        with patch("utils.os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data="not valid json")):
            result = utils.getConfig()
        self.assertIsNone(result)


class StoreConfigTests(unittest.TestCase):
    def test_writes_json_to_file(self):
        config_data = {"key": "value"}
        m = mock_open()
        with patch("builtins.open", m):
            utils.storeConfig(config_data)
        handle = m()
        written = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertEqual(json.loads(written), config_data)


# ---------------------------------------------------------------------------
# Key generation helpers
# ---------------------------------------------------------------------------

class GenerateFlaskKeyTests(unittest.TestCase):
    def test_does_nothing_when_config_is_none(self):
        with patch("utils.getConfig", return_value=None), \
             patch("utils.storeConfig") as mock_store:
            utils.generateFlaskKey()
        mock_store.assert_not_called()

    def test_does_not_overwrite_existing_key(self):
        config = {"flaskConfig": {"SECRET_KEY": "existing"}}
        with patch("utils.getConfig", return_value=config), \
             patch("utils.storeConfig") as mock_store:
            utils.generateFlaskKey()
        mock_store.assert_not_called()

    def test_generates_and_stores_new_key_when_missing(self):
        config = {"flaskConfig": {}}
        with patch("utils.getConfig", return_value=config), \
             patch("utils.storeConfig") as mock_store:
            utils.generateFlaskKey()
        mock_store.assert_called_once()
        stored_config = mock_store.call_args[0][0]
        self.assertIn("SECRET_KEY", stored_config["flaskConfig"])
        self.assertTrue(len(stored_config["flaskConfig"]["SECRET_KEY"]) > 0)


class GenerateJWTSecretKeyTests(unittest.TestCase):
    def test_does_nothing_when_config_is_none(self):
        with patch("utils.getConfig", return_value=None), \
             patch("utils.storeConfig") as mock_store:
            utils.generateJWTSecretKey()
        mock_store.assert_not_called()

    def test_does_not_overwrite_existing_key(self):
        config = {"jwtSecretKey": "already-set"}
        with patch("utils.getConfig", return_value=config), \
             patch("utils.storeConfig") as mock_store:
            utils.generateJWTSecretKey()
        mock_store.assert_not_called()

    def test_generates_and_stores_new_key_when_missing(self):
        config = {}
        with patch("utils.getConfig", return_value=config), \
             patch("utils.storeConfig") as mock_store:
            utils.generateJWTSecretKey()
        mock_store.assert_called_once()
        stored = mock_store.call_args[0][0]
        self.assertIn("jwtSecretKey", stored)
        self.assertTrue(len(stored["jwtSecretKey"]) > 0)


class GenerateRconPasswordTests(unittest.TestCase):
    def test_does_nothing_when_config_is_none(self):
        with patch("utils.getConfig", return_value=None), \
             patch("utils.storeConfig") as mock_store:
            utils.generateRconPassword()
        mock_store.assert_not_called()

    def test_does_not_overwrite_existing_password(self):
        config = {"rconPassword": "already-set"}
        with patch("utils.getConfig", return_value=config), \
             patch("utils.storeConfig") as mock_store:
            utils.generateRconPassword()
        mock_store.assert_not_called()

    def test_generates_and_stores_new_password_when_missing(self):
        config = {}
        with patch("utils.getConfig", return_value=config), \
             patch("utils.storeConfig") as mock_store:
            utils.generateRconPassword()
        mock_store.assert_called_once()
        stored = mock_store.call_args[0][0]
        self.assertIn("rconPassword", stored)
        self.assertTrue(len(stored["rconPassword"]) > 0)


# ---------------------------------------------------------------------------
# getMaxPlayers
# ---------------------------------------------------------------------------

class GetMaxPlayersTests(unittest.TestCase):
    def test_returns_20_when_server_path_is_none(self):
        self.assertEqual(utils.getMaxPlayers(None), 20)

    def test_returns_20_when_properties_file_missing(self):
        with patch("utils.os.path.isfile", return_value=False), \
             patch("utils.serverSessionsManager.serverInstances", {}):
            self.assertEqual(utils.getMaxPlayers("/fake/path"), 20)

    def test_parses_max_players_from_properties(self):
        props_content = "server-port=25565\nmax-players=42\n"
        with patch("utils.serverSessionsManager.serverInstances", {}), \
             patch("utils.os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data=props_content)):
            result = utils.getMaxPlayers("/fake/server")
        self.assertEqual(result, 42)

    def test_returns_20_when_max_players_key_absent(self):
        props_content = "server-port=25565\nmotd=My Server\n"
        with patch("utils.serverSessionsManager.serverInstances", {}), \
             patch("utils.os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data=props_content)):
            result = utils.getMaxPlayers("/fake/server")
        self.assertEqual(result, 20)

    def test_returns_cached_value_from_running_server_instance(self):
        mock_server = MagicMock()
        mock_server.working_dir = "/fake/server"
        mock_server.is_running.return_value = True
        mock_server.max_players = 100
        with patch("utils.serverSessionsManager.serverInstances", {"test": mock_server}), \
             patch("utils.os.path.abspath", side_effect=lambda x: x):
            result = utils.getMaxPlayers("/fake/server")
        self.assertEqual(result, 100)


# ---------------------------------------------------------------------------
# getOnlinePlayers
# ---------------------------------------------------------------------------

class GetOnlinePlayersTests(unittest.TestCase):
    def _make_server(self, running=True, rcon_output=None):
        server = MagicMock()
        server.running = running
        server.working_dir = "/fake/server"
        server.send_rcon_command.return_value = rcon_output
        return server

    def test_returns_max_only_when_server_not_running(self):
        with patch("utils.getMaxPlayers", return_value=20):
            result = utils.getOnlinePlayers(None)
        self.assertEqual(result, {"max": 20})

    def test_returns_max_only_when_server_stopped(self):
        server = self._make_server(running=False)
        with patch("utils.getMaxPlayers", return_value=20):
            result = utils.getOnlinePlayers(server)
        self.assertEqual(result, {"max": 20})

    def test_returns_max_only_when_rcon_returns_none(self):
        server = self._make_server(running=True, rcon_output=None)
        with patch("utils.getMaxPlayers", return_value=20):
            result = utils.getOnlinePlayers(server)
        self.assertEqual(result, {"max": 20})

    def test_parses_online_players_correctly(self):
        output = "There are 2 of a max of 20 players online: Steve, Alex"
        server = self._make_server(running=True, rcon_output=output)
        with patch("utils.getMaxPlayers", return_value=20):
            result = utils.getOnlinePlayers(server)
        self.assertEqual(result["online"], 2)
        self.assertEqual(result["max"], 20)
        self.assertIn("Steve", result["players"])
        self.assertIn("Alex", result["players"])

    def test_parses_zero_online_players(self):
        output = "There are 0 of a max of 20 players online: "
        server = self._make_server(running=True, rcon_output=output)
        with patch("utils.getMaxPlayers", return_value=20):
            result = utils.getOnlinePlayers(server)
        self.assertEqual(result["online"], 0)
        self.assertEqual(result["players"], [])

    def test_returns_max_on_exception(self):
        server = self._make_server(running=True)
        server.send_rcon_command.side_effect = Exception("RCON error")
        with patch("utils.getMaxPlayers", return_value=20):
            result = utils.getOnlinePlayers(server)
        self.assertEqual(result, {"max": 20})


# ---------------------------------------------------------------------------
# getLaunchCommand
# ---------------------------------------------------------------------------

class GetLaunchCommandTests(unittest.TestCase):
    def test_returns_command_from_sh_script_on_unix(self):
        with patch("utils.os.name", "posix"), \
             patch("utils.os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data="java -jar server.jar\n")):
            result = utils.getLaunchCommand("/fake/server")
        self.assertEqual(result, "java -jar server.jar")

    def test_returns_command_from_bat_script_on_windows(self):
        with patch("utils.os.name", "nt"), \
             patch("utils.os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data="java -jar server.jar\n")):
            result = utils.getLaunchCommand("/fake/server")
        self.assertEqual(result, "java -jar server.jar")

    def test_returns_none_when_script_missing(self):
        with patch("utils.os.path.isfile", return_value=False):
            result = utils.getLaunchCommand("/fake/server")
        self.assertIsNone(result)

    def test_returns_none_on_file_read_error(self):
        with patch("utils.os.path.isfile", return_value=True), \
             patch("builtins.open", side_effect=IOError("read error")):
            result = utils.getLaunchCommand("/fake/server")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# getMaxMemoryMB
# ---------------------------------------------------------------------------

class GetMaxMemoryMBTests(unittest.TestCase):
    def test_returns_negative_one_when_path_is_none(self):
        self.assertEqual(utils.getMaxMemoryMB(None), -1)

    def test_returns_negative_one_when_launch_command_missing(self):
        with patch("utils.serverSessionsManager.serverInstances", {}), \
             patch("utils.getLaunchCommand", return_value=None):
            result = utils.getMaxMemoryMB("/fake/server")
        self.assertEqual(result, -1)

    def test_parses_xmx_in_megabytes(self):
        cmd = "java -Xmx2048M -jar server.jar nogui"
        with patch("utils.serverSessionsManager.serverInstances", {}), \
             patch("utils.getLaunchCommand", return_value=cmd):
            result = utils.getMaxMemoryMB("/fake/server")
        self.assertEqual(result, 2048)

    def test_parses_xmx_in_gigabytes(self):
        cmd = "java -Xmx4G -jar server.jar nogui"
        with patch("utils.serverSessionsManager.serverInstances", {}), \
             patch("utils.getLaunchCommand", return_value=cmd):
            result = utils.getMaxMemoryMB("/fake/server")
        self.assertEqual(result, 4096)

    def test_parses_xmx_in_bytes(self):
        cmd = "java -Xmx1073741824 -jar server.jar nogui"
        with patch("utils.serverSessionsManager.serverInstances", {}), \
             patch("utils.getLaunchCommand", return_value=cmd):
            result = utils.getMaxMemoryMB("/fake/server")
        self.assertEqual(result, 1024)

    def test_returns_default_when_no_xmx_flag(self):
        cmd = "java -jar server.jar nogui"
        with patch("utils.serverSessionsManager.serverInstances", {}), \
             patch("utils.getLaunchCommand", return_value=cmd):
            result = utils.getMaxMemoryMB("/fake/server")
        self.assertEqual(result, 1024)

    def test_returns_cached_value_from_running_server_instance(self):
        mock_server = MagicMock()
        mock_server.working_dir = "/fake/server"
        mock_server.is_running.return_value = True
        mock_server.max_memory_mb = 4096
        with patch("utils.serverSessionsManager.serverInstances", {"test": mock_server}), \
             patch("utils.os.path.abspath", side_effect=lambda x: x):
            result = utils.getMaxMemoryMB("/fake/server")
        self.assertEqual(result, 4096)


# ---------------------------------------------------------------------------
# patchServerProperties
# ---------------------------------------------------------------------------

class PatchServerPropertiesTests(unittest.TestCase):
    def test_raises_on_empty_path(self):
        with self.assertRaises(ValueError):
            utils.patchServerProperties("", {"key": "val"})

    def test_raises_when_path_is_none(self):
        with self.assertRaises((ValueError, TypeError)):
            utils.patchServerProperties(None, {"key": "val"})

    def test_raises_when_path_is_outside_servers_dir(self):
        with self.assertRaises(ValueError):
            utils.patchServerProperties("/etc/passwd_dir", {"key": "val"})

    def test_creates_properties_when_file_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            servers_dir = os.path.join(tmpdir, "servers")
            server_dir = os.path.join(servers_dir, "myserver")
            os.makedirs(server_dir)

            with patch("utils.os.path.abspath", side_effect=lambda p: os.path.abspath(p.replace("servers", servers_dir.rstrip("/servers").rstrip("\\servers")))):
                # Use the actual filesystem: patch only the "servers" base path resolution
                # Simpler: just work with the real temp dir
                pass

            # Directly patch os.path.abspath to return our tmpdir paths
            original_abspath = os.path.abspath

            def fake_abspath(p):
                if p == "servers":
                    return servers_dir
                return original_abspath(p)

            with patch("utils.os.path.abspath", side_effect=fake_abspath):
                utils.patchServerProperties(server_dir, {"server-port": "25566"})

            props_path = os.path.join(server_dir, "server.properties")
            self.assertTrue(os.path.isfile(props_path))
            with open(props_path) as f:
                content = f.read()
            self.assertIn("server-port=25566", content)

    def test_updates_existing_property_in_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            servers_dir = os.path.join(tmpdir, "servers")
            server_dir = os.path.join(servers_dir, "myserver")
            os.makedirs(server_dir)
            props_path = os.path.join(server_dir, "server.properties")

            with open(props_path, "w") as f:
                f.write("server-port=25565\nmax-players=20\n")

            original_abspath = os.path.abspath

            def fake_abspath(p):
                if p == "servers":
                    return servers_dir
                return original_abspath(p)

            with patch("utils.os.path.abspath", side_effect=fake_abspath):
                utils.patchServerProperties(server_dir, {"server-port": "25566"})

            with open(props_path) as f:
                content = f.read()
            self.assertIn("server-port=25566", content)
            self.assertIn("max-players=20", content)
            self.assertNotIn("server-port=25565", content)

    def test_appends_new_property_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            servers_dir = os.path.join(tmpdir, "servers")
            server_dir = os.path.join(servers_dir, "myserver")
            os.makedirs(server_dir)
            props_path = os.path.join(server_dir, "server.properties")

            with open(props_path, "w") as f:
                f.write("server-port=25565\n")

            original_abspath = os.path.abspath

            def fake_abspath(p):
                if p == "servers":
                    return servers_dir
                return original_abspath(p)

            with patch("utils.os.path.abspath", side_effect=fake_abspath):
                utils.patchServerProperties(server_dir, {"rcon.port": "25575"})

            with open(props_path) as f:
                content = f.read()
            self.assertIn("rcon.port=25575", content)
            self.assertIn("server-port=25565", content)

    def test_preserves_comments_in_properties_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            servers_dir = os.path.join(tmpdir, "servers")
            server_dir = os.path.join(servers_dir, "myserver")
            os.makedirs(server_dir)
            props_path = os.path.join(server_dir, "server.properties")

            with open(props_path, "w") as f:
                f.write("#This is a comment\nserver-port=25565\n")

            original_abspath = os.path.abspath

            def fake_abspath(p):
                if p == "servers":
                    return servers_dir
                return original_abspath(p)

            with patch("utils.os.path.abspath", side_effect=fake_abspath):
                utils.patchServerProperties(server_dir, {"server-port": "25566"})

            with open(props_path) as f:
                content = f.read()
            self.assertIn("#This is a comment", content)
            self.assertIn("server-port=25566", content)

    def test_raises_when_server_dir_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            servers_dir = os.path.join(tmpdir, "servers")
            os.makedirs(servers_dir)
            nonexistent_dir = os.path.join(servers_dir, "ghost")

            original_abspath = os.path.abspath

            def fake_abspath(p):
                if p == "servers":
                    return servers_dir
                return original_abspath(p)

            with patch("utils.os.path.abspath", side_effect=fake_abspath):
                with self.assertRaises(ValueError):
                    utils.patchServerProperties(nonexistent_dir, {"key": "val"})


# ---------------------------------------------------------------------------
# getNewPort
# ---------------------------------------------------------------------------

class GetNewPortTests(unittest.TestCase):
    def test_raises_on_invalid_type(self):
        with self.assertRaises(ValueError):
            utils.getNewPort(set(), type="invalid")

    def test_returns_base_port_25565_for_server(self):
        with patch("utils.serverSessionsManager.usedPorts", set()), \
             patch("utils.getNewPort.__wrapped__" if hasattr(utils.getNewPort, "__wrapped__") else "builtins.id", create=True):
            # Patch the inner socket check so port is always free
            with patch("socket.socket") as mock_sock_cls:
                mock_sock = MagicMock()
                mock_sock.__enter__ = lambda s: s
                mock_sock.__exit__ = MagicMock(return_value=False)
                mock_sock_cls.return_value = mock_sock
                result = utils.getNewPort(set(), type="server")
        self.assertEqual(result, 25565)

    def test_returns_base_port_25575_for_rcon(self):
        with patch("socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock.__enter__ = lambda s: s
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_sock_cls.return_value = mock_sock
            result = utils.getNewPort(set(), type="rcon")
        self.assertEqual(result, 25575)

    def test_skips_already_used_port(self):
        used = {25565}
        with patch("socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock.__enter__ = lambda s: s
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_sock_cls.return_value = mock_sock
            result = utils.getNewPort(used, type="server")
        self.assertEqual(result, 25566)


# ---------------------------------------------------------------------------
# getServerStats
# ---------------------------------------------------------------------------

class GetServerStatsTests(unittest.TestCase):
    def _make_server_instance(self):
        server = MagicMock()
        server.last_stats = None
        server.last_stats_time = 0
        server._stats_lock = None
        server.working_dir = "/fake/server"
        server.get_cpu_usage_percent.return_value = 5.0
        server.get_memory_usage_mb.return_value = 256.0
        return server

    def test_returns_fresh_stats_when_force_is_true(self):
        server = self._make_server_instance()
        with patch("utils.getMaxMemoryMB", return_value=1024), \
             patch("utils.getOnlinePlayers", return_value={"online": 1, "max": 20}):
            stats = utils.getServerStats(server, force=True)
        self.assertEqual(stats["cpu_usage_percent"], 5.0)
        self.assertEqual(stats["memory_usage_mb"], 256.0)
        self.assertEqual(stats["max_memory_mb"], 1024)

    def test_returns_cached_stats_within_ttl(self):
        import time
        server = self._make_server_instance()
        cached = {"cpu_usage_percent": 99.0, "memory_usage_mb": 999.0, "max_memory_mb": 2048}
        server.last_stats = cached
        server.last_stats_time = time.time()  # Very recent

        result = utils.getServerStats(server, force=False)
        self.assertEqual(result, cached)

    def test_collects_new_stats_when_cache_is_stale(self):
        server = self._make_server_instance()
        server.last_stats = {"cpu_usage_percent": 99.0}
        server.last_stats_time = 0  # Very old
        with patch("utils.getMaxMemoryMB", return_value=1024), \
             patch("utils.getOnlinePlayers", return_value={"online": 0, "max": 20}):
            stats = utils.getServerStats(server, force=False)
        self.assertEqual(stats["cpu_usage_percent"], 5.0)


# ---------------------------------------------------------------------------
# getGlobalStats
# ---------------------------------------------------------------------------

class GetGlobalStatsTests(unittest.TestCase):
    def test_returns_zero_stats_when_no_servers_running(self):
        server = MagicMock()
        server.is_running.return_value = False
        result = utils.getGlobalStats([server])
        self.assertEqual(result["cpu_usage_percent"], 0.0)
        self.assertEqual(result["memory_usage_mb"], 0.0)
        self.assertEqual(result["online_players"]["online"], 0)

    def test_aggregates_stats_from_multiple_running_servers(self):
        server1 = MagicMock()
        server1.is_running.return_value = True
        server2 = MagicMock()
        server2.is_running.return_value = True

        stats1 = {
            "cpu_usage_percent": 10.0,
            "memory_usage_mb": 512.0,
            "max_memory_mb": 1024,
            "online_players": {"online": 3, "max": 20, "players": ["Steve", "Alex", "Notch"]},
        }
        stats2 = {
            "cpu_usage_percent": 5.0,
            "memory_usage_mb": 256.0,
            "max_memory_mb": 2048,
            "online_players": {"online": 1, "max": 10, "players": ["Herobrine"]},
        }

        with patch("utils.getServerStats", side_effect=[stats1, stats2]):
            result = utils.getGlobalStats([server1, server2])

        self.assertAlmostEqual(result["cpu_usage_percent"], 15.0)
        self.assertAlmostEqual(result["memory_usage_mb"], 768.0)
        self.assertEqual(result["max_memory_mb"], 3072)
        self.assertEqual(result["online_players"]["online"], 4)
        self.assertEqual(result["online_players"]["max"], 30)
        self.assertIn("Steve", result["online_players"]["players"])
        self.assertIn("Herobrine", result["online_players"]["players"])

    def test_skips_stopped_servers(self):
        running = MagicMock()
        running.is_running.return_value = True
        stopped = MagicMock()
        stopped.is_running.return_value = False

        stats = {
            "cpu_usage_percent": 8.0,
            "memory_usage_mb": 128.0,
            "max_memory_mb": 512,
            "online_players": {"online": 2, "max": 10, "players": ["Player1", "Player2"]},
        }

        with patch("utils.getServerStats", return_value=stats):
            result = utils.getGlobalStats([running, stopped])

        self.assertAlmostEqual(result["cpu_usage_percent"], 8.0)
        self.assertEqual(result["online_players"]["max"], 10)


# ---------------------------------------------------------------------------
# getRequiredJavaVersion
# ---------------------------------------------------------------------------

class GetRequiredJavaVersionTests(unittest.TestCase):
    def test_1_21_requires_java_21(self):
        self.assertEqual(utils.getRequiredJavaVersion("1.21"), 21)

    def test_1_21_4_requires_java_21(self):
        self.assertEqual(utils.getRequiredJavaVersion("1.21.4"), 21)

    def test_1_20_5_requires_java_21(self):
        self.assertEqual(utils.getRequiredJavaVersion("1.20.5"), 21)

    def test_1_20_4_requires_java_17(self):
        self.assertEqual(utils.getRequiredJavaVersion("1.20.4"), 17)

    def test_1_18_requires_java_17(self):
        self.assertEqual(utils.getRequiredJavaVersion("1.18"), 17)

    def test_1_17_requires_java_17(self):
        self.assertEqual(utils.getRequiredJavaVersion("1.17"), 17)

    def test_1_16_5_requires_java_8(self):
        self.assertEqual(utils.getRequiredJavaVersion("1.16.5"), 8)

    def test_1_8_requires_java_8(self):
        self.assertEqual(utils.getRequiredJavaVersion("1.8"), 8)

    def test_unknown_version_returns_8(self):
        self.assertEqual(utils.getRequiredJavaVersion("unknown"), 8)

    def test_empty_string_returns_8(self):
        self.assertEqual(utils.getRequiredJavaVersion(""), 8)

    def test_version_with_rc_suffix(self):
        # "1.21-rc1" should parse as 1.21 → Java 21
        self.assertEqual(utils.getRequiredJavaVersion("1.21-rc1"), 21)


# ---------------------------------------------------------------------------
# getInstalledJavaMajorVersions / _getJavaMajorVersion
# ---------------------------------------------------------------------------

class GetInstalledJavaMajorVersionsTests(unittest.TestCase):
    def test_returns_version_from_path_java(self):
        with patch("shutil.which", return_value="/usr/bin/java"), \
             patch("utils.os.path.isdir", return_value=False), \
             patch("utils._getJavaMajorVersion", return_value=17):
            result = utils.getInstalledJavaMajorVersions()
        self.assertIn(17, result)

    def test_returns_empty_set_when_no_java_found(self):
        with patch("shutil.which", return_value=None), \
             patch("utils.os.path.isdir", return_value=False):
            result = utils.getInstalledJavaMajorVersions()
        self.assertEqual(result, set())

    def test_discovers_jvms_under_usr_lib_jvm(self):
        with patch("shutil.which", return_value=None), \
             patch("utils.os.path.isdir", return_value=True), \
             patch("utils.os.listdir", return_value=["temurin-25"]), \
             patch("utils.os.path.isfile", return_value=True), \
             patch("utils.os.access", return_value=True), \
             patch("utils._getJavaMajorVersion", return_value=25):
            result = utils.getInstalledJavaMajorVersions()
        self.assertIn(25, result)

    def test_ignores_jvm_entries_without_java_binary(self):
        with patch("shutil.which", return_value=None), \
             patch("utils.os.path.isdir", return_value=True), \
             patch("utils.os.listdir", return_value=["some-dir"]), \
             patch("utils.os.path.isfile", return_value=False):
            result = utils.getInstalledJavaMajorVersions()
        self.assertEqual(result, set())


class GetJavaMajorVersionTests(unittest.TestCase):
    def _make_completed_process(self, stderr):
        result = MagicMock()
        result.stderr = stderr
        result.stdout = ""
        return result

    def test_parses_java_17_version_string(self):
        output = 'openjdk version "17.0.9" 2023-10-17'
        with patch("subprocess.run", return_value=self._make_completed_process(output)):
            self.assertEqual(utils._getJavaMajorVersion("java"), 17)

    def test_parses_java_25_version_string(self):
        output = 'openjdk version "25" 2025-09-16'
        with patch("subprocess.run", return_value=self._make_completed_process(output)):
            self.assertEqual(utils._getJavaMajorVersion("java"), 25)

    def test_parses_old_java_8_version_string(self):
        output = 'java version "1.8.0_392"'
        with patch("subprocess.run", return_value=self._make_completed_process(output)):
            self.assertEqual(utils._getJavaMajorVersion("java"), 8)

    def test_returns_none_when_subprocess_raises(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            self.assertIsNone(utils._getJavaMajorVersion("/nonexistent/java"))

    def test_returns_none_on_unrecognised_output(self):
        with patch("subprocess.run", return_value=self._make_completed_process("not java output")):
            self.assertIsNone(utils._getJavaMajorVersion("java"))


# ---------------------------------------------------------------------------
# getMcVersion / saveMcVersion
# ---------------------------------------------------------------------------

class GetMcVersionTests(unittest.TestCase):
    def test_returns_none_when_file_missing(self):
        with patch("utils.os.path.isfile", return_value=False):
            self.assertIsNone(utils.getMcVersion("/fake/server"))

    def test_returns_version_from_metadata_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = {"mc_version": "1.21.4"}
            import json as _json
            with open(os.path.join(tmpdir, "mineguardian.json"), "w") as f:
                _json.dump(meta, f)
            result = utils.getMcVersion(tmpdir)
        self.assertEqual(result, "1.21.4")

    def test_returns_none_on_invalid_json(self):
        with patch("utils.os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data="bad json{")):
            result = utils.getMcVersion("/fake/server")
        self.assertIsNone(result)


class SaveMcVersionTests(unittest.TestCase):
    def _mock_abspath_for_tmpdir(self, tmpdir):
        """Return a side-effect for os.path.abspath that maps 'servers' → tmpdir/servers.

        Captures the real ``os.path.abspath`` before the patch is applied to
        avoid infinite recursion when the fallback calls the function.
        """
        servers_dir = os.path.join(tmpdir, "servers")
        _real_abspath = os.path.abspath  # saved before patch is activated

        def mock_abspath(p):
            if p == "servers":
                return servers_dir
            return _real_abspath(p)

        return mock_abspath

    def test_writes_metadata_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server_dir = os.path.join(tmpdir, "servers", "test-server")
            os.makedirs(server_dir)

            with patch("utils.os.path.abspath",
                       side_effect=self._mock_abspath_for_tmpdir(tmpdir)):
                utils.saveMcVersion(server_dir, "1.18.2")

            meta_path = os.path.join(server_dir, "mineguardian.json")
            self.assertTrue(os.path.isfile(meta_path))
            import json as _json
            with open(meta_path) as f:
                data = _json.load(f)
            self.assertEqual(data["mc_version"], "1.18.2")

    def test_does_not_raise_on_write_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server_dir = os.path.join(tmpdir, "servers", "test-server")
            os.makedirs(server_dir)
            mock_fn = self._mock_abspath_for_tmpdir(tmpdir)

            with patch("utils.os.path.abspath", side_effect=mock_fn), \
                 patch("builtins.open", side_effect=OSError("disk full")):
                utils.saveMcVersion(server_dir, "1.21")  # Should not raise

    def test_refuses_write_outside_servers_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_fn = self._mock_abspath_for_tmpdir(tmpdir)
            with patch("utils.os.path.abspath", side_effect=mock_fn), \
                 patch("builtins.open") as mock_open_fn:
                utils.saveMcVersion("/tmp/evil/path", "1.21")
            mock_open_fn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
