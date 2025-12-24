import questionary
from flask import Flask, jsonify, request
import os
from flask_cors import CORS

import setup
from utils import getConfig
from flask_socketio import SocketIO, emit, join_room

DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config.update(getConfig()['flaskConfig'])
CORS(app)
socketio = SocketIO(
    app,
    cors_allowed_origins=app.config["SOCKETIO_CORS_ALLOWED_ORIGINS"],
    async_mode="eventlet"
)

isConsoleActive = False
serverInstance = None

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
    if(serverName in setup.runningServers):
        global isConsoleActive
        global serverInstance
        isConsoleActive = True
        serverInstance = setup.runningServers[serverName]
        join_room(serverName)
        print('Client connected to server room:', serverName)
        emit('message', {'data': f"Connected to server {serverName}"})



@socketio.on('disconnect')
def handle_disconnect():
    global serverInstance
    global isConsoleActive
    serverInstance = None
    isConsoleActive = False
    print('Client disconnected')

@socketio.on('message')
def handleMessage(data):
    serverName = request.args.get('serverName')
    print(f'Message from server {serverName}: {data}')
    emit('message', {'data': f"Server {serverName} received: {data['message']}"})

@socketio.on('console')
def handleConsole(data):
    global serverInstance
    global isConsoleActive
    serverName = request.args.get('serverName')
    if not isConsoleActive:
        emit('console', {'data': f"Console is not active on server {serverName}."})
        return
    if serverInstance is None:
        serverInstance = setup.getServerInstance(serverName)

    serverInstance.send_command(data['message'])
    print(f'Message from server {serverName}: {data}')

def startServer(debug=True, port=5000, host="0.0.0.0"):
    global serverInstance
    global isConsoleActive
    socketio.run(app, debug=debug, port=port, host=host)

    while True:
        if isConsoleActive:
            if serverInstance is None:
                serverInstance = setup.getServerInstance(request.args.get('serverName'))

            output = serverInstance._read_output()
            questionary.print(f"Emitting console data: {output}", style="fg:cyan")
            emit('console', {'data': serverInstance._read_output()})

def stopServer():
    socketio.stop()
"""if __name__ == '__main__':
    global serverInstance
    global isConsoleActive
    socketio.run(app, debug=True, port=5000)

    while True:
        if isConsoleActive:
            if serverInstance is None:
                serverInstance = setup.getServerInstance(request.args.get('serverName'))

            emit('console', {'data': serverInstance.output_queue.get()})"""

