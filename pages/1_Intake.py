import re
import streamlit as st
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Idea Intake", page_icon="💬", layout="wide")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import load_all, upsert, get_by_id, generate_id
from core.models import UseCase, IntakeData
from core import llm_client

# ── Session state defaults ─────────────────────────────────────────────────────
st.session_state.setdefault("active_uc_id", None)
st.session_state.setdefault("intake_messages", [])
st.session_state.setdefault("intake_initialized", False)


def _sidebar():
    with st.sidebar:
        st.title("🤖 AI Portfolio")
        st.divider()
        st.page_link("app.py", label="Home", icon="🏠")
        st.page_link("pages/1_Intake.py", label="1. Idea Intake", icon="💬")
        st.page_link("pages/2_Structure.py", label="2. Structure", icon="📋")
        st.page_link("pages/3_Scoring.py", label="3. Scoring", icon="📊")
        st.page_link("pages/4_Portfolio.py", label="4. Portfolio", icon="🗂️")
        st.page_link("pages/5_Handoff.py", label="5. Handoff", icon="📄")
        st.divider()

        if st.button("➕ New Use Case", use_container_width=True):
            st.session_state["active_uc_id"] = None
            st.session_state["intake_messages"] = []
            st.session_state["intake_initialized"] = False
            st.rerun()

        st.divider()
        st.caption("Load existing use case")
        use_cases = load_all()
        incomplete = [uc for uc in use_cases if not uc.meta.intake_complete]
        if incomplete:
            options = {uc.id: uc.title for uc in incomplete}
            selected = st.selectbox(
                "Resume intake",
                options=list(options.keys()),
                format_func=lambda x: options[x],
                label_visibility="collapsed",
            )
            if st.button("Load", use_container_width=True):
                uc = get_by_id(selected)
                st.session_state["active_uc_id"] = selected
                st.session_state["intake_messages"] = uc.intake.chat_history.copy()
                st.session_state["intake_initialized"] = True
                st.rerun()
        else:
            st.caption("No incomplete intake sessions.")


def _initialize_new_use_case() -> str:
    """Create a new UseCase record and send the AI's opening message."""
    uc_id = generate_id()
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(
        id=uc_id,
        title="New Use Case",
        status="idea",
        department="",
        created_at=now,
        updated_at=now,
    )
    upsert(uc)
    st.session_state["active_uc_id"] = uc_id

    # Get opening message from AI
    system_prompt = llm_client.load_prompt("intake_system.txt")
    opening = llm_client.chat_intake(
        [{"role": "user", "content": "Hi, I have an AI use case idea I'd like to document."}],
        system_prompt,
    )
    messages = [
        {"role": "user", "content": "Hi, I have an AI use case idea I'd like to document."},
        {"role": "assistant", "content": opening},
    ]
    st.session_state["intake_messages"] = messages

    uc.intake.chat_history = messages
    upsert(uc)
    st.session_state["intake_initialized"] = True
    return uc_id


def _send_message(user_input: str, uc_id: str):
    """Append user message, get AI response, persist."""
    messages = st.session_state["intake_messages"]
    messages.append({"role": "user", "content": user_input})

    system_prompt = llm_client.load_prompt("intake_system.txt")
    response = llm_client.chat_intake(messages, system_prompt)
    messages.append({"role": "assistant", "content": response})

    st.session_state["intake_messages"] = messages

    uc = get_by_id(uc_id)
    if uc:
        uc.intake.chat_history = messages
        # Update title from first user message if still default
        if uc.title == "New Use Case" and len(messages) >= 3:
            first_user = next((m["content"] for m in messages if m["role"] == "user"), "")
            if first_user and first_user != "Hi, I have an AI use case idea I'd like to document.":
                uc.title = first_user[:60].strip()
        upsert(uc)


def _finalize_intake(uc_id: str):
    """Generate summary, mark intake complete, navigate to structure page."""
    messages = st.session_state["intake_messages"]
    with st.spinner("Generating intake summary…"):
        summary = llm_client.generate_summary(messages)

    uc = get_by_id(uc_id)
    if uc:
        uc.intake.chat_history = messages
        uc.intake.raw_summary = summary
        uc.meta.intake_complete = True
        uc.status = "idea"
        upsert(uc)

    st.session_state["intake_initialized"] = False
    st.switch_page("pages/2_Structure.py")


