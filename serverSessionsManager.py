import subprocess
import threading
import time

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

    def add_listener(self, callback):
        if callback not in self.listeners:
            self.listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def _broadcast(self, line):
        self.log_history.append(line)
        if len(self.log_history) > self.max_history:
            self.log_history.pop(0)
        
        for listener in self.listeners:
            try:
                listener(line)
            except Exception as e:
                print(f"Error in listener callback: {e}")

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
