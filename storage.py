import json
import os

CHAT_HISTORY_FILE = "chat_history.json"

def load_chat_history():
    """Load chat history from a JSON file."""
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r") as file:
            return json.load(file)
    return {}

def save_chat_history(history):
    """Save chat history to a JSON file."""
    with open(CHAT_HISTORY_FILE, "w") as file:
        json.dump(history, file, indent=4)

def add_chat_entry(user_input, chatbot_response):
    """Add a new chat entry to the history."""
    history = load_chat_history()
    history[len(history) + 1] = {"user": user_input, "bot": chatbot_response}
    save_chat_history(history)
