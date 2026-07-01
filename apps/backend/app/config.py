import os
from dotenv import load_dotenv


load_dotenv()


class Settings:

    APP_ENV = os.getenv(
        "APP_ENV",
        "development"
    )


    JIRA_WEBHOOK_SECRET = os.getenv(
        "JIRA_WEBHOOK_SECRET",
        "change-me"
    )


    BACKEND_PUBLIC_URL = os.getenv(
        "BACKEND_PUBLIC_URL",
        "http://localhost:8000"
    )


    STORAGE_FILE = os.getenv(
        "STORAGE_FILE",
        "./data/app_state.json"
    )


settings = Settings()