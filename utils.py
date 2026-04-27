from __future__ import annotations
import os
import re
import secrets
import questionary
import requests
import json
import time
import serverSessionsManager

def getRequiredJavaVersion(mcVersion: str) -> int:
    try:
        parts = tuple(int(re.match(r"(\d+)", s).group(1)) for s in mcVersion.split(".") if re.match(r"\d", s))
    except Exception:
        return 8

    if parts >= (26, 1):   return 25
    if parts >= (1, 20, 5): return 21
    if parts >= (1, 18):    return 17
    if parts >= (1, 17):    return 16
    return 8


def getInstalledJavaMajorVersions() -> set[int]:
    config = getConfig()
    if not config:
        return set()
    return {
        int(v)
        for v, path in config.get("javaRuntimes", {}).items()
        if path and validateJavaRuntime(path, int(v))
    }

def validateJavaRuntime(javaPath: str, expectedMajorVersion: int) -> bool:
    import subprocess, shutil

    if not javaPath or not javaPath.strip():
        return False

    # Check if it's on PATH or a valid file path
    resolved = shutil.which(javaPath)
    if resolved is None and not os.path.isfile(javaPath):
        return False

    try:
        result = subprocess.run(
            [javaPath, "-version"],
            capture_output=True, text=True, timeout=5
        )
        output = result.stderr or result.stdout
        match = re.search(r'version "(\d+)(?:\.(\d+))?', output)
        if not match:
            return False

        major = int(match.group(1))
        if major == 1:
            major = int(match.group(2))

        return major == expectedMajorVersion
    except Exception:
        return False



def displayTitle():

    print("\n" + "="*50)
    print("MineGuardian Backend CLI")
    print("="*50 + "\n")


