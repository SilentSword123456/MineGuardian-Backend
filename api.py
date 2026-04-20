from flask import jsonify, request, session
from apiflask import APIFlask
import os
import time
import eventlet
from flask_cors import CORS
import serverSessionsManager
import utils
from Database.database import db, generateDB
from services.dbHandler import db_blueprint
from utils import getConfig
from flask_socketio import SocketIO, emit, join_room, leave_room
from services.servers import servers_bp
from services.auth import jwt, auth_blueprint
from flask_jwt_extended import decode_token
from Database import repositories

DIR = os.path.dirname(os.path.abspath(__file__))

app = APIFlask(__name__)
app.config.update(getConfig()['flaskConfig'])
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mineguardian.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = getConfig()['jwtSecretKey']
app.security_schemes = {
    'BearerAuth': {
        'type': 'http',
        'scheme': 'bearer',
        'bearerFormat': 'JWT',
    }
}
CORS(app)
socketio = SocketIO(
    app,
    cors_allowed_origins=app.config["SOCKETIO_CORS_ALLOWED_ORIGINS"],
    async_mode="eventlet"
)

app.register_blueprint(servers_bp)
app.register_blueprint(db_blueprint)
app.register_blueprint(auth_blueprint)
jwt.init_app(app)
db.init_app(app)

generateDB(app)

@app.route('/')
def homeRoute():
    return jsonify({
        'status': 'Test4',
    })

def register_socketio_listener(serverName, serverInstance):
    """Ensures a SocketIO broadcast listener is registered for the server instance."""
    if not hasattr(serverInstance, '_socketio_listener_added'):
        print(f"Registering SocketIO listeners for server '{serverName}'")
        # Existing console listener
        def socketio_console_listener(entry):
            socketio.emit('console', {'data': entry['line'], 'user': entry['source']}, to=serverName)
            eventlet.sleep(0) # Yield for the event loop
        serverInstance.add_listener(socketio_console_listener)

        # New status listener (the "hook" in action)
        def socketio_status_listener(is_running):
            socketio.emit('status', {'running': is_running}, to=serverName)
            eventlet.sleep(0)

        # Register the status listener to the server instance
        serverInstance.add_status_listener(socketio_status_listener)

        serverInstance._socketio_listener_added = True
    else:
        print(f"SocketIO listeners already registered for server '{serverName}'")

@app.route('/health')
def home():
    return jsonify({
        'status': 'ok',
        'timestamp': time.time()
    }), 200

@socketio.on('connect')
def handle_connect(auth=None):
    serverName = request.args.get('serverName')
    if not serverName:
        print("Connection attempt without serverName")
        emit('error', {'data': 'No serverName provided in connection'})
        return False

    # Get user information from JWT token if available
    user_id = None
    user_name = "Anonymous"

    if auth and 'token' in auth:
        try:
            decoded = decode_token(auth['token'])
            user_id = int(decoded['sub'])
            user_name = repositories.UserRepository.getUsername(user_id) or "Unknown"
        except Exception as e:
            print(f"Failed to decode token during connect: {e}")
            # We still allow connection as "Anonymous" if no token or invalid token, 
            # or we can reject it. The guidelines say "validates JWT", so let's be strict if auth is provided.
            emit('error', {'data': 'Invalid authentication token'})
            return False
    
    session['user_id'] = user_id
    session['user_name'] = user_name

    try:
        if serverName not in serverSessionsManager.serverInstances:
            print(f"Initializing new server instance for '{serverName}' during connection")
            serverInstance = utils.setupServerInstance(os.path.join(DIR, "servers", serverName), serverName)
        else:
            serverInstance = serverSessionsManager.serverInstances[serverName]

        register_socketio_listener(serverName, serverInstance)

        join_room(serverName)
        print(f'Client connected to server room: {serverName} as {user_name}')
        emit('system', {'data': f"Connected to server {serverName} as {user_name}"})

        for entry in serverInstance.log_history:
            emit('console', {'data': entry['line'], 'user': entry['source']})

        live_running = serverInstance.running
        emit('status', {'running': live_running})

        stats = utils.getServerStats(serverInstance)
        emit('resources', stats)

        socketio.emit('status', {'running': live_running}, to=serverName, include_self=False)

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

@socketio.on('system')
def handleSystemMessage(data):
    serverName = request.args.get('serverName')
    print(f'Message from server {serverName}: {data}')
    emit('system', {'data': f"Server {serverName} received: {data['message']}"})

@socketio.on('console')
def handleConsole(data):
    serverName = request.args.get('serverName')
    if not serverName:
        emit('error', {'data': 'No serverName provided'})
        return

    if serverName not in serverSessionsManager.serverInstances:
        emit('console', {'data': f"Server '{serverName}' is not running.", "user": "server"})
        return

    serverInstance = serverSessionsManager.serverInstances[serverName]
    userName = session.get('user_name', 'Anonymous')
    serverInstance.send_command(data['message'], source=userName)

def _broadcast_stats():
    """Background task to broadcast server stats via SocketIO every 5 seconds."""
    # Ensure this task only runs once in the current process
    if getattr(_broadcast_stats, '_running', False):
        return
    _broadcast_stats._running = True

    while True:
        socketio.sleep(5)
        # Use list() to avoid dictionary modification issues
        for serverName, serverInstance in list(serverSessionsManager.serverInstances.items()):
            if serverInstance.is_running():
                # Spawn separate greenlets to collect stats in parallel for each server
                socketio.start_background_task(_emit_server_stats, serverName, serverInstance)

def _emit_server_stats(serverName, serverInstance):
    """Worker greenlet to collect and emit stats for a single server."""
    try:
        # Collect stats using the centralized function (force=True to get fresh data for broadcast)
        # get_server_stats now handles its own per-server locking
        stats = utils.getServerStats(serverInstance, force=True)

        # Emit to specific room for this server
        socketio.emit('resources', stats, to=serverName)
        # print(f"Broadcasted stats for server '{serverName}'")
    except Exception as e:
        print(f"Error broadcasting stats for '{serverName}': {e}")

# Background task management
_broadcast_stats_started = False

def start_background_tasks():
    global _broadcast_stats_started
    if _broadcast_stats_started:
        return
    
    # In debug mode, Werkzeug's reloader starts the app twice. 
    # We only want the background task in the child process.
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return

    print("Starting background stats broadcast task...")
    socketio.start_background_task(_broadcast_stats)
    _broadcast_stats_started = True

# We don't call it here at module level anymore
# start_background_tasks()

def startServer(debug=False, port=5000, host="0.0.0.0"):
    # Ensure background tasks are started (only once per process)
    # If using reloader, only start in the child process.
    if not debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_background_tasks()

    socketio.run(app, debug=debug, port=port, host=host)

def stopServer():
    socketio.stop()