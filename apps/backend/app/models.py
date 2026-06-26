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


# -------------------------------
# Task 5 Model
# -------------------------------
class DeveloperContextRequest(BaseModel):
    userEmail: str
    additionalContext: str
    repoPath: str | None = None
    branchName: str | None = None
    notes: str | None = None