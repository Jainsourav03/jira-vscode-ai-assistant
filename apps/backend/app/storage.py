import json
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Read storage location from environment variable
STATE_FILE = Path(settings.STORAGE_FILE).resolve()
DATA_DIR = STATE_FILE.parent

DEFAULT_STATE = {
    "tickets": [],
    "developerContext": {},
    "assigneeMap": {},
    "deliveryHistory": []
}


def load_state():
    """
    Load application state from disk.
    Create the file if it doesn't exist.
    """

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        if not STATE_FILE.exists():
            save_state(
                DEFAULT_STATE["tickets"],
                DEFAULT_STATE["developerContext"],
                DEFAULT_STATE["assigneeMap"],
                DEFAULT_STATE["deliveryHistory"],
            )
            return DEFAULT_STATE.copy()

        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        logger.error(f"Failed to load state: {e}")
        return DEFAULT_STATE.copy()


def save_state(
    tickets,
    developer_context,
    assignee_map,
    delivery_history,
):
    """
    Save application state to disk.
    """

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        state = {
            "tickets": tickets,
            "developerContext": developer_context,
            "assigneeMap": assignee_map,
            "deliveryHistory": delivery_history,
        }

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)

    except Exception as e:
        logger.error(f"Failed to save state: {e}")