def downloadFile(url, dest):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(dest), exist_ok=True)

        with open(dest, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        # print(f"Downloaded file to {dest}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file from {url}: {e}")

def getConfig():
    if(not os.path.isfile("config.json")):
        print("Configuration file not found.")
        return None
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            return config
    except json.JSONDecodeError as e:
        print(f"Error reading configuration file: {e}")
        return None

def storeConfig(config):
    try:
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving configuration file: {e}")

def generateFlaskKey():
    config = getConfig()
    if config is None:
        return

    if config.get('flaskConfig', {}).get('SECRET_KEY'):
        return

    secretKey = secrets.token_urlsafe(32)
    config['flaskConfig']['SECRET_KEY'] = secretKey

    storeConfig(config)
def generateJWTSecretKey():
    config = getConfig()
    if config is None:
        return
    if config.get('jwtSecretKey'):
        return

    jwtSecretKey = secrets.token_urlsafe(64)
    config['jwtSecretKey'] = jwtSecretKey
    storeConfig(config)

def generateRconPassword():
    """Generate a random RCON password and store it in config.json (once)."""
    config = getConfig()
    if config is None:
        return

    if config.get('rconPassword'):
        return

    rconPassword = secrets.token_urlsafe(24)
    config['rconPassword'] = rconPassword

    storeConfig(config)

def getMaxPlayers(serverPath: str | None = None) -> int:
    """Resolve max-players from <serverPath>/server.properties."""
    if not serverPath:
        return 20

    server_path_abs = os.path.abspath(serverPath)
    for server in serverSessionsManager.serverInstances.values():
        if (
            getattr(server, 'working_dir', None)
            and os.path.abspath(server.working_dir) == server_path_abs
            and server.is_running()
            and getattr(server, 'max_players', None) is not None
        ):
            return int(server.max_players)

    path = os.path.join(serverPath, "server.properties")

    if not os.path.isfile(path):
        return 20  # Default Minecraft max players

    try:
        with open(path, "r") as f:
            for line in f:
                if line.startswith("max-players="):
                    return int(line.split("=", 1)[1].strip())
    except Exception as e:
        print(f"Error reading max players from server.properties: {e}")

    return 20  # Default if not found in file

def getOnlinePlayers(serverInstance) -> dict[str, int | list[str]]:
    server_path = getattr(serverInstance, 'working_dir', None) if serverInstance is not None else None
    if serverInstance is None or not serverInstance.running:
        return {"max": getMaxPlayers(server_path)}

    try:
        output = serverInstance.send_rcon_command("list")
        if output is None:
            return {"max": getMaxPlayers(server_path)}

        # The output should be in a format of "There are X of a max of Y players online: player1, player2, ..."
        # Split on ": " to separate the counts sentence from the player names
        parts = output.split(": ", 1)
        counts_part = parts[0]   # "There are X of a max of Y players online"
        names_part  = parts[1] if len(parts) > 1 else ""

        # Extract online players from the counts sentence
        tokens = counts_part.split()
        online      = int(tokens[2])   # "There are X ..."
        max_players = getMaxPlayers(server_path)

        # Parse player names, filtering empty strings when no players are online
        players = [name.strip() for name in names_part.split(",") if name.strip()]

        return {
            "online": online,
            "max": max_players,
            "players": players
        }
    except Exception:
        return {"max": getMaxPlayers(server_path)}

def getServerStats(serverInstance, force=False):
    now = time.time()
    last_stats = getattr(serverInstance, 'last_stats', None)
    last_time = getattr(serverInstance, 'last_stats_time', 0)

    if not force and last_stats and (now - last_time < 5):
        return last_stats

    lock = getattr(serverInstance, '_stats_lock', None)
    if lock:
        acquired = lock.acquire(timeout=10)
        if not acquired:
            # If we can't get the lock in 10s, just return cached stats
            return last_stats if last_stats else {
                'cpu_usage_percent': 0.0,
                'memory_usage_mb': 0.0,
                'max_memory_mb': getMaxMemoryMB(getattr(serverInstance, 'working_dir', None)),
                'online_players': {"max": getMaxPlayers(getattr(serverInstance, 'working_dir', None))}
            }

        try:
            # Re-check cache after acquiring lock
            now = time.time()
            if not force and serverInstance.last_stats and (now - serverInstance.last_stats_time < 5):
                return serverInstance.last_stats

            stats = {
                'cpu_usage_percent': serverInstance.get_cpu_usage_percent(),
                'memory_usage_mb': serverInstance.get_memory_usage_mb(),
                'max_memory_mb': getMaxMemoryMB(getattr(serverInstance, 'working_dir', None)),
            }


            try:
                stats['online_players'] = getOnlinePlayers(serverInstance)
            except Exception:
                stats['online_players'] = {"max": getMaxPlayers(getattr(serverInstance, 'working_dir', None))}

            serverInstance.last_stats = stats
            serverInstance.last_stats_time = now
            print("Collected new stats", stats)

            return stats
        finally:
            lock.release()
    else:
        # Fallback if no lock present
        stats = {
            'cpu_usage_percent': serverInstance.get_cpu_usage_percent(),
            'memory_usage_mb': serverInstance.get_memory_usage_mb(),
            'max_memory_mb': getMaxMemoryMB(getattr(serverInstance, 'working_dir', None)),
            'online_players': getOnlinePlayers(serverInstance)
        }
        return stats


def getGlobalStats(serverInstances=None):
    if serverInstances is None:
        serverInstances = serverSessionsManager.serverInstances.values()

    global_stats = {
        'cpu_usage_percent': 0.0,
        'memory_usage_mb': 0.0,
        'max_memory_mb': 0,
        'online_players': {
            'online': 0,
            'max': 0,
            'players': []
        }
    }

    for serverInstance in list(serverInstances):
        if not serverInstance.is_running():
            continue

        server_stats = getServerStats(serverInstance, force=True)
        global_stats['cpu_usage_percent'] += float(server_stats.get('cpu_usage_percent', 0.0))
        global_stats['memory_usage_mb'] += float(server_stats.get('memory_usage_mb', 0.0))
        global_stats['max_memory_mb'] += int(server_stats.get('max_memory_mb', 0))

        online_players = server_stats.get('online_players', {})
        players = online_players.get('players', [])

        global_stats['online_players']['max'] += int(online_players.get('max', 0))
        global_stats['online_players']['online'] += int(online_players.get('online', len(players)))
        global_stats['online_players']['players'].extend(players)

    return global_stats

def getJavaPathForVersion(serverVersion: str) -> str:
    config = getConfig()
    if config is None:
        return "java"

    runtimes = config.get("javaRuntimes", {})
    requiredVersion = getRequiredJavaVersion(serverVersion)

    for v in sorted(int(k) for k in runtimes.keys()):
        if v >= requiredVersion:
            path = runtimes.get(str(v), "")
            if validateJavaRuntime(path, v):
                return path

    return "java"

def createRunScript(path, serverVersion) -> str | None:
    config = getConfig()
    if config is None:
        return None
    arguments = config.get("startMcServerArguments")
    if not arguments:
        print("'startMcServerArguments' not set in config.")
        return None

    javaPath = getJavaPathForVersion(serverVersion)
    command = f'{javaPath} {arguments}'

    fileName = ""
    if(os.name == "nt"):  # Windows
        fileName = "launch.bat"
    else:
        fileName = "launch.sh"

    filePath = os.path.join(path, fileName)

    if os.path.exists(filePath):
        print(f"Overwriting launch script.")

    with open(filePath, "w") as f:
        f.write(command)

    # Only set permissions on Unix-like systems, on windows it is not needed
    if os.name != "nt":
        os.chmod(filePath, 0o755)

    print(f"Launch script created at {filePath} with the command \"'{command}'\".")

    return command


def runMinecraftServer(serverName=None, path="servers", serverId=None):
    if serverName is None:
        serverName = questionary.select("Select a server to run:", choices=[name for name in os.listdir(path)
        if os.path.isdir(os.path.join(path, name))]).ask()

    if serverName not in serverSessionsManager.serverInstances:
        if serverId is None:
            print(f"Server ID is required to start '{serverName}'.")
            return None
        setupServerInstance(os.path.join(path, serverName), serverName, serverId)

    if(serverName in serverSessionsManager.serverInstances):
        server = serverSessionsManager.serverInstances[serverName]
        if not server.running:
            print(f"\nStarting Minecraft server '{serverName}' in background...")
            server.start()
            input("\nPress Enter to return to menu...")
        else:
            print(f"\nServer '{serverName}' is already running.")
            input("\nPress Enter to return to menu...")
    else:
        print(f"Server '{serverName}' not found.")
        input("\nPress Enter to continue...")
        return None


def patchServerProperties(path: str, overrides: dict):
    if not path:
        raise ValueError("_patch_server_properties: path must not be empty or None")

    abs_path = os.path.abspath(path)
    servers_dir = os.path.abspath("servers")

    # Ensure the target directory is inside the servers/ folder, never the project root or above
    if not abs_path.startswith(servers_dir + os.sep):
        raise ValueError(
            f"patchServerProperties: refusing to write to '{abs_path}' — "
            f"path must be inside the servers/ directory ('{servers_dir}')"
        )

    if not os.path.isdir(abs_path):
        raise ValueError(f"patchServerProperties: server directory does not exist: '{abs_path}'")

    props_path = os.path.join(abs_path, "server.properties")
    lines = []

    if os.path.isfile(props_path):
        with open(props_path, "r") as f:
            lines = f.readlines()

    # Track which keys we've already patched
    patched = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0]
        if key in overrides:
            new_lines.append(f"{key}={overrides[key]}\n")
            patched.add(key)
        else:
            new_lines.append(line)

    # Append any keys that weren't already in the file
    for key, value in overrides.items():
        if key not in patched:
            new_lines.append(f"{key}={value}\n")

    with open(props_path, "w") as f:
        f.writelines(new_lines)


