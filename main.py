import eventlet
eventlet.monkey_patch(all=True)

import warnings
# Suppress the DeprecationWarning from eventlet and other benign warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import os
import questionary
import serverSessionsManager
import manageLocalServers
import utils
import api
from utils import displayTitle


def main_menu():
    while True:
        displayTitle()
        choice = questionary.select(
            "What would you like to do?",
            choices=[
                "Start API Server",
                "Run Minecraft Server",
                "Attach to Server",
                "Exit"
            ]
        ).ask()

        if choice == "Start API Server":
            start_server()
        elif choice == "Run Minecraft Server":
            utils.runMinecraftServer()
        elif choice == "Attach to Server":
            utils.attachToServer()
        elif choice == "Exit":
            if(serverSessionsManager.serverInstances):
                questionary.print("\nHold on, let me close all the running servers first.", style="fg:yellow")
                utils.closeAllServers()
            questionary.print("\nGoodbye!", style="bold fg:green")
            break

def start_server(host=None,port=None,debug=None):
    questionary.print("\nStart API Server\n", style="bold fg:cyan")

    if(host is None):
        host = questionary.text("Host:", default="0.0.0.0").ask()
    if(port is None):
        port = questionary.text("Port:", default="5000").ask()
    if(debug is None):
        debug = questionary.confirm("Enable debug mode?", default=False).ask()

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


def firstLaunch():
    displayTitle()
    choice = questionary.confirm(
        "It looks like this is your first time running the application. Would you like to set it up now?",
        default=True).ask()
    if (not choice):
        questionary.print("\nGoodbye!", style="bold fg:green")
        exit(0)

    utils.generateRconPassword()
    utils.generateFlaskKey()
    utils.generateJWTSecretKey()


if __name__ == '__main__':
    if(not os.path.isfile("config.json")):
        firstLaunch()

    if(utils.getConfig() is None):
        questionary.print("Configuration error. Please fix your config.json file and restart the application.", style="fg:red")

    if(utils.getConfig()["autoStartApiServer"]):
        start_server(**utils.getConfig()["defaultApiServerConfig"])

    main_menu()

