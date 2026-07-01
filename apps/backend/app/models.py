from pydantic import BaseModel, Field
from typing import List

# Jira Ticket Event Model

class JiraTicketEvent(BaseModel):

    event_type: str = Field(..., min_length=1)
    ticket_key: str = Field(..., min_length=1)
    ticket_title: str = Field(..., min_length=1)
    ticket_description: str = Field(..., min_length=1)
    ticket_status: str = Field(..., min_length=1)
    ticket_priority: str = Field(..., min_length=1)
    ticket_url: str = Field(..., min_length=1)
    comments: List[str]
    assignee_email: str = Field(..., min_length=1)

# Task 8 - Ticket Comments Model

class TicketComment(BaseModel):

    comment: str = Field(..., min_length=1)

# VS Code Client Registration

class ClientRegistrationRequest(BaseModel):

    type: str = Field(..., min_length=1)
    userEmail: str = Field(..., min_length=1)
    clientId: str = Field(..., min_length=1)

    # Important:VS Code extension can send extra information also
    
    class Config:
        extra = "allow"

# Developer Context Submission

class DeveloperContextRequest(BaseModel):

    userEmail: str = Field(..., min_length=1)
    additionalContext: str = Field(..., min_length=1)
    repoPath: str | None = None
    branchName: str | None = None
    notes: str | None = None