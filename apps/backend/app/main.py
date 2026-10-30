import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app import database
from app import jira_service
from app import ai_service
from app.models import (
    JiraTicketEvent,
    DeveloperContextRequest,
    ClientRegistrationRequest,
    AiAnalyzeRequest,
    FetchJiraTicketRequest,
    CreateTicketRequest
)
from app.response_models import DeveloperContextResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema and seed default data
    database.init_db()
    logger.info("FastAPI backend initialized with SQLite persistence and AI engine")
    yield


app = FastAPI(
    title="Jira VS Code Assistant Backend",
    version="2.0.0",
    description="Backend with real SQLite database, Jira Cloud REST API integration, and OpenAI-powered code assistance.",
    lifespan=lifespan
)

# Active connected WebSocket clients keyed by email
clients_by_email: Dict[str, List[Dict[str, Any]]] = {}


# Client Registration & Management

def register_client(email: str, client_id: str, websocket: WebSocket):
    if email not in clients_by_email:
        clients_by_email[email] = []
    clients_by_email[email].append({
        "client_id": client_id,
        "websocket": websocket,
        "connected_at": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat()
    })
    logger.info(f"Client registered: {email} | Client ID: {client_id}")


async def send_ticket_to_clients(ticket_dict: Dict[str, Any]):
    """
    Broadcasts a Jira ticket to relevant connected clients or all active clients.
    """
    event = JiraTicketEvent(
        event_type="ticket_assigned",
        ticket_key=ticket_dict.get("key") or ticket_dict.get("ticket_key", "UNKNOWN"),
        ticket_title=ticket_dict.get("title") or ticket_dict.get("ticket_title", "Untitled"),
        ticket_description=ticket_dict.get("description") or ticket_dict.get("ticket_description", ""),
        ticket_status=ticket_dict.get("status") or ticket_dict.get("ticket_status", "To Do"),
        ticket_priority=ticket_dict.get("priority") or ticket_dict.get("ticket_priority", "Medium"),
        ticket_url=ticket_dict.get("url") or ticket_dict.get("ticket_url", ""),
        comments=ticket_dict.get("comments") or [],
        assignee_email=ticket_dict.get("assignee_email") or ticket_dict.get("assigneeEmail", "developer@example.com"),
        assignee_name=ticket_dict.get("assignee_name") or ticket_dict.get("assigneeName"),
        project_key=ticket_dict.get("project_key") or ticket_dict.get("projectKey")
    )

    assignee = event.assignee_email.strip().lower() if event.assignee_email else ""
    dispatched = 0

    # First attempt sending to matching assignee clients
    target_clients = clients_by_email.get(assignee, [])

    # If no clients with matching email are connected, broadcast to all connected clients
    if not target_clients:
        target_clients = [c for client_list in clients_by_email.values() for c in client_list]

    for client in target_clients:
        try:
            await client["websocket"].send_json(event.model_dump())
            client["last_seen"] = datetime.now().isoformat()
            dispatched += 1
        except Exception as e:
            logger.error(f"Failed to send ticket to client: {e}")

    logger.info(f"Ticket {event.ticket_key} dispatched to {dispatched} client(s)")


# WebSocket Endpoint for VS Code Extension

@app.websocket("/ws/client")
async def websocket_client(websocket: WebSocket):
    await websocket.accept()
    email = None
    client_id = None

    try:
        logger.info("VS Code client connecting...")
        data = await websocket.receive_json()

        try:
            registration = ClientRegistrationRequest(**data)
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid registration message",
                "details": str(e)
            })
            return

        email = registration.userEmail
        client_id = registration.clientId
        register_client(email, client_id, websocket)

        await websocket.send_json({
            "type": "client_registered",
            "status": "success",
            "userEmail": email
        })

        # Fetch latest ticket from real SQLite database to display in extension
        recent_tickets = database.get_all_tickets(limit=1)
        if recent_tickets:
            latest = recent_tickets[0]
            event = JiraTicketEvent(
                event_type="ticket_assigned",
                ticket_key=latest["key"],
                ticket_title=latest["title"],
                ticket_description=latest.get("description", ""),
                ticket_status=latest.get("status", "To Do"),
                ticket_priority=latest.get("priority", "Medium"),
                ticket_url=latest.get("url", ""),
                comments=latest.get("comments", []),
                assignee_email=latest.get("assignee_email", email)
            )
            await websocket.send_json(event.model_dump())
            logger.info(f"Sent latest ticket {latest['key']} from database to {email}")

        # Keep connection open for incoming messages and heartbeats
        while True:
            message = await websocket.receive_text()
            logger.debug(f"WS message from {email}: {message}")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {email} | {client_id}")
    finally:
        if email and email in clients_by_email:
            clients_by_email[email] = [
                c for c in clients_by_email[email] if c["client_id"] != client_id
            ]
            if len(clients_by_email[email]) == 0:
                del clients_by_email[email]


