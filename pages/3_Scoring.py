import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Scoring", page_icon="📊", layout="wide")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import load_all, upsert, get_by_id
from core.scoring import compute_scores

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


def _score_color(score: int) -> str:
    if score >= 70:
        return "normal"
    elif score >= 50:
        return "off"
    else:
        return "inverse"


def _priority_badge(tier: str) -> str:
    colors = {"P1": "🔴", "P2": "🟠", "P3": "⚪"}
    return f"{colors.get(tier, '')} {tier}"


def _tier_explanation(tier: str) -> str:
    explanations = {
        "P1": "**P1 — High Priority:** Strong business impact, feasible with available data, and low risk. Recommend starting within the current quarter.",
        "P2": "**P2 — Medium Priority:** Good potential but faces some feasibility or data challenges. Schedule for next planning cycle.",
        "P3": "**P3 — Backlog:** Lower impact or significant feasibility concerns. Keep in backlog and revisit as data or conditions improve.",
    }
    return explanations.get(tier, "")


# ── Main layout ────────────────────────────────────────────────────────────────
_sidebar()

st.title("📊 Step 3: Scoring & Prioritization")
st.caption("Automated scoring based on business impact, feasibility, data readiness, and risk.")

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
    st.warning("Please complete AI structuring before scoring.")
    if st.button("← Complete Structuring First"):
        st.switch_page("pages/2_Structure.py")
    st.stop()

# Auto-score if not yet done
if not uc.meta.scoring_complete:
    scores = compute_scores(uc.structured)
    uc.scoring = scores
    uc.meta.scoring_complete = True
    uc.status = "scored"
    upsert(uc)
    uc = get_by_id(uc_id)

sc = uc.scoring

# ── Header: use case title + rescore button ────────────────────────────────────
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.subheader(uc.title)
    st.caption(f"Department: {uc.department or 'Not specified'} | Category: {uc.structured.use_case_category}")
with col_btn:
    if st.button("🔄 Recalculate", use_container_width=True):
        scores = compute_scores(uc.structured)
        uc.scoring = scores
        upsert(uc)
        st.rerun()

st.divider()

# ── Score cards row ────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Business Impact", f"{sc.business_impact}/100",
          delta="High" if sc.business_impact >= 70 else ("Medium" if sc.business_impact >= 50 else "Low"),
          delta_color=_score_color(sc.business_impact))

c2.metric("Feasibility", f"{sc.feasibility}/100",
          delta="High" if sc.feasibility >= 70 else ("Medium" if sc.feasibility >= 50 else "Low"),
          delta_color=_score_color(sc.feasibility))

c3.metric("Data Readiness", f"{sc.data_readiness}/100",
          delta="High" if sc.data_readiness >= 70 else ("Medium" if sc.data_readiness >= 50 else "Low"),
          delta_color=_score_color(sc.data_readiness))

c4.metric("Risk/Compliance", f"{sc.risk_compliance}/100",
          delta="Low risk" if sc.risk_compliance >= 70 else ("Medium" if sc.risk_compliance >= 50 else "High risk"),
          delta_color=_score_color(sc.risk_compliance))

c5.metric("Composite Score", f"{sc.composite_score}/100")

with c6:
    st.metric("Priority Tier", _priority_badge(sc.priority_tier))

st.divider()

# ── Chart + ROI panel ──────────────────────────────────────────────────────────
chart_col, roi_col = st.columns([3, 2])

with chart_col:
    st.subheader("Score Breakdown")
    chart_data = pd.DataFrame({
        "Dimension": ["Business Impact", "Feasibility", "Data Readiness", "Risk/Compliance"],
        "Score": [sc.business_impact, sc.feasibility, sc.data_readiness, sc.risk_compliance],
    }).set_index("Dimension")
    st.bar_chart(chart_data, horizontal=True, color="#4f8ef7")

with roi_col:
    st.subheader("Effort & ROI Projection")
    st.markdown(f"**Effort Estimate:** {sc.effort_estimate_weeks} weeks")
    st.markdown(f"**12-Month ROI Projection:** ${sc.roi_projection_12mo:,.0f} {sc.roi_currency}")
    st.markdown(f"**Priority:** {_priority_badge(sc.priority_tier)}")
    st.divider()
    st.markdown(_tier_explanation(sc.priority_tier))

st.divider()

# ── Scoring methodology ────────────────────────────────────────────────────────
with st.expander("📐 Scoring Methodology (Mock v1)"):
    st.markdown("""
    **Note:** Scores are deterministic mock values derived from use case attributes.
    The real scoring framework is TBD and will replace this in a future version.

    | Dimension | Weight | Driver |
    |---|---|---|
    | Business Impact | 35% | Expected benefit type (revenue > cost reduction > risk) |
    | Feasibility | 30% | Use case category + complexity estimate |
    | Data Readiness | 20% | Number of identified data sources |
    | Risk/Compliance | 15% | Use case category (NLP/recommendation = lower risk) |

    **Composite Score** = weighted average of all 4 dimensions.

    **Priority Tiers:**
    - 🔴 P1 (≥70): Do now — high-value, feasible, low-risk
    - 🟠 P2 (50–69): Plan for next quarter
    - ⚪ P3 (<50): Backlog — revisit when conditions improve

    **ROI Projection** is a rough estimate based on benefit type and business impact score.
    Effort estimate is based on complexity (low: 4w, medium: 10w, high: 20w).
    """)

st.divider()

# ── Actions ────────────────────────────────────────────────────────────────────
col_a, col_b, col_c = st.columns([2, 2, 1])
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
