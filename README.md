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
- **Demo Client**: Minimal Python client for testing websocket connectivity.

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

- `GET /`: Health check.
- `GET /servers`: List all available servers and their statuses.
- `POST /start_server`: Start a specific server. Body: `{"serverName": "name"}`.
- `POST /stop_server`: Stop a specific server. Body: `{"serverName": "name"}`.

#### Authentication

- `POST /login` validates `user_id` and `password` and sets JWT in a cookie named `accessToken`.
- On successful login, the token is returned via `Set-Cookie` (HttpOnly, `SameSite=None` with `Secure=True` outside local development; local development keeps `SameSite=Lax`/`Secure=False`), not as a JSON `access_token` field.
- Invalid credentials still return `401` with JSON error payload.

#### SocketIO Events

- `connect`: Connect with `serverName` as a query parameter.
    - Joining a server's room automatically replays the last 100 lines of console history.
- `console`: 
    - Receive: Real-time server logs.
    - Send: Send commands to the server console. Body: `{"message": "command"}`.
- `message`:
    - Receive: General status messages or echo of sent messages.
- `error`:
    - Receive: Error messages if something goes wrong (e.g., invalid payload, server not running).

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
├── websocket_client/       # Minimal Python WS client for manual testing
│   └── client.py
├── tests/                  # Automated test suite
│   ├── test_api_websockets.py
│   └── reproduce_errors.py
├── services/               # Modular service layer and blueprints
│   ├── servers.py          # API Routes for server management
│   └── server_services.py  # Business logic for server operations
├── api.py                  # Flask and SocketIO implementation
├── main.py                 # CLI entry point and menu logic
├── setup.py                # Server installation and instance setup logic
├── utils.py                # Helper functions (config, download, etc.)
├── serverSessionsManager.py # Manages server processes and I/O
├── config.json             # Application configuration
├── requirements.txt        # Python dependencies
└── servers/                # Directory where Minecraft servers are stored
    └── <server_name>/      # Individual server files
```

## Scripts

- `main.py`: The primary script to interact with the application.
- `setup.py`: Contains functions for `installMinecraftServer`, `runMinecraftServer`, and `setupServerInstance`.
- `serverSessionsManager.py`: Handles the `subprocess.Popen` lifecycle for Minecraft servers.

## Env Vars

Currently, the application relies on `config.json`. 
- // TODO: Support loading configuration from environment variables for Docker support.

## Tests

The project includes a suite of automated tests using `unittest`:

- **Websocket Tests**: `python -m unittest tests/test_api_websockets.py`
    - Covers connection, history replay, message echo, and console streaming.
- **Negative Tests**: `python -m unittest tests/reproduce_errors.py`
    - Verifies that malformed websocket payloads do not crash the server.

## Demo Client

A minimal websocket client is provided in `websocket_client/client.py`.

To use it:
1. Start the API Server via `main.py`.
2. Ensure at least one Minecraft server is running.
3. Run the client:
   ```bash
   python websocket_client/client.py <serverName>
   ```
   Example: `python websocket_client/client.py myCoolServer`

## License

- // TODO: Specify license (e.g., MIT, Apache 2.0).
