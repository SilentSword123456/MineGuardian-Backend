# MineGuardian Backend — Wiki

Welcome to the MineGuardian Backend wiki! This wiki describes the intended behaviour of every module, class, and function in the codebase: its inputs, outputs, and any special edge cases the implementation must honour. Tests should be written (or verified) against this specification.

---

## Table of Contents

### Core Modules

| Page | Description |
|------|-------------|
| [Permission Enums](Permission-Enums.md) | Integer-valued enumerations used as permission IDs (`Database/perms.py`) |
| [Repository Layer](Repository-Layer.md) | Database operations for users, servers, players, and permissions (`Database/repositories.py`) |
| [RCON Client](RCON-Client.md) | Minecraft RCON protocol implementation (`rcon.py`) |
| [Utility Functions](Utility-Functions.md) | Configuration, server stats, port management, and helpers (`utils.py`) |
| [Server Session Manager](Server-Session-Manager.md) | Live server process management (`serverSessionsManager.py`) |
| [Server Installation](Server-Installation.md) | Download and set up Minecraft servers (`manageLocalServers.py`) |

### API Layer

| Page | Description |
|------|-------------|
| [Server Service Helpers](Server-Service-Helpers.md) | Internal service helpers for server operations (`services/server_services.py`) |
| [Authentication API](Authentication-API.md) | Login and JWT token endpoints (`services/auth.py`) |
| [Database Handler API](Database-Handler-API.md) | CRUD endpoints for users, players, settings, and permissions (`services/dbHandler.py`) |
| [Server Management API](Server-Management-API.md) | Server lifecycle and management endpoints (`services/servers.py`) |
