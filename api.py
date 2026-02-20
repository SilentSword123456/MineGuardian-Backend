from flask import Flask, jsonify, request
import os
from flask_cors import CORS

import setup
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

def register_socketio_listener(serverName, serverInstance):
    """Ensures a SocketIO broadcast listener is registered for the server instance."""
    if not hasattr(serverInstance, '_socketio_listener_added'):
        def socketio_listener(line):
            socketio.emit('console', {'data': line}, to=serverName)
            socketio.sleep(0) # Yield for the event loop
        serverInstance.add_listener(socketio_listener)
        serverInstance._socketio_listener_added = True

@app.route('/')
def home():
    return jsonify({
        'status': 'API is running'
    })

@app.route('/servers', methods=['GET'])
def list_servers():
    servers = []
    i = 1
    for name in os.listdir(os.path.join(DIR, "servers")):
        servers.append({
            'name': name,
            'id': i,
            'isRunning': (setup.runningServers[name].is_running() if name in setup.runningServers else False)
        })
        i += 1
    return jsonify({
        'servers': servers
    })

@app.route('/start_server', methods=['POST'])
def start_server():
    data = request.json
    serverName = data.get('serverName')

    if not serverName:
        return jsonify({'error': 'No serverName provided'}), 400

    if serverName in setup.runningServers:
        return jsonify({'error': f"Server '{serverName}' is already running"}), 400

    serverInstance = setup.setupServerInstance(os.path.join(DIR, "servers", serverName), serverName)
    
    # Register listener for SocketIO broadcasting
    register_socketio_listener(serverName, serverInstance)
    serverInstance.start()

    return (jsonify({'message': f"Server '{serverName}' started successfully"}), 200)


@app.route('/stop_server', methods=['POST'])
def stop_server():
    data = request.json
    serverName = data.get('serverName')

    if not serverName:
        return jsonify({'error': 'No serverName provided'}), 400

    if serverName not in setup.runningServers:
        return jsonify({'error': f"No instance found for Server '{serverName}'"}), 400

    serverInstance = setup.runningServers[serverName]
    serverInstance.stop()

    return jsonify({'message': f"Server '{serverName}' stopped successfully"}), 200


@socketio.on('connect')
def handle_connect():
    serverName = request.args.get('serverName')
    if not serverName:
        emit('error', {'data': 'No serverName provided in connection'})
        return False

    if serverName not in setup.runningServers:
        emit('error', {'data': f"Server '{serverName}' is not running"})
        return False

    join_room(serverName)
    print(f'Client connected to server room: {serverName}')
    emit('message', {'data': f"Connected to server {serverName}"})

    serverInstance = setup.runningServers[serverName]
    
    # Ensure SocketIO listener is registered (especially if server was started via CLI)
    register_socketio_listener(serverName, serverInstance)

    # Send recent history to the newly connected client
    for line in serverInstance.log_history:
        emit('console', {'data': line})


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

    if serverName not in setup.runningServers:
        emit('console', {'data': f"Server '{serverName}' is not running."})
        return

    serverInstance = setup.runningServers[serverName]
    serverInstance.send_command(data['message'])

def startServer(debug=False, port=5000, host="0.0.0.0"):
    socketio.run(app, debug=debug, port=port, host=host, allow_unsafe_werkzeug=True)

def stopServer():
    socketio.stop()