import os
import questionary

import serverSessionsManager
from utils import downloadFile, createRunScript, getLocalServers
import requests

def installMinecraftServer(serverSoftware=None, serverVersion=None, serverName=None, acceptEula=False):

    if serverSoftware != "vanilla" and serverSoftware != "spigot":
        return {"error": "Invalid server software selected. Please chose between \"vanilla\" or \"spigot\""}

    if serverName in getLocalServers():
        return {"error": f"Server '{serverName}' already exists. Please choose another server"}


    downloadUrl = ""

    if serverSoftware == "vanilla":
        allVersionsDownloadPage = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        try:
            response = requests.get(allVersionsDownloadPage)
            response.raise_for_status()
            versionData = response.json()

            if serverVersion == "latest":
                serverVersion = versionData['latest']['release']

            for ver in versionData['versions']:
                if ver['id'] == serverVersion:
                    downloadUrl = ver['url']

            if downloadUrl == "":
                return {"error": f"Version {serverVersion} not found for Vanilla Minecraft"}

        except requests.exceptions.RequestException as e:
            return {"error": f"Error fetching version data from {allVersionsDownloadPage}: {e}"}

        try:
            response = requests.get(downloadUrl)
            response.raise_for_status()
            versionInfo = response.json()
            downloadUrl = versionInfo['downloads']['server']['url']

        except requests.exceptions.RequestException as e:
            return {"error": f"Error fetching version info from {downloadUrl}: {e}"}
    elif serverSoftware == "spigot":
        questionary.print("Spigot server installation is not yet implemented.", style="fg:red")
        return  {"error": "Spigot server installation is not yet implemented."}



    downloadPath = os.path.join("servers", serverName)
    downloadFile(downloadUrl, downloadPath + "/server.jar")

    createRunScript(downloadPath)

    if not acceptEula:
        questionary.print(f"You must accept the EULA to run the Minecraft server. Installation aborted. You can always edit the file manually found at {downloadPath}/eula.txt", style="fg:red")
        return {"warning": "EULA not accepted, server installed but not runnable until eula.txt is updated with 'eula=true'"}

    addAcceptEula(downloadPath)

    return True


def getAvailableVersions(serverSoftware):
    """
    Returns a flat list of available Minecraft version IDs for the given server software.
    Format: ["latest", "1.21.11", "1.21.10", ...] ordered newest to oldest.
    """
    if serverSoftware == "vanilla":
        allVersionsUrl = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        try:
            response = requests.get(allVersionsUrl)
            response.raise_for_status()
            versionData = response.json()

            versions = ["latest"] + [
                ver["id"]
                for ver in versionData["versions"]
                if ver["type"] == "release"
            ]

            return {"versions": versions}

        except requests.exceptions.RequestException as e:
            return {"error": f"Error fetching version data: {e}"}

    elif serverSoftware == "spigot":
        return {"error": "Spigot version listing is not yet implemented."}

    else:
        return {"error": "Invalid server software. Please choose between \"vanilla\" or \"spigot\""}



def addAcceptEula(path):
    eulaPath = os.path.join(path, "eula.txt")
    with open(eulaPath, "w") as f:
        f.write("eula=true\n")

    return

def uninstallMinecraftServer(serverName):
    serverPath = os.path.join("servers", serverName)
    if not os.path.exists(serverPath):
        return {"error": f"Server '{serverName}' does not exist"}

    if serverName in serverSessionsManager.serverInstances:
        if serverSessionsManager.serverInstances[serverName].is_running():
            return {"error": f"Server '{serverName}' is currently running. Please stop it before uninstalling."}
        else:
            serverSessionsManager.serverInstances[serverName].cleanup()
            del serverSessionsManager.serverInstances[serverName]

    try:
        for root, dirs, files in os.walk(serverPath, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(serverPath)
        return True
    except Exception as e:
        return {"error": f"Error uninstalling server '{serverName}': {e}"}
