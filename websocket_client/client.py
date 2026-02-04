import socketio
import sys
import threading

sio = socketio.Client()

@sio.event
def connect():
    print("\n[Client] Connected to server")

@sio.event
def disconnect():
    print("\n[Client] Disconnected from server")

@sio.on('message')
def on_message(data):
    print(f"\n[Server Message] {data.get('data')}")

@sio.on('console')
def on_console(data):
    print(f"\n[Console Output] {data.get('data')}")

@sio.on('error')
def on_error(data):
    print(f"\n[Error] {data.get('data')}")

def start_client(server_name, url="http://localhost:5000"):
    try:
        # The serverName must be passed in query string during connection
        sio.connect(f"{url}?serverName={server_name}")
        
        print(f"--- Connected to server: {server_name} ---")
        print("Commands: ")
        print("  - Type any text to send as a console command")
        print("  - Type 'exit' to disconnect and quit")
        
        while True:
            try:
                command = input("> ")
                if command.lower() == 'exit':
                    break
                if command:
                    sio.emit('console', {'message': command})
            except EOFError:
                break
            except KeyboardInterrupt:
                break
                
        sio.disconnect()
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == '__main__':
    server_name = sys.argv[1] if len(sys.argv) > 1 else "myCoolServer"
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"
    
    start_client(server_name, api_url)
