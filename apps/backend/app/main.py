from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {
        "service": "jira-vscode-assistant-backend",
        "status": "healthy",
        "message": "Backend is running"
    }