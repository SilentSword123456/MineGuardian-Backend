import os
import logging

from flask import request
from apiflask import APIBlueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
import Database.repositories
import manageLocalServers
import serverSessionsManager
import utils
import api
from services.server_services import getAllServers, get_server_instance, stop_server
from services.docs import DOCS
from services.schemas import (
    AddServerOutputSchema,
    GeneralServerInfoOutputSchema,
    GetAvailableVersionsOutputSchema,
    GetServerStatsOutputSchema,
    ListServersOutputSchema,
    RemoveServerOutputSchema,
    StartServerOutputSchema,
    StopServerOutputSchema,
)
from Database.repositories import *
from Database.perms import ServersPermissions

servers_bp = APIBlueprint('servers', __name__)
logger = logging.getLogger(__name__)


def _parse_server_id(serverId):
    try:
        return int(serverId)
    except (TypeError, ValueError):
        abort(400, message='Invalid serverId')

@servers_bp.route('/servers', methods=['GET'])
@servers_bp.doc(**DOCS['list_servers'])
@servers_bp.output(ListServersOutputSchema)
@jwt_required()
def list_servers():
    userId = int(get_jwt_identity())
    logger.info("GET /servers requested")
    logger.debug("GET /servers user context user_id=%s", userId)
    serversIds = getAllServers(userId)
    logger.info("Resolved %s visible servers", len(serversIds))
    servers = []
    for serverId in serversIds:
        serverName = ServersRepository.getServerName(serverId)
        logger.debug("Building /servers response item for server_id=%s server_name=%s", serverId, serverName)
        servers.append({
            'name': serverName,
            'server_id': serverId,
            'isRunning': (
                serverSessionsManager.serverInstances[serverName].is_running() if serverName in serverSessionsManager.serverInstances else False),
            'max_memory_mb': utils.getMaxMemoryMB(os.path.join(api.DIR, "servers", serverName)),
            'online_players': {'max': utils.getMaxPlayers(os.path.join(api.DIR, "servers", serverName))}
        })
    logger.info("Returning /servers payload with %s entries", len(servers))
    return {'servers': servers}, 200

@servers_bp.route('/servers/<serverId>', methods=['GET'])
@servers_bp.doc(**DOCS['get_general_server_info'])
@servers_bp.output(GeneralServerInfoOutputSchema)
@jwt_required()
def getGeneralServerInfo(serverId):
     userId = int(get_jwt_identity())
     serverId = _parse_server_id(serverId)
     if not ServersRepository.doesServerExist(serverId):
         abort(404, message='Server not found')

     if not ServersUsersPermsRepository.doesUserHavePerm(userId, serverId, ServersPermissions.GetServerInfo.value):
         abort(403, message='You dont have the permission to do this!')

     serverName = ServersRepository.getServerName(serverId)
     serverInstance = serverSessionsManager.serverInstances.get(serverName)
     if serverInstance:
         info = serverInstance.get_process_info()
     else:
         info = {
             'server_id': serverId,
             'is_running': False,
             'pid': 0,
             'uptime_seconds': 0.0,
             'max_memory_mb': utils.getMaxMemoryMB(os.path.join(api.DIR, "servers", serverName)),
             'max_players': utils.getMaxPlayers(os.path.join(api.DIR, "servers", serverName)),
         }

     return info, 200



@servers_bp.route('/servers/<serverId>/start', methods=['POST'])
@servers_bp.doc(**DOCS['start_server'])
@servers_bp.output(StartServerOutputSchema)
@jwt_required()
def start_minecraft_server(serverId):
    userId = int(get_jwt_identity())
    serverId = _parse_server_id(serverId)
    if not ServersRepository.doesServerExist(serverId):
        abort(404, message='Server not found')
    if not ServersUsersPermsRepository.doesUserHavePerm(userId, serverId, ServersPermissions.StartServer.value):
        abort(403, message='You dont have the permission to do this!')

    serverName = ServersRepository.getServerName(serverId)
    try:
        serverInstance = get_server_instance(serverId)
        api.register_socketio_listeners(serverName, serverInstance)
        started = serverInstance.start()
        if not started:
            abort(500, message=f"Server '{serverName}' failed to start. Check that Java is installed and the server files are intact.")
        return {'message': f"Server '{serverName}' started successfully"}, 200
    except ValueError as e:
        abort(400, message=str(e))



@servers_bp.route('/servers/<serverId>/stop', methods=['POST'])
@servers_bp.doc(**DOCS['stop_server'])
@servers_bp.output(StopServerOutputSchema)
@jwt_required()
def stop_minecraft_server(serverId):
    userId = int(get_jwt_identity())
    serverId = _parse_server_id(serverId)
    if not ServersRepository.doesServerExist(serverId):
        abort(404, message='Server not found')
    if not ServersUsersPermsRepository.doesUserHavePerm(userId, serverId, ServersPermissions.StopServer.value):
        abort(403, message='You dont have the permission to do this!')

    serverName = ServersRepository.getServerName(serverId)
    try:
        stop_server(serverId)
        return {'message': f"Server '{serverName}' stopped successfully"}, 200
    except ValueError as e:
        abort(400, message=str(e))



