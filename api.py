from gevent import monkey, sleep
monkey.patch_all()
from flask import jsonify, request, g
from apiflask import APIFlask, abort
from flask.cli import load_dotenv
import os
load_dotenv()
import re
import time
import logging
from flask_cors import CORS
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import serverSessionsManager
import utils
from Database.database import db, generateDB
from utils import getConfig
from flask_socketio import SocketIO, emit, join_room, leave_room

DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)

app = APIFlask(__name__)
app.config.update(getConfig()["flaskConfig"])

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=f"redis://{os.environ.get('REDIS_HOST', 'localhost')}:{os.environ.get('REDIS_PORT', 6379)}",
)

from Database.repositories import ServersRepository, ServersUsersPermsRepository
from services.dbHandler import db_blueprint
from services.servers import servers_bp
from services.auth import jwt, auth_blueprint
from Database.perms import ServersPermissions
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mineguardian.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = getConfig()["jwtSecretKey"]
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_ACCESS_COOKIE_NAME"] = "accessToken"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config["JWT_COOKIE_SECURE"] = os.environ.get("FLASK_ENV", "production") != "development"
app.config["JWT_COOKIE_SAMESITE"] = "None" if app.config["JWT_COOKIE_SECURE"] else "Lax"
app.security_schemes = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
}

# Explicit origin allowlist. Add entries here as needed — never use a
# catch-all in production.
_ALLOWED_WEB_ORIGINS = [
    "https://frontend.silentlab.work",
    re.compile(r"^https://[a-zA-Z0-9-]+\.andrei925-dumitru\.workers\.dev$"),
]

# Accept from all if not in production, else only from allowed origins
_IS_PRODUCTION = os.environ.get("FLASK_ENV", "production") == "production"
_CORS_ORIGINS = _ALLOWED_WEB_ORIGINS
if not _IS_PRODUCTION:
    # Always include localhost in development, but keep the production ones 
    # to allow testing them locally.
    _CORS_ORIGINS = ["http://localhost:5173"] + _ALLOWED_WEB_ORIGINS

CORS(app, supports_credentials=True, origins=_CORS_ORIGINS)

socketio = SocketIO(
    app,
    cors_allowed_origins=_CORS_ORIGINS,
    async_mode="gevent",
)

app.register_blueprint(servers_bp)
app.register_blueprint(db_blueprint)
app.register_blueprint(auth_blueprint)
jwt.init_app(app)
db.init_app(app)
generateDB(app)

# ─── Listener registry ────────────────────────────────────────────────────────
# Using a WeakSet so entries are automatically removed when a server instance
# is garbage-collected, with no monkey-patching required.
_listener_registered: set = set()
# Bind each socket connection to one validated server context.
_sid_server_context: dict[str, dict[str, int | str]] = {}


def register_socketio_listeners(server_name: str, server_instance) -> None:
    """Idempotently attach SocketIO broadcast listeners to a server instance."""
    if server_instance in _listener_registered:
        logger.debug("SocketIO listeners already registered server_name=%s", server_name)
        return

    logger.info("Registering SocketIO listeners server_name=%s", server_name)

    def console_listener(entry: dict) -> None:
        socketio.emit("console", entry, to=server_name)
        sleep(0)

    def status_listener(is_running: bool) -> None:
        socketio.emit("status", {"running": is_running}, to=server_name)
        sleep(0)

    server_instance.add_listener(console_listener)
    server_instance.add_status_listener(status_listener)
    _listener_registered.add(server_instance)


# ─── Logging helpers ──────────────────────────────────────────────────────────

_SENSITIVE_LOG_FIELDS = {
    "password", "token", "access_token", "refresh_token",
    "authorization", "cookie", "secret", "api_key",
}


