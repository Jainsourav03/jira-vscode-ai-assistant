from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, ConfigDict, model_validator

# Jira Ticket Event

class JiraTicketEvent(BaseModel):
    event_type: str = Field(..., min_length=1)
    ticket_key: str = Field(..., min_length=1)
    ticket_title: str = Field(..., min_length=1)
    ticket_description: str = Field(..., min_length=1)
    ticket_status: str = Field(..., min_length=1)
    ticket_priority: str = Field(..., min_length=1)
    ticket_url: str = Field(..., min_length=1)
    comments: List[str] = Field(default_factory=list)
    assignee_email: str = Field(..., min_length=1)

# Ticket Comment

class TicketComment(BaseModel):
    comment: str = Field(..., min_length=1)

# VS Code Client Registration

class ClientRegistrationRequest(BaseModel):
    type: str = Field(..., min_length=1)
    userEmail: str = Field(..., min_length=1)
    clientId: str = Field(..., min_length=1)

    # Allow additional fields from the VS Code extension
    model_config = ConfigDict(extra="allow")

# Developer Context Submission

class DeveloperContextRequest(BaseModel):
    userEmail: str = Field(..., min_length=1)
    additionalContext: str = Field(..., min_length=1)

    repoPath: str | None = None
    activeFile: str | None = None
    branchName: str | None = None
    notes: str | None = None

# Jira Webhook Payload

class JiraWebhookPayload(BaseModel):
    eventType: str = Field(...)

    issueKey: str = Field(...)
    summary: str = Field(...)
    description: str | None = None
    status: str | None = None
    priority: str | None = None

    issueUrl: str = Field(...)

    assigneeEmail: str | None = None
    assigneeDisplayName: str | None = None
    assigneeAccountId: str | None = None

    projectKey: str | None = None
    createdAt: str | None = None

    @model_validator(mode="after")
    def validate_payload(self):
        if self.issueKey.strip() == "":
            self.issueKey = None

        if self.summary.strip() == "":
            self.summary = None

        if self.issueUrl.strip() == "":
            self.issueUrl = None

        if self.assigneeEmail is not None and self.assigneeEmail.strip() == "":
            self.assigneeEmail = None

        if self.assigneeAccountId is not None and self.assigneeAccountId.strip() == "":
            self.assigneeAccountId = None

        if not self.issueKey:
            raise ValueError("issueKey is required")

        if not self.summary:
            raise ValueError("summary is required")

        if not self.issueUrl:
            raise ValueError("issueUrl is required")

        if not self.assigneeEmail and not self.assigneeAccountId:
            raise ValueError(
                "Either assigneeEmail or assigneeAccountId is required"
            )

        return self

# Internal Ticket Models

class InternalTicket(BaseModel):
    key: str
    title: str
    description: str
    status: str
    priority: str
    url: str
    assigneeEmail: str
    assigneeDisplayName: str | None = None
    projectKey: str | None = None
    comments: List[str] = Field(default_factory=list)

class EventMetadata(BaseModel):
    source: str
    eventId: str
    createdAt: str

class InternalTicketEvent(BaseModel):
    type: str
    ticket: InternalTicket
    metadata: EventMetadata

# Assignee Mapping

class AssigneeMappingRequest(BaseModel):
    accountId: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)