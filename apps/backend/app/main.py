from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.models import JiraTicketEvent

app = FastAPI(
    title="Jira VS Code Assistant Backend"
)

connected_clients = set()

@app.websocket("/ws/client")
async def websocket_client(websocket: WebSocket):

    # Accept connection
    await websocket.accept()

    # Store client
    connected_clients.add(websocket)

    print("VS Code client connected")
    print(f"Connected clients: {len(connected_clients)}")
    await websocket.send_json({
    "ticket_key": "PROJ-123",
    "title": "Fix login redirect issue",
    "status":"In Progress",
"priority":"High",
"description":"Users are not redirected properly after login."
    })

    try:
        while True:
            # Keep connection alive
            message = await websocket.receive_text()
            print(f"Received message: {message}")

    except WebSocketDisconnect:

        # Remove disconnected client
        connected_clients.remove(websocket)

        print("VS Code client disconnected")
        print(f"Connected clients: {len(connected_clients)}")


@app.get("/dev/clients")
def get_connected_clients():
    return {
        "connected_clients": len(connected_clients)
    }

@app.get("/health")
def health_check():
    return {
        "service": "jira-vscode-assistant-backend",
        "status": "healthy",
        "message": "Backend is running"
    }

@app.post("/dev/mock-ticket", response_model=JiraTicketEvent)
def get_mock_ticket():
 mock_ticket = JiraTicketEvent(
    event_type="ticket_assigned",
    ticket_key="PROJ-123",
    ticket_title="Fix login redirect issue ",
    ticket_description="Users are redirected to the wrong page after the successfullogin.",
    ticket_status="To Do",
    ticket_priority="Higsource myenv/bin/activateh",
    ticket_url="https://jira.example.com/browse/PROJ-123",
    comments=[
        "Issue reported by QA team.",
            "Needs investigation."
    ]
 )
 return mock_ticket