from flask import Flask, jsonify
import os
from flask_cors import CORS
from utils import getConfig
from flask_socketio import SocketIO, emit

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
    print('Client connected')
    emit('message', {'data': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('custom_event')
def handle_custom_event(data):
    print(f'Received: {data}')
    # Echo back to client
    emit('response', {'data': f"Server received: {data['message']}; IT WORKED!!!!!"})

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)

