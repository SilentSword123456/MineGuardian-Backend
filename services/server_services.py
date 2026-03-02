import os
import serverSessionsManager
import utils

DIR = os.path.dirname(os.path.abspath(__file__ + "/.."))

def get_all_servers():
    servers = []
    i = 1
    for name in os.listdir(os.path.join(DIR, "servers")):
        servers.append({
            'name': name,
            'id': i,
            'isRunning': (
                serverSessionsManager.serverInstances[name].is_running() if name in serverSessionsManager.serverInstances else False),
            "max_memory_mb": utils.getMaxMemoryMB(os.path.join(DIR, "servers", name))
        })
        i += 1
    return servers

def get_server_instance(serverName):
    if serverName in serverSessionsManager.serverInstances and serverSessionsManager.serverInstances[serverName].is_running():
        raise ValueError(f"Server '{serverName}' is already running")

    if serverName not in serverSessionsManager.serverInstances:
        return utils.setupServerInstance(os.path.join(DIR, "servers", serverName), serverName)

    return serverSessionsManager.serverInstances[serverName]

def stop_server(serverName):
    if serverName not in serverSessionsManager.serverInstances:
        raise ValueError(f"No instance found for Server '{serverName}'")
    serverSessionsManager.serverInstances[serverName].stop()
