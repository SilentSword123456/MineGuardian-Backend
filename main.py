import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import os
import subprocess
import questionary
import serverSessionsManager
import utils
from utils import displayTitle
from dotenv import set_key, dotenv_values

ENV_FILE = ".env"
REQUIRED_ENV_KEYS = ["FLASK_ENV", "RESEND_API_KEY"]

def isConfigValid():
    config = utils.getConfig()
    if config is None:
        return False
    if not config.get("rconPassword"):
        return False
    if not config.get("jwtSecretKey"):
        return False
    if not config.get("flaskConfig", {}).get("SECRET_KEY"):
        return False
    return True


def isEnvValid():
    if not os.path.isfile(ENV_FILE):
        return False
    env = dotenv_values(ENV_FILE)
    if not env.get("FLASK_ENV"):
        return False
    if env.get("FLASK_ENV") == "production" and not env.get("RESEND_API_KEY"):
        return False
    return True

def runSetup():
    displayTitle()
    questionary.print("── MineGuardian Setup ──\n", style="bold fg:cyan")

    config = utils.getConfig()

    if not config.get("rconPassword"):
        utils.generateRconPassword()
        questionary.print("Generated RCON password.", style="fg:green")
    if not config.get("flaskConfig", {}).get("SECRET_KEY"):
        utils.generateFlaskKey()
        questionary.print("Generated Flask secret key.", style="fg:green")
    if not config.get("jwtSecretKey"):
        utils.generateJWTSecretKey()
        questionary.print("Generated JWT secret key.", style="fg:green")

    config = utils.getConfig()

    questionary.print("\n── Minecraft Server Memory ──", style="bold fg:cyan")
    ram = questionary.text(
        "How much RAM (in MB) to allocate to each Minecraft server by default?",
        default="1024",
        validate=lambda v: v.isdigit() and int(v) > 0 or "Enter a positive number"
    ).ask()
    config["startMinecraftServerCommand"] = f"java -Xmx{ram}M -Xms{ram}M -jar server.jar nogui"
    utils.storeConfig(config)
    questionary.print(f"Default server RAM set to {ram}MB.", style="fg:green")

    questionary.print("\n── API Server Auto-Start ──", style="bold fg:cyan")
    wants_autostart = questionary.confirm(
        "Start the API server automatically on every launch?",
        default=False
    ).ask()

    config = utils.getConfig()
    if wants_autostart:
        current = config.get("defaultApiServerConfig", {})
        change = questionary.confirm(
            f"Current settings are host={current.get('host', '0.0.0.0')}, "
            f"port={current.get('port', 5000)}, "
            f"debug={current.get('debug', True)}. Change them?",
            default=False
        ).ask()
        if change:
            host = questionary.text("Host:", default=str(current.get("host", "0.0.0.0"))).ask()
            port = questionary.text("Port:", default=str(current.get("port", 5000))).ask()
            debug = questionary.confirm("Enable debug mode?", default=current.get("debug", True)).ask()
            config["defaultApiServerConfig"] = {"host": host, "port": int(port), "debug": debug}
        config["autoStartApiServer"] = True
    else:
        config["autoStartApiServer"] = False

    utils.storeConfig(config)
    questionary.print(
        f"Auto-start {'enabled' if wants_autostart else 'disabled'}.",
        style="fg:green"
    )

    questionary.print("\n── Environment ──", style="bold fg:cyan")
    mode = questionary.select(
        "Run mode (choose development if hosting locally):",
        choices=["development", "production"]
    ).ask()

    resend_key = ""
    if mode == "production":
        while not resend_key:
            resend_key = questionary.password("Resend API key: ").ask()
            resend_key = resend_key.strip() if resend_key else ""

    set_key(ENV_FILE, "FLASK_ENV", mode)
    set_key(ENV_FILE, "RESEND_API_KEY", resend_key)
    questionary.print(".env written.", style="fg:green")

    # 5. playit.gg
    setup_playit()

    questionary.print("\nSetup complete! MineGuardian is ready.\n", style="bold fg:green")


