import Database.repositories
from Database.repositories import ServersRepository
import gevent
import gevent.pool
from gevent.lock import Semaphore
from gevent.threadpool import ThreadPool
_tpool = ThreadPool(10)
import os
import shutil
import subprocess
import time
import psutil
import utils
from rcon import RconClient, RconError, RconAuthError

serverInstances = {}
usedPorts = set()

class ServerSession:
    def __init__(self, id, name, command, working_dir=None):
        if not ServersRepository.doesServerExist(id):
            raise KeyError(f"Server with id '{id}' does not exist")
        self.name = name
        if isinstance(command, str):
            self.command = command.split()
        else:
            self.command = command
        self.working_dir = working_dir
        self.process = None
        self.listeners = []
        self.status_listeners = []
        self.log_history = []
        self.max_history = 500
        self._running = False
        self.output_thread = None
        self.monitor_thread = None
        self.port = utils.assignNewPort(self,utils.getNewPort(type="server"), type="server")
        self.rcon_port = utils.assignNewPort(self,utils.getNewPort(type="rcon"), type="rcon")
        self.last_stats = None
        self.last_stats_time = 0
        self.started_at = 0.0
        self.max_memory_mb = None
        self.max_players = None
        self._rcon: RconClient | None = None
        self._rcon_lock = Semaphore()
        self._stats_lock = Semaphore()
        self.id = id

    @property
    def running(self):
        """Return live running state and broadcast on real transitions."""
        live = self.is_running()
        if live != self._running:
            self.running = live
        return self._running

    @running.setter
    def running(self, value):
        """Setter that triggers a broadcast if the value actually changes."""
        if self._running != value:
            self._running = value
            self._broadcast_status(value)

    def add_listener(self, callback):
        if callback not in self.listeners:
            self.listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def add_status_listener(self, callback):
        """Register a callback for status changes (running state)."""
        if callback not in self.status_listeners:
            self.status_listeners.append(callback)

    def _broadcast_status(self, is_running):
        """Notify all registered status listeners."""
        for listener in self.status_listeners:
            try:
                listener(is_running)
            except Exception as e:
                print(f"Error in status listener callback: {e}")

    def _broadcast(self, line, source="server"):
        entry = self._updateHistory(line, source)

        # If source is a numeric ID (as string or int), resolve to username.
        # Otherwise, keep as-is (e.g. "server", "admin", "custom").
        if source != "server":
            is_numeric = False
            if isinstance(source, int):
                is_numeric = True
            elif isinstance(source, str) and source.isdigit():
                is_numeric = True

            if is_numeric:
                username = Database.repositories.UserRepository.getUsername(int(source))
                if username:
                    entry["source"] = username

        print(f"[DEBUG] _broadcast firing {len(self.listeners)} listener(s)")
        for listener in self.listeners:
            try:
                listener(entry)
            except Exception as e:
                print(f"Error in listener callback: {e}")

    def _updateHistory(self, line, source="server"):
        entry = {"line": line, "source": source}
        self.log_history.append(entry)
        if len(self.log_history) > self.max_history:
            self.log_history.pop(0)
        return entry

    def start(self):
        if self.running:
            print(f"Server '{self.name}' is already running!")
            return False

        if shutil.which("java") is None:
            print(f"Failed to start server '{self.name}': Java is not installed or not on PATH. Please install a Java Runtime Environment (JRE) and ensure 'java' is accessible.")
            return False

        mcVersion = utils.getMcVersion(self.working_dir) if self.working_dir else None
        if mcVersion:
            requiredJava = utils.getRequiredJavaVersion(mcVersion)
            installedVersions = utils.getInstalledJavaMajorVersions()
            if not any(v >= requiredJava for v in installedVersions):
                print(
                    f"Failed to start server '{self.name}': Minecraft {mcVersion} requires "
                    f"Java {requiredJava} or newer, but no suitable Java installation was found "
                    f"(found: {sorted(installedVersions) if installedVersions else 'none'}). "
                    f"Please install Java {requiredJava}+."
                )
                return False

        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=self.working_dir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )

            # Latch effective runtime limits at process start to avoid drift
            # if launch files are edited while the server is running.
            self.started_at = time.time()
            self.max_memory_mb = utils.getMaxMemoryMB(self.working_dir)
            self.max_players = utils.getMaxPlayers(self.working_dir)

            self.running = True

            self.output_thread = gevent.spawn(self._read_output)
            # Watch process liveness independently from stdout to ensure stop/crash broadcasts.
            self.monitor_thread = gevent.spawn(self._monitor_process_exit, self.process)

            print(f"Server '{self.name}' started!")
            print(f"Process ID: {self.process.pid}")
            return True

        except Exception as e:
            print(f"Failed to start: {e}")
            return False

    def _read_output(self):
        try:
            while True:
                # Use tpool to avoid blocking the eventlet hub on Windows
                line = self.process.stdout.readline()
                if not line:
                    break
                stripped_line = line.rstrip()
                self._broadcast(stripped_line)
                gevent.sleep(0)
        except Exception as e:
            self._broadcast(f"[ERROR: {e}]")
        finally:
            if self.process:
                _ = self.running

    def _monitor_process_exit(self, proc):
        """Wait for process exit and sync/broadcast running=False immediately."""
        try:
            proc.wait()
        except Exception as e:
            print(f"Process monitor error for '{self.name}': {e}")
        finally:
            if self.process is proc:
                self.running = False

    def _connect_rcon(self) -> bool:
        """
        Create and connect a new persistent RconClient.
        Must be called while already holding self._rcon_lock.
        Returns True on success, False on failure.
        """
        config = utils.getConfig()
        if not config:
            return False
        password = config.get('rconPassword', '')
        if not password:
            return False

        client = RconClient("127.0.0.1", self.rcon_port, password)
        try:
            client.connect()
            self._rcon = client
            print(f"[RCON] Connected for '{self.name}' on port {self.rcon_port}.")
            return True
        except Exception as e:
            # Silently fail if connection refused (common during server startup)
            # Log as a more neutral status if it's just a refusal, or an error otherwise.
            if isinstance(e, ConnectionRefusedError) or (hasattr(e, 'errno') and e.errno == 10061):
                 # This is expected during startup, no need to clutter the logs with errors
                 pass
            else:
                 print(f"[RCON] Failed to connect for '{self.name}': {e}")
            client.disconnect()
            return False

    def send_rcon_command(self, command: str) -> str | None:
        """
        Send a command over the persistent RCON connection and return the response.
        Lazily connects on the first call. Attempts one reconnect if the connection
        has gone stale. Returns None if RCON is unavailable.
        """
        with self._rcon_lock:
            if self._rcon is None:
                if not self._connect_rcon():
                    return None

            try:
                return self._rcon.send_command(command)
            except (RconError, RconAuthError, OSError) as e:
                print(f"[RCON] Connection lost for '{self.name}' ({e}), reconnecting…")
                self._rcon.disconnect()
                self._rcon = None
                if not self._connect_rcon():
                    return None
                try:
                    return self._rcon.send_command(command)
                except Exception as e2:
                    print(f"[RCON] Reconnect attempt failed for '{self.name}': {e2}")
                    self._rcon.disconnect()
                    self._rcon = None
                    return None

    def send_command(self, command, source="server"):
        if not self.running or not self.process:
            print(f"Can't send command - server not running")
            return False

        if not command.strip():
            return False

        try:
            # Use tpool to avoid blocking the hub on Windows when writing to pipe
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
            self._broadcast("> " + command, source)
            print(f"Sent command: {command}")
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            _ = self.running
            return False

    def attach(self):
        if not self.running:
            print(f"Server '{self.name}' is not running")
            return

        print(f"\n========== ATTACHED TO '{self.name}' ==========")
        print("Type commands below. Type 'detach' or 'exit' to exit.\n")

        def display_callback(entry):
            print(f"[SERVER + {self.name}] [{entry['source']}] {entry['line']}")

        self.add_listener(display_callback)

        try:
            while self.running:
                try:
                    user_input = input()

                    if not user_input.strip():
                        continue

                    if user_input.lower() in ('detach', 'exit'):
                        break

                    self.send_command(user_input)

                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\nPress Ctrl+D or type 'detach'/'exit' to exit")
        finally:
            self.remove_listener(display_callback)
            print(f"\n========== DETACHED FROM '{self.name}' ==========\n")

    def cleanup(self):
        """Release ports held by this instance back to the available pool."""
        with self._rcon_lock:
            if self._rcon is not None:
                self._rcon.disconnect()
                self._rcon = None
                print(f"[RCON] Persistent connection closed for '{self.name}'.")

        usedPorts.discard(self.port)
        usedPorts.discard(self.rcon_port)

    def stop(self, timeout=30):

        if not self.running:
            print(f"Server '{self.name}' is not running")
            return False

        print(f"Stopping server '{self.name}'...")

        self.send_command("stop")

        print(f"Waiting up to {timeout} seconds for shutdown...")
        for i in range(timeout):
            if self.process.poll() is not None:
                print("Server stopped successfully!")
                self.running = False
                self.cleanup()
                return True

            if (i + 1) % 5 == 0:
                print(f"  Still waiting... ({i + 1}/{timeout}s)")

            time.sleep(1)

        print("Server didn't stop, forcing...")
        self.process.terminate()
        time.sleep(2)

        if self.process.poll() is None:
            self.process.kill()

        self.running = False
        print("Server stopped (forced)")
        self.cleanup()
        return True

    def is_running(self):
        if self.process:
            return self.process.poll() is None
        return False

    def _ensure_psutil_proc(self):
        if not self.is_running() or self.process is None:
            return False

        try:
            # Cache the psutil.Process object to allow cpu_percent() to work across calls
            if not hasattr(self, '_psutil_proc') or self._psutil_proc.pid != self.process.pid:
                self._psutil_proc = psutil.Process(self.process.pid)
                self._child_procs = {} # Reset child cache for new process
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def get_memory_usage_mb(self):
        if not self._ensure_psutil_proc():
            return 0.0

        try:
            p = self._psutil_proc
            total_rss = 0

            try:
                total_rss += p.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return 0.0

            try:
                for child in p.children(recursive=True):
                    try:
                        total_rss += child.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            return round(total_rss / (1024 * 1024), 2)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return 0.0

    def get_cpu_usage_percent(self):
        if not self._ensure_psutil_proc():
            return 0.0

        try:
            p = self._psutil_proc
            total_cpu_percent = 0.0

            try:
                total_cpu_percent += p.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return 0.0

            try:
                children = p.children(recursive=True)
                current_child_pids = set()

                for child in children:
                    pid = child.pid
                    current_child_pids.add(pid)

                    if pid not in self._child_procs:
                        self._child_procs[pid] = child

                    try:
                        total_cpu_percent += self._child_procs[pid].cpu_percent(interval=None)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # Cleanup dead children from cache
                self._child_procs = {pid: proc for pid, proc in self._child_procs.items() if pid in current_child_pids}

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            return round(total_cpu_percent / (psutil.cpu_count() or 1), 2)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return 0.0

    def get_process_info(self):
        is_running = self.running
        pid = self.process.pid if is_running and self.process else 0
        uptime_seconds = 0.0

        if is_running and self._ensure_psutil_proc():
            try:
                create_time = self._psutil_proc.create_time()
                uptime_seconds = round(max(0.0, time.time() - create_time), 2)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                if self.started_at > 0:
                    uptime_seconds = round(max(0.0, time.time() - self.started_at), 2)
        elif is_running and self.started_at > 0:
            uptime_seconds = round(max(0.0, time.time() - self.started_at), 2)

        max_memory_mb = self.max_memory_mb if is_running and self.max_memory_mb is not None else utils.getMaxMemoryMB(self.working_dir)
        max_players = self.max_players if is_running and self.max_players is not None else utils.getMaxPlayers(self.working_dir)

        return {
            "server_id": self.id,
            "is_running": is_running,
            "pid": pid,
            "uptime_seconds": uptime_seconds,
            "max_memory_mb": max_memory_mb,
            "max_players": max_players,
            'server_port': self.port
        }
