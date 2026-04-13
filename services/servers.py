from flask import request
from apiflask import APIBlueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity

import Database.repositories
import manageLocalServers
import serverSessionsManager
import utils
import api
from services.server_services import get_all_servers, get_server_instance, stop_server
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

servers_bp = APIBlueprint('servers', __name__)

@servers_bp.route('/servers', methods=['GET'])
@servers_bp.doc(**DOCS['list_servers'])
@servers_bp.output(ListServersOutputSchema)
def list_servers():
    return {'servers': get_all_servers()}, 200

@servers_bp.route('/servers/<serverName>', methods=['GET'])
@servers_bp.doc(**DOCS['get_general_server_info'])
@servers_bp.output(GeneralServerInfoOutputSchema)
def getGeneralServerInfo(serverName):
     servers = get_all_servers()

     match = None
     for s in servers:
        if s['server_id'] == serverName:
            match = s
            break


     if not match:
             abort(404, message='Server not found')

     serverInstance = serverSessionsManager.serverInstances.get(serverName)
     if serverInstance:
         info = serverInstance.get_process_info()
     else:
         info = {
             'server_id': match['server_id'],
             'is_running': False,
             'pid': 0,
             'uptime_seconds': 0.0,
             'max_memory_mb': match['max_memory_mb'],
             'max_players': match.get('online_players', {}).get('max', 20),
         }

     return {
         'server_id': info['server_id'],
         'is_running': info.get('is_running', False),
         'pid': info.get('pid', 0),
         'uptime_seconds': info.get('uptime_seconds', 0.0),
         'max_memory_mb': info.get('max_memory_mb', match['max_memory_mb']),
         'online_players': {'max': info.get('max_players', match.get('online_players', {}).get('max', 20))},
     }, 200



@servers_bp.route('/servers/<serverName>/start', methods=['POST'])
@servers_bp.doc(**DOCS['start_server'])
@servers_bp.output(StartServerOutputSchema)
def start_minecraft_server(serverName):
    if not serverName:
        abort(400, message='No serverName provided')
    try:
        serverInstance = get_server_instance(serverName)
        api.register_socketio_listener(serverName, serverInstance)
        serverInstance.start()
        return {'message': f"Server '{serverName}' started successfully"}, 200
    except ValueError as e:
        abort(400, message=str(e))



@servers_bp.route('/servers/<serverName>/stop', methods=['POST'])
@servers_bp.doc(**DOCS['stop_server'])
@servers_bp.output(StopServerOutputSchema)
def stop_minecraft_server(serverName):
    if not serverName:
        abort(400, message='No serverName provided')
    try:
        stop_server(serverName)
        return {'message': f"Server '{serverName}' stopped successfully"}, 200
    except ValueError as e:
        abort(400, message=str(e))



@servers_bp.route('/servers/<serverName>/stats', methods=['GET'])
@servers_bp.doc(**DOCS['get_server_stats'])
@servers_bp.output(GetServerStatsOutputSchema)
def get_server_stats_endpoint(serverName):
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
    userId = get_jwt_identity()
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

@servers_bp.route('/servers/<serverName>/uninstall', methods=['DELETE'])
@servers_bp.doc(**DOCS['remove_server'])
@servers_bp.output(RemoveServerOutputSchema)
@jwt_required()
def remove_server(serverName):
    userId = get_jwt_identity()
    if not serverName:
        abort(400, message='No serverName provided')

    status = manageLocalServers.uninstallMinecraftServer(serverName)
    if isinstance(status, dict) and 'error' in status:
        abort(400, message=status['error'])

    databaseStatus = Database.repositories.ServersRepository.removeServer(userId, serverName)
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
def global_stats():
    try:
        return utils.getGlobalStats(), 200
    except Exception as e:
        abort(500, message=f"Failed to retrieve global stats: {str(e)}")
