import os
import secrets
import questionary
import requests
import json
from rcon import RconClient


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

def getPlayersOnline(serverInstance, port: int = 25575) -> dict[str, int | list[str]]:
    """
    Send the 'list' command to a running server via RCON and return the response.
    Requires the server to have RCON enabled with the password from config.json.
    """
    if serverInstance is None or not serverInstance.running:
        raise RuntimeError("Server instance is not running")

    host = "127.0.0.1"
    port = serverInstance.rcon_port
    config = getConfig()
    if config is None:
        raise RuntimeError("Could not load config.json")

    password = config.get('rconPassword')
    if not password:
        raise RuntimeError("No rconPassword found in config.json. Run generateRconPassword() first.")

    with RconClient(host, port, password) as rcon:
        output = rcon.send_command("list")
        # The output should be in a format of "There are X of a max of Y players online: player1, player2, ..."
        try:
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
        except (IndexError, ValueError) as e:
            raise RuntimeError(
                f"Failed to parse RCON list response: '{output}' — {e}"
            ) from e

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


