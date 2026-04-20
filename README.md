# MineGuardian Backend

A Python-based backend and CLI tool for managing Minecraft servers. It allows you to download, install, run, and monitor Minecraft servers through both a terminal-based interface and a Flask-SocketIO API.

## Features

- **CLI Interface**: Interactive menu to manage servers.
- **REST API**: Modular endpoints to list, start, and stop servers.
- **Real-time Console**: Stream Minecraft server logs via SocketIO with 100-line history replay on connection.
- **Hardened API**: Robust websocket handlers that prevent server crashes from invalid client data.
- **Automatic Installation**: Helper scripts to download Vanilla Minecraft servers.
- **Server Management**: Run multiple servers in the background.
- **Auto-start API**: Configuration option to automatically launch the API server on startup.

## Stack

- **Language**: Python 3.13+
- **Web Framework**: Flask, Flask-CORS
- **Real-time Communication**: Flask-SocketIO
- **CLI Framework**: Questionary
- **Process Management**: subprocess, threading

## Requirements

- Python 3.13 or higher
- Java Runtime Environment (JRE) for running Minecraft servers
- Internet connection (for downloading server jars)

## Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mineguardian-backend
   ```

2. **Create a virtual environment (optional but recommended)**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuration**:
   Ensure `config.json` is present in the root directory. It is used to define the Minecraft startup command and Flask settings.

## Usage

### CLI (Main Entry Point)

Run the main script to access the interactive menu:

```bash
python main.py
```

From the menu, you can:
- Start the API Server.
- Download a new Minecraft Server.
- Run an existing Minecraft Server.
- Attach to a running server's console.

### API Server

The API can be started directly from `main.py` or by calling `api.py` (though `main.py` is the preferred way as it handles setup).

- **Auto-start**: Can be enabled in `config.json` via `autoStartApiServer`.
- **Host/Port**: Default `0.0.0.0:5000`, configurable in `config.json`.

#### API Endpoints

- `GET /health`: Health check.
- `POST /login`: Authenticate and set `accessToken` JWT cookie.
- `GET /isSessionValid`: Validate current JWT session.
- `GET /servers`: List visible servers.
- `GET /servers/<serverId>`: Get server details.
- `POST /servers/<serverId>/start`: Start server by id.
- `POST /servers/<serverId>/stop`: Stop server by id.
- `GET /servers/<serverId>/stats`: Get live server stats.
- `DELETE /servers/<serverId>/uninstall`: Uninstall server by id.
- `POST /manage/addServer`: Install/register server.
- `GET /manage/<software>/getAvailableVersions`: List installable versions.
- `GET /servers/globalStats`: Aggregate runtime stats for visible running servers.

#### Authentication

- `POST /login` validates `user_id` and `password` and sets JWT in a cookie named `accessToken`.
- On successful login, the token is returned via `Set-Cookie` (HttpOnly, `SameSite=None` with `Secure=True` outside local development; local development keeps `SameSite=Lax`/`Secure=False`), not as a JSON `access_token` field.
- Invalid credentials still return `401` with JSON error payload.

#### SocketIO Events

- `connect`:
    - Send auth payload once: `{ "serverId": <int> }`.
    - On success, backend binds `sid -> {user_id, server_id, server_name}`, joins the server room, replays console history, and emits `status/resources`.
- `console`:
    - Receive: real-time server logs for the connected server room.
    - Send command payload: `{ "message": "command" }`.
    - Response ack event: `console_ack` with `{ "ok", "code", "message" }`.
- `system`:
    - Send payload: `{ "message": "..." }`.
    - Receive system informational messages.
- `status`:
    - Receive running-state updates for current server room.
- `resources`:
    - Receive periodic resource updates.
- `error`:
    - Receive error messages for invalid socket context/payloads.

`console_ack.code` values:
- `SENT`, `INVALID_SERVER`, `INVALID_MESSAGE`, `SERVER_OFFLINE`, `DISPATCH_FAILED`.

## Configuration (`config.json`)

The project uses a `config.json` file for settings:

```json
{
    "startMinecraftServerCommand": "java -Xmx1024M -Xms1024M -jar server.jar nogui",
    "flaskConfig": {
        "SECRET_KEY": "your-secret-key",
        "SOCKETIO_CORS_ALLOWED_ORIGINS": "*"
    },
    "autoStartApiServer": true,
    "defaultApiServerConfig": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": true
    }
}
```

- `startMinecraftServerCommand`: The command used to launch the Minecraft `.jar` file.
- `flaskConfig`: Standard Flask and SocketIO configurations.
- `autoStartApiServer`: If set to `true`, the API server will start automatically when `main.py` is launched.
- `defaultApiServerConfig`: Default settings (host, port, debug) used when the API server starts automatically.

## Project Structure

```text
.
├── tests/                  # Automated unittest suite
├── services/               # Modular service layer and blueprints
│   ├── servers.py          # API routes for server management
│   └── server_services.py  # Business logic for server operations
├── api.py                  # Flask + SocketIO implementation
├── main.py                 # CLI entry point and menu logic
├── manageLocalServers.py   # Server installation/uninstall logic
├── utils.py                # Helpers (config, setup, stats, etc.)
├── serverSessionsManager.py # Manages server processes and I/O
├── config.json             # Application configuration
├── requirements.txt        # Python dependencies
└── servers/                # Directory where Minecraft servers are stored
```

## Scripts

- `main.py`: The primary script to interact with the application.
- `manageLocalServers.py`: Contains install/uninstall helpers for local Minecraft servers.
- `serverSessionsManager.py`: Handles the `subprocess.Popen` lifecycle for Minecraft servers.

## Env Vars

Currently, the application relies on `config.json`. 
- // TODO: Support loading configuration from environment variables for Docker support.

## Tests

The project includes an automated `unittest` suite under `tests/`.

Run all tests:
```bash
python -m unittest
```

Run selected API route tests:
```bash
python -m unittest tests/test_server_routes_api.py tests/test_endpoint_map_api.py
```

## License

- // TODO: Specify license (e.g., MIT, Apache 2.0).
