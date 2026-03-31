import streamlit as st
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="AI Structuring", page_icon="📋", layout="wide")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import load_all, upsert, get_by_id
from core.models import (
    StructuredData,
    SPOKE_ALIGNMENTS, SOLUTION_CATEGORIES, GROUPINGS, IMPACT_OPTIONS, COMPLEXITY_OPTIONS,
)
from core import llm_client


st.session_state.setdefault("active_uc_id", None)


def _sidebar():
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

        use_cases = load_all()
        ready = [uc for uc in use_cases if uc.meta.intake_complete]
        if ready:
            options = {uc.id: uc.title for uc in ready}
            st.caption("Switch use case")
            current = st.session_state["active_uc_id"]
            idx = list(options.keys()).index(current) if current in options else 0
            selected = st.selectbox(
                "Select", list(options.keys()),
                format_func=lambda x: options[x],
                label_visibility="collapsed", index=idx,
            )
            if st.button("Load", use_container_width=True):
                st.session_state["active_uc_id"] = selected
                st.rerun()


def _run_structuring(uc_id: str) -> StructuredData:
    uc = get_by_id(uc_id)
    prompt_template = llm_client.load_prompt("structuring.txt")
    raw = llm_client.structure_use_case(uc.intake.chat_history, prompt_template)

    s = uc.structured
    s.problem_statement           = raw.get("problem_statement", "")
    s.impacted_users              = raw.get("impacted_users", "")
    s.available_data_sources      = raw.get("available_data_sources", [])
    s.expected_benefit_description = raw.get("expected_benefit_description", "")
    s.suggested_approach          = raw.get("suggested_approach", "")
    s.spoke_alignment             = raw.get("spoke_alignment", "")
    s.solution_category           = raw.get("solution_category", "")
    s.grouping                    = raw.get("grouping", "")
    s.business_impact_level       = raw.get("business_impact_level", "medium").lower()
    s.foundational_impact_level   = raw.get("foundational_impact_level", "medium").lower()
    s.technical_complexity        = raw.get("technical_complexity",
                                            raw.get("complexity_estimate", "medium")).lower()
    s.data_availability_level     = raw.get("data_availability_level", "medium").lower()
    s.structuring_completed_at    = datetime.now(timezone.utc).isoformat()

    if s.problem_statement and uc.title in ("New Use Case", ""):
        uc.title = s.problem_statement[:60].strip()

    uc.structured = s
    uc.meta.structuring_complete = True
    uc.status = "structured"
    upsert(uc)
    return s


def _impact_index(val: str) -> int:
    """Map low/medium/high → selectbox index (case-insensitive)."""
    opts = [o.lower() for o in IMPACT_OPTIONS]
    return opts.index(val.lower()) if val.lower() in opts else 1


# ── Main ───────────────────────────────────────────────────────────────────────
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

# Auto-run structuring on first visit (intake-sourced records)
if not uc.meta.structuring_complete or not uc.structured.structuring_completed_at:
    if uc.intake.chat_history:
        with st.spinner("AI is structuring your use case…"):
            _run_structuring(uc_id)
        uc = get_by_id(uc_id)
        st.success("Structuring complete! Review and edit the fields below.")
    else:
        # Pre-loaded record — mark structuring as done so we skip the spinner
        uc.meta.structuring_complete = True
        upsert(uc)

s = uc.structured

# ── Layout: summary left / form right ─────────────────────────────────────────
left_col, right_col = st.columns([2, 3])

with left_col:
    st.subheader("Intake Summary")
    if uc.intake.raw_summary:
        st.markdown(uc.intake.raw_summary)
    elif s.problem_statement:
        st.markdown(s.problem_statement)
    else:
        st.caption("No summary available.")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Re-run AI Structuring", use_container_width=True,
                     disabled=not bool(uc.intake.chat_history)):
            with st.spinner("Re-structuring…"):
                _run_structuring(uc_id)
            st.rerun()
    with col_b:
        if st.button("← Back to Intake", use_container_width=True):
            st.switch_page("pages/1_Intake.py")

