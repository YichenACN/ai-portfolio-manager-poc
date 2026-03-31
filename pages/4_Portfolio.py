import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Portfolio", page_icon="🗂️", layout="wide")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import load_all, upsert, delete as delete_uc
from core.models import UseCase, STATUS_ORDER

# ── Session state defaults ─────────────────────────────────────────────────────
st.session_state.setdefault("active_uc_id", None)

STATUS_COLORS = {
    "idea": "gray",
    "structured": "blue",
    "scored": "orange",
    "validated": "green",
    "in_progress": "violet",
    "deployed": "green",
}

PRIORITY_COLORS = {"P1": "red", "P2": "orange", "P3": "gray"}

KANBAN_COLUMNS = ["idea", "validated", "in_progress", "deployed"]
KANBAN_LABELS = {
    "idea": "💡 Idea / Backlog",
    "validated": "✅ Validated",
    "in_progress": "🔨 In Progress",
    "deployed": "🚀 Deployed",
}


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
        if st.button("➕ New Use Case", use_container_width=True, type="primary"):
            st.session_state["active_uc_id"] = None
            st.switch_page("pages/1_Intake.py")


def _apply_filters(use_cases: list[UseCase], filters: dict) -> list[UseCase]:
    result = use_cases
    if filters.get("departments"):
        result = [uc for uc in result if uc.department in filters["departments"]]
    if filters.get("statuses"):
        result = [uc for uc in result if uc.status in filters["statuses"]]
    if filters.get("priorities"):
        result = [uc for uc in result if uc.scoring.priority_tier in filters["priorities"]]
    if filters.get("categories"):
        result = [uc for uc in result if uc.structured.use_case_category in filters["categories"]]
    if filters.get("min_roi") and filters["min_roi"] > 0:
        result = [uc for uc in result if uc.scoring.roi_projection_12mo >= filters["min_roi"]]
    if filters.get("search"):
        q = filters["search"].lower()
        result = [
            uc for uc in result
            if q in uc.title.lower()
            or q in uc.department.lower()
            or q in uc.structured.problem_statement.lower()
        ]
    return result


def _status_badge(status: str) -> str:
    icons = {
        "idea": "💡", "structured": "📋", "scored": "📊",
        "validated": "✅", "in_progress": "🔨", "deployed": "🚀",
    }
    return f"{icons.get(status, '')} {status.replace('_', ' ').title()}"


def _render_kanban_card(uc: UseCase):
    with st.container(border=True):
        col_title, col_badge = st.columns([3, 1])
        with col_title:
            st.markdown(f"**{uc.title[:45]}**")
        with col_badge:
            tier = uc.scoring.priority_tier
            st.markdown(
                f"<span style='color: {'red' if tier=='P1' else 'orange' if tier=='P2' else 'gray'}'>"
                f"● {tier}</span>",
                unsafe_allow_html=True,
            )
        st.caption(f"{uc.department or 'No dept'} · {uc.structured.use_case_category}")
        if uc.scoring.composite_score > 0:
            st.caption(
                f"Score: {uc.scoring.composite_score}/100 · "
                f"ROI: ${uc.scoring.roi_projection_12mo:,.0f}"
            )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Open", key=f"open_{uc.id}", use_container_width=True):
                st.session_state["active_uc_id"] = uc.id
                st.switch_page("pages/5_Handoff.py")
        with col_b:
            # Next status transition
            current_idx = STATUS_ORDER.index(uc.status) if uc.status in STATUS_ORDER else 0
            if current_idx < len(STATUS_ORDER) - 1:
                next_status = STATUS_ORDER[current_idx + 1]
                if st.button(f"→ {next_status.replace('_',' ').title()}", key=f"adv_{uc.id}", use_container_width=True):
                    uc.status = next_status
                    upsert(uc)
                    st.rerun()


def _build_dataframe(use_cases: list[UseCase]) -> pd.DataFrame:
    rows = []
    for uc in use_cases:
        rows.append({
            "ID": uc.id,
            "Title": uc.title,
            "Department": uc.department,
            "Category": uc.structured.use_case_category,
            "Status": uc.status,
            "Priority": uc.scoring.priority_tier,
            "Score": uc.scoring.composite_score,
            "ROI ($)": uc.scoring.roi_projection_12mo,
            "Effort (wks)": uc.scoring.effort_estimate_weeks,
        })
    return pd.DataFrame(rows)


# ── Main layout ────────────────────────────────────────────────────────────────
_sidebar()

st.title("🗂️ Step 4: Portfolio Dashboard")
st.caption("Track, filter, and manage all AI initiatives.")

use_cases = load_all()

if not use_cases:
    st.info("No use cases yet. Start by creating one!")
    if st.button("➕ New Use Case", type="primary"):
        st.switch_page("pages/1_Intake.py")
    st.stop()

