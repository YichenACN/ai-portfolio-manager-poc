import streamlit as st
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="AI Structuring", page_icon="📋", layout="wide")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import load_all, upsert, get_by_id
from core.models import StructuredData, USE_CASE_CATEGORIES, BENEFIT_TYPES, COMPLEXITY_OPTIONS, STRATEGIC_ALIGNMENT_OPTIONS
from core import llm_client


# ── Session state defaults ─────────────────────────────────────────────────────
st.session_state.setdefault("active_uc_id", None)


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

        use_cases = load_all()
        ready = [uc for uc in use_cases if uc.meta.intake_complete]
        if ready:
            options = {uc.id: uc.title for uc in ready}
            st.caption("Switch use case")
            selected = st.selectbox(
                "Select",
                list(options.keys()),
                format_func=lambda x: options[x],
                label_visibility="collapsed",
                index=list(options.keys()).index(st.session_state["active_uc_id"])
                if st.session_state["active_uc_id"] in options else 0,
            )
            if st.button("Load", use_container_width=True):
                st.session_state["active_uc_id"] = selected
                st.rerun()


def _run_structuring(uc_id: str) -> StructuredData:
    uc = get_by_id(uc_id)
    prompt_template = llm_client.load_prompt("structuring.txt")
    raw = llm_client.structure_use_case(uc.intake.chat_history, prompt_template)

    structured = uc.structured
    structured.problem_statement = raw.get("problem_statement", "")
    structured.use_case_category = raw.get("use_case_category", "other")
    structured.impacted_users = raw.get("impacted_users", "")
    structured.available_data_sources = raw.get("available_data_sources", [])
    structured.expected_benefit_type = raw.get("expected_benefit_type", "other")
    structured.expected_benefit_description = raw.get("expected_benefit_description", "")
    structured.complexity_estimate = raw.get("complexity_estimate", "medium")
    structured.suggested_approach = raw.get("suggested_approach", "")
    structured.strategic_alignment = raw.get("strategic_alignment", [])
    structured.structuring_completed_at = datetime.now(timezone.utc).isoformat()

    # Update use case title from problem statement
    if structured.problem_statement and uc.title in ("New Use Case", ""):
        uc.title = structured.problem_statement[:60].strip()

    uc.structured = structured
    uc.meta.structuring_complete = True
    uc.status = "structured"
    upsert(uc)
    return structured


# ── Main layout ────────────────────────────────────────────────────────────────
_sidebar()

st.title("📋 Step 2: AI Structuring")
st.caption("Review and refine the AI-extracted structure of your use case.")

uc_id = st.session_state.get("active_uc_id")

if not uc_id:
    st.warning("No active use case. Go back to Idea Intake to start one.")
    if st.button("← Go to Intake"):
        st.switch_page("pages/1_Intake.py")
    st.stop()

uc = get_by_id(uc_id)
if not uc:
    st.error("Use case not found.")
    st.stop()

if not uc.meta.intake_complete:
    st.warning("Intake is not yet complete for this use case.")
    if st.button("← Complete Intake First"):
        st.switch_page("pages/1_Intake.py")
    st.stop()

# Auto-run structuring on first visit
if not uc.meta.structuring_complete or not uc.structured.structuring_completed_at:
    with st.spinner("AI is structuring your use case…"):
        structured = _run_structuring(uc_id)
    uc = get_by_id(uc_id)
    st.success("Structuring complete! Review and edit the fields below.")

structured = uc.structured

# Layout: summary left, form right
left_col, right_col = st.columns([2, 3])

with left_col:
    st.subheader("Intake Summary")
    if uc.intake.raw_summary:
        st.markdown(uc.intake.raw_summary)
    else:
        st.caption("No summary available. Raw chat history below.")
        for msg in uc.intake.chat_history[-6:]:
            role_label = "You" if msg["role"] == "user" else "AI"
            st.caption(f"**{role_label}:** {msg['content'][:200]}")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Re-run AI Structuring", use_container_width=True):
            with st.spinner("Re-structuring…"):
                _run_structuring(uc_id)
            st.rerun()
    with col_b:
        if st.button("← Back to Intake", use_container_width=True):
            st.switch_page("pages/1_Intake.py")

with right_col:
    st.subheader("Structured Use Case")

    with st.form("structuring_form"):
        title = st.text_input("Use Case Title", value=uc.title)
        department = st.text_input("Department / Business Unit", value=uc.department)

        problem_statement = st.text_area(
            "Problem Statement", value=structured.problem_statement, height=100
        )

        col1, col2 = st.columns(2)
        with col1:
            category_idx = USE_CASE_CATEGORIES.index(structured.use_case_category) \
                if structured.use_case_category in USE_CASE_CATEGORIES else 0
            use_case_category = st.selectbox(
                "Use Case Category", USE_CASE_CATEGORIES, index=category_idx
            )
            benefit_idx = BENEFIT_TYPES.index(structured.expected_benefit_type) \
                if structured.expected_benefit_type in BENEFIT_TYPES else 3
            expected_benefit_type = st.selectbox(
                "Benefit Type", BENEFIT_TYPES, index=benefit_idx
            )
        with col2:
            complexity_idx = COMPLEXITY_OPTIONS.index(structured.complexity_estimate) \
                if structured.complexity_estimate in COMPLEXITY_OPTIONS else 1
            complexity_estimate = st.selectbox(
                "Complexity", COMPLEXITY_OPTIONS, index=complexity_idx
            )
            strategic_alignment = st.multiselect(
                "Strategic Alignment",
                STRATEGIC_ALIGNMENT_OPTIONS,
                default=[s for s in structured.strategic_alignment if s in STRATEGIC_ALIGNMENT_OPTIONS],
            )

        impacted_users = st.text_input("Impacted Users / Teams", value=structured.impacted_users)

        data_sources_str = st.text_area(
            "Available Data Sources (one per line)",
            value="\n".join(structured.available_data_sources),
            height=80,
        )

        expected_benefit_description = st.text_area(
            "Expected Benefit Description", value=structured.expected_benefit_description, height=80
        )

        suggested_approach = st.text_area(
            "Suggested AI Approach", value=structured.suggested_approach, height=100
        )

        submitted = st.form_submit_button("💾 Save & Proceed to Scoring →", type="primary")

    if submitted:
        uc.title = title
        uc.department = department
        uc.structured.problem_statement = problem_statement
        uc.structured.use_case_category = use_case_category
        uc.structured.impacted_users = impacted_users
        uc.structured.available_data_sources = [
            s.strip() for s in data_sources_str.splitlines() if s.strip()
        ]
        uc.structured.expected_benefit_type = expected_benefit_type
        uc.structured.expected_benefit_description = expected_benefit_description
        uc.structured.complexity_estimate = complexity_estimate
        uc.structured.suggested_approach = suggested_approach
        uc.structured.strategic_alignment = strategic_alignment
        uc.meta.structuring_complete = True
        uc.status = "structured"
        upsert(uc)
        st.success("Saved!")
        st.switch_page("pages/3_Scoring.py")
