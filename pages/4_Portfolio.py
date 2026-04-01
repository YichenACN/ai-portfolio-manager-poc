import html
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Portfolio", page_icon="🗂️", layout="wide")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import load_all, upsert, delete as delete_uc
from core.models import UseCase, STATUS_ORDER, CATEGORIES, SPOKE_ALIGNMENTS, GROUPINGS

st.session_state.setdefault("active_uc_id", None)

# ── Style constants ────────────────────────────────────────────────────────────
CATEGORY_STYLE = {
    "Quick Win":            ("🟢", "#1a7a4a", "#d4edda"),
    "Strategic Initiative": ("🔵", "#1a4a8a", "#d0e4f7"),
    "Backlog":              ("⚪", "#555555", "#eeeeee"),
    "Deprioritized":        ("🔴", "#8a1a1a", "#f7d0d0"),
}

STATUS_ICON = {
    "idea": "💡", "structured": "📋", "scored": "📊",
    "validated": "✅", "in_progress": "🔨", "deployed": "🚀",
}

# Kanban: category-based columns (not status-based)
KANBAN_COLS = ["Quick Win", "Strategic Initiative", "Backlog", "Deprioritized"]


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
        if st.button("➕ New Use Case", use_container_width=True, type="primary"):
            st.session_state["active_uc_id"] = None
            st.switch_page("pages/1_Intake.py")


def _apply_filters(use_cases: list, filters: dict) -> list:
    result = use_cases
    if filters.get("categories"):
        result = [uc for uc in result if uc.scoring.category in filters["categories"]]
    if filters.get("spokes"):
        result = [uc for uc in result if uc.structured.spoke_alignment in filters["spokes"]]
    if filters.get("statuses"):
        result = [uc for uc in result if uc.status in filters["statuses"]]
    if filters.get("groupings"):
        result = [uc for uc in result if uc.structured.grouping in filters["groupings"]]
    if filters.get("net_value"):
        result = [uc for uc in result if uc.scoring.net_value in filters["net_value"]]
    if filters.get("search"):
        q = filters["search"].lower()
        result = [
            uc for uc in result
            if q in uc.title.lower()
            or q in uc.department.lower()
            or q in uc.structured.problem_statement.lower()
        ]
    return result


def _category_chip(category: str) -> str:
    icon, text_color, bg = CATEGORY_STYLE.get(category, ("⚪", "#555", "#eee"))
    return (
        f"<span style='background:{bg};color:{text_color};border:1px solid {text_color};"
        f"padding:2px 8px;border-radius:12px;font-size:0.78rem;font-weight:600;'>"
        f"{icon} {category}</span>"
    )


def _render_kanban_card(uc: UseCase):
    _, text_color, bg = CATEGORY_STYLE.get(uc.scoring.category, ("⚪","#555","#eee"))
    with st.container(border=True):
        st.markdown(
            f"<div style='font-weight:600;font-size:0.92rem;'>{html.escape(uc.title[:50])}</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            f"{uc.structured.spoke_alignment or uc.department or '—'} · "
            f"{uc.structured.solution_category or '—'}"
        )
        if uc.scoring.total_score > 0:
            st.caption(
                f"Score: **{uc.scoring.total_score}/100** · "
                f"Value: **{uc.scoring.net_value}** ({uc.scoring.net_value_score}/55) · "
                f"Effort: **{uc.scoring.net_effort}** ({uc.scoring.net_effort_score}/45)"
            )
        st.markdown(
            f"Status: {STATUS_ICON.get(uc.status,'')} "
            f"*{uc.status.replace('_',' ').title()}*"
        )

        col_open, col_adv = st.columns(2)
        with col_open:
            if st.button("Open", key=f"open_{uc.id}", use_container_width=True):
                st.session_state["active_uc_id"] = uc.id
                st.switch_page("pages/5_Handoff.py")
        with col_adv:
            current_idx = STATUS_ORDER.index(uc.status) if uc.status in STATUS_ORDER else 0
            if current_idx < len(STATUS_ORDER) - 1:
                next_status = STATUS_ORDER[current_idx + 1]
                if st.button(
                    f"→ {next_status.replace('_',' ').title()}",
                    key=f"adv_{uc.id}", use_container_width=True,
                ):
                    uc.status = next_status
                    upsert(uc)
                    st.rerun()


