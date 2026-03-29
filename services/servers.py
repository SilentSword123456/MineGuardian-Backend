from flask import request
from apiflask import APIBlueprint, abort

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
    return {'servers': get_all_servers()}

@servers_bp.route('/servers/<serverName>', methods=['GET'])
@servers_bp.doc(**DOCS['get_general_server_info'])
@servers_bp.output(GeneralServerInfoOutputSchema)
def getGeneralServerInfo(serverName):
     servers = get_all_servers()

     match = None
     for s in servers:
        if s['name'] == serverName:
            match = s
            break


     if not match:
             abort(404, message='Server not found')

     serverInstance = serverSessionsManager.serverInstances.get(serverName)
     if serverInstance:
         info = serverInstance.get_process_info()
     else:
         info = {
             'name': match['name'],
             'is_running': False,
             'pid': 0,
             'uptime_seconds': 0.0,
             'max_memory_mb': match['max_memory_mb'],
             'max_players': match.get('online_players', {}).get('max', 20),
         }

     return {
         'name': info['name'],
         'is_running': info.get('is_running', False),
         'pid': info.get('pid', 0),
         'uptime_seconds': info.get('uptime_seconds', 0.0),
         'max_memory_mb': info.get('max_memory_mb', match['max_memory_mb']),
         'online_players': {'max': info.get('max_players', match.get('online_players', {}).get('max', 20))},
     }



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
        stats = utils.get_server_stats(serverInstance)
        return stats, 200
    except Exception as e:
        abort(500, message=f"Failed to retrieve stats: {str(e)}")

@servers_bp.route('/manage/addServer', methods=['POST'])
@servers_bp.doc(**DOCS['add_server'])
@servers_bp.output(AddServerOutputSchema)
def add_server():
    args = request.get_json()
    if not args or 'serverName' not in args or 'serverSoftware' not in args or 'serverVersion' not in args:
        abort(400, message='Missing required parameters: serverName, serverSoftware, serverVersion')

    serverName = args['serverName']
    serverSoftware = args['serverSoftware'].lower()
    serverVersion = args['serverVersion']
    acceptEula = args.get('acceptEula', False)

    return manageLocalServers.installMinecraftServer(serverSoftware, serverVersion, serverName, acceptEula)


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



@servers_bp.route('/servers/<serverName>/uninstall', methods=['DELETE'])
@servers_bp.doc(**DOCS['remove_server'])
@servers_bp.output(RemoveServerOutputSchema)
def remove_server(serverName):
    if not serverName:
        abort(400, message='No serverName provided')

    return manageLocalServers.uninstallMinecraftServer(serverName)

@servers_bp.route('/servers/globalStats', methods=['GET'])
@servers_bp.doc(**DOCS['get_global_stats'])
@servers_bp.output(GetServerStatsOutputSchema)
def global_stats():
    try:
        global_stats_payload = {
            'cpu_usage_percent': 0.0,
            'memory_usage_mb': 0.0,
            'max_memory_mb': 0,
            'online_players': {
                'online': 0,
                'max': 0,
                'players': []
            }
        }

        for serverInstance in list(serverSessionsManager.serverInstances.values()):
            if not serverInstance.is_running():
                continue

            stats = utils.get_server_stats(serverInstance, force=True)
            global_stats_payload['cpu_usage_percent'] += float(stats.get('cpu_usage_percent', 0.0))
            global_stats_payload['memory_usage_mb'] += float(stats.get('memory_usage_mb', 0.0))
            global_stats_payload['max_memory_mb'] += int(stats.get('max_memory_mb', 0))

            online_players = stats.get('online_players', {})
            players = online_players.get('players', [])

            global_stats_payload['online_players']['max'] += int(online_players.get('max', 0))
            global_stats_payload['online_players']['online'] += int(online_players.get('online', len(players)))
            global_stats_payload['online_players']['players'].extend(players)

        return global_stats_payload, 200
    except Exception as e:
        abort(500, message=f"Failed to retrieve global stats: {str(e)}")
