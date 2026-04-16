from flask import jsonify, request, g
from apiflask import APIFlask, abort
import os
import re
import time
import logging
import eventlet
from flask_cors import CORS
from flask_jwt_extended import jwt_required, get_jwt_identity
import serverSessionsManager
import utils
from Database.database import db, generateDB
from Database.repositories import ServersRepository, ServersUsersPermsRepository
from services.dbHandler import db_blueprint
from utils import getConfig
from flask_socketio import SocketIO, emit, join_room, leave_room
from services.servers import servers_bp
from services.auth import jwt, auth_blueprint
from Database.perms import ServersPermissions

DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)

app = APIFlask(__name__)
app.config.update(getConfig()['flaskConfig'])
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mineguardian.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = getConfig()['jwtSecretKey']
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_ACCESS_COOKIE_NAME"] = "accessToken"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config["JWT_COOKIE_SECURE"] = os.environ.get('FLASK_ENV', 'production') != 'development'
app.config["JWT_COOKIE_SAMESITE"] = "None" if app.config["JWT_COOKIE_SECURE"] else "Lax"
app.security_schemes = {
    'BearerAuth': {
        'type': 'http',
        'scheme': 'bearer',
        'bearerFormat': 'JWT',
    }
}
# ORIGINAL allowlist (temporarily disabled):
# _ALLOWED_WEB_ORIGINS = [
#     "https://frontend.silentlab.work",
#     re.compile(r"^https://[a-zA-Z0-9-]+\.andrei925-dumitru\.workers\.dev$"),
# ]
#
# TEMPORARY: allow from everywhere while cross-server access is needed.
# TODO(backend-team, 2026-04-16, TEMP-OPEN-CORS): restore the allowlist above.
_ALLOWED_WEB_ORIGINS = re.compile(r".*")
CORS(app, supports_credentials=True, origins=_ALLOWED_WEB_ORIGINS)
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

_SENSITIVE_LOG_FIELDS = {"password", "token", "access_token", "refresh_token", "authorization", "cookie"}


def _sanitize_for_log(value):
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if str(key).lower() in _SENSITIVE_LOG_FIELDS:
                sanitized[key] = "***"
            else:
                sanitized[key] = _sanitize_for_log(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_for_log(item) for item in value]
    return value


@app.before_request
def _log_request_start():
    g._request_start_time = time.perf_counter()
    payload = request.get_json(silent=True) if request.is_json else None
    logger.info(
        "HTTP request started method=%s path=%s endpoint=%s args=%s payload=%s",
        request.method,
        request.path,
        request.endpoint,
        _sanitize_for_log(request.args.to_dict(flat=True)),
        _sanitize_for_log(payload),
    )


@app.after_request
def _log_request_end(response):
    started_at = getattr(g, "_request_start_time", None)
    duration_ms = ((time.perf_counter() - started_at) * 1000) if started_at else None
    logger.info(
        "HTTP request completed method=%s path=%s endpoint=%s status=%s duration_ms=%.2f",
        request.method,
        request.path,
        request.endpoint,
        response.status_code,
        duration_ms if duration_ms is not None else -1.0,
    )
    return response

def register_socketio_listener(serverName, serverInstance):
    """Ensures a SocketIO broadcast listener is registered for the server instance."""
    if not hasattr(serverInstance, '_socketio_listener_added'):
        print(f"Registering SocketIO listeners for server '{serverName}'")
        # Existing console listener
        def socketio_console_listener(line):
            socketio.emit('console', {'data': line}, to=serverName)
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


