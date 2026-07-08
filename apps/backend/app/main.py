from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from pydantic import BaseModel, Field
from app.models import (JiraTicketEvent, DeveloperContextRequest, ClientRegistrationRequest, JiraWebhookPayload, AssigneeMappingRequest)
from app.response_models import (DeveloperContextResponse)
import logging
from datetime import datetime
from app.config import settings
from app.storage import load_state, save_state


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Jira VS Code Assistant Backend")

# Storage
# Storage

clients_by_email = {}

state = load_state()

generated_tickets = state["tickets"]
developer_contexts = state["developerContext"]
assignee_email_map = state["assigneeMap"]
delivery_history = state["deliveryHistory"]

# Mock Ticket Request Model

class MockTicketRequest(BaseModel):

    assigneeEmail: str = Field(..., min_length=1)
    ticketKey: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)

# Create Mock Ticket


    assigneeEmail: str = Field(..., min_length=1)
    ticketKey: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)

# Create Mock Ticket

def create_mock_ticket(data=None):

    if data:
        assignee_email = data.assigneeEmail
        ticket_key = data.ticketKey
        ticket_title = data.title

    else:
        assignee_email = "developer@example.com"
        ticket_key = "PROJ-123"
        ticket_title = "Fix login redirect issue"

    if not ticket_key.strip():

        raise HTTPException(status_code=400, detail="Ticket key cannot be empty")

    ticket = JiraTicketEvent(
        event_type= "ticket_assigned",
        ticket_key= ticket_key,
        ticket_title= ticket_title,
        ticket_description= "Users are redirected to wrong page after login.",
        ticket_status="To Do",
        ticket_priority="High",
        ticket_url=(f"{settings.BACKEND_PUBLIC_URL}/browse/{ticket_key}"),
        comments=["Issue reported by QA team.", "Needs investigation."],
        assignee_email=assignee_email
    )
    return ticket

#Add a normalization function

def normalize_ticket_event(
    ticket: JiraTicketEvent,
    source: str = "mock",
    assignee_display_name: str | None = None,
    project_key: str | None = None,
):

    created_at = datetime.utcnow().isoformat() + "Z"

    return {
        "type": "ticket_assigned",
        "ticket": {
            "key": ticket.ticket_key,
            "title": ticket.ticket_title,
            "description": ticket.ticket_description,
            "status": ticket.ticket_status,
            "priority": ticket.ticket_priority,
            "url": ticket.ticket_url,
            "assigneeEmail": ticket.assignee_email,
            "assigneeDisplayName": assignee_display_name,
            "projectKey": project_key,
            "comments": ticket.comments,
        },
        "metadata": {
            "source": source,
            "eventId": f"{source}-{ticket.ticket_key}-{created_at}",
            "createdAt": created_at,
        },
    }

# Register Client

def register_client(email, client_id, websocket):

    if email not in clients_by_email:
        clients_by_email[email] = []

    # Prevent duplicate client registration
    for client in clients_by_email[email]:
        if client["client_id"] == client_id:
            client["websocket"] = websocket
            client["last_seen"] = datetime.now().isoformat()
            return

    clients_by_email[email].append(
        {
            "client_id": client_id,
            "websocket": websocket,
            "connected_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat()
        }
    )

    logger.info(f"{email} -> {client_id} registered")

# Send Ticket

async def send_ticket_to_clients(ticket, event=None):
    email = ticket.assignee_email

    if email not in clients_by_email:
        logger.info(f"No connected client for {email}")
        return False

    # If no normalized event was provided (e.g. mock ticket),
    # create one automatically.
    if event is None:
        event = normalize_ticket_event(ticket)

    # If no normalized event was provided (e.g. mock ticket),
    # create one automatically.
    if event is None:
        event = normalize_ticket_event(ticket)

    dead_clients = []

    for client in clients_by_email[email]:
        try:
            await client["websocket"].send_json(event)

            client["last_seen"] = datetime.now().isoformat()

            logger.info(
                f"Ticket sent to {email} ({client['client_id']})"
            )

        except Exception as e:
            logger.error(str(e))
            dead_clients.append(client)

    async def send_ticket_to_clients(ticket, event=None):
     email = ticket.assignee_email

    if email not in clients_by_email:
        logger.info(f"No connected client for {email}")
        return False

    if event is None:
        event = normalize_ticket_event(ticket)

    dead_clients = []

    for client in clients_by_email[email]:
        try:
            await client["websocket"].send_json(event)
            client["last_seen"] = datetime.now().isoformat()

            logger.info(
                f"Ticket sent to {email} ({client['client_id']})"
            )

        except Exception as e:
            logger.error(str(e))
            dead_clients.append(client)

    for client in dead_clients:
        clients_by_email[email].remove(client)

    if email in clients_by_email and len(clients_by_email[email]) == 0:
        del clients_by_email[email]

    return True



