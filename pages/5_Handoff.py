import streamlit as st
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Handoff", page_icon="📄", layout="wide")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_store import load_all, upsert, get_by_id
from core.models import STATUS_ORDER
from core import llm_client

# ── Session state defaults ─────────────────────────────────────────────────────
st.session_state.setdefault("active_uc_id", None)

DOC_LABELS = {
    "prd": "Product Requirements Doc",
    "tech_spec": "Technical Specification",
    "jira_ticket": "Jira Tickets",
}

DOC_ICONS = {"prd": "📘", "tech_spec": "⚙️", "jira_ticket": "🎫"}


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
        scored = [uc for uc in use_cases if uc.status in ("scored", "validated", "in_progress", "deployed")]
        if scored:
            options = {uc.id: uc.title for uc in scored}
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


def _generate_doc(uc_id: str, doc_type: str) -> str:
    uc = get_by_id(uc_id)
    from core.models import use_case_to_dict
    uc_dict = use_case_to_dict(uc)
    prompt_template = llm_client.load_prompt("document_generation.txt")
    content = llm_client.generate_documents(uc_dict, doc_type, prompt_template)

    now = datetime.now(timezone.utc).isoformat()
    doc_record = {"content": content, "generated_at": now, "version": 1}

    existing_doc = getattr(uc.documents, doc_type, None)
    if existing_doc:
        doc_record["version"] = (existing_doc.get("version", 1) if isinstance(existing_doc, dict) else 1) + 1

    setattr(uc.documents, doc_type, doc_record)
    uc.meta.handoff_complete = True
    upsert(uc)
    return content


def _get_download_filename(uc, doc_type: str) -> str:
    slug = uc.title[:40].lower().replace(" ", "_").replace("/", "_")
    suffixes = {"prd": "prd", "tech_spec": "tech_spec", "jira_ticket": "jira"}
    return f"{slug}_{suffixes.get(doc_type, doc_type)}.md"


def _render_doc_tab(uc, doc_type: str):
    label = DOC_LABELS[doc_type]
    icon = DOC_ICONS[doc_type]

    existing = getattr(uc.documents, doc_type, None)
    if isinstance(existing, dict):
        content = existing.get("content", "")
        generated_at = existing.get("generated_at", "")
        version = existing.get("version", 1)
    else:
        content = ""
        generated_at = ""
        version = 0

    # Generate / Regenerate button
    col_btn, col_meta = st.columns([2, 3])
    with col_btn:
        btn_label = f"🔄 Regenerate {label}" if content else f"✨ Generate {label}"
        if st.button(btn_label, key=f"gen_{doc_type}", use_container_width=True, type="primary"):
            with st.spinner(f"Generating {label}…"):
                content = _generate_doc(uc.id, doc_type)
            st.rerun()
    with col_meta:
        if generated_at:
            st.caption(f"Version {version} · Generated {generated_at[:19].replace('T', ' ')} UTC")

    if content:
        # Rendered view
        st.markdown(content)
        st.divider()

        # Download + copy
        dl_col, raw_col = st.columns([1, 2])
        with dl_col:
            st.download_button(
                label=f"⬇️ Download {label}",
                data=content,
                file_name=_get_download_filename(uc, doc_type),
                mime="text/markdown",
                use_container_width=True,
            )
        with raw_col:
            with st.expander("📋 Raw Markdown"):
                st.code(content, language="markdown")
    else:
        st.info(f"Click the button above to generate the {label}.")


# ── Main layout ────────────────────────────────────────────────────────────────
_sidebar()

st.title("📄 Step 5: Handoff to Delivery")

uc_id = st.session_state.get("active_uc_id")

if not uc_id:
    st.warning("No active use case selected.")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("← Go to Portfolio"):
            st.switch_page("pages/4_Portfolio.py")
    with col_b:
        if st.button("← Go to Scoring"):
            st.switch_page("pages/3_Scoring.py")
    st.stop()

uc = get_by_id(uc_id)
if not uc:
    st.error("Use case not found.")
    st.stop()

# ── Header ─────────────────────────────────────────────────────────────────────
header_col, status_col = st.columns([4, 2])
with header_col:
    st.subheader(uc.title)
    st.caption(
        f"Department: {uc.department or 'N/A'} · "
        f"Category: {uc.structured.use_case_category} · "
        f"Priority: {uc.scoring.priority_tier} · "
        f"Score: {uc.scoring.composite_score}/100"
    )
with status_col:
    st.markdown(f"**Status:** {uc.status.replace('_', ' ').title()}")
    current_idx = STATUS_ORDER.index(uc.status) if uc.status in STATUS_ORDER else 0
    available_statuses = STATUS_ORDER[current_idx:]
    new_status = st.selectbox(
        "Update status",
        available_statuses,
        format_func=lambda s: s.replace("_", " ").title(),
        label_visibility="collapsed",
    )
    if st.button("Update Status", use_container_width=True):
        uc.status = new_status
        upsert(uc)
        st.success(f"Status updated to {new_status.replace('_', ' ').title()}")
        st.rerun()

st.divider()

# ── Problem statement quick view ───────────────────────────────────────────────
if uc.structured.problem_statement:
    with st.expander("📌 Problem Statement"):
        st.markdown(uc.structured.problem_statement)
        col1, col2, col3 = st.columns(3)
        col1.metric("Composite Score", f"{uc.scoring.composite_score}/100")
        col2.metric("Effort", f"{uc.scoring.effort_estimate_weeks} weeks")
        col3.metric("12-mo ROI", f"${uc.scoring.roi_projection_12mo:,.0f}")

# ── Document tabs ──────────────────────────────────────────────────────────────
tab_prd, tab_tech, tab_jira = st.tabs([
    f"📘 Product Requirements Doc",
    f"⚙️ Technical Specification",
    f"🎫 Jira Tickets",
])

with tab_prd:
    _render_doc_tab(uc, "prd")

with tab_tech:
    _render_doc_tab(uc, "tech_spec")

with tab_jira:
    _render_doc_tab(uc, "jira_ticket")

st.divider()

if st.button("← Back to Portfolio", use_container_width=False):
    st.switch_page("pages/4_Portfolio.py")
