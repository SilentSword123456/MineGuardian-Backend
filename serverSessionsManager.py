import subprocess
import threading
import queue
import time

class ServerSession:
    def __init__(self, name, command, working_dir=None):
        self.name = name
        self.command = command.split()
        self.working_dir = working_dir
        self.process = None
        self.output_queue = queue.Queue()
        self.running = False
        self.output_thread = None

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
                self.output_queue.put(line.rstrip())
        except Exception as e:
            self.output_queue.put(f"[ERROR: {e}]")
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

        def display_output():
            while self.running and not stop_display.is_set():
                try:
                    line = self.output_queue.get(timeout=0.1)
                    print(f"[SERVER + {self.name}] {line}")
                except queue.Empty:
                    continue

        stop_display = threading.Event()

        display_thread = threading.Thread(target=display_output, daemon=True)
        display_thread.start()

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
            stop_display.set()
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
