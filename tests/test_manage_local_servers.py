"""
Tests for manageLocalServers.py.

External HTTP calls and filesystem operations are mocked.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch, mock_open, call

import manageLocalServers


# ---------------------------------------------------------------------------
# addAcceptEula
# ---------------------------------------------------------------------------

class AddAcceptEulaTests(unittest.TestCase):
    def test_writes_eula_true_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manageLocalServers.addAcceptEula(tmpdir)
            eula_path = os.path.join(tmpdir, "eula.txt")
            self.assertTrue(os.path.isfile(eula_path))
            with open(eula_path) as f:
                content = f.read()
            self.assertIn("eula=true", content)


# ---------------------------------------------------------------------------
# getAvailableVersions
# ---------------------------------------------------------------------------

class GetAvailableVersionsTests(unittest.TestCase):
    def _mock_version_manifest(self, versions):
        """Build a minimal Mojang version manifest dict."""
        return {
            "latest": {"release": versions[0]["id"] if versions else "latest"},
            "versions": versions,
        }

    def test_returns_error_for_spigot(self):
        result = manageLocalServers.getAvailableVersions("spigot")
        self.assertIn("error", result)

    def test_returns_error_for_invalid_software(self):
        result = manageLocalServers.getAvailableVersions("forge")
        self.assertIn("error", result)

    def test_returns_versions_list_for_vanilla(self):
        manifest = self._mock_version_manifest([
            {"id": "1.21.1", "type": "release"},
            {"id": "1.20.4", "type": "release"},
            {"id": "1.20.4-rc1", "type": "snapshot"},
        ])
        mock_response = MagicMock()
        mock_response.json.return_value = manifest
        mock_response.raise_for_status = MagicMock()

        with patch("manageLocalServers.requests.get", return_value=mock_response):
            result = manageLocalServers.getAvailableVersions("vanilla")

        self.assertIn("versions", result)
        self.assertIn("latest", result["versions"])
        self.assertIn("1.21.1", result["versions"])
        self.assertIn("1.20.4", result["versions"])
        # Snapshots should be excluded
        self.assertNotIn("1.20.4-rc1", result["versions"])

    def test_returns_error_when_request_fails(self):
        import requests
        with patch("manageLocalServers.requests.get", side_effect=requests.exceptions.RequestException("network error")):
            result = manageLocalServers.getAvailableVersions("vanilla")
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# installMinecraftServer
# ---------------------------------------------------------------------------

class InstallMinecraftServerTests(unittest.TestCase):
    def test_returns_error_for_invalid_software(self):
        result = manageLocalServers.installMinecraftServer(
            serverSoftware="forge",
            serverVersion="1.21",
            serverName="test-server",
        )
        self.assertIn("error", result)

    def test_returns_error_for_spigot(self):
        with patch("manageLocalServers.getLocalServers", return_value=[]):
            result = manageLocalServers.installMinecraftServer(
                serverSoftware="spigot",
                serverVersion="1.21",
                serverName="test-server",
            )
        self.assertIn("error", result)

    def test_returns_error_when_server_already_exists(self):
        with patch("manageLocalServers.getLocalServers", return_value=["existing-server"]):
            result = manageLocalServers.installMinecraftServer(
                serverSoftware="vanilla",
                serverVersion="1.21",
                serverName="existing-server",
            )
        self.assertIn("error", result)
        self.assertIn("already exists", result["error"])

    def test_returns_warning_when_eula_not_accepted(self):
        manifest = {
            "latest": {"release": "1.21.1"},
            "versions": [{"id": "1.21.1", "url": "https://example.com/1.21.1.json"}],
        }
        version_info = {"downloads": {"server": {"url": "https://example.com/server.jar"}}}

        mock_manifest_response = MagicMock()
        mock_manifest_response.json.return_value = manifest
        mock_manifest_response.raise_for_status = MagicMock()

        mock_version_response = MagicMock()
        mock_version_response.json.return_value = version_info
        mock_version_response.raise_for_status = MagicMock()

        mock_jar_response = MagicMock()
        mock_jar_response.raise_for_status = MagicMock()
        mock_jar_response.iter_content.return_value = [b"fake-jar-data"]

        with patch("manageLocalServers.getLocalServers", return_value=[]), \
             patch("manageLocalServers.requests.get", side_effect=[
                 mock_manifest_response,
                 mock_version_response,
                 mock_jar_response,
             ]), \
             patch("manageLocalServers.downloadFile"), \
             patch("manageLocalServers.createRunScript"):
            result = manageLocalServers.installMinecraftServer(
                serverSoftware="vanilla",
                serverVersion="1.21.1",
                serverName="test-server",
                acceptEula=False,
            )

        self.assertIn("warning", result)

    def test_returns_true_when_eula_accepted(self):
        manifest = {
            "latest": {"release": "1.21.1"},
            "versions": [{"id": "1.21.1", "url": "https://example.com/1.21.1.json"}],
        }
        version_info = {"downloads": {"server": {"url": "https://example.com/server.jar"}}}

        mock_manifest = MagicMock()
        mock_manifest.json.return_value = manifest
        mock_manifest.raise_for_status = MagicMock()

        mock_version = MagicMock()
        mock_version.json.return_value = version_info
        mock_version.raise_for_status = MagicMock()

        with patch("manageLocalServers.getLocalServers", return_value=[]), \
             patch("manageLocalServers.requests.get", side_effect=[mock_manifest, mock_version]), \
             patch("manageLocalServers.downloadFile"), \
             patch("manageLocalServers.createRunScript"), \
             patch("manageLocalServers.addAcceptEula") as mock_accept:
            result = manageLocalServers.installMinecraftServer(
                serverSoftware="vanilla",
                serverVersion="1.21.1",
                serverName="new-server",
                acceptEula=True,
            )

        self.assertTrue(result)
        mock_accept.assert_called_once()

    def test_returns_error_when_version_not_found(self):
        manifest = {
            "latest": {"release": "1.21.1"},
            "versions": [{"id": "1.21.1", "url": "https://example.com/1.21.1.json"}],
        }
        mock_response = MagicMock()
        mock_response.json.return_value = manifest
        mock_response.raise_for_status = MagicMock()

        with patch("manageLocalServers.getLocalServers", return_value=[]), \
             patch("manageLocalServers.requests.get", return_value=mock_response):
            result = manageLocalServers.installMinecraftServer(
                serverSoftware="vanilla",
                serverVersion="9.99.99",
                serverName="new-server",
            )

        self.assertIn("error", result)
        self.assertIn("not found", result["error"])

    def test_uses_latest_version_when_specified(self):
        manifest = {
            "latest": {"release": "1.21.1"},
            "versions": [{"id": "1.21.1", "url": "https://example.com/1.21.1.json"}],
        }
        version_info = {"downloads": {"server": {"url": "https://example.com/server.jar"}}}

        mock_manifest = MagicMock()
        mock_manifest.json.return_value = manifest
        mock_manifest.raise_for_status = MagicMock()

        mock_version = MagicMock()
        mock_version.json.return_value = version_info
        mock_version.raise_for_status = MagicMock()

        with patch("manageLocalServers.getLocalServers", return_value=[]), \
             patch("manageLocalServers.requests.get", side_effect=[mock_manifest, mock_version]) as mock_get, \
             patch("manageLocalServers.downloadFile"), \
             patch("manageLocalServers.createRunScript"), \
             patch("manageLocalServers.addAcceptEula"):
            result = manageLocalServers.installMinecraftServer(
                serverSoftware="vanilla",
                serverVersion="latest",
                serverName="new-server",
                acceptEula=True,
            )

        # The second call should use the resolved URL for 1.21.1
        self.assertTrue(result)
        mock_get.assert_any_call("https://example.com/1.21.1.json")


# ---------------------------------------------------------------------------
# uninstallMinecraftServer
# ---------------------------------------------------------------------------

class UninstallMinecraftServerTests(unittest.TestCase):
    def test_returns_error_when_server_path_does_not_exist(self):
        with patch("manageLocalServers.os.path.exists", return_value=False):
            result = manageLocalServers.uninstallMinecraftServer("ghost-server")
        self.assertIn("error", result)
        self.assertIn("does not exist", result["error"])

    def test_returns_error_when_server_is_running(self):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True

        with patch("manageLocalServers.os.path.exists", return_value=True), \
             patch("manageLocalServers.serverSessionsManager.serverInstances", {"running-server": mock_instance}):
            result = manageLocalServers.uninstallMinecraftServer("running-server")

        self.assertIn("error", result)
        self.assertIn("currently running", result["error"])

    def test_removes_instance_and_deletes_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server_name = "delete-me"
            server_path = os.path.join(tmpdir, "servers", server_name)
            os.makedirs(server_path)
            # Create a file to test deletion
            with open(os.path.join(server_path, "server.jar"), "w") as f:
                f.write("fake jar")

            mock_instance = MagicMock()
            mock_instance.is_running.return_value = False

            server_instances = {server_name: mock_instance}

            def fake_exists(p):
                return os.path.exists(p.replace("servers", os.path.join(tmpdir, "servers")))

            original_join = os.path.join

            def fake_join(*args):
                if args[0] == "servers" and len(args) == 2:
                    return original_join(tmpdir, "servers", args[1])
                return original_join(*args)

            with patch("manageLocalServers.os.path.exists", side_effect=lambda p: True), \
                 patch("manageLocalServers.serverSessionsManager.serverInstances", server_instances), \
                 patch("manageLocalServers.os.path.join", side_effect=fake_join), \
                 patch("manageLocalServers.os.walk", return_value=[
                     (server_path, [], ["server.jar"]),
                 ]), \
                 patch("manageLocalServers.os.remove") as mock_remove, \
                 patch("manageLocalServers.os.rmdir") as mock_rmdir:
                result = manageLocalServers.uninstallMinecraftServer(server_name)

            self.assertTrue(result)
            mock_instance.cleanup.assert_called_once()
            self.assertNotIn(server_name, server_instances)


            self.assertTrue(result)
            mock_instance.cleanup.assert_called_once()
            self.assertNotIn(server_name, server_instances)


# ---------------------------------------------------------------------------
# Java version check during installMinecraftServer
# ---------------------------------------------------------------------------

class InstallMinecraftServerJavaCheckTests(unittest.TestCase):
    """Verify that install is blocked when the required Java version is absent."""

    def _manifest_for(self, version_id):
        return {
            "latest": {"release": version_id},
            "versions": [{"id": version_id, "url": f"https://example.com/{version_id}.json"}],
        }

    def _mock_manifest_response(self, manifest):
        m = MagicMock()
        m.json.return_value = manifest
        m.raise_for_status = MagicMock()
        return m

    def test_returns_error_when_java_not_sufficient(self):
        """Installing a 1.21 server without Java 21 should return an error."""
        manifest = self._manifest_for("1.21.1")
        with patch("manageLocalServers.getLocalServers", return_value=[]), \
             patch("manageLocalServers.requests.get",
                   return_value=self._mock_manifest_response(manifest)), \
             patch("manageLocalServers.getInstalledJavaMajorVersions", return_value={17}):
            result = manageLocalServers.installMinecraftServer(
                serverSoftware="vanilla",
                serverVersion="1.21.1",
                serverName="new-server",
                acceptEula=True,
            )
        self.assertIn("error", result)
        self.assertIn("Java 21", result["error"])

    def test_proceeds_when_java_is_sufficient(self):
        """Installing a 1.21 server with Java 21 should succeed."""
        manifest = self._manifest_for("1.21.1")
        version_info = {"downloads": {"server": {"url": "https://example.com/server.jar"}}}

        mock_manifest = self._mock_manifest_response(manifest)
        mock_version = MagicMock()
        mock_version.json.return_value = version_info
        mock_version.raise_for_status = MagicMock()

        with patch("manageLocalServers.getLocalServers", return_value=[]), \
             patch("manageLocalServers.requests.get",
                   side_effect=[mock_manifest, mock_version]), \
             patch("manageLocalServers.getInstalledJavaMajorVersions", return_value={21}), \
             patch("manageLocalServers.downloadFile"), \
             patch("manageLocalServers.saveMcVersion"), \
             patch("manageLocalServers.createRunScript"), \
             patch("manageLocalServers.addAcceptEula"):
            result = manageLocalServers.installMinecraftServer(
                serverSoftware="vanilla",
                serverVersion="1.21.1",
                serverName="new-server",
                acceptEula=True,
            )
        self.assertTrue(result)

    def test_proceeds_with_higher_java_than_required(self):
        """Java 25 should satisfy a server that requires Java 21."""
        manifest = self._manifest_for("1.21.1")
        version_info = {"downloads": {"server": {"url": "https://example.com/server.jar"}}}

        mock_manifest = self._mock_manifest_response(manifest)
        mock_version = MagicMock()
        mock_version.json.return_value = version_info
        mock_version.raise_for_status = MagicMock()

        with patch("manageLocalServers.getLocalServers", return_value=[]), \
             patch("manageLocalServers.requests.get",
                   side_effect=[mock_manifest, mock_version]), \
             patch("manageLocalServers.getInstalledJavaMajorVersions", return_value={25}), \
             patch("manageLocalServers.downloadFile"), \
             patch("manageLocalServers.saveMcVersion"), \
             patch("manageLocalServers.createRunScript"), \
             patch("manageLocalServers.addAcceptEula"):
            result = manageLocalServers.installMinecraftServer(
                serverSoftware="vanilla",
                serverVersion="1.21.1",
                serverName="new-server",
                acceptEula=True,
            )
        self.assertTrue(result)

    def test_saves_mc_version_metadata_on_success(self):
        """mineguardian.json should be written with the resolved version."""
        manifest = self._manifest_for("1.18.2")
        version_info = {"downloads": {"server": {"url": "https://example.com/server.jar"}}}

        mock_manifest = self._mock_manifest_response(manifest)
        mock_version = MagicMock()
        mock_version.json.return_value = version_info
        mock_version.raise_for_status = MagicMock()

        with patch("manageLocalServers.getLocalServers", return_value=[]), \
             patch("manageLocalServers.requests.get",
                   side_effect=[mock_manifest, mock_version]), \
             patch("manageLocalServers.getInstalledJavaMajorVersions", return_value={17}), \
             patch("manageLocalServers.downloadFile"), \
             patch("manageLocalServers.saveMcVersion") as mock_save, \
             patch("manageLocalServers.createRunScript"), \
             patch("manageLocalServers.addAcceptEula"):
            manageLocalServers.installMinecraftServer(
                serverSoftware="vanilla",
                serverVersion="1.18.2",
                serverName="new-server",
                acceptEula=True,
            )
        mock_save.assert_called_once()
        _, saved_version = mock_save.call_args[0]
        self.assertEqual(saved_version, "1.18.2")


if __name__ == "__main__":
    unittest.main()
