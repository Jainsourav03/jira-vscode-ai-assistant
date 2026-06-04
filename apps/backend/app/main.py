from fastapi import FastAPI
from app.models import JiraTicketEvent

app = FastAPI(
    title="Jira VS Code Assistant Backend"
)

@app.get("/health")
def health_check():
    return {
        "service": "jira-vscode-assistant-backend",
        "status": "healthy",
        "message": "Backend is running"
    }

@app.post("/dev/mock-ticket", response_model=JiraTicketEvent)
def get_mock_ticket():
 mock_ticket = JiraTicketEvent(
    event_type="ticket_assigned",
    ticket_key="PROJ-123",
    ticket_title="Fix login redirect issue ",
    ticket_description="Users are redirected to the wrong page after the successfullogin.",
    ticket_status="To Do",
    ticket_priority="High",
    ticket_url="https://jira.example.com/browse/PROJ-123",
    comments=[
        "Issue reported by QA team.",
            "Needs investigation."
    ]
 )
 return mock_ticket