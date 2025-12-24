import threading
import queue

import questionary
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
    async_mode="eventlet"
)

activeDisplayThreads = {}
stopEvents = {}
roomClientCount = {}

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
            'id': i
        })
        i += 1
    return jsonify({
        'servers': servers
    })

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

    if serverName not in roomClientCount:
        roomClientCount[serverName] = 0
    roomClientCount[serverName] += 1

    print(f'Client connected to server room: {serverName} (total clients: {roomClientCount[serverName]})')
    emit('message', {'data': f"Connected to server {serverName}"})

    if serverName not in activeDisplayThreads or not activeDisplayThreads[serverName].is_alive():
        serverInstance = setup.runningServers[serverName]
        stopEvents[serverName] = threading.Event()

        def display_output():
            print(f"Starting console display thread for server {serverName}")
            while serverInstance.running and not stopEvents[serverName].is_set():
                try:
                    line = serverInstance.output_queue.get(timeout=0.1)
                    socketio.emit('console', {'data': line}, to=serverName)
                except queue.Empty:
                    continue
            print(f"Console display thread stopped for server {serverName}")

        display_thread = threading.Thread(target=display_output, daemon=True)
        activeDisplayThreads[serverName] = display_thread
        display_thread.start()
        print(f"Console display thread started for server {serverName}")


@socketio.on('disconnect')
def handle_disconnect():
    serverName = request.args.get('serverName')
    if not serverName:
        print('Client disconnected (no serverName)')
        return

    leave_room(serverName)

    if serverName in roomClientCount:
        roomClientCount[serverName] -= 1
        print(f'Client disconnected from server room: {serverName} (remaining clients: {roomClientCount[serverName]})')

        if roomClientCount[serverName] <= 0:
            if serverName in stopEvents:
                stopEvents[serverName].set()
                print(f'Stopping console display thread for server {serverName} (no clients remaining)')
            roomClientCount[serverName] = 0
    else:
        print(f'Client disconnected from server room: {serverName}')

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
    socketio.run(app, debug=debug, port=port, host=host)

def stopServer():
    for serverName in list(stopEvents.keys()):
        stopEvents[serverName].set()
    socketio.stop()

"""
if __name__ == '__main__':
    global serverInstance
    global isConsoleActive
    socketio.run(app, debug=True, port=5000)

    while True:
        if isConsoleActive:
            if serverInstance is None:
                serverInstance = setup.getServerInstance(request.args.get('serverName'))

            emit('console', {'data': serverInstance.output_queue.get()})
"""