def _build_dataframe(use_cases: list) -> pd.DataFrame:
    rows = []
    for uc in use_cases:
        rows.append({
            "ID": uc.id,
            "Title": uc.title,
            "R&D Function": uc.department,
            "Spoke": uc.structured.spoke_alignment,
            "Solution": uc.structured.solution_category,
            "Grouping": uc.structured.grouping,
            "Category": uc.scoring.category,
            "Total Score": uc.scoring.total_score,
            "Net Value": uc.scoring.net_value,
            "NV Score": uc.scoring.net_value_score,
            "Net Effort": uc.scoring.net_effort,
            "NE Score": uc.scoring.net_effort_score,
            "Status": uc.status.replace("_", " ").title(),
        })
    return pd.DataFrame(rows)


# ── Main ───────────────────────────────────────────────────────────────────────
_sidebar()

st.title("🗂️ Step 4: Portfolio Dashboard")
st.caption("Track and manage all AI initiatives across the R&D portfolio.")

use_cases = load_all()

if not use_cases:
    st.info("No use cases yet. Start by creating one!")
    if st.button("➕ New Use Case", type="primary"):
        st.switch_page("pages/1_Intake.py")
    st.stop()

# ── Filters ────────────────────────────────────────────────────────────────────
with st.expander("🔍 Filters", expanded=True):
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)

    all_spokes    = sorted(set(uc.structured.spoke_alignment for uc in use_cases if uc.structured.spoke_alignment))
    all_groupings = sorted(set(uc.structured.grouping for uc in use_cases if uc.structured.grouping))
    all_statuses  = STATUS_ORDER

    f_cat      = fc1.multiselect("Category",       CATEGORIES)
    f_spoke    = fc2.multiselect("Spoke",           all_spokes)
    f_grouping = fc3.multiselect("Grouping",        all_groupings)
    f_status   = fc4.multiselect("Status",          all_statuses,
                                  format_func=lambda s: s.replace("_"," ").title())
    f_search   = fc5.text_input("Search",           placeholder="Search title / description…")

filters = {
    "categories": f_cat,
    "spokes":     f_spoke,
    "groupings":  f_grouping,
    "statuses":   f_status,
    "search":     f_search,
}
filtered = _apply_filters(use_cases, filters)

# ── Summary metrics ────────────────────────────────────────────────────────────
mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
mc1.metric("Total",               len(filtered))
mc2.metric("🟢 Quick Wins",       sum(1 for uc in filtered if uc.scoring.category == "Quick Win"))
mc3.metric("🔵 Strategic",        sum(1 for uc in filtered if uc.scoring.category == "Strategic Initiative"))
mc4.metric("⚪ Backlog",          sum(1 for uc in filtered if uc.scoring.category == "Backlog"))
mc5.metric("🔴 Deprioritized",    sum(1 for uc in filtered if uc.scoring.category == "Deprioritized"))
mc6.metric("🔨 In Progress",      sum(1 for uc in filtered if uc.status == "in_progress"))

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_kanban, tab_table, tab_plot, tab_analytics = st.tabs(["Kanban", "Table", "2×2 Plot", "Analytics"])

# ── Kanban ─────────────────────────────────────────────────────────────────────
with tab_kanban:
    cols = st.columns(4)
    for col, cat in zip(cols, KANBAN_COLS):
        with col:
            icon, text_color, bg = CATEGORY_STYLE[cat]
            items = [uc for uc in filtered if uc.scoring.category == cat]
            st.markdown(
                f"<div style='background:{bg};color:{text_color};padding:6px 10px;"
                f"border-radius:6px;font-weight:700;margin-bottom:8px;'>"
                f"{icon} {cat} <span style='font-weight:400;'>({len(items)})</span></div>",
                unsafe_allow_html=True,
            )
            if not items:
                st.caption("None")
            for uc in items:
                _render_kanban_card(uc)

# ── Table ──────────────────────────────────────────────────────────────────────
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
            col_open, col_score, col_struct, col_del = st.columns([2, 2, 2, 1])
            with col_open:
                if st.button("📄 Open Handoff", use_container_width=True, type="primary"):
                    st.switch_page("pages/5_Handoff.py")
            with col_score:
                if st.button("📊 View Scoring", use_container_width=True):
                    st.switch_page("pages/3_Scoring.py")
            with col_struct:
                if st.button("📋 Edit Structure", use_container_width=True):
                    st.switch_page("pages/2_Structure.py")
            with col_del:
                if st.button("🗑️ Delete", use_container_width=True):
                    delete_uc(selected_uc.id)
                    st.session_state["active_uc_id"] = None
                    st.rerun()
    else:
        st.info("No use cases match the current filters.")

