# Backend — Jira VS Code AI Assistant

This folder contains the backend service for the Jira VS Code AI Assistant project.

The backend is responsible for:

- Managing VS Code extension connections using WebSockets
- Registering VS Code clients
- Generating mock Jira ticket events
- Sending assigned tickets to connected clients
- Receiving developer context from VS Code
- Providing debug and testing endpoints


# Week 2 Backend Flow

The Week 2 backend flow:

VS Code Extension
|
|
WebSocket Connection
|
|
Client Registration
|
|
Backend stores connected client
|
|
Mock Jira Ticket Created
|
|
Backend sends ticket event
|
|
VS Code Extension receives ticket
|
|
Developer submits context
|
|
Backend stores developer context

---

## Setup

 Create virtual environment

python -m venv venv

 ## Activate

Mac/Linux
source venv/bin/activate

Windows
venv\Scripts\activate

---

## Install dependencies

pip install -r requirements.txt

---

 ## Run server

uvicorn app.main:app --reload

Backend runs at:

http://localhost:8000

Swagger documentation:

http://localhost:8000/docs

---

## VS Code Client Registration Flow

The VS Code extension connects to backend using WebSocket:

ws://localhost:8000/ws/client

After connection, the extension sends a registration message.

Client Registration Message Contract

Example:

{
  "type": "client_register",
  "userEmail": "developer@example.com",
  "clientId": "vscode-client-001"
}

Backend validates:

Message type
User email
Client ID

Successful response:

{
  "type": "client_registered",
  "status": "success",
  "userEmail": "developer@example.com"
}

---

## Updated WebSocket Message Contract

Ticket Event Sent From Backend

Example:

{
  "event_type": "ticket_assigned",
  "ticket_key": "PROJ-123",
  "ticket_title": "Fix login redirect issue",
  "ticket_description": "Users are redirected to wrong page after login.",
  "ticket_status": "To Do",
  "ticket_priority": "High",
  "ticket_url": "https://jira.example.com/browse/PROJ-123",
  "comments": [
    "Issue reported by QA team.",
    "Needs investigation."
  ],
  "assignee_email": "developer@example.com"
}

---

## Mock ticket endpoint with assignee email
Create Mock Jira Ticket

Endpoint:

POST /dev/mock-ticket

Swagger:

http://localhost:8000/docs

Request:

{
  "assigneeEmail": "developer@example.com",
  "ticketKey": "PROJ-123",
  "title": "Fix login issue"
}

Flow:

Swagger
   |
   |
POST /dev/mock-ticket
   |
   |
Backend creates ticket
   |
   |
Ticket sent to connected VS Code clients

---

## Developer Context Endpoint
Submit Developer Context

Endpoint:

POST /tickets/{ticket_key}/developer-context

Example:

POST /tickets/PROJ-123/developer-context

Request:

{
  "userEmail": "developer@example.com",
  "additionalContext": "Working on login module",
  "repoPath": "/project",
  "branchName": "fix-login",
  "notes": "Testing changes"
}

Response:

{
  "success": true,
  "message": "Developer context submitted successfully",
  "ticketKey": "PROJ-123"
}

---

## Debug Endpoints

Health Check
GET /health

Checks backend status.

---

## Connected VS Code Clients

GET /dev/clients

Shows currently connected extensions.

Example:

{
  "developer@example.com": {
    "active_clients": 1
  }
}

---

## Ticket History
GET /dev/tickets

Returns generated mock tickets.

---

## Developer Context History
GET /dev/tickets/{ticket_key}/developer-context

Example:

GET /dev/tickets/PROJ-123/developer-context

Returns stored developer submissions.

---

## Testing Steps
1. Start backend
uvicorn app.main:app --reload
2. Connect VS Code Extension

Connect:

ws://localhost:8000/ws/client

Verify registration.

3. Check connected clients

Open Swagger:

GET /dev/clients
4. Create mock ticket

Execute:

POST /dev/mock-ticket

Provide:

{
  "assigneeEmail": "developer@example.com",
  "ticketKey": "PROJ-123",
  "title": "Fix login issue"
}
5. Verify ticket received

VS Code extension should receive:

ticket_assigned event
6. Submit developer context

Execute:

POST /tickets/{ticket_key}/developer-context
7. Verify stored context

Execute:

GET /dev/tickets/{ticket_key}/developer-context

---

## Known Limitations
Uses in-memory storage only.
Data is lost after backend restart.
No real Jira API integration.
No authentication system.
No database persistence.
No production WebSocket scaling.
No AI-based ticket analysis yet.
Mock tickets are used for testing.