import questionary
import setup
from api import app
from utils import displayTitle


def main_menu():
    while True:
        displayTitle()
        choice = questionary.select(
            "What would you like to do?",
            choices=[
                "Start API Server",
                "Download Minecraft Server",
                "Run Minecraft Server",
                "Attach to Server",
                "Exit"
            ]
        ).ask()

        if choice == "Start API Server":
            start_server()
        elif choice == "Download Minecraft Server":
            setup.installMinecraftServer()
        elif choice == "Run Minecraft Server":
            setup.runMinecraftServer()
        elif choice == "Attach to Server":
            setup.attachToServer()
        elif choice == "Exit":
            if(setup.runningServers):
                questionary.print("\nHold on, let me close all the running servers first.", style="fg:yellow")
                setup.closeAllServers()
            questionary.print("\nGoodbye!", style="bold fg:green")
            break

def start_server():
    questionary.print("\nStart API Server\n", style="bold fg:cyan")

    host = questionary.text("Host:", default="0.0.0.0").ask()
    port = questionary.text("Port:", default="5000").ask()
    debug = questionary.confirm("Enable debug mode?", default=True).ask()

    questionary.print(f"\nStarting server on {host}:{port}", style="fg:green")
    questionary.print("Press Ctrl+C to stop\n", style="fg:yellow")

    try:
        app.run(debug=debug, host=host, port=int(port), use_reloader=False)
    except KeyboardInterrupt:
        questionary.print("\nServer stopped!", style="fg:yellow")
    except Exception as e:
        questionary.print(f"\nError: {e}", style="fg:red")
    finally:
        input("\nPress Enter to continue...")

if __name__ == '__main__':
    #if(not os.path.isfile("config.json")):
    #    setup.firstLauch()

    main_menu()