def _extract_learnings(messages: list[dict]) -> dict:
    """Simple keyword scan of conversation to show progress panel."""
    full_text = " ".join(m["content"] for m in messages).lower()

    learnings = {}

    # Problem hints
    problem_keywords = ["problem", "issue", "challenge", "pain", "manual", "error", "slow", "inefficient"]
    if any(kw in full_text for kw in problem_keywords):
        user_msgs = [m["content"] for m in messages if m["role"] == "user"]
        if user_msgs:
            learnings["Problem glimpse"] = user_msgs[-1][:120] + "…"

    # Users
    user_patterns = re.findall(r"\b(\d+)\s*(people|users|fte|employees|team members|staff)\b", full_text)
    team_patterns = re.findall(r"\b([\w\s]+team|[\w\s]+department|[\w\s]+group)\b", full_text)
    hints = []
    if user_patterns:
        hints.append(f"~{user_patterns[0][0]} {user_patterns[0][1]}")
    if team_patterns:
        hints.append(team_patterns[0].strip().title())
    if hints:
        learnings["Impacted users"] = ", ".join(hints[:3])

    # Data sources
    data_keywords = ["database", "crm", "erp", "excel", "spreadsheet", "sql", "api", "salesforce",
                     "sap", "data warehouse", "csv", "log", "system", "platform"]
    data_found = [kw for kw in data_keywords if kw in full_text]
    if data_found:
        learnings["Data sources"] = ", ".join(data_found[:4])

    # Benefit
    benefit_patterns = re.findall(r"\$[\d,]+|\d+[%]|\d+\s*hours?|\d+\s*days?", full_text)
    if benefit_patterns:
        learnings["Benefit hints"] = ", ".join(benefit_patterns[:3])

    return learnings


# ── Main layout ────────────────────────────────────────────────────────────────
_sidebar()

st.title("💬 Step 1: Idea Intake")
st.caption("Chat with the AI advisor to document your use case idea.")

# Initialize or load
if not st.session_state["intake_initialized"]:
    uc_id = st.session_state.get("active_uc_id")
    if uc_id:
        # Load existing
        uc = get_by_id(uc_id)
        if uc and uc.intake.chat_history:
            st.session_state["intake_messages"] = uc.intake.chat_history.copy()
            st.session_state["intake_initialized"] = True
        else:
            with st.spinner("Starting intake session…"):
                uc_id = _initialize_new_use_case()
    else:
        with st.spinner("Starting intake session…"):
            uc_id = _initialize_new_use_case()

uc_id = st.session_state.get("active_uc_id")
messages = st.session_state.get("intake_messages", [])
user_turn_count = sum(1 for m in messages if m["role"] == "user")

# Layout: chat left, panel right
chat_col, panel_col = st.columns([3, 2])

with chat_col:
    # Render messages
    chat_container = st.container(height=500)
    with chat_container:
        for msg in messages:
            if msg["role"] == "user" and msg["content"] == "Hi, I have an AI use case idea I'd like to document.":
                continue  # hide the seed message
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # Input
    if user_input := st.chat_input("Share your idea or answer the question…"):
        with st.spinner("Thinking…"):
            _send_message(user_input, uc_id)
        st.rerun()

with panel_col:
    st.subheader("What I've learned so far")

    learnings = _extract_learnings(messages)
    if learnings:
        for key, value in learnings.items():
            with st.container(border=True):
                st.caption(key)
                st.write(value[:150])
    else:
        st.info("Start chatting and key details will appear here.")

    st.divider()

    # Progress indicator
    min_turns = 4
    progress = min(user_turn_count / min_turns, 1.0)
    st.progress(progress, text=f"Conversation depth: {user_turn_count} exchanges")

    if user_turn_count < min_turns:
        remaining = min_turns - user_turn_count
        st.caption(f"💡 {remaining} more exchange(s) recommended before finalizing.")
    else:
        st.success("Ready to finalize when you're satisfied with the conversation.")

    st.divider()

    finalize_disabled = user_turn_count < 2
    if st.button(
        "✅ Finalize Intake → Structure",
        disabled=finalize_disabled,
        type="primary",
        use_container_width=True,
    ):
        _finalize_intake(uc_id)

    if finalize_disabled:
        st.caption("Complete at least 2 exchanges before finalizing.")