with right_col:
    st.subheader("Structured Use Case")

    with st.form("structuring_form"):

        # ── Identity ─────────────────────────────────────────────────────────
        st.markdown("**Identity**")
        c1, c2 = st.columns(2)
        title      = c1.text_input("Use Case Title",          value=uc.title)
        department = c2.text_input("R&D Function / Department", value=uc.department)

        problem_statement = st.text_area(
            "Problem Statement", value=s.problem_statement, height=90,
        )
        impacted_users = st.text_input("Impacted Users / Teams", value=s.impacted_users)

        st.divider()

        # ── Classification ───────────────────────────────────────────────────
        st.markdown("**Classification**")
        c3, c4, c5 = st.columns(3)

        spoke_idx = SPOKE_ALIGNMENTS.index(s.spoke_alignment) \
            if s.spoke_alignment in SPOKE_ALIGNMENTS else 0
        spoke_alignment = c3.selectbox("Spoke Alignment", SPOKE_ALIGNMENTS, index=spoke_idx)

        sol_idx = SOLUTION_CATEGORIES.index(s.solution_category) \
            if s.solution_category in SOLUTION_CATEGORIES else 0
        solution_category = c4.selectbox("Solution Category", SOLUTION_CATEGORIES, index=sol_idx)

        grp_idx = GROUPINGS.index(s.grouping) if s.grouping in GROUPINGS else 0
        grouping = c5.selectbox("Grouping", GROUPINGS, index=grp_idx)

        st.divider()

        # ── Scoring inputs (4 dimensions) ────────────────────────────────────
        st.markdown("**Scoring Inputs**")
        st.caption(
            "These four dimensions feed directly into Net Value and Net Effort scores. "
            "Business Impact is weighted 2×."
        )

        sc1, sc2, sc3, sc4 = st.columns(4)

        business_impact_level = sc1.selectbox(
            "Business Impact",
            IMPACT_OPTIONS,
            index=_impact_index(s.business_impact_level),
            help="Direct impact on cycle time, portfolio growth, or operational efficiency.",
        )
        foundational_impact_level = sc2.selectbox(
            "Foundational Impact",
            IMPACT_OPTIONS,
            index=_impact_index(s.foundational_impact_level),
            help="Cross-functional or enterprise-wide enablement value.",
        )
        technical_complexity = sc3.selectbox(
            "Technical Complexity",
            COMPLEXITY_OPTIONS,
            index=_impact_index(s.technical_complexity),
            help="Lower complexity = higher effort score (easier to execute).",
        )
        data_availability_level = sc4.selectbox(
            "Data Availability",
            IMPACT_OPTIONS,
            index=_impact_index(s.data_availability_level),
            help="How readily available and accessible the required data is.",
        )

        st.divider()

        # ── Supporting detail ─────────────────────────────────────────────────
        st.markdown("**Supporting Detail**")

        data_sources_str = st.text_area(
            "Available Data Sources (one per line)",
            value="\n".join(s.available_data_sources),
            height=70,
        )
        expected_benefit_description = st.text_area(
            "Expected Benefit / Justification",
            value=s.expected_benefit_description,
            height=70,
        )
        suggested_approach = st.text_area(
            "Suggested Approach",
            value=s.suggested_approach,
            height=80,
        )

        submitted = st.form_submit_button(
            "💾 Save & Proceed to Scoring →", type="primary",
        )

    if submitted:
        uc.title      = title
        uc.department = department
        uc.structured.problem_statement          = problem_statement
        uc.structured.impacted_users             = impacted_users
        uc.structured.spoke_alignment            = spoke_alignment
        uc.structured.solution_category          = solution_category
        uc.structured.grouping                   = grouping
        uc.structured.business_impact_level      = business_impact_level.lower()
        uc.structured.foundational_impact_level  = foundational_impact_level.lower()
        uc.structured.technical_complexity       = technical_complexity.lower()
        uc.structured.data_availability_level    = data_availability_level.lower()
        uc.structured.available_data_sources     = [
            ln.strip() for ln in data_sources_str.splitlines() if ln.strip()
        ]
        uc.structured.expected_benefit_description = expected_benefit_description
        uc.structured.suggested_approach           = suggested_approach
        uc.meta.structuring_complete = True
        uc.status = "structured"
        upsert(uc)
        st.success("Saved!")
        st.switch_page("pages/3_Scoring.py")
