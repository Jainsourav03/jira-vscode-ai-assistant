from pydantic import BaseModel
from app.models import JiraTicketEvent


class MockTicketResponse(BaseModel):
    broadcast_attempted: bool
    connected_clients: int
    ticket_event: JiraTicketEvent

# Response Model

class DeveloperContextResponse(BaseModel):
    success: bool
    message: str
    ticketKey: str
    submittedAt: str