# ── 2×2 Plot ───────────────────────────────────────────────────────────────────
with tab_plot:
    from core.scoring import compute_scores as _cs, NET_VALUE_THRESHOLD, NET_EFFORT_THRESHOLD, NET_VALUE_MAX, NET_EFFORT_MAX
    scored = []
    for uc in filtered:
        if uc.meta.scoring_complete:
            if uc.scoring.scoring_version != "v2":
                uc.scoring = _cs(uc.structured)   # recompute in-memory only, don't save
            scored.append(uc)
    if not scored:
        st.info("No scored use cases to plot. Score some use cases first.")
    else:

        # X-axis = Complexity (inverted effort: high effort score = low complexity)
        # Y-axis = Value (net_value_score)
        # Quadrant dividers match the scoring thresholds
        X_DIVIDER = NET_EFFORT_MAX - NET_EFFORT_THRESHOLD  # 45 - 23 = 22
        Y_DIVIDER = NET_VALUE_THRESHOLD                    # 30

        CATEGORY_COLOR = {
            "Quick Win":            "#1a7a4a",
            "Strategic Initiative": "#1a4a8a",
            "Backlog":              "#888888",
            "Deprioritized":        "#8a1a1a",
        }

        x_vals, y_vals, labels, colors, hovers = [], [], [], [], []
        for uc in scored:
            x = NET_EFFORT_MAX - uc.scoring.net_effort_score   # invert: high = complex
            y = uc.scoring.net_value_score
            x_vals.append(x)
            y_vals.append(y)
            labels.append(uc.title[:35] + ("…" if len(uc.title) > 35 else ""))
            colors.append(CATEGORY_COLOR.get(uc.scoring.category, "#888"))
            hovers.append(
                f"<b>{uc.title}</b><br>"
                f"Category: {uc.scoring.category}<br>"
                f"Total Score: {uc.scoring.total_score}/100<br>"
                f"Net Value: {uc.scoring.net_value} ({uc.scoring.net_value_score}/55)<br>"
                f"Net Effort: {uc.scoring.net_effort} ({uc.scoring.net_effort_score}/45)<br>"
                f"Spoke: {uc.structured.spoke_alignment or 'N/A'}<br>"
                f"Solution: {uc.structured.solution_category or 'N/A'}"
            )

        fig = go.Figure()

        # ── Quadrant background shading ───────────────────────────────────────
        quad_config = [
            # (x0, x1, y0, y1, color, label, label_x, label_y)
            (0,          X_DIVIDER, Y_DIVIDER, NET_VALUE_MAX,  "rgba(212,237,218,0.4)", "QUICK WINS",           X_DIVIDER * 0.5,           NET_VALUE_MAX * 0.95),
            (X_DIVIDER,  NET_EFFORT_MAX, Y_DIVIDER, NET_VALUE_MAX, "rgba(208,228,247,0.4)", "STRATEGIC INITIATIVES", X_DIVIDER + (NET_EFFORT_MAX - X_DIVIDER) * 0.5, NET_VALUE_MAX * 0.95),
            (0,          X_DIVIDER, 0,          Y_DIVIDER,     "rgba(238,238,238,0.4)", "BACKLOG",              X_DIVIDER * 0.5,           Y_DIVIDER * 0.1),
            (X_DIVIDER,  NET_EFFORT_MAX, 0,      Y_DIVIDER,     "rgba(247,208,208,0.4)", "DEPRIORITIZED",        X_DIVIDER + (NET_EFFORT_MAX - X_DIVIDER) * 0.5, Y_DIVIDER * 0.1),
        ]
        for x0, x1, y0, y1, fill, qlabel, lx, ly in quad_config:
            fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                          fillcolor=fill, line_width=0, layer="below")
            fig.add_annotation(x=lx, y=ly, text=f"<b>{qlabel}</b>",
                               showarrow=False, font=dict(size=11, color="#555"),
                               xanchor="center", yanchor="top")

        # ── Divider lines ─────────────────────────────────────────────────────
        fig.add_shape(type="line", x0=X_DIVIDER, x1=X_DIVIDER, y0=0, y1=NET_VALUE_MAX,
                      line=dict(color="#aaa", width=1.5, dash="dash"))
        fig.add_shape(type="line", x0=0, x1=NET_EFFORT_MAX, y0=Y_DIVIDER, y1=Y_DIVIDER,
                      line=dict(color="#aaa", width=1.5, dash="dash"))

        # ── Data points ───────────────────────────────────────────────────────
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_vals,
            mode="markers+text",
            marker=dict(size=14, color=colors, line=dict(width=1.5, color="white")),
            text=labels,
            textposition="top center",
            textfont=dict(size=9, color="#333"),
            hovertext=hovers,
            hoverinfo="text",
            showlegend=False,
        ))

        # ── Legend (manual) ───────────────────────────────────────────────────
        for cat, col in CATEGORY_COLOR.items():
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode="markers",
                marker=dict(size=10, color=col),
                name=cat, showlegend=True,
            ))

        fig.update_layout(
            height=620,
            margin=dict(l=60, r=40, t=40, b=60),
            xaxis=dict(
                title="Complexity →  (Low effort score = High complexity)",
                range=[-1, NET_EFFORT_MAX + 1],
                showgrid=True, gridcolor="#eee",
                zeroline=False,
                dtick=2, tick0=0,
            ),
            yaxis=dict(
                title="Value →",
                range=[-1, NET_VALUE_MAX + 2],
                showgrid=True, gridcolor="#eee",
                zeroline=False,
                dtick=2, tick0=0,
            ),
            plot_bgcolor="white",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1,
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

# ── Analytics ──────────────────────────────────────────────────────────────────
with tab_analytics:
    if not filtered:
        st.info("No data to display.")
    else:
        # Row 1: Category + Spoke breakdown
        a1, a2 = st.columns(2)

        with a1:
            st.subheader("Use Cases by Category")
            cat_df = pd.DataFrame(
                [(c, sum(1 for uc in filtered if uc.scoring.category == c))
                 for c in CATEGORIES],
                columns=["Category", "Count"],
            ).set_index("Category")
            st.bar_chart(cat_df)

        with a2:
            st.subheader("Use Cases by Spoke Alignment")
            spoke_counts = {}
            for uc in filtered:
                sp = uc.structured.spoke_alignment or "Unspecified"
                spoke_counts[sp] = spoke_counts.get(sp, 0) + 1
            spoke_df = (
                pd.DataFrame(list(spoke_counts.items()), columns=["Spoke", "Count"])
                .set_index("Spoke")
                .sort_values("Count", ascending=False)
            )
            st.bar_chart(spoke_df)

        # Row 2: Grouping + Net Value distribution
        a3, a4 = st.columns(2)

        with a3:
            st.subheader("Use Cases by Grouping")
            grp_counts = {}
            for uc in filtered:
                g = uc.structured.grouping or "Unspecified"
                grp_counts[g] = grp_counts.get(g, 0) + 1
            grp_df = (
                pd.DataFrame(list(grp_counts.items()), columns=["Grouping", "Count"])
                .set_index("Grouping")
                .sort_values("Count", ascending=False)
            )
            st.bar_chart(grp_df)

        with a4:
            st.subheader("Net Value vs Net Effort Distribution")
            scored = [uc for uc in filtered if uc.scoring.net_value_score > 0]
            if scored:
                heatmap_data = {
                    "High Value / Low Effort":  sum(1 for uc in scored if uc.scoring.net_value=="High" and uc.scoring.net_effort=="Low"),
                    "High Value / High Effort": sum(1 for uc in scored if uc.scoring.net_value=="High" and uc.scoring.net_effort=="High"),
                    "Low Value / Low Effort":   sum(1 for uc in scored if uc.scoring.net_value=="Low"  and uc.scoring.net_effort=="Low"),
                    "Low Value / High Effort":  sum(1 for uc in scored if uc.scoring.net_value=="Low"  and uc.scoring.net_effort=="High"),
                }
                heat_df = (
                    pd.DataFrame(list(heatmap_data.items()), columns=["Quadrant", "Count"])
                    .set_index("Quadrant")
                )
                st.bar_chart(heat_df)

        # Row 3: Net Value Score distribution
        st.subheader("Net Value Score Distribution")
        scored = [uc for uc in filtered if uc.scoring.net_value_score > 0]
        if scored:
            score_counts = {}
            for uc in scored:
                s = str(uc.scoring.net_value_score)
                score_counts[s] = score_counts.get(s, 0) + 1
            score_df = (
                pd.DataFrame(
                    [(k, v) for k, v in sorted(score_counts.items())],
                    columns=["Net Value Score", "Count"],
                ).set_index("Net Value Score")
            )
            st.bar_chart(score_df)