# ── Filters ────────────────────────────────────────────────────────────────────
with st.expander("🔍 Filters", expanded=True):
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)
    all_departments = sorted(set(uc.department for uc in use_cases if uc.department))
    all_statuses = STATUS_ORDER
    all_priorities = ["P1", "P2", "P3"]
    all_categories = sorted(set(uc.structured.use_case_category for uc in use_cases))

    f_dept = fc1.multiselect("Department", all_departments)
    f_status = fc2.multiselect("Status", all_statuses, format_func=lambda s: s.replace("_", " ").title())
    f_priority = fc3.multiselect("Priority", all_priorities)
    f_category = fc4.multiselect("Category", all_categories)
    f_search = fc5.text_input("Search", placeholder="Search title/dept…")

filters = {
    "departments": f_dept,
    "statuses": f_status,
    "priorities": f_priority,
    "categories": f_category,
    "search": f_search,
}
filtered = _apply_filters(use_cases, filters)

# ── Summary metrics ────────────────────────────────────────────────────────────
mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
mc1.metric("Total", len(filtered))
mc2.metric("P1", sum(1 for uc in filtered if uc.scoring.priority_tier == "P1"))
mc3.metric("P2", sum(1 for uc in filtered if uc.scoring.priority_tier == "P2"))
mc4.metric("P3", sum(1 for uc in filtered if uc.scoring.priority_tier == "P3"))
mc5.metric("In Progress", sum(1 for uc in filtered if uc.status == "in_progress"))
mc6.metric("Deployed", sum(1 for uc in filtered if uc.status == "deployed"))

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_kanban, tab_table, tab_analytics = st.tabs(["Kanban", "Table", "Analytics"])

# ── Kanban tab ─────────────────────────────────────────────────────────────────
with tab_kanban:
    cols = st.columns(4)
    for col, status_key in zip(cols, KANBAN_COLUMNS):
        with col:
            # Include scored/structured items in the "idea" column
            if status_key == "idea":
                col_items = [uc for uc in filtered if uc.status in ("idea", "structured", "scored")]
            else:
                col_items = [uc for uc in filtered if uc.status == status_key]

            st.markdown(f"**{KANBAN_LABELS[status_key]}** ({len(col_items)})")
            st.divider()
            if not col_items:
                st.caption("Empty")
            for uc in col_items:
                _render_kanban_card(uc)

# ── Table tab ──────────────────────────────────────────────────────────────────
with tab_table:
    if filtered:
        df = _build_dataframe(filtered)
        display_df = df.drop(columns=["ID"])
        selection = st.dataframe(
            display_df,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
        )

        if selection and selection.selection.rows:
            row_idx = selection.selection.rows[0]
            selected_uc = filtered[row_idx]
            st.session_state["active_uc_id"] = selected_uc.id

            st.divider()
            col_open, col_score, col_del = st.columns([2, 2, 1])
            with col_open:
                if st.button("📄 Open Handoff", use_container_width=True, type="primary"):
                    st.switch_page("pages/5_Handoff.py")
            with col_score:
                if st.button("📊 View Scoring", use_container_width=True):
                    st.switch_page("pages/3_Scoring.py")
            with col_del:
                if st.button("🗑️ Delete", use_container_width=True):
                    delete_uc(selected_uc.id)
                    st.session_state["active_uc_id"] = None
                    st.rerun()
    else:
        st.info("No use cases match the current filters.")

# ── Analytics tab ──────────────────────────────────────────────────────────────
with tab_analytics:
    if not filtered:
        st.info("No data to display.")
    else:
        a1, a2 = st.columns(2)

        with a1:
            st.subheader("Use Cases by Status")
            status_df = pd.DataFrame(
                [(s.replace("_", " ").title(), sum(1 for uc in filtered if uc.status == s))
                 for s in STATUS_ORDER],
                columns=["Status", "Count"],
            ).set_index("Status")
            st.bar_chart(status_df)

        with a2:
            st.subheader("Priority Distribution")
            priority_df = pd.DataFrame(
                [(p, sum(1 for uc in filtered if uc.scoring.priority_tier == p))
                 for p in ["P1", "P2", "P3"]],
                columns=["Priority", "Count"],
            ).set_index("Priority")
            st.bar_chart(priority_df)

        st.subheader("ROI by Department")
        dept_data = {}
        for uc in filtered:
            dept = uc.department or "Unspecified"
            dept_data[dept] = dept_data.get(dept, 0) + uc.scoring.roi_projection_12mo
        if dept_data:
            dept_df = pd.DataFrame(
                list(dept_data.items()), columns=["Department", "Total ROI ($)"]
            ).set_index("Department").sort_values("Total ROI ($)", ascending=False)
            st.bar_chart(dept_df)

        st.subheader("Score vs. Effort")
        scatter_df = pd.DataFrame([
            {"Use Case": uc.title[:30], "Composite Score": uc.scoring.composite_score,
             "Effort (weeks)": uc.scoring.effort_estimate_weeks}
            for uc in filtered if uc.scoring.composite_score > 0
        ])
        if not scatter_df.empty:
            st.dataframe(
                scatter_df.sort_values("Composite Score", ascending=False),
                use_container_width=True,
            )
