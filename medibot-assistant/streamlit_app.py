"""MediBot Streamlit frontend.

Talks to the FastAPI backend over HTTP only. RBAC is enforced server-side:
the role is resolved from the session token inside /chat, never sent by this UI.

Run:  streamlit run streamlit_app.py   (with uvicorn running on port 8000)
"""
import os

import requests
import streamlit as st

API_URL = os.getenv("MEDIBOT_API_URL", "http://localhost:8000")

# Mirrors DEMO_USERS in app/auth.py
DEMO_USERS = [
    ("Doctor", "doctor", "doctor"),
    ("Nurse", "nurse", "nurse"),
    ("Billing", "billing_executive", "billing_executive"),
    ("Technician", "technician", "technician"),
    ("Admin", "admin", "admin"),
]

# Display only. The backend decides what each role can actually retrieve.
ALL_COLLECTIONS = ["general", "clinical", "nursing", "billing", "equipment"]
SQL_ROLES = {"billing_executive", "admin"}

SAMPLE_QUESTIONS = {
    "doctor": ["What is the first-line treatment for hypertension?", "How do I apply for annual leave?"],
    "nurse": ["What are the hand hygiene steps in infection control?", "Show me all insurance billing codes."],
    "billing_executive": ["How do I submit an insurance claim?", "How many claims are there by status?"],
    "technician": ["How often should the ventilator be calibrated?", "What are the drug dosages for sepsis?"],
    "admin": ["Which equipment category has the most open maintenance tickets?", "What is the code of conduct on patient privacy?"],
}

st.set_page_config(page_title="MediBot", page_icon="🏥", layout="wide")


# ---------- API calls ----------

class Unauthorized(Exception):
    pass


def api_post(path, payload, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        res = requests.post(f"{API_URL}{path}", json=payload, headers=headers, timeout=120)
    except requests.ConnectionError:
        raise RuntimeError(f"Cannot reach the MediBot backend at {API_URL}. Is uvicorn running?")
    if res.status_code == 401:
        raise Unauthorized(res.json().get("detail", "Unauthorized"))
    if not res.ok:
        raise RuntimeError(f"Backend error ({res.status_code}). Check the uvicorn logs.")
    return res.json()


def role_label(role):
    return role.replace("_", " ").title()


def join_words(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


# ---------- Session ----------

def do_login(username, password):
    try:
        data = api_post("/login", {"username": username, "password": password})
    except Unauthorized:
        st.session_state.login_error = "Invalid username or password"
        return
    except RuntimeError as e:
        st.session_state.login_error = str(e)
        return
    st.session_state.user = {
        "username": username,
        "token": data["token"],
        "role": data["role"],
        "collections": data["collections"],
    }
    st.session_state.messages = []
    st.session_state.login_error = None


def do_logout():
    st.session_state.user = None
    st.session_state.messages = []


# ---------- Login screen ----------

def login_screen():
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.title("🏥 MediBot")
        st.caption("MediAssist Health Network · internal assistant")

        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign in", type="primary", use_container_width=True):
                do_login(username, password)
                st.rerun()

        if st.session_state.get("login_error"):
            st.error(st.session_state.login_error)

        st.markdown("**Demo accounts:** click one to sign in")
        for username, password, role in DEMO_USERS:
            if st.button(f"{username}  ·  `{username} / {password}`  ·  {role_label(role)}",
                         key=f"demo_{username}", use_container_width=True):
                do_login(username, password)
                st.rerun()


# ---------- Chat screen ----------

def render_bot_message(res, user):
    is_sql = res["retrieval_type"] == "sql_rag"
    # The backend returns no sources from hybrid RAG when the RBAC-filtered
    # retrieval found nothing relevant, i.e. the question is outside this role's collections.
    blocked = not is_sql and not res.get("sources")

    st.caption("🧮 **SQL RAG**" if is_sql else "🔎 **Hybrid RAG**")

    if blocked:
        cols = user["collections"]
        st.warning(
            f"**As a {role_label(user['role']).lower()}, you don't have access to the documents needed to answer this.**\n\n"
            f"I can only answer questions from the {join_words(cols)} collection{'s' if len(cols) > 1 else ''}. "
            "Restricted documents are filtered out at retrieval, so they are never shown to the model.",
            icon="🔒",
        )
        return

    st.markdown(res["answer"])

    if is_sql:
        st.caption("**Source:** mediassist.db (claims, maintenance_tickets)")
        return

    seen, lines = set(), []
    for s in res["sources"]:
        key = (s["source_document"], s.get("section_title"))
        if key in seen:
            continue
        seen.add(key)
        section = f" › {s['section_title']}" if s.get("section_title") else ""
        lines.append(f"- `{s['collection']}` **{s['source_document']}**{section}")
    with st.expander(f"📄 Sources ({len(lines)})", expanded=True):
        st.markdown("\n".join(lines))


def sidebar(user):
    with st.sidebar:
        st.title("🏥 MediBot")
        st.markdown(f"Signed in as **{user['username']}**")
        st.markdown(f":blue-background[**{role_label(user['role'])}**]")

        st.subheader("Document collections")
        for c in ALL_COLLECTIONS:
            if c in user["collections"]:
                st.markdown(f"✅ {c.title()}")
            else:
                st.markdown(f"🚫 ~~{c.title()}~~")

        st.subheader("Analytics")
        st.markdown("✅ SQL analytics" if user["role"] in SQL_ROLES else "🚫 ~~SQL analytics~~")

        st.divider()
        if st.button("Sign out", use_container_width=True):
            do_logout()
            st.rerun()


def chat_screen():
    user = st.session_state.user
    sidebar(user)

    st.header(f"Ask MediBot · {role_label(user['role'])}")

    messages = st.session_state.messages

    question = st.chat_input("Ask about protocols, policies, billing codes, equipment…")

    if not messages and not question:
        st.caption("Answers come only from the collections your role can access. Try:")
        for q in SAMPLE_QUESTIONS.get(user["role"], []):
            if st.button(q, key=f"sample_{q}"):
                question = q

    for m in messages:
        with st.chat_message(m["from"]):
            if m["from"] == "user":
                st.markdown(m["text"])
            elif "error" in m:
                st.error(m["error"])
            else:
                render_bot_message(m["response"], user)

    if not question:
        return

    messages.append({"from": "user", "text": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("MediBot is searching your documents…"):
            try:
                res = api_post("/chat", {"question": question}, token=user["token"])
            except Unauthorized:
                # Sessions live in backend memory, so a uvicorn restart invalidates the token.
                do_logout()
                st.session_state.login_error = "Your session expired. Please sign in again."
                st.rerun()
            except RuntimeError as e:
                messages.append({"from": "assistant", "error": str(e)})
                st.error(str(e))
                return
        messages.append({"from": "assistant", "response": res})
        render_bot_message(res, user)


# ---------- Entry ----------

st.session_state.setdefault("user", None)
st.session_state.setdefault("messages", [])

if st.session_state.user:
    chat_screen()
else:
    login_screen()
