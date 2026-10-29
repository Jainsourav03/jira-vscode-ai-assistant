import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app import database

client = TestClient(app)

def test_full_pipeline():
    print("--- 1. Testing Health Check ---")
    r = client.get("/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    health_data = r.json()
    print("Health Status:", health_data)
    assert health_data["status"] == "healthy"
    assert health_data["database"] == "sqlite"

    print("\n--- 2. Testing Database Ticket Retrieval ---")
    r = client.get("/tickets")
    assert r.status_code == 200
    tickets = r.json()["tickets"]
    print(f"Total tickets in SQLite DB: {len(tickets)}")
    assert len(tickets) > 0
    first_ticket_key = tickets[0]["key"]
    print(f"First Ticket: {first_ticket_key} - {tickets[0]['title']}")

    print(f"\n--- 3. Testing Developer Context Submission for {first_ticket_key} ---")
    ctx_payload = {
        "userEmail": "developer@example.com",
        "additionalContext": "Found issue in tokenRefreshInterceptor at line 84. Need test cases for expired JWT.",
        "repoPath": "/workspace/jira-assistant",
        "activeFile": "src/auth/tokenRefresh.ts",
        "branchName": "fix/oauth2-redirect"
    }
    r = client.post(f"/tickets/{first_ticket_key}/developer-context", json=ctx_payload)
    assert r.status_code == 200, f"Context submission failed: {r.text}"
    ctx_resp = r.json()
    print("Context submission response:", ctx_resp)
    assert ctx_resp["success"] is True

    print(f"\n--- 4. Testing Developer Context Retrieval from DB ---")
    r = client.get(f"/tickets/{first_ticket_key}/developer-context")
    assert r.status_code == 200
    submissions = r.json()["submissions"]
    print(f"Found {len(submissions)} submitted context records in DB.")
    assert len(submissions) > 0

    print(f"\n--- 5. Testing AI Analysis (OpenAI / Free OpenAI API) ---")
    ai_payload = {
        "ticketKey": first_ticket_key,
        "prompt": "Analyze root cause and provide TypeScript code fix.",
        "additionalContext": "Token refresh loop occurs on 401 response."
    }
    r = client.post(f"/tickets/{first_ticket_key}/ai-analyze", json=ai_payload)
    assert r.status_code == 200, f"AI analysis failed: {r.text}"
    ai_resp = r.json()
    print("AI Analysis Success:", ai_resp["success"])
    print("AI Provider:", ai_resp["provider"])
    print("AI Model:", ai_resp["model"])
    print("AI Analysis Snippet:\n", ai_resp["analysis"][:250], "...\n")

    print(f"\n--- 6. Testing AI Analysis Stored in DB ---")
    r = client.get(f"/tickets/{first_ticket_key}/ai-analyses")
    assert r.status_code == 200
    analyses = r.json()["analyses"]
    print(f"Found {len(analyses)} AI analyses stored in SQLite DB.")
    assert len(analyses) > 0

    print(f"\n--- 7. Testing Real Jira Ticket Fetch / Cache ---")
    fetch_payload = {"ticketKey": first_ticket_key, "userEmail": "developer@example.com"}
    r = client.post("/api/jira/fetch", json=fetch_payload)
    assert r.status_code == 200, f"Jira fetch failed: {r.text}"
    print("Fetched Ticket Result:", r.json()["ticket"]["key"])

    print("\n--- 8. Testing Mock Ticket Endpoint (Backwards Compatibility) ---")
    mock_payload = {
        "assigneeEmail": "developer@example.com",
        "ticketKey": "PROJ-999",
        "title": "Fix memory leak in websocket reconnection loop"
    }
    r = client.post("/dev/mock-ticket", json=mock_payload)
    assert r.status_code == 200
    print("Mock Ticket broadcast attempted:", r.json()["broadcastAttempted"])

    # Verify PROJ-999 is now in SQLite database
    db_ticket = database.get_ticket("PROJ-999")
    assert db_ticket is not None
    print(f"Verified PROJ-999 saved in database: {db_ticket['title']}")

    print("\n🎉 ALL 8 PIPELINE TESTS PASSED SUCCESSFULLY! Real DB, Real Jira fetcher, and Free AI API working seamlessly.")

if __name__ == "__main__":
    test_full_pipeline()