# Root Welcome & Landing Page

@app.get("/", response_class=HTMLResponse)
def root_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jira VS Code Assistant - Backend API</title>
    <style>
        :root {
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-hover: #0284c7;
            --success: #22c55e;
            --border: #334155;
            --code-bg: #0b1120;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
        }
        .container {
            max-width: 860px;
            width: 100%;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(34, 197, 94, 0.15);
            color: var(--success);
            border: 1px solid rgba(34, 197, 94, 0.3);
            border-radius: 9999px;
            padding: 4px 12px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 16px;
        }
        .badge-dot {
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            display: inline-block;
        }
        h1 {
            font-size: 32px;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 8px;
        }
        p.subtitle {
            color: var(--text-muted);
            font-size: 16px;
            margin-bottom: 32px;
            line-height: 1.5;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: transform 0.15s ease, border-color 0.15s ease;
            text-decoration: none;
            color: inherit;
            display: block;
        }
        .card:hover {
            transform: translateY(-2px);
            border-color: var(--accent);
        }
        .card h3 {
            font-size: 16px;
            font-weight: 600;
            color: var(--accent);
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .card p {
            color: var(--text-muted);
            font-size: 13px;
            line-height: 1.4;
        }
        .endpoints-section {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
        }
        .endpoints-section h2 {
            font-size: 18px;
            margin-bottom: 16px;
            font-weight: 600;
        }
        .endpoint-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }
        .endpoint-row:last-child {
            border-bottom: none;
        }
        .method {
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            font-family: monospace;
        }
        .method-get { background: rgba(56, 189, 248, 0.15); color: var(--accent); }
        .method-post { background: rgba(34, 197, 94, 0.15); color: var(--success); }
        .method-ws { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
        .route-link {
            color: var(--text-main);
            text-decoration: none;
            font-family: monospace;
            font-size: 13px;
        }
        .route-link:hover { color: var(--accent); text-decoration: underline; }
        .route-desc {
            color: var(--text-muted);
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="badge"><span class="badge-dot"></span> Backend Active &amp; Operational</div>
        <h1>Jira VS Code Assistant API</h1>
        <p class="subtitle">FastAPI Real-Time WebSocket &amp; Issue Context Service with SQLite Persistence and AI Analysis.</p>

        <div class="grid">
            <a href="/docs" class="card">
                <h3>📖 Interactive Swagger Docs &rarr;</h3>
                <p>Test all API endpoints, inspect request/response schemas, and execute live calls.</p>
            </a>
            <a href="/health" class="card">
                <h3>🩺 Health &amp; Diagnostics &rarr;</h3>
                <p>Check SQLite connection state, active WebSocket clients, and AI provider status.</p>
            </a>
            <a href="/tickets" class="card">
                <h3>📋 Active Tickets in DB &rarr;</h3>
                <p>View current synced Jira tickets and mock developer backlog.</p>
            </a>
        </div>

        <div class="endpoints-section">
            <h2>Core Service Routes</h2>
            <div class="endpoint-row">
                <div>
                    <span class="method method-get">GET</span>
                    <a href="/docs" class="route-link">/docs</a>
                </div>
                <span class="route-desc">Swagger UI Documentation</span>
            </div>
            <div class="endpoint-row">
                <div>
                    <span class="method method-get">GET</span>
                    <a href="/health" class="route-link">/health</a>
                </div>
                <span class="route-desc">System health &amp; connected clients status</span>
            </div>
            <div class="endpoint-row">
                <div>
                    <span class="method method-get">GET</span>
                    <a href="/tickets" class="route-link">/tickets</a>
                </div>
                <span class="route-desc">List tickets stored in SQLite</span>
            </div>
            <div class="endpoint-row">
                <div>
                    <span class="method method-ws">WS</span>
                    <span class="route-link">/ws/client</span>
                </div>
                <span class="route-desc">Persistent full-duplex WebSocket hub for VS Code extension</span>
            </div>
            <div class="endpoint-row">
                <div>
                    <span class="method method-post">POST</span>
                    <span class="route-link">/tickets/{key}/developer-context</span>
                </div>
                <span class="route-desc">Submit active editor file, Git branch &amp; notes</span>
            </div>
            <div class="endpoint-row">
                <div>
                    <span class="method method-post">POST</span>
                    <span class="route-link">/tickets/{key}/ai-analyze</span>
                </div>
                <span class="route-desc">Trigger AI implementation plan &amp; architectural analysis</span>
            </div>
            <div class="endpoint-row">
                <div>
                    <span class="method method-post">POST</span>
                    <span class="route-link">/api/jira/webhook</span>
                </div>
                <span class="route-desc">Atlassian Jira Cloud incoming webhook handler</span>
            </div>
        </div>
    </div>
</body>
</html>
"""


# Health Check & Service Status

@app.get("/health")
def health_check():
    return {
        "service": "jira-vscode-assistant-backend",
        "status": "healthy",
        "database": "sqlite",
        "db_path": database.DB_PATH,
        "jira_configured": jira_service.is_jira_configured(),
        "ai_provider": "openai" if os.environ.get("OPENAI_API_KEY") else "free_openai_pollinations",
        "connected_clients": sum(len(c) for c in clients_by_email.values())
    }


# Real Database Ticket Endpoints

@app.get("/tickets")
def list_tickets(limit: int = 50):
    """Returns list of tickets stored in SQLite database."""
    tickets = database.get_all_tickets(limit=limit)
    return {"tickets": tickets, "count": len(tickets)}


@app.get("/tickets/{ticket_key}")
def get_ticket(ticket_key: str):
    """Retrieves full ticket details, developer contexts, and AI analyses from DB."""
    ticket = database.get_ticket(ticket_key)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_key} not found")

    contexts = database.get_developer_contexts(ticket_key)
    analyses = database.get_ai_analyses(ticket_key)

    return {
        "ticket": ticket,
        "developerContexts": contexts,
        "aiAnalyses": analyses
    }


@app.post("/tickets")
async def create_ticket(request: CreateTicketRequest):
    """Manually creates/upserts a ticket into database and broadcasts to VS Code."""
    ticket_dict = database.upsert_ticket({
        "key": request.ticketKey,
        "title": request.title,
        "description": request.description,
        "status": request.status,
        "priority": request.priority,
        "assignee_email": request.assigneeEmail,
        "assignee_name": request.assigneeName,
        "comments": request.comments or []
    })
    await send_ticket_to_clients(ticket_dict)
    return {"success": True, "ticket": ticket_dict}


# Developer Context Endpoints

@app.get("/tickets/{ticket_key}/developer-context")
@app.get("/dev/tickets/{ticket_key}/developer-context")
def get_developer_contexts(ticket_key: str):
    """Fetches developer contexts for a ticket."""
    submissions = database.get_developer_contexts(ticket_key)
    return {
        "ticketKey": ticket_key,
        "submissions": submissions
    }


@app.post("/tickets/{ticket_key}/developer-context", response_model=DeveloperContextResponse)
def submit_developer_context(ticket_key: str, request: DeveloperContextRequest):
    """Saves developer context into SQLite database."""
    if not ticket_key.strip():
        return DeveloperContextResponse(
            success=False,
            message="Invalid ticket key",
            ticketKey=ticket_key,
            submittedAt=""
        )

    if not request.additionalContext.strip():
        return DeveloperContextResponse(
            success=False,
            message="additionalContext cannot be empty",
            ticketKey=ticket_key,
            submittedAt=""
        )

    saved = database.insert_developer_context({
        "ticketKey": ticket_key,
        "userEmail": request.userEmail,
        "additionalContext": request.additionalContext,
        "repoPath": request.repoPath,
        "activeFile": request.activeFile,
        "branchName": request.branchName,
        "notes": request.notes
    })

    return DeveloperContextResponse(
        success=True,
        message="Developer context submitted successfully to database",
        ticketKey=ticket_key,
        submittedAt=saved["submittedAt"]
    )


# AI Analysis Endpoint (Powered by OpenAI / Free OpenAI API)

@app.post("/tickets/{ticket_key}/ai-analyze")
async def analyze_ticket_with_ai(ticket_key: str, request: Optional[AiAnalyzeRequest] = None):
    """
    Executes AI analysis for a Jira ticket using OpenAI-compatible API.
    Uses free OpenAI API when no key is set, or user's custom OpenAI key.
    """
    ticket = database.get_ticket(ticket_key)
    if not ticket:
        # If ticket not found in DB, try fetching from Jira or create basic record
        try:
            ticket = await jira_service.fetch_jira_ticket(ticket_key)
        except Exception:
            ticket = {
                "key": ticket_key,
                "title": f"Jira Issue {ticket_key}",
                "description": "Developer initiated AI analysis.",
                "status": "In Progress",
                "priority": "Medium",
                "comments": []
            }

    # Fetch latest developer context from database or request
    contexts = database.get_developer_contexts(ticket_key)
    latest_context = contexts[0] if contexts else None

    # Merge context from request payload if passed
    if request:
        dev_ctx = {
            "additionalContext": request.additionalContext or (latest_context.get("additional_context") if latest_context else ""),
            "activeFile": request.activeFile or (latest_context.get("active_file") if latest_context else ""),
            "repoPath": request.repoPath or (latest_context.get("repo_path") if latest_context else ""),
            "branchName": request.branchName or (latest_context.get("branch_name") if latest_context else "")
        }
        custom_prompt = request.prompt
    else:
        dev_ctx = latest_context
        custom_prompt = None

    result = await ai_service.generate_ai_analysis(
        ticket=ticket,
        developer_context=dev_ctx,
        custom_prompt=custom_prompt
    )
    return result


@app.get("/tickets/{ticket_key}/ai-analyses")
def get_ticket_ai_analyses(ticket_key: str):
    """Retrieves previous AI analyses for a ticket."""
    analyses = database.get_ai_analyses(ticket_key)
    return {"ticketKey": ticket_key, "analyses": analyses}


# Real Jira Cloud Integration Endpoints

@app.post("/api/jira/fetch")
async def fetch_jira_ticket_endpoint(request: FetchJiraTicketRequest):
    """
    Fetches a real Jira ticket from Atlassian Jira Cloud REST API v3,
    persists it into SQLite database, and broadcasts it to connected VS Code extensions.
    """
    try:
        ticket = await jira_service.fetch_jira_ticket(request.ticketKey)
        await send_ticket_to_clients(ticket)
        return {
            "success": True,
            "message": f"Ticket {request.ticketKey} fetched successfully",
            "ticket": ticket
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch Jira ticket: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch Jira ticket: {str(e)}")


@app.post("/api/jira/webhook")
async def jira_webhook_receiver(request: Request):
    """
    Real Atlassian Jira Cloud Webhook endpoint.
    Configure Jira -> System -> WebHooks to point to this URL.
    Receives issue created/updated events, persists to SQLite DB, and broadcasts live.
    """
    try:
        payload = await request.json()
        event_name = payload.get("webhookEvent", "jira:issue_updated")
        issue = payload.get("issue")

        if not issue:
            return {"status": "ignored", "reason": "No issue payload"}

        logger.info(f"Received real Jira webhook event: {event_name}")
        normalized_ticket = jira_service.parse_jira_issue_payload(issue)
        await send_ticket_to_clients(normalized_ticket)

        return {
            "status": "success",
            "event": event_name,
            "ticketKey": normalized_ticket["key"]
        }
    except Exception as e:
        logger.error(f"Error handling Jira webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")


# Legacy / Dev Endpoints (Preserved for backwards compatibility)

@app.get("/dev/clients")
def get_connected_clients():
    response = {}
    for email, clients in clients_by_email.items():
        response[email] = {
            "active_clients": len(clients)
        }
    return response


@app.get("/dev/tickets")
def get_generated_tickets():
    tickets = database.get_all_tickets(limit=50)
    return {"tickets": tickets}


class MockTicketRequest(BaseModel):
    assigneeEmail: str = Field(..., min_length=1)
    ticketKey: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)


@app.post("/dev/mock-ticket")
async def get_mock_ticket(request: MockTicketRequest):
    ticket_dict = {
        "key": request.ticketKey,
        "title": request.title,
        "description": "Users are redirected to wrong page after login.",
        "status": "To Do",
        "priority": "High",
        "url": f"https://jira.example.com/browse/{request.ticketKey}",
        "assignee_email": request.assigneeEmail,
        "comments": ["Issue reported by QA team.", "Needs investigation."]
    }
    saved = database.upsert_ticket(ticket_dict)
    await send_ticket_to_clients(saved)
    return {
        "broadcastAttempted": True,
        "ticketKey": request.ticketKey
    }