def _sanitize_for_log(value):
    if isinstance(value, dict):
        return {
            k: "***" if str(k).lower() in _SENSITIVE_LOG_FIELDS else _sanitize_for_log(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_for_log(item) for item in value]
    return value


@app.before_request
def _log_request_start():
    g.request_start_time = time.perf_counter()
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
    started_at = getattr(g, "request_start_time", None)
    duration_ms = f"{(time.perf_counter() - started_at) * 1000:.2f}" if started_at else "unknown"
    logger.info(
        "HTTP request completed method=%s path=%s endpoint=%s status=%s duration_ms=%s",
        request.method,
        request.path,
        request.endpoint,
        response.status_code,
        duration_ms,
    )
    return response


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_server_id(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _current_sid() -> str | None:
    # request.sid is injected by Flask-SocketIO during socket events.
    return getattr(request, "sid", None)


def _resolve_server(auth_payload: dict) -> tuple[int, str] | tuple[None, None]:
    """
    Extract and validate serverId from the SocketIO auth payload.
    Returns (serverId, serverName) or (None, None) on failure.

    All events — connect, disconnect, console, system — pass serverId
    through the auth object for consistency.
    """
    server_id = _parse_server_id(auth_payload.get("serverId") if auth_payload else None)
    if server_id is None:
        return None, None
    if not ServersRepository.doesServerExist(server_id):
        return None, None
    server_name = ServersRepository.getServerName(server_id)
    return server_id, server_name


# ─── REST ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": time.time()}), 200


# ─── SocketIO events ─────────────────────────────────────────────────────────

@socketio.on("connect")
@jwt_required()
def handle_connect(auth=None):
    sid = _current_sid()
    logger.info("SocketIO connect sid=%s auth=%s", sid, _sanitize_for_log(auth or {}))
    user_id = int(get_jwt_identity())
    server_id, server_name = _resolve_server(auth)

    if server_id is None:
        logger.warning("SocketIO connect rejected: invalid or missing serverId sid=%s", sid)
        emit("error", {"data": "Invalid serverId"})
        return False

    if not ServersUsersPermsRepository.doesUserHavePerm(
            user_id, server_id, ServersPermissions.ViewServer.value
    ):
        logger.warning(
            "SocketIO connect rejected: no permission sid=%s user_id=%s server_id=%s",
            sid, user_id, server_id,
        )
        abort(401, message="You don't have permission to access this server")

    try:
        if server_name not in serverSessionsManager.serverInstances:
            logger.info("Initialising server instance server_name=%s", server_name)
            server_instance = utils.setupServerInstance(
                os.path.join(DIR, "servers", server_name), server_name, server_id
            )
        else:
            server_instance = serverSessionsManager.serverInstances[server_name]

        register_socketio_listeners(server_name, server_instance)
        if sid:
            _sid_server_context[sid] = {
                "user_id": user_id,
                "server_id": server_id,
                "server_name": server_name,
            }
        join_room(server_name)

        logger.info(
            "SocketIO connect accepted sid=%s user_id=%s server_id=%s server_name=%s",
            sid, user_id, server_id, server_name,
        )
        emit("system", {"data": f"Connected to server {server_name}"})

        for entry in list(server_instance.log_history):
            emit("console", entry)

        is_running = server_instance.running
        emit("status", {"running": is_running})
        emit("resources", utils.getServerStats(server_instance))

        # Broadcast current status to other clients in the room
        socketio.emit("status", {"running": is_running}, to=server_name, include_self=False)

    except Exception:
        if sid:
            _sid_server_context.pop(sid, None)
        logger.exception("SocketIO connect failed sid=%s server_name=%s", sid, server_name)
        emit("error", {"data": "Connection error — please try again"})
        return False


@socketio.on("disconnect")
def handle_disconnect():
    sid = _current_sid()
    context = _sid_server_context.pop(sid, None) if sid else None
    if not context:
        logger.info("SocketIO disconnected sid=%s with no bound server context", sid)
        return

    server_name = str(context["server_name"])
    leave_room(server_name)
    logger.info(
        "SocketIO disconnected sid=%s user_id=%s server_id=%s server_name=%s",
        sid,
        context["user_id"],
        context["server_id"],
        server_name,
    )


def _require_server_access():
    """
    Shared guard for event handlers that require an authenticated user with
    ViewServer permission. Uses sid-bound server context from connect.
    Returns (user_id, server_id, server_name) or emits an error and returns
    (None, None, None).
    """
    user_id = int(get_jwt_identity())
    sid = _current_sid()
    context = _sid_server_context.get(sid) if sid else None
    if not context:
        logger.warning("SocketIO access denied: no bound server context sid=%s", sid)
        emit("error", {"data": "No active server binding for this connection"})
        return None, None, None

    server_id = int(context["server_id"])
    server_name = str(context["server_name"])
    bound_user_id = int(context["user_id"])
    if bound_user_id != user_id:
        logger.warning(
            "SocketIO access denied: sid/user mismatch sid=%s bound_user_id=%s user_id=%s",
            sid, bound_user_id, user_id,
        )
        emit("error", {"data": "Invalid socket user context"})
        return None, None, None

    if not ServersUsersPermsRepository.doesUserHavePerm(
            user_id, server_id, ServersPermissions.ViewServer.value
    ):
        logger.warning(
            "SocketIO access denied: no permission sid=%s user_id=%s server_id=%s",
            sid, user_id, server_id,
        )
        abort(401, message="You don't have permission to access this server")

    return user_id, server_id, server_name


@socketio.on("system")
@jwt_required()
def handle_system(data):
    logger.info("SocketIO system event payload=%s", _sanitize_for_log(data))
    payload = data if isinstance(data, dict) else {}
    _, _, server_name = _require_server_access()
    if server_name is None:
        return
    emit("system", {"data": f"Server {server_name} received: {payload.get('message', '')}"})


@socketio.on("console")
@jwt_required()
def handle_console(data):
    logger.info("SocketIO console event payload=%s", _sanitize_for_log(data))
    payload = data if isinstance(data, dict) else {}
    user_id, server_id, server_name = _require_server_access()
    if server_name is None:
        emit("console_ack", {
            "ok": False,
            "code": "INVALID_SERVER",
            "message": "Invalid or unauthorized server access",
        })
        return

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        logger.warning(
            "Console command rejected: invalid message user_id=%s server_id=%s server_name=%s",
            user_id, server_id, server_name,
        )
        emit("error", {"data": "Invalid console message"})
        emit("console_ack", {
            "ok": False,
            "code": "INVALID_MESSAGE",
            "message": "Console message must be a non-empty string",
        })
        return

    if server_name not in serverSessionsManager.serverInstances:
        logger.warning(
            "Console command rejected: server offline user_id=%s server_id=%s server_name=%s",
            user_id, server_id, server_name,
        )
        emit("console", {"data": f"Server '{server_name}' is not running."})
        emit("console_ack", {
            "ok": False,
            "code": "SERVER_OFFLINE",
            "message": f"Server '{server_name}' is not running.",
        })
        return

    server_instance = serverSessionsManager.serverInstances[server_name]
    sent = server_instance.send_command(message, user_id)
    if not sent:
        logger.warning(
            "Console command dispatch failed user_id=%s server_id=%s server_name=%s",
            user_id, server_id, server_name,
        )
        emit("console_ack", {
            "ok": False,
            "code": "DISPATCH_FAILED",
            "message": "Command was not accepted by the server process",
        })
        return

    logger.info(
        "Console command forwarded user_id=%s server_id=%s server_name=%s message_len=%s",
        user_id, server_id, server_name, len(message),
    )
    emit("console_ack", {
        "ok": True,
        "code": "SENT",
        "message": "Command forwarded",
    })


# ─── Background stats broadcast ──────────────────────────────────────────────

def _emit_server_stats(server_name: str, server_instance) -> None:
    try:
        stats = utils.getServerStats(server_instance, force=True)
        socketio.emit("resources", stats, to=server_name)
    except Exception:
        logger.exception("Error broadcasting stats server_name=%s", server_name)


def _broadcast_stats() -> None:
    while True:
        socketio.sleep(5)
        for server_name, server_instance in list(serverSessionsManager.serverInstances.items()):
            if server_instance.is_running():
                socketio.start_background_task(_emit_server_stats, server_name, server_instance)


_broadcast_started = False


def _start_background_tasks() -> None:
    global _broadcast_started
    if _broadcast_started:
        return
    # In debug mode, Werkzeug's reloader forks the process; only start in child.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    logger.info("Starting background stats broadcast task")
    socketio.start_background_task(_broadcast_stats)
    _broadcast_started = True


def startServer(debug: bool = False, port: int = 5000, host: str = "0.0.0.0") -> None:
    _start_background_tasks()
    socketio.run(app, debug=debug, port=port, host=host)


def stopServer() -> None:
    socketio.stop()