@servers_bp.route('/servers/<serverId>/stats', methods=['GET'])
@servers_bp.doc(**DOCS['get_server_stats'])
@servers_bp.output(GetServerStatsOutputSchema)
@jwt_required()
def get_server_stats_endpoint(serverId):
    userId = int(get_jwt_identity())
    serverId = _parse_server_id(serverId)
    if not ServersRepository.doesServerExist(serverId):
        abort(404, message='Server not found')
    if not ServersUsersPermsRepository.doesUserHavePerm(userId, serverId, ServersPermissions.GetServerInfo.value):
        abort(403, message='You dont have the permission to do this!')

    serverName = ServersRepository.getServerName(serverId)
    if not serverName:
        abort(400, message='No serverName provided')

    serverInstance = serverSessionsManager.serverInstances.get(serverName)
    if not serverInstance or not serverInstance.is_running():
        abort(404, message=f"Server '{serverName}' is not running")

    try:
        # Use the centralized function (it handles caching internally)
        stats = utils.getServerStats(serverInstance)
        return stats, 200
    except Exception as e:
        abort(500, message=f"Failed to retrieve stats: {str(e)}")

@servers_bp.route('/manage/addServer', methods=['POST'])
@servers_bp.doc(**DOCS['add_server'])
@servers_bp.output(AddServerOutputSchema)
@jwt_required()
def add_server():
    userId = int(get_jwt_identity())
    args = request.get_json()
    if not args or 'serverName' not in args or 'serverSoftware' not in args or 'serverVersion' not in args:
        abort(400, message='Missing required parameters: serverName, serverSoftware, serverVersion')

    serverName = args['serverName']
    serverSoftware = args['serverSoftware'].lower()
    serverVersion = args['serverVersion']
    acceptEula = args.get('acceptEula', False)

    status = manageLocalServers.installMinecraftServer(serverSoftware, serverVersion, serverName, acceptEula)
    if isinstance(status, dict) and 'error' in status:
        abort(400, message=status['error'])

    databaseStatus = Database.repositories.ServersRepository.addServer(userId, serverName)

    if not databaseStatus:
        abort(500, message='Failed to register server in database')

    if isinstance(status, dict) and 'warning' in status:
        return {'status': True, 'message': status['warning']}, 200

    return {'status': True, 'message': f"Server '{serverName}' installed and registered successfully"}, 200

@servers_bp.route('/servers/<serverId>/uninstall', methods=['DELETE'])
@servers_bp.doc(**DOCS['remove_server'])
@servers_bp.output(RemoveServerOutputSchema)
@jwt_required()
def remove_server(serverId):
    userId = int(get_jwt_identity())
    serverId = _parse_server_id(serverId)
    if not ServersRepository.doesServerExist(serverId):
        abort(404, message='Server not found')

    if not ServersUsersPermsRepository.doesUserHavePerm(userId, serverId, ServersPermissions.UninstallServer.value):
        abort(403, message='You dont have the permission to do this!')

    serverName = ServersRepository.getServerName(serverId)
    status = manageLocalServers.uninstallMinecraftServer(serverName)
    if isinstance(status, dict) and 'error' in status:
        abort(400, message=status['error'])

    databaseStatus = ServersRepository.removeServer(userId, serverName)
    if not databaseStatus:
        abort(404, message='Failed to remove server from database')
    return {'status': True, 'message': f"Server '{serverName}' uninstalled and removed successfully"}, 200

@servers_bp.route('/manage/<software>/getAvailableVersions', methods=['GET'])
@servers_bp.doc(**DOCS['get_available_versions'])
@servers_bp.output(GetAvailableVersionsOutputSchema)
def get_available_software(software=""):
    if not software:
        # Fallback to vanilla if software is not specified
        software = "vanilla"
    result = manageLocalServers.getAvailableVersions(software.lower())
    if "error" in result:
        abort(400, message=result.get('error', 'Failed to get available versions'))
    return result, 200

@servers_bp.route('/servers/globalStats', methods=['GET'])
@servers_bp.doc(**DOCS['get_global_stats'])
@servers_bp.output(GetServerStatsOutputSchema)
@jwt_required()
def global_stats():
    userId = int(get_jwt_identity())
    serversIds = getAllServers(userId)
    usersServers = []
    for instance in serverSessionsManager.serverInstances.values():
        if instance.id in serversIds:
            usersServers.append(instance)

    try:
        return utils.getGlobalStats(usersServers), 200
    except Exception as e:
        abort(500, message=f"Failed to retrieve global stats: {str(e)}")
