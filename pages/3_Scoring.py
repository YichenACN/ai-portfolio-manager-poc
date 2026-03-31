import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Scoring", page_icon="📊", layout="wide")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import load_all, upsert, get_by_id
from core.scoring import compute_scores, NET_VALUE_THRESHOLD, NET_EFFORT_THRESHOLD

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
        ready = [uc for uc in use_cases if uc.meta.structuring_complete]
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


CATEGORY_STYLE = {
    "Quick Win":           ("🟢", "#1a7a4a", "#d4edda"),
    "Strategic Initiative":("🔵", "#1a4a8a", "#d0e4f7"),
    "Backlog":             ("⚪", "#555555", "#eeeeee"),
    "Deprioritized":       ("🔴", "#8a1a1a", "#f7d0d0"),
}

SCORE_TO_LABEL = {1: "Low", 2: "Medium", 3: "High"}
TC_SCORE_TO_LABEL = {3: "Low", 2: "Medium", 1: "High"}   # inverted for display


def _category_badge(category: str) -> str:
    icon, _, _ = CATEGORY_STYLE.get(category, ("⚪", "#555", "#eee"))
    return f"{icon} {category}"


def _score_bar(score: int, max_score: int, color: str = "#4f8ef7") -> str:
    """Return an HTML progress bar."""
    pct = int(score / max_score * 100)
    return (
        f"<div style='background:#e0e0e0;border-radius:4px;height:12px;'>"
        f"<div style='background:{color};width:{pct}%;height:12px;border-radius:4px;'></div>"
        f"</div>"
    )


# ── Main ───────────────────────────────────────────────────────────────────────
_sidebar()

st.title("📊 Step 3: Scoring & Prioritisation")
st.caption(
    "Scores are derived from the four structured inputs using the CSL R&D "
    "AI Value Prioritisation Framework."
)

uc_id = st.session_state.get("active_uc_id")
if not uc_id:
    st.warning("No active use case. Complete structuring first.")
    if st.button("← Go to Structure"):
        st.switch_page("pages/2_Structure.py")
    st.stop()

uc = get_by_id(uc_id)
if not uc:
    st.error("Use case not found.")
    st.stop()

if not uc.meta.structuring_complete:
    st.warning("Please complete structuring before scoring.")
    if st.button("← Complete Structuring First"):
        st.switch_page("pages/2_Structure.py")
    st.stop()

# Auto-score if not yet done
if not uc.meta.scoring_complete:
    sc = compute_scores(uc.structured)
    uc.scoring = sc
    uc.meta.scoring_complete = True
    uc.status = "scored"
    upsert(uc)
    uc = get_by_id(uc_id)

sc = uc.scoring

# ── Header ─────────────────────────────────────────────────────────────────────
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.subheader(uc.title)
    st.caption(
        f"Spoke: **{uc.structured.spoke_alignment or 'N/A'}** · "
        f"Solution: **{uc.structured.solution_category or 'N/A'}** · "
        f"Grouping: **{uc.structured.grouping or 'N/A'}**"
    )
with col_btn:
    if st.button("🔄 Recalculate", use_container_width=True):
        uc.scoring = compute_scores(uc.structured)
        upsert(uc)
        st.rerun()

st.divider()

# ── Category result (hero element) ────────────────────────────────────────────
icon, text_color, bg_color = CATEGORY_STYLE.get(sc.category, ("⚪", "#555", "#eee"))
st.markdown(
    f"""<div style='background:{bg_color};border-left:6px solid {text_color};
        padding:16px 20px;border-radius:6px;margin-bottom:16px;'>
        <span style='font-size:1.6rem;font-weight:700;color:{text_color};'>
        {icon} {sc.category}</span>
        <span style='color:{text_color};font-size:0.95rem;margin-left:12px;'>
        Net Value: <b>{sc.net_value}</b> ({sc.net_value_score}/9) &nbsp;·&nbsp;
        Net Effort: <b>{sc.net_effort}</b> ({sc.net_effort_score}/6)
        </span></div>""",
    unsafe_allow_html=True,
)

# ── Two-column layout: dimensions left, 2×2 matrix right ──────────────────────
dim_col, matrix_col = st.columns([3, 2])

