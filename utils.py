from __future__ import annotations
import os
import secrets
import questionary
import requests
import json
import time
from rcon import RconClient
import serverSessionsManager


def displayTitle():
    questionary.print("\n" + "="*50, style="bold")
    questionary.print("MineGuardian Backend CLI", style="bold fg:cyan")
    questionary.print("="*50 + "\n", style="bold")


def downloadFile(url, dest):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(dest), exist_ok=True)

        with open(dest, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        #questionary.print(f"Downloaded file to {dest}", style="fg:green")
    except requests.exceptions.RequestException as e:
        questionary.print(f"Error downloading file from {url}: {e}", style="fg:red")

def getConfig():
    if(not os.path.isfile("config.json")):
        questionary.print("Configuration file not found.", style="fg:red")
        return None
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            return config
    except json.JSONDecodeError as e:
        questionary.print(f"Error reading configuration file: {e}", style="fg:red")
        return None

def storeConfig(config):
    try:
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        questionary.print(f"Error saving configuration file: {e}", style="fg:red")

def runCommand(command, cwd=None):
    if cwd:
        original_dir = os.getcwd()
        os.chdir(cwd)
        os.system(command)
        os.chdir(original_dir)
    else:
        os.system(command)

def generateFlaskKey():
    config = getConfig()
    if config is None:
        return

    if config.get('flaskConfig', {}).get('SECRET_KEY'):
        return

    secretKey = secrets.token_urlsafe(32)
    config['flaskConfig']['SECRET_KEY'] = secretKey

    storeConfig(config)

def generateRconPassword():
    """Generate a random RCON password and store it in config.json (once)."""
    config = getConfig()
    if config is None:
        return

    if config.get('rconPassword'):
        return

    rconPassword = secrets.token_urlsafe(16)
    config['rconPassword'] = rconPassword

    storeConfig(config)
    
def getMaxPlayers(serverInstance) -> int:
    if serverInstance is None or not getattr(serverInstance, 'working_dir', None):
        return 20

    path = os.path.join(serverInstance.working_dir, "server.properties")
    
    if not os.path.isfile(path):
        return 20  # Default Minecraft max players
    
    try:
        with open(path, "r") as f:
            for line in f:
                if line.startswith("max-players="):
                    return int(line.split("=", 1)[1].strip())
    except Exception as e:
        questionary.print(f"Error reading max players from server.properties: {e}", style="fg:red")

    return 20  # Default if not found in file

def getPlayersOnline(serverInstance) -> dict[str, int | list[str]]:
    """
    Send the 'list' command to a running server via RCON and return the response.
    Returns a dictionary with 'online', 'max', and 'players' if successful.
    If the server is not running or RCON communication fails, returns ONLY 'max'
    to avoid reporting potentially inaccurate '0 players online' data.
    """
    if serverInstance is None or not serverInstance.running:
        return {"max": getMaxPlayers(serverInstance)}

    host = "127.0.0.1"
    port = serverInstance.rcon_port
    config = getConfig()
    if config is None:
        return {"max": getMaxPlayers(serverInstance)}

    password = config.get('rconPassword')
    if not password:
        return {"max": getMaxPlayers(serverInstance)}

    try:
        with RconClient(host, port, password) as rcon:
            output = rcon.send_command("list")
            # The output should be in a format of "There are X of a max of Y players online: player1, player2, ..."
            # Split on ": " to separate the counts sentence from the player names
            parts = output.split(": ", 1)
            counts_part = parts[0]   # "There are X of a max of Y players online"
            names_part  = parts[1] if len(parts) > 1 else ""

            # Extract X and Y from the counts sentence
            tokens = counts_part.split()
            online      = int(tokens[2])   # "There are X ..."
            max_players = int(tokens[7])   # "... of a max of Y ..."

            # Parse player names, filtering empty strings when no players are online
            players = [name.strip() for name in names_part.split(",") if name.strip()]

            return {
                "online": online,
                "max": max_players,
                "players": players
            }
    except Exception:
        # If RCON connection, authentication, or parsing fails, return only max capacity
        return {"max": getMaxPlayers(serverInstance)}

def get_server_stats(serverInstance, force=False):
    """
    Collects stats for a server instance. Uses cached data if it's recent (e.g., < 5s)
    unless 'force' is True.
    """
    # Check cache (assumes last_stats and last_stats_time are initialized on the instance)
    now = time.time()
    last_stats = getattr(serverInstance, 'last_stats', None)
    last_time = getattr(serverInstance, 'last_stats_time', 0)

    if not force and last_stats and (now - last_time < 5):
        return last_stats

    # Collect new stats
    stats = {
        'cpu_usage_percent': serverInstance.get_cpu_usage_percent(),
        'memory_usage_mb': serverInstance.get_memory_usage_mb(),
    }

    # Safely try to get player info
    try:
        stats['online_players'] = getPlayersOnline(serverInstance)
    except Exception:
        # Final safety fallback if getPlayersOnline fails unexpectedly
        stats['online_players'] = {"max": getMaxPlayers(serverInstance)}

    # Update cache
    serverInstance.last_stats = stats
    serverInstance.last_stats_time = now

    return stats

def getRconInfo(serverName):
    file = f"servers/{serverName}/rcon_info.json"
    if not os.path.isfile(file):
        return None

    try:
        content = None
        with open(file, "r") as f:
            content = json.load(f)
        return {
            "enable-rcon": content.get("enable-rcon", "false"),
            "rcon.port": int(content.get("rcon.port", "25575"))
        }
    except Exception as e:
        questionary.print(f"Error reading RCON info for server '{serverName}': {e}", style="fg:red")
        return None


def createRunScript(path) -> str | None:
    config = getConfig()
    if config is None:
        return None
    command = config.get("startMinecraftServerCommand")
    if not command:
        questionary.print("'startMinecraftServerCommand' not set in config.", style="fg:red")
        return None

    fileName = ""
    if(os.name == "nt"):  # Windows
        fileName = "launch.bat"
    else:
        fileName = "launch.sh"

    filePath = os.path.join(path, fileName)

    if os.path.exists(filePath):
        questionary.print(f"Overwriting launch script.", style="fg:yellow")

    with open(filePath, "w") as f:
        f.write(command)

    # Only set permissions on Unix-like systems, on windows it is not needed
    if os.name != "nt":
        os.chmod(filePath, 0o755)

    return command


def runMinecraftServer(serverName = None, path = "servers"):
    if serverName is None:
        serverName = questionary.select("Select a server to run:", choices=[name for name in os.listdir(path)
        if os.path.isdir(os.path.join(path, name))]).ask()

    if serverName not in serverSessionsManager.serverInstances:
        setupServerInstance(os.path.join(path, serverName), serverName)

    if(serverName in serverSessionsManager.serverInstances):
        server = serverSessionsManager.serverInstances[serverName]
        if not server.running:
            questionary.print(f"\nStarting Minecraft server '{serverName}' in background...", style="fg:green")
            server.start()
            input("\nPress Enter to return to menu...")
        else:
            questionary.print(f"\nServer '{serverName}' is already running.", style="fg:yellow")
            input("\nPress Enter to return to menu...")
    else:
        questionary.print(f"Server '{serverName}' not found.", style="fg:red")
        input("\nPress Enter to continue...")
        return None


def _patch_server_properties(path: str, overrides: dict):
    """
    Read server.properties from `path`, apply key=value `overrides`, and write it back.
    Creates the file if it doesn't exist yet (Minecraft will merge on first boot).
    """
    if not path:
        raise ValueError("_patch_server_properties: path must not be empty or None")

    abs_path = os.path.abspath(path)
    servers_dir = os.path.abspath("servers")

    # Ensure the target directory is inside the servers/ folder, never the project root or above
    if not abs_path.startswith(servers_dir + os.sep):
        raise ValueError(
            f"_patch_server_properties: refusing to write to '{abs_path}' — "
            f"path must be inside the servers/ directory ('{servers_dir}')"
        )

    if not os.path.isdir(abs_path):
        raise ValueError(f"_patch_server_properties: server directory does not exist: '{abs_path}'")

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
    fileName = ""
    if(os.name == "nt"):  # Windows
        fileName = "launch.bat"
    else:
        fileName = "launch.sh"

    filePath = os.path.join(path, fileName)
    if os.path.isfile(filePath):
        try:
            with open(filePath, "r") as f:
                command = f.read().strip()
                return command
        except Exception as e:
            return None
    else:
        return None

def setupServerInstance(path, serverName):
    launchCommand = getLaunchCommand(path) or createRunScript(path)
    if launchCommand is None:
        questionary.print(f"Failed to get/create launch script for server '{serverName}'.", style="fg:red")
        return None

    server = serverSessionsManager.ServerSession(serverName, launchCommand, os.path.abspath(path))
    serverSessionsManager.serverInstances[serverName] = server
    return server


def attachToServer():
    if not serverSessionsManager.serverInstances:
        questionary.print("No running servers to attach to.", style="fg:red")
        return

    questionary.print(f"RunningServers: {serverSessionsManager.serverInstances}", style="fg:green")

    serverName = questionary.select("Select a server to attach to:", choices=list(serverSessionsManager.serverInstances.keys())).ask()
    if serverName in serverSessionsManager.serverInstances:
        server = serverSessionsManager.serverInstances[serverName]
        server.attach()
    else:
        questionary.print(f"Server '{serverName}' not found.", style="fg:red")
    return


def closeAllServers():
    for serverName, server in serverSessionsManager.serverInstances.items():
        if server.running:
            questionary.print(f"\nStopping server '{serverName}'...", style="fg:yellow")
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


    while basePort in usedPorts:
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
    _patch_server_properties(path, {
        "server-port": port,
        "query.port": port,
    })


def updateRconSettings(path, port: int = 25575):
    # Inject RCON settings so the server is ready to accept RCON connections
    rcon_password = getConfig().get("rconPassword", "")
    if rcon_password:
        _patch_server_properties(path, {
            "enable-rcon": "true",
            "rcon.port": port,
            "rcon.password": rcon_password,
        })

def getLocalServers():
    return [name for name in os.listdir("servers") if os.path.isdir(os.path.join("servers", name))]

def getMaxMemoryMB(serverPath):
    if serverPath is None:
        return -1

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
        questionary.print(f"Error reading max memory from server.properties: {e}", style="fg:red")

    return 1024  # Default if not found in file