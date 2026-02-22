serverInstances = {}
usedPorts = set()

import subprocess
import threading
import time
import psutil
import utils

class ServerSession:
    def __init__(self, name, command, working_dir=None):
        self.name = name
        self.command = command.split()
        self.working_dir = working_dir
        self.process = None
        self.listeners = []
        self.log_history = []
        self.max_history = 100
        self.running = False
        self.output_thread = None
        self.port = utils.assignNewPort(self,utils.getNewPort(type="server"), type="server")
        self.rcon_port = utils.assignNewPort(self,utils.getNewPort(type="rcon"), type="rcon")

    def add_listener(self, callback):
        if callback not in self.listeners:
            self.listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def _broadcast(self, line):
        self._updateHistory(line)

        for listener in self.listeners:
            try:
                listener(line)
            except Exception as e:
                print(f"Error in listener callback: {e}")

    def _updateHistory(self, line):
        self.log_history.append(line)
        if len(self.log_history) > self.max_history:
            self.log_history.pop(0)

    def start(self):
        if self.running:
            print(f"Server '{self.name}' is already running!")
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
                cwd=self.working_dir
            )


            self.running = True

            self.output_thread = threading.Thread(
                target=self._read_output,
                daemon=True
            )
            self.output_thread.start()

            print(f"Server '{self.name}' started!")
            print(f"Process ID: {self.process.pid}")
            return True

        except Exception as e:
            print(f"Failed to start: {e}")
            return False

    def _read_output(self):
        try:
            for line in self.process.stdout:
                stripped_line = line.rstrip()
                self._broadcast(stripped_line)
                time.sleep(0) # Yield for context switching
        except Exception as e:
            self._broadcast(f"[ERROR: {e}]")
        finally:
            if self.process and self.process.poll() is not None:
                self.running = False

    def send_command(self, command):
        if not self.running or not self.process:
            print(f"Can't send command - server not running")
            return False

        if not command.strip():
            return False

        try:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
            self._updateHistory(f"> {command}") # TODO: after adding auth and authorisation, we can mark commands from the user differently in the history
            print(f"Sent command: {command}")
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False

    def attach(self):
        if not self.running:
            print(f"Server '{self.name}' is not running")
            return

        print(f"\n========== ATTACHED TO '{self.name}' ==========")
        print("Type commands below. Type 'detach' or 'exit' to exit.\n")

        def display_callback(line):
            print(f"[SERVER + {self.name}] {line}")

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

    def stop(self, timeout=30):

        if not self.is_running():
            print(f"Server '{self.name}' is not running")
            return False

        print(f"Stopping server '{self.name}'...")

        self.send_command("stop")

        print(f"Waiting up to {timeout} seconds for shutdown...")
        for i in range(timeout):
            if self.process.poll() is not None:
                print("Server stopped successfully!")
                self.running = False
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
        if not self._ensure_psutil_proc():
            return None

        try:
            p = self._psutil_proc
            try:
                create_time = p.create_time()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return None

            uptime = time.time() - create_time

            return {
                "name": self.name,
                "is_running": True,
                "pid": self.process.pid,
                "memory_usage_mb": self.get_memory_usage_mb(),
                "cpu_usage_percent": self.get_cpu_usage_percent(),
                "uptime_seconds": round(uptime, 2),
                "online_players": utils.getPlayersOnline(self)
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
