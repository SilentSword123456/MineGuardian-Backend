import os
import setup

DIR = os.path.dirname(os.path.abspath(__file__ + "/.."))

def get_all_servers():
    servers = []
    i = 1
    for name in os.listdir(os.path.join(DIR, "servers")):
        servers.append({
            'name': name,
            'id': i,
            'isRunning': (setup.runningServers[name].is_running() if name in setup.runningServers else False)
        })
        i += 1
    return servers

def start_server(serverName):
    if serverName in setup.runningServers and setup.runningServers[serverName].is_running():
        raise ValueError(f"Server '{serverName}' is already running")

    if serverName not in setup.runningServers:
        return setup.setupServerInstance(os.path.join(DIR, "servers", serverName), serverName)

    return setup.runningServers[serverName]

def stop_server(serverName):
    if serverName not in setup.runningServers:
        raise ValueError(f"No instance found for Server '{serverName}'")
    setup.runningServers[serverName].stop()
