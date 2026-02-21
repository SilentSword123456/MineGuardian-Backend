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
            'isRunning': (setup.serverInstances[name].is_running() if name in setup.serverInstances else False)
        })
        i += 1
    return servers

def start_server(serverName):
    if serverName in setup.serverInstances and setup.serverInstances[serverName].is_running():
        raise ValueError(f"Server '{serverName}' is already running")

    if serverName not in setup.serverInstances:
        return setup.setupServerInstance(os.path.join(DIR, "servers", serverName), serverName)

    return setup.serverInstances[serverName]

def stop_server(serverName):
    if serverName not in setup.serverInstances:
        raise ValueError(f"No instance found for Server '{serverName}'")
    setup.serverInstances[serverName].stop()
