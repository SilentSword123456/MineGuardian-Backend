from flask import Blueprint, jsonify
import serverSessionsManager
from services.server_services import get_all_servers, get_server_instance, stop_server
import api
from utils import getPlayersOnline

servers_bp = Blueprint('servers', __name__)

@servers_bp.route('/servers', methods=['GET'])
def list_servers():
    return jsonify({'servers': get_all_servers()})

@servers_bp.route('/servers/<serverName>', methods=['GET'])
def getGeneralServerInfo(serverName):
     servers = get_all_servers()

     match = None
     for s in servers:
        if s['name'] == serverName:
            match = s
            break


     if not match:
             return jsonify({'error': 'Server not found'}), 404

     serverInstance = serverSessionsManager.serverInstances.get(serverName)
     if serverInstance and serverInstance.is_running():
             return jsonify(serverInstance.get_process_info())

     # Not running: return basic metadata
     return jsonify(match)



@servers_bp.route('/servers/<serverName>/start', methods=['POST'])
def start_minecraft_server(serverName):
    if not serverName:
        return jsonify({'error': 'No serverName provided'}), 400
    try:
        serverInstance = get_server_instance(serverName)
        api.register_socketio_listener(serverName, serverInstance)
        serverInstance.start()
        return jsonify({'message': f"Server '{serverName}' started successfully"}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400



@servers_bp.route('/servers/<serverName>/stop', methods=['POST'])
def stop_minecraft_server(serverName):
    if not serverName:
        return jsonify({'error': 'No serverName provided'}), 400
    try:
        stop_server(serverName)
        return jsonify({'message': f"Server '{serverName}' stopped successfully"}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400



@servers_bp.route('/servers/<serverName>/stats', methods=['GET'])
def get_server_stats(serverName):
    if not serverName:
        return jsonify({'error': 'No serverName provided'}), 400

    serverInstance = serverSessionsManager.serverInstances.get(serverName)
    if not serverInstance or not serverInstance.is_running():
        return jsonify({'error': f"Server '{serverName}' is not running"}), 404

    # Use cached stats if available and fresh (less than 10s old)
    import time
    if serverInstance.last_stats and (time.time() - serverInstance.last_stats_time < 10):
        return jsonify(serverInstance.last_stats), 200

    try:
        stats = {
            'cpu_usage_percent': serverInstance.get_cpu_usage_percent(),
            'memory_usage_mb': serverInstance.get_memory_usage_mb(),
            "online_players": getPlayersOnline(serverInstance)
        }
        # Update cache
        serverInstance.last_stats = stats
        serverInstance.last_stats_time = time.time()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': f"Failed to retrieve stats: {str(e)}"}), 500

