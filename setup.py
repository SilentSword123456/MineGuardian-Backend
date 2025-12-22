import os
import questionary

import utils
from utils import displayTitle, downloadFile
import requests

def firstLauch():
    displayTitle()
    choice = questionary.confirm("It looks like this is your first time running the application. Would you like to set it up now?", default=True).ask()
    if(not choice):
        questionary.print("\n👋 Goodbye!", style="bold fg:green")
        exit(0)

    questionary.print("\nGreat! Let's set up the application!", style="bold fg:cyan")

    choice = questionary.confirm("Do you want to install the Minecraft Server automatically?", default=True).ask()

    if(not choice):
        questionary.print("\nOk, you can install the minecraft server later from the main menu, or you can do it yourself.", style="fg:yellow")
        input("\nPress Enter to continue...")
        return

    installMinecraftServer()

def installMinecraftServer():
    serverSoftware = questionary.select("Select the Minecraft server software to install:", choices=["vanilla", "spigot"], default="vanilla").ask()
    serverVersion = questionary.text("Enter the Minecraft server version to install (e.g., 1.21.11 or latest):", default="latest").ask()
    serverName = questionary.text("Enter a name for the server (used for folder name):", default=f"{serverSoftware}_{serverVersion}").ask()

    if(serverSoftware != "vanilla" and serverSoftware != "spigot"):
        questionary.print("Invalid server software selected. Please chose between Vanilla or Spigot", style="fg:red")
        return

    #questionary.print(f"\nInstalling {serverSoftware} on version {serverVersion}\n", style="bold fg:cyan")

    downloadUrl = ""

    if(serverSoftware == "vanilla"):
        allVersionsDownloadPage = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        try:
            response = requests.get(allVersionsDownloadPage)
            response.raise_for_status()
            versionData = response.json()

            if(serverVersion == "latest"):
                serverVersion = versionData['latest']['release']

            for ver in versionData['versions']:
                if(ver['id'] == serverVersion):
                    downloadUrl = ver['url']

            if(downloadUrl == ""):
                questionary.print(f"Version {serverVersion} not found for Vanilla Minecraft.", style="fg:red")
                return

        except requests.exceptions.RequestException as e:
            questionary.print(f"Error fetching version data from {allVersionsDownloadPage}: {e}", style="fg:red")
            return

        try:
            response = requests.get(downloadUrl)
            response.raise_for_status()
            versionInfo = response.json()
            downloadUrl = versionInfo['downloads']['server']['url']

        except requests.exceptions.RequestException as e:
            questionary.print(f"Error fetching version info from {downloadUrl}: {e}", style="fg:red")
            return
    elif(serverSoftware == "spigot"):
        questionary.print("Spigot server installation is not yet implemented.", style="fg:red")
        return

    questionary.print(f"Downloading {serverSoftware} on version {serverVersion} from {downloadUrl}", style="fg:green")

    downloadPath = os.path.join("servers", serverName) + "/server.jar"
    downloadFile(downloadUrl, downloadPath)

def createRunScript():
    fileName = ""
    command = utils.getConfig()["startMinecraftServerCommand"]
    if(os.name == "nt"):  # Windows
        fileName = "launch.bat"
    else:
        fileName = "launch.sh"

    if(not os.path.exists(fileName)):
        with open(fileName, "w") as f:
            f.write(command)
        # Only set permissions on Unix-like systems, on windows it is not needed
        if(os.name != "nt"):
            os.chmod(fileName, 0o755)

    else:
        questionary.print(f"Overwriting launch script.", style="fg:yellow")
        with open(fileName, "w") as f:
            f.write(command)
        # Same here, only set permissions on Unix-like systems, on windows it is not needed
        if(os.name != "nt"):
            os.chmod(fileName, 0o755)

    return