# Health Check

@app.get("/health")
def health_check():

    return {
      "service":"jira-vscode-assistant-backend",
      "status":"healthy",
      "environment":settings.APP_ENV

    }

# Connected Clients

@app.get("/dev/clients")
def get_connected_clients():

    response = {}

    for email, clients in clients_by_email.items():
        response[email] = {
            "active_clients": len(clients),
            "clients": [
                {
                    "clientId": client["client_id"],
                    "connectedAt": client["connected_at"],
                    "lastSeen": client["last_seen"]
                }
                for client in clients
            ]
        }

    return response

# Ticket History

@app.get("/dev/tickets")
def get_generated_tickets():

    return {
        "tickets":generated_tickets
    }

#ticket key

@app.get("/dev/tickets/{ticket_key}")
def get_ticket(ticket_key: str):

    for ticket in generated_tickets:
        if ticket["key"] == ticket_key:
            return ticket

    raise HTTPException(
        status_code=404,
        detail="Ticket not found"
    )

# Developer Context GET

@app.get("/dev/tickets/{ticket_key}/developer-context")
def get_ticket_developer_context(ticket_key: str):

    submissions = developer_contexts.get(ticket_key, [])

    return {
        "ticketKey": ticket_key,
        "submissions": submissions
    }

#dilivery history
@app.get("/dev/delivery-history")
def get_delivery_history(ticketKey: str | None = None):

    if ticketKey:
        return [
            item
            for item in delivery_history
            if item["ticketKey"] == ticketKey
        ]

    return delivery_history

#assignee maps 

@app.get("/dev/assignee-map")
def get_assignee_mapping():

    return assignee_email_map

@app.post("/dev/assignee-map")
def add_assignee_mapping(request: AssigneeMappingRequest):

    assignee_email_map[request.accountId] = request.email

#task 12 
    save_state(
    generated_tickets,
    developer_contexts,
    assignee_email_map,
    delivery_history,
)

    return {
        "success": True,
        "accountId": request.accountId,
        "email": request.email
    }

# Mock Ticket

@app.post("/dev/mock-ticket")
async def get_mock_ticket(request: MockTicketRequest):

    ticket = create_mock_ticket(request)

    generated_tickets.append(
        {
            "key": ticket.ticket_key,
            "title": ticket.ticket_title,
            "assigneeEmail": ticket.assignee_email,
            "status": ticket.ticket_status
        }
    )

    # Send ticket to connected client(s)
    delivered = await send_ticket_to_clients(ticket)

    # Store delivery history
    delivery_history.append(
    {
        "ticketKey": ticket.ticket_key,
        "assigneeEmail": ticket.assignee_email,
        "matchedClients": len(
            clients_by_email.get(ticket.assignee_email, [])
        ),
        "delivered": delivered,
        "source": "mock",   # change to "jira" in webhook
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }
)

    save_state(
        generated_tickets,
        developer_contexts,
        assignee_email_map,
        delivery_history
    )

    return {
        "status": "success",
        "ticketKey": ticket.ticket_key,
        "delivered": delivered
    }


