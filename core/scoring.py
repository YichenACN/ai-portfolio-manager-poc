"""
Scoring engine v2 — point-based CSL R&D AI prioritisation framework.

Each use case is scored across four dimensions (max 100 points total):

  Business Impact    — 30 pts
    business_impact_level     high=15  med=9   low=3
    expected_benefit_type     revenue/cost=9   productivity=6  other=3
    strategic_alignment       2+ tags=6  1 tag=3  none=0

  Foundational Impact — 25 pts
    foundational_impact_level high=15  med=9   low=3
    grouping                  Ops Eff/Data=10  Content=6  Other=3

  Data Availability   — 25 pts
    data_availability_level   high=17  med=10  low=3
    available_data_sources    2+=8  1=4  none=0

  Tech Complexity     — 20 pts  (inverted — lower complexity = higher score)
    technical_complexity      low=10  med=6  high=2
    complexity_estimate       low=6   med=3  high=0
    solution_category         BI=4  GenAI=3  AI/ML=1  N/A=0

2×2 category (value vs effort axes):
  Value  = BI_pts + FI_pts   (max 55)   threshold ≥ 30 → High
  Effort = TC_pts + DA_pts   (max 45)   threshold ≥ 23 → Low (easy)

  High Value + Low Effort  → Quick Win
  High Value + High Effort → Strategic Initiative
  Low Value  + Low Effort  → Backlog
  Low Value  + High Effort → Deprioritized

  Total Score = Value + Effort  (max 100)  — used for ranking within category
"""

from datetime import datetime, timezone
from core.models import StructuredData, ScoringData

# ── Dimension maxima ───────────────────────────────────────────────────────────
BI_MAX = 30
FI_MAX = 25
DA_MAX = 25
TC_MAX = 20
NET_VALUE_MAX   = BI_MAX + FI_MAX          # 55
NET_EFFORT_MAX  = TC_MAX + DA_MAX          # 45
TOTAL_SCORE_MAX = NET_VALUE_MAX + NET_EFFORT_MAX  # 100

# ── 2×2 thresholds ────────────────────────────────────────────────────────────
NET_VALUE_THRESHOLD  = 30   # ≥ 30 out of 55 → High Value
NET_EFFORT_THRESHOLD = 23   # ≥ 23 out of 45 → Low Effort

# ── Point tables ──────────────────────────────────────────────────────────────

_BI_LEVEL   = {"high": 15, "medium": 9, "low": 3}
_FI_LEVEL   = {"high": 15, "medium": 9, "low": 3}
_DA_LEVEL   = {"high": 17, "medium": 10, "low": 3}
_TC_LEVEL   = {"low": 10, "medium": 6, "high": 2}   # inverted
_COMPLEXITY_ESTIMATE = {"low": 6, "medium": 3, "high": 0}

_OPS_DATA_GROUPINGS = {
    "operational efficiency", "process automation", "predictive analytics",
}
_CONTENT_GROUPINGS = {"content generation", "knowledge management"}


def _benefit_type_pts(val: str) -> int:
    v = (val or "").lower()
    if any(x in v for x in ("revenue", "cost")):
        return 9
    if "productivity" in v:
        return 6
    return 3


def _strategic_align_pts(tags: list) -> int:
    n = len(tags or [])
    if n >= 2:
        return 6
    if n == 1:
        return 3
    return 0


def _grouping_pts(val: str) -> int:
    v = (val or "").lower()
    if v in _OPS_DATA_GROUPINGS:
        return 10
    if v in _CONTENT_GROUPINGS:
        return 6
    return 3


def _data_sources_pts(sources: list) -> int:
    n = len(sources or [])
    if n >= 2:
        return 8
    if n == 1:
        return 4
    return 0


def _solution_category_pts(val: str) -> int:
    v = (val or "").lower()
    if v == "bi":
        return 4
    if any(x in v for x in ("genai", "gen ai")):
        return 3
    if "ai/ml" in v or "aiml" in v:
        return 1
    return 0


def compute_scores(structured: StructuredData) -> ScoringData:
    """
    Derive all scoring outputs from the structured inputs.
    Returns a ScoringData with:
        bi_score / fi_score / tc_score / da_score — dimension point totals
        net_value_score  (BI + FI, max 55)
        net_effort_score (TC + DA, max 45)
        total_score      (all four, max 100)
        net_value / net_effort / category — 2×2 classification
    """
    # ── Business Impact ────────────────────────────────────────────────────────
    bi_level   = _BI_LEVEL.get((structured.business_impact_level or "medium").lower(), 9)
    bi_benefit = _benefit_type_pts(structured.expected_benefit_type)
    bi_align   = _strategic_align_pts(structured.strategic_alignment)
    bi_pts     = bi_level + bi_benefit + bi_align

    # ── Foundational Impact ───────────────────────────────────────────────────
    fi_level = _FI_LEVEL.get((structured.foundational_impact_level or "medium").lower(), 9)
    fi_group = _grouping_pts(structured.grouping)
    fi_pts   = fi_level + fi_group

    # ── Data Availability ─────────────────────────────────────────────────────
    da_level   = _DA_LEVEL.get((structured.data_availability_level or "medium").lower(), 10)
    da_sources = _data_sources_pts(structured.available_data_sources)
    da_pts     = da_level + da_sources

    # ── Technical Complexity (inverted) ───────────────────────────────────────
    tc_level    = _TC_LEVEL.get((structured.technical_complexity or "medium").lower(), 6)
    tc_estimate = _COMPLEXITY_ESTIMATE.get((structured.complexity_estimate or "medium").lower(), 3)
    tc_cat      = _solution_category_pts(structured.solution_category)
    tc_pts      = tc_level + tc_estimate + tc_cat

    # ── Composite scores ──────────────────────────────────────────────────────
    net_value_score  = bi_pts + fi_pts       # max 55
    net_effort_score = tc_pts + da_pts       # max 45
    total_score      = net_value_score + net_effort_score  # max 100

    net_value  = "High" if net_value_score  >= NET_VALUE_THRESHOLD  else "Low"
    net_effort = "Low"  if net_effort_score >= NET_EFFORT_THRESHOLD else "High"

    # ── 2×2 category ──────────────────────────────────────────────────────────
    if net_value == "High" and net_effort == "Low":
        category = "Quick Win"
    elif net_value == "High" and net_effort == "High":
        category = "Strategic Initiative"
    elif net_value == "Low" and net_effort == "Low":
        category = "Backlog"
    else:
        category = "Deprioritized"

    return ScoringData(
        bi_score=bi_pts,
        fi_score=fi_pts,
        tc_score=tc_pts,
        da_score=da_pts,
        net_value_score=net_value_score,
        net_effort_score=net_effort_score,
        total_score=total_score,
        net_value=net_value,
        net_effort=net_effort,
        category=category,
        scoring_version="v2",
        scored_at=datetime.now(timezone.utc).isoformat(),
        # Legacy aliases
        business_impact=bi_pts,
        feasibility=fi_pts,
        data_readiness=da_pts,
        risk_compliance=tc_pts,
        effort_estimate_weeks=net_effort_score,
    )
