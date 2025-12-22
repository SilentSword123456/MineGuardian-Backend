import os
import questionary
import requests
import json
import subprocess
import threading
import platform
import shlex

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

def runCommand(command):
    os.system(command)

def startServerProcess(server_name, command, working_dir):
    try:
        # Handle path quoting based on OS
        if platform.system() == "Windows":
            # Windows: Use quotes for paths with spaces
            if not command.startswith('"') and ' ' in command:
                command = f'"{command}"'
        else:
            # Linux/Mac: Use shlex.quote for proper escaping
            # But only if it's a file path (not already a complex command)
            if not command.startswith(('./', '/', '"', "'")):
                command = shlex.quote(command)

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_dir,
            shell=True,
            text=True,
            bufsize=1
        )

        running_servers[server_name] = process

        def read_output(proc):
            try:
                for line in proc.stdout:
                    print(f"[{server_name}] {line.rstrip()}")
            except:
                pass

        output_thread = threading.Thread(target=read_output, args=(process,), daemon=True)
        output_thread.start()

        questionary.print(f"Server '{server_name}' started successfully (PID: {process.pid})", style="fg:green")
        return process
    except Exception as e:
        questionary.print(f"Error starting server '{server_name}': {e}", style="fg:red")
        return None

def sendCommandToServer(server_name, command):

    if server_name not in running_servers:
        questionary.print(f"Server '{server_name}' is not running", style="fg:red")
        return False

    process = running_servers[server_name]

    if process.poll() is not None:
        questionary.print(f"Server '{server_name}' has stopped", style="fg:yellow")
        del running_servers[server_name]
        return False

    try:
        process.stdin.write(command + "\n")
        process.stdin.flush()
        return True
    except Exception as e:
        questionary.print(f"Error sending command to server '{server_name}': {e}", style="fg:red")
        return False

def stopServer(server_name):

    if sendCommandToServer(server_name, "stop"):
        questionary.print(f"Sent stop command to server '{server_name}'", style="fg:yellow")
        process = running_servers.get(server_name)
        if process:
            try:
                process.wait(timeout=30)
                questionary.print(f"Server '{server_name}' stopped successfully", style="fg:green")
            except subprocess.TimeoutExpired:
                process.kill()
                questionary.print(f"Server '{server_name}' forcefully terminated", style="fg:red")
            finally:
                if server_name in running_servers:
                    del running_servers[server_name]
        return True
    return False

def getRunningServers():
    dead_servers = []
    for name, process in running_servers.items():
        if process.poll() is not None:
            dead_servers.append(name)

    for name in dead_servers:
        del running_servers[name]

    return list(running_servers.keys())

