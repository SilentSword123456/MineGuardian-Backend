import os
import serverSessionsManager
import utils
from Database.perms import ServersPermissions
from Database.repositories import ServersUsersPermsRepository, ServersRepository

DIR = os.path.dirname(os.path.abspath(__file__ + "/.."))

def getAllServers(userId: int):
    serversIds = ServersUsersPermsRepository.getServersWithUserPerm(userId, ServersPermissions.ViewServer.value)
    return serversIds

def get_server_instance(serverId):
    serverName = ServersRepository.getServerName(serverId)
    if serverName in serverSessionsManager.serverInstances and serverSessionsManager.serverInstances[serverName].is_running():
        raise ValueError(f"Server '{serverName}' is already running")

    if serverName not in serverSessionsManager.serverInstances:
        return utils.setupServerInstance(os.path.join(DIR, "servers", serverName), serverName, serverId)

    return serverSessionsManager.serverInstances[serverName]

def stop_server(serverId):
    serverName = ServersRepository.getServerName(serverId)
    if serverName not in serverSessionsManager.serverInstances:
        raise ValueError(f"No instance found for Server '{serverName}'")
    serverSessionsManager.serverInstances[serverName].stop()


