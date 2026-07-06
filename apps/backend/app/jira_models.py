from pydantic import BaseModel

class JiraIssueFields(BaseModel):
    summary: str
    description: str | None = ""
    priority: dict | None = None
    status: dict | None = None
    assignee: dict | None = None


class JiraIssue(BaseModel):
    key: str
    fields: JiraIssueFields


class JiraWebhookPayload(BaseModel):
    issue: JiraIssue