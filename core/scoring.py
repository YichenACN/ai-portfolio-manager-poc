import hashlib
from datetime import datetime, timezone

from core.models import StructuredData, ScoringData

CATEGORY_FEASIBILITY_BASE = {
    "automation": 70,
    "nlp": 60,
    "forecasting": 55,
    "recommendation": 60,
    "anomaly_detection": 58,
    "computer_vision": 45,
    "other": 50,
}

COMPLEXITY_MODIFIER = {"low": 15, "medium": 0, "high": -20}

BENEFIT_IMPACT_BASE = {
    "revenue": 80,
    "cost_reduction": 70,
    "risk": 65,
    "other": 50,
}

ROI_MULTIPLIERS = {
    "revenue": 15000,
    "cost_reduction": 10000,
    "risk": 8000,
    "other": 5000,
}

EFFORT_BASE = {"low": 4, "medium": 10, "high": 20}


def _hash_int(seed: str, index: int, lo: int, hi: int) -> int:
    digest = hashlib.md5(f"{seed}:{index}".encode()).hexdigest()
    raw = int(digest[:8], 16)
    span = hi - lo + 1
    return lo + (raw % span)


def compute_scores(structured: StructuredData) -> ScoringData:
    seed = f"{structured.problem_statement[:40]}{structured.use_case_category}"

    # Business impact
    impact_base = BENEFIT_IMPACT_BASE.get(structured.expected_benefit_type, 50)
    business_impact = max(10, min(100, impact_base + _hash_int(seed, 0, -10, 10)))

    # Feasibility
    feas_base = CATEGORY_FEASIBILITY_BASE.get(structured.use_case_category, 50)
    complexity_mod = COMPLEXITY_MODIFIER.get(structured.complexity_estimate, 0)
    feasibility = max(10, min(100, feas_base + complexity_mod + _hash_int(seed, 1, -8, 8)))

    # Data readiness
    data_count = len(structured.available_data_sources)
    data_base = min(90, 30 + data_count * 15)
    data_readiness = max(10, min(100, data_base + _hash_int(seed, 2, -5, 5)))

    # Risk/compliance (higher = lower risk = better)
    risk_base = 80 if structured.use_case_category in ("nlp", "recommendation") else 60
    risk_compliance = max(10, min(100, risk_base + _hash_int(seed, 3, -10, 10)))

    # Composite
    composite_score = int(
        business_impact * 0.35
        + feasibility * 0.30
        + data_readiness * 0.20
        + risk_compliance * 0.15
    )

    # Effort
    effort_base = EFFORT_BASE.get(structured.complexity_estimate, 10)
    effort_estimate_weeks = max(2, effort_base + _hash_int(seed, 4, -2, 4))

    # ROI
    roi_base = ROI_MULTIPLIERS.get(structured.expected_benefit_type, 5000)
    roi_noise_pct = _hash_int(seed, 5, -20, 40)
    roi_projection_12mo = int(roi_base * (business_impact / 100) * (1 + roi_noise_pct / 100))

    # Priority tier
    if composite_score >= 70:
        priority_tier = "P1"
    elif composite_score >= 50:
        priority_tier = "P2"
    else:
        priority_tier = "P3"

    return ScoringData(
        business_impact=business_impact,
        feasibility=feasibility,
        data_readiness=data_readiness,
        risk_compliance=risk_compliance,
        composite_score=composite_score,
        effort_estimate_weeks=effort_estimate_weeks,
        roi_projection_12mo=roi_projection_12mo,
        roi_currency="USD",
        priority_tier=priority_tier,
        scoring_version="mock_v1",
        scored_at=datetime.now(timezone.utc).isoformat(),
    )
