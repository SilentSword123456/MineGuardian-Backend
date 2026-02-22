from flask import Blueprint, jsonify, request

import serverSessionsManager
import setup
from services.server_services import get_all_servers, start_server, stop_server
import api

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
def start_server_route(serverName):
    if not serverName:
        return jsonify({'error': 'No serverName provided'}), 400
    try:
        serverInstance = start_server(serverName)
        api.register_socketio_listener(serverName, serverInstance)
        serverInstance.start()
        return jsonify({'message': f"Server '{serverName}' started successfully"}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@servers_bp.route('/servers/<serverName>/stop', methods=['POST'])
def stop_server_route(serverName):
    if not serverName:
        return jsonify({'error': 'No serverName provided'}), 400
    try:
        stop_server(serverName)
        return jsonify({'message': f"Server '{serverName}' stopped successfully"}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

