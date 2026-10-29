from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

# Jira Ticket Event Model

class JiraTicketEvent(BaseModel):
    event_type: str = Field(default="ticket_assigned")
    ticket_key: str = Field(..., min_length=1)
    ticket_title: str = Field(..., min_length=1)
    ticket_description: str = Field(default="")
    ticket_status: str = Field(default="To Do")
    ticket_priority: str = Field(default="Medium")
    ticket_url: str = Field(default="")
    comments: List[str] = Field(default_factory=list)
    assignee_email: str = Field(default="developer@example.com")
    assignee_name: Optional[str] = None
    project_key: Optional[str] = None

# Task 8 - Ticket Comments Model

class TicketComment(BaseModel):
    comment: str = Field(..., min_length=1)

# VS Code Client Registration

class ClientRegistrationRequest(BaseModel):
    type: str = Field(..., min_length=1)
    userEmail: str = Field(..., min_length=1)
    clientId: str = Field(..., min_length=1)

    class Config:
        extra = "allow"

# Developer Context Submission

class DeveloperContextRequest(BaseModel):
    userEmail: str = Field(..., min_length=1)
    additionalContext: str = Field(..., min_length=1)
    repoPath: Optional[str] = None
    activeFile: Optional[str] = None
    branchName: Optional[str] = None
    notes: Optional[str] = None

# AI Analyze Request

class AiAnalyzeRequest(BaseModel):
    ticketKey: str = Field(..., min_length=1)
    prompt: Optional[str] = None
    additionalContext: Optional[str] = None
    activeFile: Optional[str] = None
    repoPath: Optional[str] = None
    branchName: Optional[str] = None

# Fetch Jira Ticket Request

class FetchJiraTicketRequest(BaseModel):
    ticketKey: str = Field(..., min_length=1)
    userEmail: Optional[str] = None

# Create / Upsert Ticket Request

class CreateTicketRequest(BaseModel):
    ticketKey: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: Optional[str] = ""
    status: Optional[str] = "To Do"
    priority: Optional[str] = "Medium"
    assigneeEmail: Optional[str] = "developer@example.com"
    assigneeName: Optional[str] = "Developer"
    comments: Optional[List[str]] = None