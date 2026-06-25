from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from app.models import JiraTicketEvent
from app.response_models import MockTicketResponse
import logging
from datetime import datetime
<<<<<<< Updated upstream
import uuid
import asyncio
=======
>>>>>>> Stashed changes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Jira VS Code Assistant Backend")

# Store connected clients
clients_by_email = {}
# -------------------------------
# Task 3 Request Model
# -------------------------------
class MockTicketRequest(BaseModel):
    assigneeEmail: str = "developer@example.com"
    ticketKey: str = "PROJ-123"
    title: str = "Fix login redirect issue"
# -------------------------------
# Create Mock Jira Ticket
# -------------------------------
def create_mock_ticket(data=None):
    if data:
        assignee_email = data.assigneeEmail
        ticket_key = data.ticketKey
        ticket_title = data.title
    else:
        assignee_email = "developer@example.com"
        ticket_key = "PROJ-123"
        ticket_title = "Fix login redirect issue"
    ticket = JiraTicketEvent(
        event_type="ticket_assigned",
        ticket_key=ticket_key,
        ticket_title=ticket_title,
        ticket_description=
        "Users are redirected to wrong page after login.",
        ticket_status="To Do",
        ticket_priority="High",
        ticket_url=f"https://jira.example.com/browse/{ticket_key}",
        comments=[
            "Issue reported by QA team.",
            "Needs investigation."
        ],
        assignee_email=assignee_email
    )
    return ticket
# -------------------------------
# Register VS Code Client
# -------------------------------
def register_client(
        email,
        client_id,
        websocket
):
    client_data = {
        "client_id": client_id,
        "websocket": websocket,
        "connected_at":datetime.now().isoformat(),
        "last_seen":datetime.now().isoformat()
    }
    if email not in clients_by_email:
        clients_by_email[email] = []

    clients_by_email[email].append(client_data)
    logger.info(
        f"Client registered successfully | "
        f"Email: {email} | "
        f"Client ID: {client_id}"
    )
# -------------------------------
# Send Ticket To Connected Clients
# -------------------------------
async def send_ticket_to_clients(ticket=None):
    if ticket is None:
        ticket = create_mock_ticket()
    logger.info(f"Automatic Jira ticket created: {ticket.ticket_key}")
    for email, clients in clients_by_email.items():
        for client in clients:
            await client["websocket"].send_json(ticket.model_dump())
            client["last_seen"] = datetime.now().isoformat()
            logger.info(f"Ticket sent to {email}")
<<<<<<< Updated upstream
=======
# -------------------------------
# WebSocket Endpoint
# -------------------------------
>>>>>>> Stashed changes
@app.websocket("/ws/client")
async def websocket_client(websocket: WebSocket):

    await websocket.accept()
    email = None
    client_id = None
    logger.info("VS Code client connected")
    try:
<<<<<<< Updated upstream

        # First message from VS Code
        data = await websocket.receive_json()

        email = data["userEmail"]

        client_id = register_client(
            email,
            websocket
        )

        # Send acknowledgement
        await websocket.send_json({

            "type": "client_registered",

            "status": "success",

            "userEmail": email

        })

        logger.info(
            f"{email} connected {client_id}"
        )
        await asyncio.sleep(1)

=======
        # Wait for registration message
        data = await websocket.receive_json()
        # Validate
        if (
            data.get("type") != "client_register"
            or "userEmail" not in data
            or "clientId" not in data
        ):
            await websocket.send_json({
                "type":"error",
                "message":"Invalid registration message"
            })
            logger.warning("Invalid registration rejected")
            return
        email = data["userEmail"]
        client_id = data["clientId"]
        register_client(
            email,
            client_id,
            websocket
        )
        # acknowledgement
        await websocket.send_json({
            "type":"client_registered",
            "status":"success",
            "userEmail":email
        })
        # Send automatic ticket
>>>>>>> Stashed changes
        await send_ticket_to_clients()
        while True:

            message = await websocket.receive_text()
<<<<<<< Updated upstream

            logger.info(
                f"Message received {message}"
            )
            await send_ticket_to_clients()

=======
            logger.info(f"Message received: {message}")
>>>>>>> Stashed changes
            for client in clients_by_email[email]:

                if client["client_id"] == client_id:
<<<<<<< Updated upstream

                    client["last_seen"] = (
                        datetime.now().isoformat()
                    )

    except WebSocketDisconnect:

=======
                    client["last_seen"] = (datetime.now().isoformat())
    except WebSocketDisconnect:
        logger.info("Client disconnected")
>>>>>>> Stashed changes
        if email and client_id:

            for client in clients_by_email[email]:

                if client["client_id"] == client_id:
<<<<<<< Updated upstream

                    clients_by_email[email].remove(
                        client
                    )

=======
                    clients_by_email[email].remove(client)
>>>>>>> Stashed changes
            if len(clients_by_email[email]) == 0:

                del clients_by_email[email]
<<<<<<< Updated upstream

        logger.info(
            "Client disconnected"
        )
=======
# -------------------------------
# Check connected clients
# -------------------------------
>>>>>>> Stashed changes
@app.get("/dev/clients")
def get_connected_clients():
    response = {}
    for email, clients in clients_by_email.items():
        response[email] = {
            "active_clients":len(clients)
        }
    return response

@app.get("/health")
def health_check():
    return {
        "service":"jira-vscode-assistant-backend",
        "status":"healthy",
        "message":"Backend is running"
    }
# -------------------------------
# Task 3 Mock Ticket Endpoint
# -------------------------------

@app.post("/dev/mock-ticket", response_model=MockTicketResponse)
async def get_mock_ticket(request: MockTicketRequest | None = None):

    ticket = create_mock_ticket(request)
    await send_ticket_to_clients(ticket)
    return MockTicketResponse(
        broadcast_attempted=True,
        connected_clients=sum(
            len(value)
            for value in clients_by_email.values()
        ),
        ticket_event=ticket
    )