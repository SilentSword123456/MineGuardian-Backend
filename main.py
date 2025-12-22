import questionary
from api import app

def main_menu():
    while True:
        questionary.print("\n" + "="*50, style="bold")
        questionary.print("MineGuardian Backend CLI", style="bold fg:cyan")
        questionary.print("="*50 + "\n", style="bold")

        choice = questionary.select(
            "What would you like to do?",
            choices=[
                "Start API Server",
                "Exit"
            ]
        ).ask()

        if choice == "Start API Server":
            start_server()
        elif choice == "Exit":
            questionary.print("\n👋 Goodbye!", style="bold fg:green")
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
    main_menu()