def getLaunchCommand(path):
    if not path:
        return None

    normalized = os.path.normpath(path)

    fileName = ""
    if(os.name == "nt"):  # Windows
        fileName = "launch.bat"
    else:
        fileName = "launch.sh"

    filePath = os.path.join(normalized, fileName)
    if os.path.isfile(filePath):
        try:
            with open(filePath, "r") as f:
                command = f.read().strip()
                return command
        except Exception as e:
            return None
    else:
        return None

def setupServerInstance(path, serverName, serverId):
    if not serverId:
        print(f"Failed to resolve server id for '{serverName}'.")
        return None

    from Database.repositories import ServersRepository
    launchCommand = getLaunchCommand(path) or createRunScript(path, ServersRepository.getServerVersion(serverId))
    if launchCommand is None:
        print(f"Failed to get/create launch script for server '{serverName}'.")
        return None

    server = serverSessionsManager.ServerSession(serverId, serverName, launchCommand, os.path.abspath(path))
    serverSessionsManager.serverInstances[serverName] = server
    return server


def attachToServer():
    if not serverSessionsManager.serverInstances:
        print("No running servers to attach to.")
        return

    print(f"RunningServers: {serverSessionsManager.serverInstances}")

    serverName = questionary.select("Select a server to attach to:", choices=list(serverSessionsManager.serverInstances.keys())).ask()
    if serverName in serverSessionsManager.serverInstances:
        server = serverSessionsManager.serverInstances[serverName]
        server.attach()
    else:
        print(f"Server '{serverName}' not found.")
    return


