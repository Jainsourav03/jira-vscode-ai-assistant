import websocket
import json
import uuid

print("Connecting...")

ws = websocket.create_connection(
    "ws://127.0.0.1:8000/ws/client"
)
print("Connected")
<<<<<<< Updated upstream

register_data = {

    "type":
    "client_register",

    "userEmail":
    "developer@example.com",

    "clientId":
    f"vscode-client-{uuid.uuid4()}"

}

ws.send(
    json.dumps(register_data)
)

print("Registration sent")

while True:

=======
register_data = {
    "type":"client_register",
    "userEmail":"developer@example.com",
    "clientId":"vscode-client-123"
}

ws.send(json.dumps(register_data))
print("Registration sent")

while True:
>>>>>>> Stashed changes
    try:

        message = ws.recv()

        print(
            "RAW MESSAGE RECEIVED:"
        )

        print(message)

    except Exception as e:

<<<<<<< Updated upstream
        print(
            "Error:",
            e
        )
=======
        print("Error:",e)
>>>>>>> Stashed changes

        break