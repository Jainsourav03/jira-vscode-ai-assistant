from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.models import JiraTicketEvent
from app.response_models import MockTicketResponse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Jira VS Code Assistant Backend")

# Store connected VS Code clients
connected_clients = set()
# Prevent duplicate ticket sending

ticket_sent = False

def create_mock_ticket():
    mock_ticket = JiraTicketEvent(
        event_type = "ticket_assigned",
        ticket_key = "PROJ-123",
        ticket_title = "Fix login redirect issue",
        ticket_description = "Users are redirected to the wrong page after successful login.",
        ticket_status = "To Do",
        ticket_priority="High",
        ticket_url = "https://jira.example.com/browse/PROJ-123",
        comments=[
            "Issue reported by QA team.",
            "Needs investigation."
        ]
    )
    return mock_ticket

async def send_ticket_to_clients():

    global ticket_sent

    # If already sent, don't send again
    if ticket_sent:
        return
    mock_ticket = create_mock_ticket()
    logger.info(f"Automatic Jira ticket created: {mock_ticket.ticket_key}")
    disconnected_clients = []
    for client in connected_clients.copy():
        try:
            await client.send_json(mock_ticket.model_dump())
            logger.info("Ticket sent automatically")
            ticket_sent = True

        except Exception as e:
            logger.error(f"Broadcast failed: {e}")
            disconnected_clients.append(client)

    for client in disconnected_clients:
     connected_clients.remove(client) 

@app.websocket("/ws/client")
async def websocket_client(websocket: WebSocket):

    await websocket.accept()
    connected_clients.add(websocket)
    logger.info("VS Code client connected")
    logger.info(f"Connected clients: {len(connected_clients)}")

# Automatically send ticket once
    await send_ticket_to_clients()

    try:
        while True:
            message = await websocket.receive_text()
            logger.info(f"Received message: {message}")

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info("VS Code client disconnected")
        logger.info(f"Connected clients: {len(connected_clients)}")

@app.get("/dev/clients")
def get_connected_clients():

    logger.info( "/dev/clients endpoint accessed")

    return {
        "connected_clients":
        len(connected_clients)
    }

@app.get("/health")
def health_check():
    logger.info("Health check endpoint accessed")

    return {
"service": "jira-vscode-assistant-backend",
"status": "healthy",
"message": "Backend is running"
 }

# Keep this for Swagger schema
@app.post("/dev/mock-ticket",response_model=MockTicketResponse)
async def get_mock_ticket():
    mock_ticket = create_mock_ticket()
    logger.info(f"Manual ticket created: {mock_ticket.ticket_key}")
    await send_ticket_to_clients()
    return MockTicketResponse(
        broadcast_attempted=True,
        connected_clients=len(connected_clients),
        ticket_event=mock_ticket
    )