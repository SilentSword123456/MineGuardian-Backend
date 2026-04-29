# MineGuardian — Backend

The Python backend that powers MineGuardian. It handles everything the frontend needs: downloading and installing Minecraft server jars, launching and monitoring server processes, streaming console output in real time, and managing user accounts with JWT authentication.

It also ships with a standalone CLI so you can manage servers directly from a terminal without the frontend at all.

---

## What it does

### Server process management
Each Minecraft server runs as a closely managed subprocess. The backend spawns the process, holds a reference to it, monitors its lifecycle, and tears it down cleanly on stop. Every line written to stdout is captured the moment it's printed and immediately broadcast to connected clients over WebSockets — so the console in the frontend is a true live stream, not a poll.

### Real-time resource monitoring over WebSockets
Beyond console output, the backend continuously pushes CPU and RAM usage stats to the frontend via Socket.io. The frontend gauges always reflect what's actually happening right now — no polling, no delay.

### Full database layer
The backend uses a full relational database to persist everything:
- **Users** — accounts, credentials, verification state
- **Servers** — installed server records and metadata
- **Settings** — per-user and global configuration
- **Permissions** — access control between users and servers

### User accounts & email verification
Registration, login, and email verification are all built from scratch. On sign-up, the backend sends a verification email with a code via an email service integration. JWT tokens are issued on login and required for all protected API routes.

### Multi-runtime Java support
Different Minecraft versions require different Java versions. The backend supports configuring separate Java executables for versions 8, 11, 17, 21, and 25, and selects the right one per server automatically.

### CLI interface
`python main.py` drops you into an interactive menu for managing servers without touching the frontend — useful for headless setups or initial configuration.

---

## Requirements

- Python 3.13+
- Java installed (Java 21 or 25 recommended)
- Internet connection (for downloading server jars)

---

## Setup

```bash
git clone https://github.com/SilentSword123456/MineGuardian-Backend
cd MineGuardian-Backend
```

Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Then run:

```bash
python main.py
```

On first run, an interactive configuration wizard will walk you through the setup — no manual config file editing needed.

The only thing worth knowing in advance: **Java runtimes**. In the config, you can set absolute paths to Java executables for each supported version (8, 11, 17, 21, 25). If you only have one Java version installed, leave the others blank and the backend will fall back to the system default.

---

## Using the frontend

Once the backend is running, you have two options:

- **Just testing it out?** Head over to **[frontend.silentlab.work](https://frontend.silentlab.work/)** — it's already connected to a live backend, no setup needed.
- **Self-hosting?** Clone and run the frontend yourself. Instructions are in the **[MineGuardian-WebPage](https://github.com/SilentSword123456/MineGuardian-WebPage)** repo. Point it at your backend URL and you're good to go.

---

## Development mode

Set `FLASK_ENV=development` before running to enable dev aids:
- Verification codes are printed to the console instead of sent by email
- Additional debug features are enabled

---

## Tests

```bash
pytest
```

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| Language | Python 3.13 |
| Web framework | Flask |
| Real-time | Flask-SocketIO |
| Auth | JWT |
| Email | Resend |
| Database | SQLite |
| Server management | subprocess + psutil |
 
