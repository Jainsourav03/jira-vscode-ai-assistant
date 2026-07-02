from pydantic import BaseModel, Field, model_validator
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

    # --------------------------------------
# Task 8 - Jira Webhook Payload
# --------------------------------------

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

        # Treat empty strings as missing values
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