with dim_col:
    st.subheader("Scoring Dimensions")

    # ── NET VALUE ──────────────────────────────────────────────────────────────
    st.markdown("##### Net Value Score &nbsp; `= (BI × 2) + (FI × 1)`")

    r1c1, r1c2, r1c3 = st.columns([2, 1, 3])
    r1c1.markdown("**Business Impact** _(×2 weight)_")
    r1c2.markdown(f"**{SCORE_TO_LABEL.get(sc.bi_score, '—')}** `{sc.bi_score}/3`")
    r1c3.markdown(
        _score_bar(sc.bi_score * 2, 6, "#1a7a4a"),
        unsafe_allow_html=True,
    )

    r2c1, r2c2, r2c3 = st.columns([2, 1, 3])
    r2c1.markdown("**Foundational Impact** _(×1 weight)_")
    r2c2.markdown(f"**{SCORE_TO_LABEL.get(sc.fi_score, '—')}** `{sc.fi_score}/3`")
    r2c3.markdown(
        _score_bar(sc.fi_score, 3, "#2a6aaa"),
        unsafe_allow_html=True,
    )

    nv_color = "#1a7a4a" if sc.net_value == "High" else "#8a1a1a"
    st.markdown(
        f"<div style='text-align:right;font-size:1.1rem;margin:4px 0 12px;'>"
        f"Net Value Score: <b style='color:{nv_color};font-size:1.3rem;'>"
        f"{sc.net_value_score}</b>/9 &nbsp;"
        f"<span style='background:{nv_color};color:white;padding:2px 8px;"
        f"border-radius:4px;font-size:0.85rem;'>{sc.net_value}</span>"
        f"&nbsp; (threshold ≥{NET_VALUE_THRESHOLD})</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── NET EFFORT ─────────────────────────────────────────────────────────────
    st.markdown("##### Net Effort Score &nbsp; `= TC + DA`")

    r3c1, r3c2, r3c3 = st.columns([2, 1, 3])
    r3c1.markdown("**Technical Complexity** _(inverted — Low is better)_")
    r3c2.markdown(f"**{TC_SCORE_TO_LABEL.get(sc.tc_score, '—')}** `{sc.tc_score}/3`")
    r3c3.markdown(
        _score_bar(sc.tc_score, 3, "#7a5a1a"),
        unsafe_allow_html=True,
    )

    r4c1, r4c2, r4c3 = st.columns([2, 1, 3])
    r4c1.markdown("**Data Availability**")
    r4c2.markdown(f"**{SCORE_TO_LABEL.get(sc.da_score, '—')}** `{sc.da_score}/3`")
    r4c3.markdown(
        _score_bar(sc.da_score, 3, "#5a1a7a"),
        unsafe_allow_html=True,
    )

    ne_color = "#1a7a4a" if sc.net_effort == "Low" else "#8a1a1a"
    st.markdown(
        f"<div style='text-align:right;font-size:1.1rem;margin:4px 0 12px;'>"
        f"Net Effort Score: <b style='color:{ne_color};font-size:1.3rem;'>"
        f"{sc.net_effort_score}</b>/6 &nbsp;"
        f"<span style='background:{ne_color};color:white;padding:2px 8px;"
        f"border-radius:4px;font-size:0.85rem;'>{sc.net_effort} Effort</span>"
        f"&nbsp; (threshold ≥{NET_EFFORT_THRESHOLD} = Low)</div>",
        unsafe_allow_html=True,
    )

with matrix_col:
    st.subheader("2×2 Prioritisation Matrix")
    st.caption("Net Value (x-axis) vs Net Effort (y-axis)")

    # Build a visual 2×2 using HTML
    def _cell(label: str, icon: str, active: bool, bg: str, text_col: str) -> str:
        border = f"4px solid {text_col}" if active else "2px solid #ccc"
        opacity = "1" if active else "0.35"
        return (
            f"<td style='width:50%;padding:18px 12px;text-align:center;"
            f"background:{bg};border:{border};border-radius:6px;opacity:{opacity};'>"
            f"<div style='font-size:1.6rem;'>{icon}</div>"
            f"<div style='font-weight:700;color:{text_col};font-size:0.95rem;'>{label}</div>"
            f"</td>"
        )

    qw_active  = sc.category == "Quick Win"
    si_active  = sc.category == "Strategic Initiative"
    bl_active  = sc.category == "Backlog"
    dp_active  = sc.category == "Deprioritized"

    matrix_html = f"""
    <table style='width:100%;border-collapse:separate;border-spacing:8px;'>
      <thead>
        <tr>
          <th style='text-align:center;color:#666;font-weight:500;padding-bottom:4px;'>
            Low Effort ✓</th>
          <th style='text-align:center;color:#666;font-weight:500;padding-bottom:4px;'>
            High Effort</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style='padding:4px 0;color:#666;font-size:0.8rem;font-weight:600;
              text-align:right;padding-right:8px;vertical-align:middle;'>High Value</td>
          {_cell("Quick Win", "🟢", qw_active, "#d4edda", "#1a7a4a")}
          {_cell("Strategic Initiative", "🔵", si_active, "#d0e4f7", "#1a4a8a")}
        </tr>
        <tr>
          <td style='padding:4px 0;color:#666;font-size:0.8rem;font-weight:600;
              text-align:right;padding-right:8px;vertical-align:middle;'>Low Value</td>
          {_cell("Backlog", "⚪", bl_active, "#eeeeee", "#555555")}
          {_cell("Deprioritized", "🔴", dp_active, "#f7d0d0", "#8a1a1a")}
        </tr>
      </tbody>
    </table>
    """
    st.markdown(matrix_html, unsafe_allow_html=True)

    st.divider()
    st.markdown("**Scoring formula recap**")
    st.markdown(
        """
| Dimension | Weight | Low | Med | High |
|---|---|---|---|---|
| Business Impact | ×2 | 1 | 2 | 3 |
| Foundational Impact | ×1 | 1 | 2 | 3 |
| Technical Complexity | ×1 | **3** | 2 | 1 |
| Data Availability | ×1 | 1 | 2 | **3** |

Net Value ≥ **6** → High &nbsp;·&nbsp; Net Effort ≥ **5** → Low
        """
    )

st.divider()

# ── Bar chart summary ──────────────────────────────────────────────────────────
st.subheader("Score Breakdown")
chart_df = pd.DataFrame({
    "Dimension": [
        "Business Impact (×2)",
        "Foundational Impact (×1)",
        "Technical Complexity (inverted)",
        "Data Availability (×1)",
    ],
    "Score (out of 3)": [sc.bi_score, sc.fi_score, sc.tc_score, sc.da_score],
}).set_index("Dimension")
st.bar_chart(chart_df, color="#4f8ef7")

st.divider()

# ── Actions ────────────────────────────────────────────────────────────────────
col_a, col_b = st.columns([2, 2])
with col_a:
    if st.button("✅ Accept & Add to Portfolio →", type="primary", use_container_width=True):
        uc = get_by_id(uc_id)
        if uc.status in ("idea", "structured", "scored"):
            uc.status = "scored"
            upsert(uc)
        st.switch_page("pages/4_Portfolio.py")
with col_b:
    if st.button("← Back to Structure", use_container_width=True):
        st.switch_page("pages/2_Structure.py")

with st.expander("ℹ️ About this framework"):
    st.markdown("""
    **CSL R&D AI Value Prioritisation Framework**

    Use cases are evaluated on two axes:

    **Net Value** = (Business Impact × 2) + (Foundational Impact × 1)
    - *Business Impact*: direct effect on cycle time, portfolio growth, or operational efficiency
    - *Foundational Impact*: enterprise-wide or cross-functional enablement value
    - Threshold: score ≥ **6** out of 9 = High Value

    **Net Effort** = Technical Complexity (inverted) + Data Availability
    - *Technical Complexity*: Low complexity scores **3** (easier to build)
    - *Data Availability*: High availability scores **3** (data is ready)
    - Threshold: score ≥ **5** out of 6 = Low Effort

    **Categories**
    - 🟢 **Quick Win** — High Value, Low Effort → do now
    - 🔵 **Strategic Initiative** — High Value, High Effort → plan and invest
    - ⚪ **Backlog** — Low Value, Low Effort → monitor
    - 🔴 **Deprioritized** — Low Value, High Effort → park for now
    """)
