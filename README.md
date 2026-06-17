# Jira Assistant VS Code Extension

## Overview

Jira Assistant is a Visual Studio Code extension that connects to a FastAPI backend using WebSocket and displays Jira ticket information inside VS Code.

Features included in Week 1:

* Open Jira Assistant panel inside VS Code
* Connect extension to FastAPI backend
* Receive mock Jira ticket events
* Show VS Code notifications for assigned tickets
* Store latest received ticket in extension memory
* Open ticket details from notification
* Display ticket information dynamically inside the panel
* Placeholder AI button for future integration

---

## Project Structure

```text
apps/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   └── models.py
│   └── requirements.txt

├── vscode-extension/
│   ├── src/
│   │   └── extension.ts
│   ├── out/
│   ├── package.json
│   └── tsconfig.json
```

---

## Install Dependencies

### Backend

Navigate to backend folder:

```bash
cd apps/backend
```

Create virtual environment:

```bash
python3 -m venv venv
```

Activate environment:

Mac/Linux:

```bash
source venv/bin/activate
```

Install packages:

```bash
pip install -r requirements.txt
```

Install websocket support:

```bash
pip install "uvicorn[standard]"
```

---

### VS Code Extension

Navigate to extension folder:

```bash
cd apps/vscode-extension
```

Install dependencies:

```bash
npm install
```

Compile extension:

```bash
npm run compile
```

---

## Run Extension Locally

### Start Backend

Open terminal:

```bash
cd apps/backend
source venv/bin/activate
uvicorn app.main:app --reload
```

Expected:

```text
Application startup complete.
```

---

### Start Extension

Open another terminal:

```bash
cd apps/vscode-extension
npm run compile
```

Launch extension:

```text
fn + F5
```

This opens Extension Development Host.

---

## Connect To Backend

Inside Extension Host:

Open Command Palette:

```text
Cmd + Shift + P
```

Run:

```text
Jira Assistant: Connect Backend
```

Expected:

```text
Connected to backend
```

---

## Available Commands

### Jira Assistant: Hello

Shows extension activation message.

---

### Jira Assistant: Open Panel

Opens Jira ticket details panel.

---

### Jira Assistant: Show Mock Ticket Notification

Displays mock Jira notification.

---

### Jira Assistant: Connect Backend

Creates WebSocket connection to backend.

---

## Test Mock Ticket Flow

1. Start backend
2. Compile extension
3. Launch Extension Host
4. Run:

```text
Jira Assistant: Connect Backend
```

Expected notification:

```text
New Jira ticket assigned:
PROJ-123 - Fix login redirect issue
```

Click:

```text
Open Ticket
```

Expected result:

* Jira Assistant panel opens
* Ticket data displayed
* Ticket information loaded from backend

---

## Known Issues / Limitations

* AI button is currently placeholder only
* Backend currently sends mock ticket events
* Ticket data is stored temporarily in memory
* Connection closes when Extension Host closes
* No persistent storage implemented

---

## Future Improvements

* Real Jira integration
* AI ticket analysis
* Persistent ticket history
* Enhanced panel UI
* Authentication support
