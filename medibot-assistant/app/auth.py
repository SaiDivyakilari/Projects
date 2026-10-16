import secrets
from app.config import ROLES

DEMO_USERS = {
    "Doctor":     {"password": "doctor",            "role": "doctor"},
    "Nurse":  {"password": "nurse",             "role": "nurse"},
    "Billing": {"password": "billing_executive", "role": "billing_executive"},
    "Technician":   {"password": "technician",        "role": "technician"},
    "Admin":    {"password": "admin",             "role": "admin"},
}

SESSIONS = {}


def login(username, password):
    user = DEMO_USERS.get(username)
    if not user or user["password"] != password:
        return None
    token = secrets.token_urlsafe(16)
    SESSIONS[token] = user["role"]
    return token


def role_for_token(token):
    return SESSIONS.get(token)


def collections_for(role):
    return [c for c, roles in ROLES.items() if role in roles]