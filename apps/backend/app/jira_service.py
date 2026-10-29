import os
import base64
import logging
import httpx
from typing import Dict, Any, Optional, List
from app import database

logger = logging.getLogger(__name__)

JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")


def get_jira_auth_headers() -> Dict[str, str]:
    """Generates Basic Auth header for Jira Cloud REST API."""
    if not JIRA_EMAIL or not JIRA_API_TOKEN:
        return {}
    token_str = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    encoded = base64.b64encode(token_str.encode()).decode("utf-8")
    return {
        "Authorization": f"Basic {encoded}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


def is_jira_configured() -> bool:
    """Checks whether Jira credentials are fully provided."""
    return bool(JIRA_BASE_URL and JIRA_EMAIL and JIRA_API_TOKEN)


def extract_adf_text(adf_node: Any) -> str:
    """
    Recursively extracts text from Atlassian Document Format (ADF) JSON structure.
    """
    if not adf_node:
        return ""
    if isinstance(adf_node, str):
        return adf_node
    if not isinstance(adf_node, dict):
        return ""

    node_type = adf_node.get("type", "")
    content = adf_node.get("content", [])

    if node_type == "text":
        return adf_node.get("text", "")

    extracted_parts = []
    for child in content:
        child_text = extract_adf_text(child)
        if child_text:
            extracted_parts.append(child_text)

    joined = "".join(extracted_parts)
    if node_type in ["paragraph", "heading"]:
        return joined + "\n\n"
    elif node_type == "listItem":
        return f"- {joined}\n"
    elif node_type == "codeBlock":
        lang = adf_node.get("attrs", {}).get("language", "")
        return f"\n```{lang}\n{joined}\n```\n"

    return joined


def parse_jira_issue_payload(issue_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes a Jira Cloud REST API issue payload into a standardized ticket dictionary.
    """
    key = issue_data.get("key", "UNKNOWN")
    fields = issue_data.get("fields", {})

    title = fields.get("summary", "Untitled Jira Ticket")

    # Parse description (can be ADF structure or plain string)
    desc_raw = fields.get("description")
    if isinstance(desc_raw, dict):
        description = extract_adf_text(desc_raw).strip()
    elif isinstance(desc_raw, str):
        description = desc_raw
    else:
        description = "No description provided."

    status = fields.get("status", {}).get("name", "To Do")
    priority = fields.get("priority", {}).get("name", "Medium")

    assignee = fields.get("assignee") or {}
    assignee_email = assignee.get("emailAddress", "unassigned@example.com")
    assignee_name = assignee.get("displayName", "Unassigned")

    project = fields.get("project") or {}
    project_key = project.get("key", key.split("-")[0] if "-" in key else "PROJ")

    # Parse comments
    comments_list = []
    comments_obj = fields.get("comment", {})
    if isinstance(comments_obj, dict):
        raw_comments = comments_obj.get("comments", [])
        for c in raw_comments:
            c_body = c.get("body")
            if isinstance(c_body, dict):
                c_text = extract_adf_text(c_body).strip()
            else:
                c_text = str(c_body)
            author = c.get("author", {}).get("displayName", "Team Member")
            if c_text:
                comments_list.append(f"{author}: {c_text}")

    jira_browse_url = f"{JIRA_BASE_URL}/browse/{key}" if JIRA_BASE_URL else f"https://jira.atlassian.com/browse/{key}"

    normalized_ticket = {
        "key": key,
        "title": title,
        "description": description,
        "status": status,
        "priority": priority,
        "url": jira_browse_url,
        "assignee_email": assignee_email,
        "assignee_name": assignee_name,
        "project_key": project_key,
        "comments": comments_list,
        "raw_data": {"id": issue_data.get("id"), "self": issue_data.get("self")}
    }

    # Store ticket in the real SQLite database
    saved_ticket = database.upsert_ticket(normalized_ticket)
    return saved_ticket or normalized_ticket


async def fetch_jira_ticket(ticket_key: str) -> Dict[str, Any]:
    """
    Fetches a real Jira ticket from Atlassian Jira Cloud REST API v3.
    """
    clean_key = ticket_key.strip().upper()
    if not clean_key:
        raise ValueError("Ticket key cannot be empty")

    if not is_jira_configured():
        # Check if ticket is already cached in database
        existing = database.get_ticket(clean_key)
        if existing:
            logger.info(f"Retrieved ticket {clean_key} from local database cache")
            return existing

        raise ValueError(
            "Jira is not configured on the backend. Please provide JIRA_BASE_URL, "
            "JIRA_EMAIL, and JIRA_API_TOKEN in apps/backend/.env or your environment."
        )

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{clean_key}"
    headers = get_jira_auth_headers()

    logger.info(f"Fetching real ticket {clean_key} from Jira API: {url}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            issue_json = response.json()
            return parse_jira_issue_payload(issue_json)
        elif response.status_code == 404:
            raise ValueError(f"Jira ticket '{clean_key}' was not found in your Jira instance.")
        elif response.status_code == 401 or response.status_code == 403:
            raise ValueError("Jira authentication failed. Please verify your JIRA_EMAIL and JIRA_API_TOKEN.")
        else:
            raise ValueError(f"Jira API error ({response.status_code}): {response.text[:200]}")


async def search_assigned_jira_tickets(user_email: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Queries Jira Cloud API for recent issues assigned to a user or currentUser().
    """
    if not is_jira_configured():
        return database.get_all_tickets(limit=10)

    url = f"{JIRA_BASE_URL}/rest/api/3/search"
    headers = get_jira_auth_headers()

    jql = f'assignee = "{user_email}" ORDER BY updated DESC' if user_email else "assignee = currentUser() ORDER BY updated DESC"
    params = {"jql": jql, "maxResults": 10}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            issues = data.get("issues", [])
            saved_tickets = []
            for issue in issues:
                saved = parse_jira_issue_payload(issue)
                saved_tickets.append(saved)
            return saved_tickets
        else:
            logger.warning(f"Jira search failed: {response.text[:200]}")
            return database.get_all_tickets(limit=10)
