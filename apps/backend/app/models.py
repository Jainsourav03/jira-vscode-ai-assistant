from pydantic import BaseModel
from typing import List

class JiraTicketEvent(BaseModel):
    event_type: str
    ticket_key: str
    ticket_title: str
    ticket_description: str
    ticket_status: str
    ticket_priority: str
    ticket_url: str
    comments: List[str]
    assignee_email: str