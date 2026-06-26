from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from app.models import (JiraTicketEvent, DeveloperContextRequest)
from app.response_models import (MockTicketResponse, DeveloperContextResponse)
import logging
from datetime import datetime


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Jira VS Code Assistant Backend")


# Store connected clients
clients_by_email = {}

# Store developer context submissions
developer_contexts = {}

# Store generated mock tickets
generated_tickets = []

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

# -------------------------------
# Send Ticket Only To Assigned Developer
# -------------------------------
async def send_ticket_to_assignee(ticket):
    assignee_email = ticket.assignee_email

    logger.info(
        f"Looking for connected client of {assignee_email}"
    )

    matched_clients = clients_by_email.get(assignee_email, [])

    if len(matched_clients) == 0:
        logger.info(
            f"No active VS Code client found for {assignee_email}"
        )
        return 0

    disconnected_clients = []

    for client in matched_clients:
        try:
            await client["websocket"].send_json(
                ticket.model_dump()
            )

            client["last_seen"] = (
                datetime.now().isoformat()
            )

            logger.info(
                f"Ticket sent to {assignee_email} "
                f"(Client ID: {client['client_id']})"
            )

        except Exception:
            disconnected_clients.append(client)

    for client in disconnected_clients:
        matched_clients.remove(client)

    if len(matched_clients) == 0:
        clients_by_email.pop(assignee_email, None)

    return len(matched_clients)

# -------------------------------
# WebSocket Endpoint
# -------------------------------
@app.websocket("/ws/client")
async def websocket_client(websocket: WebSocket):
   await websocket.accept()
   email = None
   client_id = None
   logger.info("VS Code client connected")
   try:
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
       await send_ticket_to_clients()
       while True:
           message = await websocket.receive_text()
           logger.info(f"Message received: {message}")
           for client in clients_by_email[email]:
               if client["client_id"] == client_id:
                   client["last_seen"] = (datetime.now().isoformat())
   except WebSocketDisconnect:
       logger.info("Client disconnected")
       if email and client_id:
           for client in clients_by_email[email]:
               if client["client_id"] == client_id:
                   clients_by_email[email].remove(client)
           if len(clients_by_email[email]) == 0:
               del clients_by_email[email]
# -------------------------------
# Check connected clients
# -------------------------------
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
# Task 6 Developer Context Debug Endpoint
# -------------------------------
@app.get("/dev/tickets/{ticket_key}/developer-context")
def get_ticket_developer_context(ticket_key: str):

    submissions = developer_contexts.get(ticket_key, [])

    logger.info(
        f"Developer context requested for ticket: {ticket_key}"
    )

    return {
        "ticketKey": ticket_key,
        "submissions": submissions
    }

# -------------------------------
# Task 7 Ticket History Endpoint
# -------------------------------
@app.get("/dev/tickets")
def get_generated_tickets():

    logger.info("Returning generated ticket history")

    return {
        "tickets": generated_tickets
    }

# -------------------------------
# Task 3 Mock Ticket Endpoint
# -------------------------------


@app.post("/dev/mock-ticket")
async def get_mock_ticket(request: MockTicketRequest | None = None):

    ticket = create_mock_ticket(request)

    # Store generated ticket in memory
    generated_tickets.append({
    "key": ticket.ticket_key,
    "title": ticket.ticket_title,
    "assigneeEmail": ticket.assignee_email,
    "status": ticket.ticket_status
})

    logger.info(
    f"Mock ticket stored | Ticket: {ticket.ticket_key}"
    )

    matched_clients = await send_ticket_to_assignee(ticket)

    if matched_clients == 0:
        return {
            "broadcastAttempted": True,
            "deliveryType": "targeted",
            "assigneeEmail": ticket.assignee_email,
            "matchedClients": 0,
            "message":
                "No active VS Code client found for assignee"
        }

    return {
        "broadcastAttempted": True,
        "deliveryType": "targeted",
        "assigneeEmail": ticket.assignee_email,
        "matchedClients": matched_clients,
        "ticketKey": ticket.ticket_key
    }

# -------------------------------
# Task 5
# Submit Developer Context
# -------------------------------
@app.post(
    "/tickets/{ticket_key}/developer-context",
    response_model=DeveloperContextResponse
)
def submit_developer_context(
    ticket_key: str,
    request: DeveloperContextRequest
):

    # Validate ticket key
    if not ticket_key.strip():
        return DeveloperContextResponse(
            success=False,
            message="Invalid ticket key",
            ticketKey=ticket_key,
            submittedAt=""
        )

    # Validate additional context
    if not request.additionalContext.strip():
        return DeveloperContextResponse(
            success=False,
            message="additionalContext cannot be empty",
            ticketKey=ticket_key,
            submittedAt=""
        )

    # Store submission
    context = {
        "ticketKey": ticket_key,
        "userEmail": request.userEmail,
        "additionalContext": request.additionalContext,
        "repoPath": request.repoPath,
        "branchName": request.branchName,
        "notes": request.notes,
        "submittedAt": datetime.now().isoformat()
    }

    if ticket_key not in developer_contexts:
        developer_contexts[ticket_key] = []

    developer_contexts[ticket_key].append(context)

    logger.info(
        f"Developer context submitted | "
        f"Ticket={ticket_key} | "
        f"User={request.userEmail}"
    )

    return DeveloperContextResponse(
        success=True,
        message="Developer context submitted successfully",
        ticketKey=ticket_key,
        submittedAt=context["submittedAt"]
    )