def praseSocketServerId(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

@app.route('/health')
def home():
    return jsonify({
        'status': 'ok',
        'timestamp': time.time()
    }), 200

@socketio.on('connect')
@jwt_required()
def handle_connect(auth=None):
    logger.info("SocketIO connect received args=%s", _sanitize_for_log(request.args.to_dict(flat=True)))
    userId = int(get_jwt_identity())
    serverId = praseSocketServerId(request.args.get('serverId'))
    if serverId is None:
        logger.warning("SocketIO connect rejected due to invalid serverId")
        emit('error', {'data': 'Invalid serverId'})
        return False

    if not ServersRepository.doesServerExist(serverId):
        logger.warning("SocketIO connect rejected server not found server_id=%s", serverId)
        abort(404, message='Server not found')

    if not ServersUsersPermsRepository.doseUserHavePerm(userId, serverId, ServersPermissions.ViewServer.value):
        logger.warning("SocketIO connect rejected permissions user_id=%s server_id=%s", userId, serverId)
        abort(401, message='You dont have the permission to do that')

    serverName = ServersRepository.getServerName(serverId)
    if not serverName:
        logger.warning("SocketIO connect rejected due to missing server name server_id=%s", serverId)
        emit('error', {'data': 'No serverName provided in connection'})
        return False

    try:
        if serverName not in serverSessionsManager.serverInstances:
            print(f"Initializing new server instance for '{serverName}' during connection")
            serverInstance = utils.setupServerInstance(os.path.join(DIR, "servers", serverName), serverName, serverId)
        else:
            serverInstance = serverSessionsManager.serverInstances[serverName]

        register_socketio_listener(serverName, serverInstance)

        join_room(serverName)
        logger.info("SocketIO connect accepted user_id=%s server_id=%s server_name=%s", userId, serverId, serverName)
        emit('system', {'data': f"Connected to server {serverName}"})

        for line in serverInstance.log_history:
            emit('console', {'data': line})

        live_running = serverInstance.running
        emit('status', {'running': live_running})

        stats = utils.getServerStats(serverInstance)
        emit('resources', stats)

        socketio.emit('status', {'running': live_running}, to=serverName, include_self=False)

    except Exception as e:
        logger.exception("SocketIO connect failed server_name=%s error=%s", serverName, e)
        import traceback
        traceback.print_exc()
        emit('error', {'data': f"Connection error: {str(e)}"})
        return False



@socketio.on('disconnect')
def handle_disconnect():
    logger.info("SocketIO disconnect received args=%s", _sanitize_for_log(request.args.to_dict(flat=True)))
    serverId = praseSocketServerId(request.args.get('serverId'))
    if serverId is None:
        return

    if not ServersRepository.doesServerExist(serverId):
        return

    serverName = ServersRepository.getServerName(serverId)
    if serverName:
        leave_room(serverName)
        logger.info("SocketIO disconnected from room server_id=%s server_name=%s", serverId, serverName)
    else:
        logger.info('SocketIO disconnected without server name server_id=%s', serverId)

@socketio.on('system')
@jwt_required()
def handleSystemMessage(data):
    logger.info("SocketIO system event received payload=%s args=%s", _sanitize_for_log(data), _sanitize_for_log(request.args.to_dict(flat=True)))
    userId = int(get_jwt_identity())
    serverId = praseSocketServerId(request.args.get('serverId'))
    if serverId is None:
        emit('error', {'data': 'Invalid serverId'})
        return

    if not ServersRepository.doesServerExist(serverId):
        abort(404, message='Server not found')

    if not ServersUsersPermsRepository.doseUserHavePerm(userId, serverId, ServersPermissions.ViewServer.value):
        abort(401, message='You dont have the permission to do that')

    serverName = ServersRepository.getServerName(serverId)
    logger.info("SocketIO system event processed server_name=%s", serverName)
    emit('system', {'data': f"Server {serverName} received: {data['message']}"})

@socketio.on('console')
@jwt_required()
def handleConsole(data):
    logger.info("SocketIO console event received payload=%s args=%s", _sanitize_for_log(data), _sanitize_for_log(request.args.to_dict(flat=True)))
    userId = int(get_jwt_identity())
    serverId = praseSocketServerId(request.args.get('serverId'))
    if serverId is None:
        emit('error', {'data': 'Invalid serverId'})
        return

    if not ServersRepository.doesServerExist(serverId):
        abort(404, message='Server not found')

    if not ServersUsersPermsRepository.doseUserHavePerm(userId, serverId, ServersPermissions.ViewServer.value):
        abort(401, message='You dont have the permission to do that')

    serverName = ServersRepository.getServerName(serverId)
    if not serverName:
        emit('error', {'data': 'No serverName provided'})
        return

    if serverName not in serverSessionsManager.serverInstances:
        logger.warning("SocketIO console command rejected because server is offline server_name=%s", serverName)
        emit('console', {'data': f"Server '{serverName}' is not running."})
        return

    serverInstance = serverSessionsManager.serverInstances[serverName]
    logger.info("SocketIO console command forwarded server_name=%s", serverName)
    serverInstance.send_command(data['message'])

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
