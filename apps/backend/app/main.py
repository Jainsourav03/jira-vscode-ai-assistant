from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.models import JiraTicketEvent
from app.response_models import MockTicketResponse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jira VS Code Assistant Backend"
)

# Store connected VS Code clients
connected_clients = set()


@app.websocket("/ws/client")
async def websocket_client(websocket: WebSocket):

    # Accept connection
    await websocket.accept()

    # Store client
    connected_clients.add(websocket)

    logger.info("VS Code client connected")
    logger.info(f"Connected clients: {len(connected_clients)}")

    try:
        while True:
            # Keep connection alive
            message = await websocket.receive_text()
            logger.info(f"Received message: {message}")

    except WebSocketDisconnect:

        # Remove disconnected client
        connected_clients.remove(websocket)

        logger.info("VS Code client disconnected")
        logger.info(f"Connected clients: {len(connected_clients)}")


@app.get("/dev/clients")
def get_connected_clients():

    logger.info("/dev/clients endpoint accessed")

    return {
        "connected_clients": len(connected_clients)
    }


@app.get("/health")
def health_check():

    logger.info("Health check endpoint accessed")

    return {
        "service": "jira-vscode-assistant-backend",
        "status": "healthy",
        "message": "Backend is running"
    }


@app.post("/dev/mock-ticket", response_model=MockTicketResponse)
async def get_mock_ticket():

    # Create mock ticket event
    mock_ticket = JiraTicketEvent(
        event_type="ticket_assigned",
        ticket_key="PROJ-123",
        ticket_title="Fix login redirect issue",
        ticket_description="Users are redirected to the wrong page after successful login.",
        ticket_status="To Do",
        ticket_priority="High",
        ticket_url="https://jira.example.com/browse/PROJ-123",
        comments=[
            "Issue reported by QA team.",
            "Needs investigation."
        ]
    )

    logger.info(f"Mock ticket created: {mock_ticket.ticket_key}")

    broadcast_attempted = False
    disconnected_clients = []

    # Broadcast to all connected clients
    if connected_clients:

        broadcast_attempted = True

        logger.info(
            f"Broadcasting ticket to {len(connected_clients)} clients"
        )

        for client in connected_clients.copy():
            try:
                await client.send_json(mock_ticket.model_dump())

            except Exception as e:
                logger.error(f"Broadcast failed: {e}")
                disconnected_clients.append(client)

        # Remove disconnected clients
        for client in disconnected_clients:
            connected_clients.remove(client)

    else:
        logger.info("No clients connected")

    return MockTicketResponse(
        broadcast_attempted=broadcast_attempted,
        connected_clients=len(connected_clients),
        ticket_event=mock_ticket
    )