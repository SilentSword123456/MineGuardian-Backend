# MineGuardian Backend

A Python-based backend and CLI tool for managing Minecraft servers. It allows you to download, install, run, and monitor Minecraft servers through both a terminal-based interface and a Flask-SocketIO API.
## Requirements

- Python 3.13 or higher
- Java Runtime Environment (JRE) for running Minecraft servers
- Internet connection (for downloading server jars)

## Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/SilentSword123456/MineGuardian-Backend
   cd MineGuardian-Backend
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
### Access

To access it, you will need to install the frontend. You can find those instructions here https://github.com/SilentSword123456/MineGuardian-WebPage

## Configuration (`config.json`)

The project uses a `config.json` file for settings:

```json
{
    "startMcServerArguments": "-Xmx1024M -Xms1024M -jar server.jar nogui",
    "javaRuntimes": {
        "8":  "",
        "11": "",
        "17": "",
        "21": "",
        "25": ""
    },
    "flaskConfig": {
        "SECRET_KEY": "",
        "SOCKETIO_CORS_ALLOWED_ORIGINS": "*"
    },
    "autoStartApiServer": false,
    "defaultApiServerConfig": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": true
    },
    "rconPassword": "",
    "jwtSecretKey": ""
}
```

- `startMcServerArguments`: The arguments used to launch the Minecraft `.jar` file.
- `javaRuntimes`: The path for eatch java version, I recommand having at least java 25 or 21 installed
- `flaskConfig`: Standard Flask and SocketIO configurations.
- `autoStartApiServer`: If set to `true`, the API server will start automatically when `main.py` is launched.
- `defaultApiServerConfig`: Default settings (host, port, debug) used when the API server starts automatically.

## Env Vars
`FLASK_ENV`: If this is set to `development`, the app will dispaly the verification codes in the console instead of sending them, and will enable onther feutures that helped me develop the app.

## Tests

Run all tests:
```bash
pytest
```
