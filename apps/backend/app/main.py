from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.models import JiraTicketEvent
from app.response_models import MockTicketResponse
import logging
from datetime import datetime
import uuid
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Jira VS Code Assistant Backend")

# Week 2 Connection Manager
clients_by_email = {}

def create_mock_ticket():
    mock_ticket = JiraTicketEvent(
        event_type="ticket_assigned",
        ticket_key="PROJ-123",
        ticket_title="Fix login redirect issue",
        ticket_description="Users are redirected to wrong page after login.",
        ticket_status="To Do",
        ticket_priority="High",
        ticket_url="https://jira.example.com/browse/PROJ-123",
        comments=[
            "Issue reported by QA team.",
            "Needs investigation."
        ]
    )
    return mock_ticket

def register_client(email, websocket):

    client_id = str(uuid.uuid4())

    client_data = {

        "client_id": client_id,
        "websocket": websocket,
        "connected_at": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat()
    }

    if email not in clients_by_email:

        clients_by_email[email] = []

    clients_by_email[email].append(client_data)

    return client_id

async def send_ticket_to_clients():

    ticket = create_mock_ticket()

    logger.info(f"Automatic Jira ticket created: {ticket.ticket_key}")

    for email, clients in clients_by_email.items():
        for client in clients:
            await client["websocket"].send_json(ticket.model_dump())
            client["last_seen"] = datetime.now().isoformat()
            logger.info(f"Ticket sent to {email}")
@app.websocket("/ws/client")
async def websocket_client(websocket: WebSocket):

    await websocket.accept()

    email = None
    client_id = None

    logger.info("VS Code client connected")

    try:

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

        await send_ticket_to_clients()

        while True:

            message = await websocket.receive_text()

            logger.info(
                f"Message received {message}"
            )
            await send_ticket_to_clients()

            for client in clients_by_email[email]:

                if client["client_id"] == client_id:

                    client["last_seen"] = (
                        datetime.now().isoformat()
                    )

    except WebSocketDisconnect:

        if email and client_id:

            for client in clients_by_email[email]:

                if client["client_id"] == client_id:

                    clients_by_email[email].remove(
                        client
                    )

            if len(clients_by_email[email]) == 0:

                del clients_by_email[email]

        logger.info(
            "Client disconnected"
        )
@app.get("/dev/clients")
def get_connected_clients():

    response = {}

    for email, clients in clients_by_email.items():

        response[email] = {"active_clients":len(clients)}

    return response

@app.get("/health")
def health_check():

    return {
        "service": "jira-vscode-assistant-backend",
        "status": "healthy",
        "message": "Backend is running"
    }

@app.post("/dev/mock-ticket",
response_model=MockTicketResponse)

async def get_mock_ticket():
    ticket = create_mock_ticket()
    await send_ticket_to_clients()
    return MockTicketResponse(
        broadcast_attempted=True,
        connected_clients=sum(
            len(value)
            for value in clients_by_email.values()
        ),
        ticket_event=ticket
    )