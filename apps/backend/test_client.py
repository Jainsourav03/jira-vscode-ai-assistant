import websocket
import json


print("Connecting...")


ws = websocket.create_connection(
   "ws://127.0.0.1:8000/ws/client"
)
print("Connected")
register_data = {
   "type":"client_register",
   "userEmail":"developer@example.com",
   "clientId":"vscode-client-123"
}


ws.send(json.dumps(register_data))
print("Registration sent")


while True:
   try:
       message = ws.recv()
       print("RAW MESSAGE RECEIVED:")
       print(message)


   except Exception as e:


       print("Error:",e)

       break
