import os
import questionary
import serverSessionsManager
import utils
from utils import displayTitle, downloadFile
import requests

runningServers = {}

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

    downloadPath = os.path.join("servers", serverName)
    downloadFile(downloadUrl, downloadPath + "/server.jar")

    createRunScript(downloadPath)

    choice = questionary.confirm("Do you accept the Minecraft EULA? Please read and make sure you read the eula before accepting!", default=False).ask()
    if(not choice):
        questionary.print(f"You must accept the EULA to run the Minecraft server. Installation aborted. You can always edit the file manually found at {downloadPath}/eula.txt", style="fg:red")
        return

    acceptEula(downloadPath)
    server = setupServerInstance(downloadPath, serverName)
    server.start()


def createRunScript(path):
    fileName = ""
    command = utils.getConfig()["startMinecraftServerCommand"]
    if(os.name == "nt"):  # Windows
        fileName = "launch.bat"
    else:
        fileName = "launch.sh"

    filePath = os.path.join(path, fileName)

    if(not os.path.exists(filePath)):
        with open(filePath, "w") as f:
            f.write(command)
        # Only set permissions on Unix-like systems, on windows it is not needed
        if(os.name != "nt"):
            os.chmod(filePath, 0o755)

    else:
        questionary.print(f"Overwriting launch script.", style="fg:yellow")
        with open(filePath, "w") as f:
            f.write(command)
        # Same here, only set permissions on Unix-like systems, on windows it is not needed
        if(os.name != "nt"):
            os.chmod(filePath, 0o755)

    return


def runMinecraftServer(serverName = None, path = "servers"):
    if serverName is None:
        serverName = questionary.select("Select a server to run:", choices=[name for name in os.listdir(path)
        if os.path.isdir(os.path.join(path, name))]).ask()

    if serverName not in runningServers:
        setupServerInstance(path+"/"+serverName, serverName)

    if(serverName in runningServers):
        server = runningServers[serverName]
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


def acceptEula(path):
    eulaPath = os.path.join(path, "eula.txt")
    with open(eulaPath, "w") as f:
        f.write("eula=true\n")

    return

def setupServerInstance(path, serverName):
    server = serverSessionsManager.ServerSession(serverName, utils.getConfig()["startMinecraftServerCommand"], path)
    runningServers[serverName] = server
    return server

def attachToServer():
    serverName = questionary.select("Select a server to attach to:", choices=list(runningServers.keys())).ask()
    if(serverName in runningServers):
        server = runningServers[serverName]
        server.attach()
    else:
        questionary.print(f"Server '{serverName}' not found.", style="fg:red")
    return

def closeAllServers():
    for serverName, server in runningServers.items():
        if server.running:
            questionary.print(f"\nStopping server '{serverName}'...", style="fg:yellow")
            server.stop()
    return
