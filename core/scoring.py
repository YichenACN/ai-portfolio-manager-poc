"""
Scoring engine — implements the real CSL R&D AI prioritisation framework.

Net Value Score  = (BI × 2) + (FI × 1)        range: 3–9
Net Effort Score = TC_score + DA_score          range: 2–6

Scoring legend  (Low=1, Medium=2, High=3; Technical Complexity is INVERTED)
  Business Impact     Low=1  Medium=2  High=3
  Foundational Impact Low=1  Medium=2  High=3
  Technical Complexity Low=3  Medium=2  High=1   ← lower complexity is BETTER
  Data Availability   Low=1  Medium=2  High=3

Thresholds (from Assumptions sheet):
  Net Value ≥ 6  → "High";  < 6 → "Low"
  Net Effort ≥ 5 → "Low" (easier);  < 5 → "High" (harder)

2×2 Category matrix:
  High Value + Low Effort  → Quick Win
  High Value + High Effort → Strategic Initiative
  Low Value  + Low Effort  → Backlog
  Low Value  + High Effort → Deprioritized
"""

from datetime import datetime, timezone
from core.models import StructuredData, ScoringData

NET_VALUE_THRESHOLD = 6    # ≥ 6 → High
NET_EFFORT_THRESHOLD = 5   # ≥ 5 → Low effort (good)

LABEL_TO_SCORE = {"low": 1, "medium": 2, "high": 3}
TC_LABEL_TO_SCORE = {"low": 3, "medium": 2, "high": 1}   # inverted


def compute_scores(structured: StructuredData) -> ScoringData:
    """
    Derive all scoring outputs from the structured inputs.
    Inputs read from StructuredData:
        business_impact_level, foundational_impact_level,
        technical_complexity, data_availability_level
    """
    bi = LABEL_TO_SCORE.get(structured.business_impact_level.lower(), 2)
    fi = LABEL_TO_SCORE.get(structured.foundational_impact_level.lower(), 2)
    tc = TC_LABEL_TO_SCORE.get(structured.technical_complexity.lower(), 2)
    da = LABEL_TO_SCORE.get(structured.data_availability_level.lower(), 2)

    net_value_score = bi * 2 + fi * 1        # BI weighted 2x
    net_effort_score = tc + da

    net_value = "High" if net_value_score >= NET_VALUE_THRESHOLD else "Low"
    net_effort = "Low" if net_effort_score >= NET_EFFORT_THRESHOLD else "High"

    # 2×2 category
    if net_value == "High" and net_effort == "Low":
        category = "Quick Win"
    elif net_value == "High" and net_effort == "High":
        category = "Strategic Initiative"
    elif net_value == "Low" and net_effort == "Low":
        category = "Backlog"
    else:
        category = "Deprioritized"

    return ScoringData(
        bi_score=bi,
        fi_score=fi,
        tc_score=tc,
        da_score=da,
        net_value_score=net_value_score,
        net_effort_score=net_effort_score,
        net_value=net_value,
        net_effort=net_effort,
        category=category,
        scoring_version="v1",
        scored_at=datetime.now(timezone.utc).isoformat(),
        # Keep legacy aliases populated
        business_impact=bi,
        feasibility=fi,
        data_readiness=da,
        risk_compliance=tc,
        effort_estimate_weeks=net_effort_score,
    )