def setup_playit():
    questionary.print("\n── Public Access (playit.gg) ──", style="bold fg:cyan")
    questionary.print(
        "playit.gg gives your servers a permanent public address without port forwarding.\n",
        style="fg:white"
    )
    if not questionary.confirm("Set this up now?", default=True).ask():
        questionary.print("Skipped. Add \"playitAddress\" to config.json later.\n", style="fg:yellow")
        return

    questionary.print(
        "\n1. Install: https://playit.gg/download  (Linux: sudo apt install playit)\n"
        "2. Create a free account at https://playit.gg\n"
        "3. Add a Minecraft tunnel for port 25565\n"
        "4. Copy the public address (e.g. abc123.ply.gg:25565)\n",
        style="fg:white"
    )
    input("Press Enter once you have your public address...")

    address = questionary.text("Paste your playit.gg address:").ask()
    if not address or not address.strip():
        questionary.print("Skipped. Add it later via \"playitAddress\" in config.json.\n", style="fg:yellow")
        return

    config = utils.getConfig()
    config["playitAddress"] = address.strip()
    utils.storeConfig(config)
    questionary.print(f"Saved! Players connect to: {address.strip()}\n", style="fg:green")


def start_server(host=None, port=None, debug=None):
    from gevent import monkey
    monkey.patch_all(all=True)
    import api

    questionary.print(f"\nStarting server on {host}:{port}", style="fg:green")
    questionary.print("Press Ctrl+C to stop\n", style="fg:yellow")

    try:
        api.startServer(debug=debug, host=host, port=int(port))
    except KeyboardInterrupt:
        questionary.print("\nServer stopped!", style="fg:yellow")
    except Exception as e:
        questionary.print(f"\nError: {e}", style="fg:red")
    finally:
        api.stopServer()
        input("\nPress Enter to continue...")

def main_menu():
    while True:
        displayTitle()
        choice = questionary.select(
            "What would you like to do?",
            choices=[
                "Start API Server",
                "Run Tests",
                "Redo Setup",
                "Exit"
            ]
        ).ask()

        if choice == "Start API Server":
            config = utils.getConfig()
            start_server(**config["defaultApiServerConfig"])

        elif choice == "Run Tests":
            questionary.print("\nRunning test suite...\n", style="bold fg:cyan")
            result = subprocess.run(["pytest", "--tb=short", "-q"], check=False)
            questionary.print(
                "\nAll tests passed!" if result.returncode == 0
                else f"\nSome tests failed (exit code {result.returncode}).",
                style="bold fg:green" if result.returncode == 0 else "bold fg:red"
            )
            input("\nPress Enter to continue...")

        elif choice == "Redo Setup":
            if questionary.confirm("This will overwrite your current config. Sure?", default=False).ask():
                runSetup()
                input("\nPress Enter to continue...")

        elif choice == "Exit":
            if serverSessionsManager.serverInstances:
                questionary.print("\nClosing all running servers first...", style="fg:yellow")
                utils.closeAllServers()
            questionary.print("\nGoodbye!", style="bold fg:green")
            break


if __name__ == '__main__':
    config_ok = isConfigValid()
    env_ok = isEnvValid()

    if not config_ok or not env_ok:
        if not config_ok:
            questionary.print("config.json has empty required values.", style="fg:yellow")
        if not env_ok:
            questionary.print(".env is missing or incomplete.", style="fg:yellow")

        if not questionary.confirm("Run setup now?", default=True).ask():
            questionary.print("Cannot continue without a valid configuration. Goodbye!", style="fg:red")
            exit(1)

        runSetup()

    config = utils.getConfig()
    if config is None:
        questionary.print("Failed to load config.json. Goodbye!", style="fg:red")
        exit(1)

    if config.get("autoStartApiServer"):
        start_server(**config["defaultApiServerConfig"])

    main_menu()