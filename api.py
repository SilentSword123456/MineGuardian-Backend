from flask import Flask, jsonify, request
import os
from flask_cors import CORS
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
    serverId = request.args.get('serverId')
    if(serverId):
        join_room(serverId)
        print('Client connected to server room:', serverId)
        emit('message', {'data': f"Connected to server {serverId}"})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('message')
def handleMessage(data):
    server_id = request.args.get('serverId')
    print(f'Message from server {server_id}: {data}')
    emit('message', {'data': f"Server {server_id} received: {data['message']}"})

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)