def closeAllServers():
    for serverName, server in serverSessionsManager.serverInstances.items():
        if server.running:
            print(f"\nStopping server '{serverName}'...")
            server.stop()
    return

def getNewPort(usedPorts: set | None=None, type="server") -> int:
    if usedPorts is None:
        usedPorts = serverSessionsManager.usedPorts

    if type not in ("server", "rcon"):
        raise ValueError("type must be 'server' or 'rcon'")

    basePort = 25565
    if type == "rcon":
        basePort = 25575

    def is_port_physically_free(port):
        """Check if a port is actually available on the local machine."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                # We try to bind to see if the port is taken by any process
                # (including ones from previous runs that didn't exit).
                s.bind(('127.0.0.1', port))
                return True
            except OSError:
                return False

    while basePort in usedPorts or not is_port_physically_free(basePort):
        basePort += 1
        if basePort > 65535:
            raise RuntimeError("No available ports")

    return basePort

def assignNewPort(serverInstance: serverSessionsManager.ServerSession, port: int, type, usedPorts: set | None=None):
    if type not in ("server", "rcon"):
        raise ValueError("type must be 'server' or 'rcon'")
    if usedPorts is None:
        usedPorts = serverSessionsManager.usedPorts

    if port in usedPorts:
        raise ValueError(f"Port {port} is already in use")

    if type == "server":
        updateServerSettings(serverInstance.working_dir, port)
    else:
        updateRconSettings(serverInstance.working_dir, port)

    usedPorts.add(port)
    return port

def updateServerSettings(path, port: int = 25565):
    # Inject server port settings so the server is ready to run on the assigned port
    patchServerProperties(path, {
        "server-port": port,
        "query.port": port,
    })


def updateRconSettings(path, port: int = 25575):
    # Inject RCON settings so the server is ready to accept RCON connections
    rcon_password = getConfig().get("rconPassword", "")
    if rcon_password:
        patchServerProperties(path, {
            "enable-rcon": "true",
            "rcon.port": port,
            "rcon.password": rcon_password,
        })

def getLocalServers():
    return [name for name in os.listdir("servers") if os.path.isdir(os.path.join("servers", name))]

def getMaxMemoryMB(serverPath):
    if serverPath is None:
        return -1

    server_path_abs = os.path.abspath(serverPath)
    for server in serverSessionsManager.serverInstances.values():
        if (
            getattr(server, 'working_dir', None)
            and os.path.abspath(server.working_dir) == server_path_abs
            and server.is_running()
            and getattr(server, 'max_memory_mb', None) is not None
        ):
            return int(server.max_memory_mb)

    try:
        launchCommand = getLaunchCommand(serverPath)
        if launchCommand is None:
            return -1
        # Look for -Xmx flag in the launch command to determine max memory allocation
        tokens = launchCommand.split()
        for i, token in enumerate(tokens):
            if token.startswith("-Xmx"):
                mem_str = token[4:]
                if mem_str.endswith("G"):
                    return int(mem_str[:-1]) * 1024
                elif mem_str.endswith("M"):
                    return int(mem_str[:-1])
                else:
                    return int(mem_str) // (1024 * 1024)  # Assume bytes if no unit
    except Exception as e:
        print(f"Error reading max memory from server.properties: {e}")

    return 1024  # Default if not found in file