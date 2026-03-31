import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="AI Portfolio Manager",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.session_state.setdefault("active_uc_id", None)

CATEGORY_STYLE = {
    "Quick Win":            ("🟢", "#1a7a4a", "#d4edda"),
    "Strategic Initiative": ("🔵", "#1a4a8a", "#d0e4f7"),
    "Backlog":              ("⚪", "#555555", "#eeeeee"),
    "Deprioritized":        ("🔴", "#8a1a1a", "#f7d0d0"),
}

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🤖 AI Portfolio")
    st.divider()
    st.page_link("app.py",              label="Home",          icon="🏠")
    st.page_link("pages/1_Intake.py",   label="1. Idea Intake",icon="💬")
    st.page_link("pages/2_Structure.py",label="2. Structure",  icon="📋")
    st.page_link("pages/3_Scoring.py",  label="3. Scoring",    icon="📊")
    st.page_link("pages/4_Portfolio.py",label="4. Portfolio",  icon="🗂️")
    st.page_link("pages/5_Handoff.py",  label="5. Handoff",    icon="📄")
    st.divider()

    try:
        from core.data_store import load_all
        use_cases = load_all()
        total = len(use_cases)

        st.caption("Portfolio Summary")
        c1, c2 = st.columns(2)
        c1.metric("🟢 Quick Wins",  sum(1 for uc in use_cases if uc.scoring.category == "Quick Win"))
        c2.metric("🔵 Strategic",   sum(1 for uc in use_cases if uc.scoring.category == "Strategic Initiative"))
        c3, c4 = st.columns(2)
        c3.metric("⚪ Backlog",     sum(1 for uc in use_cases if uc.scoring.category == "Backlog"))
        c4.metric("🔴 Deprioritised",sum(1 for uc in use_cases if uc.scoring.category == "Deprioritized"))

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
    "Turn AI ideas into **structured, scored, and delivery-ready initiatives** — "
    "from first conversation to PRD in minutes."
)

st.divider()

# ── Portfolio metrics ──────────────────────────────────────────────────────────
try:
    from core.data_store import load_all
    use_cases = load_all()

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Use Cases",       len(use_cases))
    col2.metric("🟢 Quick Wins",         sum(1 for uc in use_cases if uc.scoring.category == "Quick Win"))
    col3.metric("🔵 Strategic",          sum(1 for uc in use_cases if uc.scoring.category == "Strategic Initiative"))
    col4.metric("⚪ Backlog",            sum(1 for uc in use_cases if uc.scoring.category == "Backlog"))
    col5.metric("🔴 Deprioritised",      sum(1 for uc in use_cases if uc.scoring.category == "Deprioritized"))
    col6.metric("🔨 In Progress",        sum(1 for uc in use_cases if uc.status == "in_progress"))
except Exception as e:
    st.warning(f"Could not load portfolio data: {e}")

st.divider()

# ── Workflow overview ──────────────────────────────────────────────────────────
st.subheader("How it works")
steps = [
    ("💬", "1. Idea Intake",  "Chat with an AI agent to capture and document your idea."),
    ("📋", "2. AI Structuring","Auto-extract problem statement, spoke alignment, solution category, and scoring inputs."),
    ("📊", "3. Scoring",      "Compute Net Value & Net Effort scores using the CSL R&D prioritisation framework."),
    ("🗂️", "4. Portfolio",    "View all initiatives on a categorised Kanban board with filters and analytics."),
    ("📄", "5. Handoff",      "Generate PRD, technical spec, and Jira tickets ready for delivery teams."),
]
cols = st.columns(5)
for col, (icon, title, desc) in zip(cols, steps):
    with col:
        st.markdown(f"### {icon}")
        st.markdown(f"**{title}**")
        st.caption(desc)

st.divider()

# ── Scoring framework recap ────────────────────────────────────────────────────
st.subheader("Prioritisation Framework")
fc1, fc2, fc3, fc4 = st.columns(4)
for col, (cat, (icon, text_col, bg)) in zip(
    [fc1, fc2, fc3, fc4], CATEGORY_STYLE.items()
):
    with col:
        st.markdown(
            f"<div style='background:{bg};border-left:5px solid {text_col};"
            f"padding:14px 16px;border-radius:6px;height:100px;'>"
            f"<div style='font-size:1.4rem;'>{icon}</div>"
            f"<div style='font-weight:700;color:{text_col};'>{cat}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.caption(
    "**Net Value** = (Business Impact ×2) + Foundational Impact &nbsp;·&nbsp; "
    "**Net Effort** = Technical Complexity (inverted) + Data Availability &nbsp;·&nbsp; "
    "Threshold: Value ≥ 6 → High · Effort ≥ 5 → Low"
)

st.divider()

col_a, col_b = st.columns([1, 3])
with col_a:
    if st.button("➕ New Use Case", type="primary", use_container_width=True):
        st.session_state["active_uc_id"] = None
        st.switch_page("pages/1_Intake.py")
with col_b:
    if st.button("🗂️ View Portfolio", use_container_width=True):
        st.switch_page("pages/4_Portfolio.py")
