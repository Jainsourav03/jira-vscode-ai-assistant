import websocket
import json
import sys

# Check command-line arguments
if len(sys.argv) != 3:
    print("Usage:")
    print("python test_client.py <userEmail> <clientId>")
    print()
    print("Example:")
    print("python test_client.py developer@example.com vscode-client-123")
    sys.exit(1)

user_email = sys.argv[1]
client_id = sys.argv[2]

print("Connecting...")

try:
    ws = websocket.create_connection(
        "ws://127.0.0.1:8000/ws/client"
    )

    print("Connected")

    register_data = {
        "type": "client_register",
        "userEmail": user_email,
        "clientId": client_id
    }

    ws.send(json.dumps(register_data))

    print("Registration sent")
    print(f"User Email : {user_email}")
    print(f"Client ID  : {client_id}")
    print("-" * 50)

    while True:
        try:
            message = ws.recv()

            print("\nRAW MESSAGE RECEIVED:")
            print(message)

        except KeyboardInterrupt:
            print("\nClient stopped by user.")
            break

        except Exception as e:
            print("\nConnection closed.")
            print("Error:", e)
            break

except Exception as e:
    print("Failed to connect:", e)