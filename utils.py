import os
import questionary
import requests
import json


running_servers = {}

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

def runCommand(command, cwd=None):
    if cwd:
        original_dir = os.getcwd()
        os.chdir(cwd)
        os.system(command)
        os.chdir(original_dir)
    else:
        os.system(command)
