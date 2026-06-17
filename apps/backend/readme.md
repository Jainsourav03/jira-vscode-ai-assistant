## Backend — Jira VS Code AI Assistant

- This folder contains the backend service for the Jira VS Code AI Assistant project.

- The backend will be responsible for receiving Jira ticket events, managing connected VS Code clients, and sending ticket notifications to the VS Code extension.

# Jira VS Code AI Assistant Backend

## Overview

This backend simulates Jira ticket events and sends them to connected VS Code extensions through WebSockets.

---

## Setup

### Create virtual environment

python -m venv venv

### Activate

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

---

## API Endpoints

GET /health

POST /dev/mock-ticket

GET /dev/clients

WebSocket:
/ws/client

---

## Testing Mock Ticket

1. Start backend

2. Connect VS Code extension to:

ws://localhost:8000/ws/client

3. Open Swagger:

http://localhost:8000/docs

4. Execute:

POST /dev/mock-ticket

5. Ticket event will be sent to all connected clients.

---

## Known Limitations

- Uses in-memory storage.
- No database.
- No Jira integration.
- No authentication.
- No AI integration.