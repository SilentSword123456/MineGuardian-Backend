from flask import Flask, jsonify, request
import os
import time
from flask_cors import CORS

import serverSessionsManager
import manageLocalServers
import utils
from utils import getConfig
from flask_socketio import SocketIO, emit, join_room, leave_room

DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config.update(getConfig()['flaskConfig'])
CORS(app)
socketio = SocketIO(
    app,
    cors_allowed_origins=app.config["SOCKETIO_CORS_ALLOWED_ORIGINS"],
    async_mode="threading"
)

from services.servers import servers_bp
app.register_blueprint(servers_bp)

def register_socketio_listener(serverName, serverInstance):
    """Ensures a SocketIO broadcast listener is registered for the server instance."""
    if not hasattr(serverInstance, '_socketio_listener_added'):
        print(f"Registering SocketIO listeners for server '{serverName}'")
        # Existing console listener
        def socketio_console_listener(line):
            socketio.emit('console', {'data': line}, to=serverName)
            socketio.sleep(0) # Yield for the event loop
        serverInstance.add_listener(socketio_console_listener)

        # New status listener (the "hook" in action)
        def socketio_status_listener(is_running):
            socketio.emit('status', {'running': is_running}, to=serverName)
            socketio.sleep(0)

        # Register the status listener to the server instance
        serverInstance.add_status_listener(socketio_status_listener)

        serverInstance._socketio_listener_added = True
    else:
        print(f"SocketIO listeners already registered for server '{serverName}'")

@app.route('/')
@app.route('/health')
def home():
    return jsonify({
        'status': 'ok',
        'timestamp': time.time()
    }), 200

@socketio.on('connect')
def handle_connect():
    serverName = request.args.get('serverName')
    if not serverName:
        print("Connection attempt without serverName")
        emit('error', {'data': 'No serverName provided in connection'})
        return False

    try:
        if serverName not in serverSessionsManager.serverInstances:
            print(f"Initializing new server instance for '{serverName}' during connection")
            serverInstance = utils.setupServerInstance(os.path.join(DIR, "servers", serverName), serverName)
        else:
            serverInstance = serverSessionsManager.serverInstances[serverName]

        register_socketio_listener(serverName, serverInstance)

        join_room(serverName)
        print(f'Client connected to server room: {serverName}')
        emit('message', {'data': f"Connected to server {serverName}"})

        for line in serverInstance.log_history:
            emit('console', {'data': line})

        emit('status', {'running': serverInstance.running})

        #if serverInstance.is_running():
        stats = utils.get_server_stats(serverInstance)
        emit('resources', stats)

        socketio.emit('status', {'running': serverInstance.running}, to=serverName, include_self=False)

    except Exception as e:
        print(f"ERROR in handle_connect for '{serverName}': {e}")
        import traceback
        traceback.print_exc()
        emit('error', {'data': f"Connection error: {str(e)}"})
        return False



@socketio.on('disconnect')
def handle_disconnect():
    serverName = request.args.get('serverName')
    if serverName:
        leave_room(serverName)
        print(f'Client disconnected from server room: {serverName}')
    else:
        print('Client disconnected (no serverName)')

@socketio.on('message')
def handleMessage(data):
    serverName = request.args.get('serverName')
    print(f'Message from server {serverName}: {data}')
    emit('message', {'data': f"Server {serverName} received: {data['message']}"})

@socketio.on('console')
def handleConsole(data):
    serverName = request.args.get('serverName')
    if not serverName:
        emit('error', {'data': 'No serverName provided'})
        return

    if serverName not in serverSessionsManager.serverInstances:
        emit('console', {'data': f"Server '{serverName}' is not running."})
        return

    serverInstance = serverSessionsManager.serverInstances[serverName]
    serverInstance.send_command(data['message'])

def _broadcast_stats():
    """Background task to broadcast server stats via SocketIO every 5 seconds."""
    while True:
        socketio.sleep(5)
        # Use list() to avoid dictionary modification issues
        for serverName, serverInstance in list(serverSessionsManager.serverInstances.items()):
            if serverInstance.is_running():
                try:
                    # Collect stats using the centralized function (force=True to get fresh data for broadcast)
                    stats = utils.get_server_stats(serverInstance, force=True)

                    # Emit to specific room for this server
                    socketio.emit('resources', stats, to=serverName)
                    print("Broadcasted stats for server '{}': {}".format(serverName, stats))
                except Exception as e:
                    print(f"Error broadcasting stats for '{serverName}': {e}")

socketio.start_background_task(_broadcast_stats)

def startServer(debug=False, port=5000, host="0.0.0.0"):
    socketio.run(app, debug=debug, port=port, host=host, allow_unsafe_werkzeug=True)

def stopServer():
    socketio.stop()