@app.post("/webhooks/jira/assigned")
async def jira_assignment_webhook(
    payload: JiraWebhookPayload,
    x_jira_webhook_secret: str | None = Header(default=None)
):

    # Validate webhook secret
    if (
        x_jira_webhook_secret is None
        or x_jira_webhook_secret != settings.JIRA_WEBHOOK_SECRET
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid Jira webhook secret"
        )

    # Resolve assignee email
    assignee_email = payload.assigneeEmail

    # Fallback to account ID mapping
    if not assignee_email:
        assignee_email = assignee_email_map.get(
            payload.assigneeAccountId
        )

    # Still unresolved
    if not assignee_email:
        raise HTTPException(
            status_code=400,
            detail="Unable to resolve assignee email"
        )

    # Convert Jira payload to internal ticket event
    ticket = JiraTicketEvent(
        event_type=payload.eventType,
        ticket_key=payload.issueKey,
        ticket_title=payload.summary,
        ticket_description=payload.description or "",
        ticket_status=payload.status or "",
        ticket_priority=payload.priority or "",
        ticket_url=payload.issueUrl,
        comments=[],
        assignee_email=assignee_email
    )

    # Store ticket history
    generated_tickets.append(
        {
            "key": ticket.ticket_key,
            "title": ticket.ticket_title,
            "assigneeEmail": ticket.assignee_email,
            "status": ticket.ticket_status
        }
    )

    # Count connected clients
    matched_clients = len(
        clients_by_email.get(ticket.assignee_email, [])
    )

    # Normalize event
    event = normalize_ticket_event(
        ticket=ticket,
        source="jira",
        assignee_display_name=payload.assigneeDisplayName,
        project_key=payload.projectKey,
    )

    # Send ticket
    delivered = await send_ticket_to_clients(ticket, event)

    # Store delivery history
    delivery_history.append(
    {
        "ticketKey": ticket.ticket_key,
        "assigneeEmail": ticket.assignee_email,
        "matchedClients": matched_clients,
        "delivered": delivered,
        "source": "jira",
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }
)

    save_state(
        generated_tickets,
        developer_contexts,
        assignee_email_map,
        delivery_history
    )

    if matched_clients > 0:
        return {
            "status": "processed",
            "ticketKey": ticket.ticket_key,
            "assigneeEmail": ticket.assignee_email,
            "matchedClients": matched_clients,
            "delivered": delivered
        }

    return {
        "status": "processed",
        "ticketKey": ticket.ticket_key,
        "assigneeEmail": ticket.assignee_email,
        "matchedClients": 0,
        "delivered": delivered,
        "message": "No active VS Code client found for assignee"
    }



# Developer Context Submit

@app.post("/tickets/{ticket_key}/developer-context")
def submit_developer_context(
    ticket_key: str,
    request: DeveloperContextRequest
):

    context = {
        "ticketKey": ticket_key,
        "userEmail": request.userEmail,
        "additionalContext": request.additionalContext,
        "repoPath": request.repoPath,
        "activeFile": request.activeFile,
        "branchName": request.branchName,
        "notes": request.notes,
        "submittedAt": datetime.now().isoformat()
    }

    if ticket_key not in developer_contexts:
        developer_contexts[ticket_key] = []

    developer_contexts[ticket_key].append(context)

    save_state(
        generated_tickets,
        developer_contexts,
        assignee_email_map,
        delivery_history
    )

    return {
        "status": "received",
        "ticketKey": ticket_key,
        "message": "Developer context saved successfully"
    }

# WebSocket Endpoint


@app.websocket("/ws/client")
async def websocket_client(websocket: WebSocket):
    await websocket.accept()

    email = None
    client_id = None

    try:
        logger.info("VS Code client connected")
        data = await websocket.receive_json()

        # Validation
        try:

            registration = ClientRegistrationRequest(**data)
        except Exception as e:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Invalid registration message",
                    "details": str(e) 
                }
            )
            return
        
        email = registration.userEmail
        client_id = registration.clientId

        register_client(email, client_id, websocket)

        await websocket.send_json(
            {
                "type": "client_registered",
                "status": "success",
                "userEmail": email
            }
        )

        # Ticket behaviour

        ticket = create_mock_ticket()

        await websocket.send_json(ticket.model_dump())
        logger.info("Ticket sent automatically")

        while True:
            message = await websocket.receive_text()
            logger.info(f"Message received {message}")

    except WebSocketDisconnect:

        logger.info("Client disconnected")

    finally:

        if email and email in clients_by_email:
            clients_by_email[email] = [
                client
                for client in clients_by_email[email]
                if client["client_id"] != client_id
            ]
            if len(clients_by_email[email]) == 0:
                del clients_by_email[email]