import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="AI Portfolio Manager",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize shared session state
st.session_state.setdefault("active_uc_id", None)

# Sidebar
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

    # Quick stats
    try:
        from core.data_store import load_all
        use_cases = load_all()
        total = len(use_cases)
        p1 = sum(1 for uc in use_cases if uc.scoring.priority_tier == "P1")
        p2 = sum(1 for uc in use_cases if uc.scoring.priority_tier == "P2")
        p3 = sum(1 for uc in use_cases if uc.scoring.priority_tier == "P3")
        st.caption("Portfolio Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("P1", p1)
        col2.metric("P2", p2)
        col3.metric("P3", p3)

        active_id = st.session_state.get("active_uc_id")
        if active_id:
            active = next((uc for uc in use_cases if uc.id == active_id), None)
            if active:
                st.divider()
                st.caption("Active Use Case")
                st.info(active.title[:40] + ("…" if len(active.title) > 40 else ""))
    except Exception:
        pass

# ── Home page ──────────────────────────────────────────────────────────────────
st.title("AI Initiative Portfolio Manager")
st.markdown(
    "Turn messy AI ideas into **structured, scored, and actionable** initiatives — "
    "from first conversation to delivery-ready documents."
)

st.divider()

# Summary metrics
try:
    from core.data_store import load_all
    use_cases = load_all()

    status_counts = {}
    for uc in use_cases:
        status_counts[uc.status] = status_counts.get(uc.status, 0) + 1

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Ideas", len(use_cases))
    col2.metric("Idea", status_counts.get("idea", 0))
    col3.metric("Structured", status_counts.get("structured", 0) + status_counts.get("scored", 0))
    col4.metric("Validated", status_counts.get("validated", 0))
    col5.metric("In Progress", status_counts.get("in_progress", 0))
    col6.metric("Deployed", status_counts.get("deployed", 0))
except Exception as e:
    st.warning(f"Could not load portfolio data: {e}")

st.divider()

# Workflow overview
st.subheader("How it works")
steps = [
    ("💬", "1. Idea Intake", "Chat with an AI agent to capture your idea through structured questions."),
    ("📋", "2. AI Structuring", "Automatically extract problem statement, category, data needs, and approach."),
    ("📊", "3. Scoring", "Get instant scores on business impact, feasibility, data readiness, and risk."),
    ("🗂️", "4. Portfolio", "Track all initiatives in a Kanban board with filters and analytics."),
    ("📄", "5. Handoff", "Generate PRD, technical spec, and Jira tickets ready for delivery teams."),
]

cols = st.columns(5)
for col, (icon, title, desc) in zip(cols, steps):
    with col:
        st.markdown(f"### {icon}")
        st.markdown(f"**{title}**")
        st.caption(desc)

st.divider()

col_a, col_b = st.columns([1, 3])
with col_a:
    if st.button("➕ New Use Case", type="primary", use_container_width=True):
        st.session_state["active_uc_id"] = None
        st.switch_page("pages/1_Intake.py")
with col_b:
    if st.button("🗂️ View Portfolio", use_container_width=True):
        st.switch_page("pages/4_Portfolio.py")
