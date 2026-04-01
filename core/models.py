from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List


@dataclass
class IntakeData:
    chat_history: List[dict] = field(default_factory=list)
    raw_summary: str = ""


@dataclass
class StructuredData:
    # Core description
    problem_statement: str = ""
    impacted_users: str = ""
    available_data_sources: List[str] = field(default_factory=list)
    expected_benefit_description: str = ""
    suggested_approach: str = ""
    structuring_completed_at: Optional[str] = None

    # Classification (aligned to Excel framework)
    spoke_alignment: str = ""            # Recommended Spoke Alignment
    solution_category: str = ""          # BI, GenAI, AI/ML, Automation, Search, etc.
    grouping: str = ""                   # Content Generation, Operational Efficiency, etc.

    # Scoring inputs (Low / Medium / High)
    business_impact_level: str = "medium"      # Business Impact
    foundational_impact_level: str = "medium"  # Foundational Impact
    technical_complexity: str = "medium"       # Technical Complexity (effort driver)
    data_availability_level: str = "medium"    # Data Availability (effort driver)

    # Legacy / compatibility fields (kept for existing records)
    use_case_category: str = "other"
    complexity_estimate: str = "medium"
    expected_benefit_type: str = ""
    strategic_alignment: List[str] = field(default_factory=list)


@dataclass
class ScoringData:
    # Raw 1-3 scores (Low=1, Medium=2, High=3; TC is inverted: Low=3, High=1)
    bi_score: int = 0    # Business Impact score (1-3)
    fi_score: int = 0    # Foundational Impact score (1-3)
    tc_score: int = 0    # Technical Complexity score (inverted: Low=3, High=1)
    da_score: int = 0    # Data Availability score (1-3)

    # Derived composite scores
    net_value_score: int = 0    # BI_pts + FI_pts  (range 0-55)
    net_effort_score: int = 0   # TC_pts + DA_pts  (range 0-45)
    total_score: int = 0        # net_value + net_effort (range 0-100)

    # High / Low labels (threshold: net_value ≥ 6 → High; net_effort ≥ 5 → Low)
    net_value: str = ""     # "High" or "Low"
    net_effort: str = ""    # "High" or "Low" (Low = easier to execute)

    # 2×2 prioritisation category
    category: str = "Backlog"  # Quick Win | Strategic Initiative | Backlog | Deprioritized

    scoring_version: str = "v1"
    scored_at: Optional[str] = None

    # Legacy aliases kept so old records don't break
    @property
    def composite_score(self):
        return self.net_value_score

    @property
    def priority_tier(self):
        return self.category

    # These are kept in the dict but not used in UI
    business_impact: int = 0
    feasibility: int = 0
    data_readiness: int = 0
    risk_compliance: int = 0
    effort_estimate_weeks: int = 0
    roi_projection_12mo: int = 0
    roi_currency: str = "USD"


@dataclass
class GeneratedDoc:
    content: str = ""
    generated_at: Optional[str] = None
    version: int = 1


@dataclass
class DocumentsData:
    prd: Optional[dict] = None
    tech_spec: Optional[dict] = None
    jira_ticket: Optional[dict] = None


@dataclass
class MetaData:
    intake_complete: bool = False
    structuring_complete: bool = False
    scoring_complete: bool = False
    handoff_complete: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class UseCase:
    id: str
    title: str
    status: str
    department: str
    created_at: str
    updated_at: str
    intake: IntakeData = field(default_factory=IntakeData)
    structured: StructuredData = field(default_factory=StructuredData)
    scoring: ScoringData = field(default_factory=ScoringData)
    documents: DocumentsData = field(default_factory=DocumentsData)
    meta: MetaData = field(default_factory=MetaData)


# ── Reference lists ────────────────────────────────────────────────────────────
STATUS_ORDER = ["idea", "structured", "scored", "validated", "in_progress", "deployed"]

CATEGORIES = ["Quick Win", "Strategic Initiative", "Backlog", "Deprioritized"]

SPOKE_ALIGNMENTS = [
    "Clinical",
    "Research",
    "Regulatory",
    "Safety",
    "Portfolio & Operational",
    "CMC",
    "Transversal - Doc Factory",
    "Transversal - Knowledge Mgmt. & Search",
    "Transversal - RWE",
    "Hub",
    "Other",
]

SOLUTION_CATEGORIES = [
    "GenAI", "AI/ML", "Automation", "BI", "Search",
    "System Integration", "Gen AI/AI/ML", "Other",
]

GROUPINGS = [
    "Content Generation",
    "Knowledge Management",
    "Operational Efficiency",
    "Predictive Analytics",
    "Process Automation",
    "Trial Execution",
    "Compliance",
]

IMPACT_OPTIONS = ["Low", "Medium", "High"]
COMPLEXITY_OPTIONS = ["Low", "Medium", "High"]


def _safe_int(val, default: int = 0, min_val: int = 0, max_val: int = 3) -> int:
    """Convert val to int safely, clamping to [min_val, max_val]."""
    if not val and val != 0:
        return default
    try:
        result = int(val)
    except (TypeError, ValueError):
        return default
    return max(min_val, min(max_val, result))


def use_case_to_dict(uc: UseCase) -> dict:
    import dataclasses
    d = dataclasses.asdict(uc)
    # Remove legacy property placeholders — they're not real fields
    sc = d.get("scoring", {})
    # Ensure new fields are present
    sc.setdefault("bi_score", sc.get("business_impact", 0))
    sc.setdefault("fi_score", sc.get("feasibility", 0))
    sc.setdefault("tc_score", sc.get("risk_compliance", 0))
    sc.setdefault("da_score", sc.get("data_readiness", 0))
    sc.setdefault("net_value_score", sc.get("composite_score", 0))
    sc.setdefault("net_effort_score", sc.get("effort_estimate_weeks", 0))
    sc.setdefault("net_value", "")
    sc.setdefault("net_effort", "")
    sc.setdefault("category", sc.get("priority_tier", "Backlog"))
    return d


def use_case_from_dict(d: dict) -> UseCase:
    _now = datetime.now(timezone.utc).isoformat()

    intake = IntakeData(
        chat_history=d.get("intake", {}).get("chat_history", []),
        raw_summary=d.get("intake", {}).get("raw_summary", ""),
    )

    s = d.get("structured", {})
    structured = StructuredData(
        problem_statement=s.get("problem_statement", ""),
        impacted_users=s.get("impacted_users", ""),
        available_data_sources=s.get("available_data_sources", []),
        expected_benefit_description=s.get("expected_benefit_description", ""),
        suggested_approach=s.get("suggested_approach", ""),
        structuring_completed_at=s.get("structuring_completed_at"),
        # New framework fields
        spoke_alignment=s.get("spoke_alignment", ""),
        solution_category=s.get("solution_category", ""),
        grouping=s.get("grouping", ""),
        business_impact_level=s.get("business_impact_level", "medium"),
        foundational_impact_level=s.get("foundational_impact_level", "medium"),
        technical_complexity=s.get("technical_complexity", s.get("complexity_estimate", "medium")),
        data_availability_level=s.get("data_availability_level", "medium"),
        # Legacy fields
        use_case_category=s.get("use_case_category", "other"),
        complexity_estimate=s.get("complexity_estimate", "medium"),
        expected_benefit_type=s.get("expected_benefit_type", ""),
        strategic_alignment=s.get("strategic_alignment", []),
    )

    sc = d.get("scoring", {})
    # Support both old and new field names
    bi = sc.get("bi_score", sc.get("business_impact", 0))
    fi = sc.get("fi_score", sc.get("feasibility", 0))
    tc = sc.get("tc_score", sc.get("risk_compliance", 0))
    da = sc.get("da_score", sc.get("data_readiness", 0))
    nvs = sc.get("net_value_score", sc.get("composite_score", 0))
    nes = sc.get("net_effort_score", sc.get("effort_estimate_weeks", 0))
    raw_cat = sc.get("category", sc.get("priority_tier", "Backlog"))
    cat = raw_cat if raw_cat in CATEGORIES else "Backlog"

    scoring = ScoringData(
        bi_score=_safe_int(bi, max_val=30),
        fi_score=_safe_int(fi, max_val=25),
        tc_score=_safe_int(tc, max_val=20),
        da_score=_safe_int(da, max_val=25),
        net_value_score=_safe_int(nvs, max_val=55),
        net_effort_score=_safe_int(nes, max_val=45),
        total_score=_safe_int(sc.get("total_score", 0), max_val=100),
        net_value=sc.get("net_value", ""),
        net_effort=sc.get("net_effort", ""),
        category=cat,
        scoring_version=sc.get("scoring_version", "v1"),
        scored_at=sc.get("scored_at"),
        # Legacy
        business_impact=_safe_int(bi, max_val=30),
        feasibility=_safe_int(fi, max_val=25),
        data_readiness=_safe_int(da, max_val=25),
        risk_compliance=_safe_int(tc, max_val=20),
        effort_estimate_weeks=_safe_int(nes, max_val=45),
    )

    docs = d.get("documents", {})
    documents = DocumentsData(
        prd=docs.get("prd"),
        tech_spec=docs.get("tech_spec"),
        jira_ticket=docs.get("jira_ticket"),
    )

    m = d.get("meta", {})
    meta = MetaData(
        intake_complete=m.get("intake_complete", False),
        structuring_complete=m.get("structuring_complete", False),
        scoring_complete=m.get("scoring_complete", False),
        handoff_complete=m.get("handoff_complete", False),
        tags=m.get("tags", []),
    )

    return UseCase(
        id=d.get("id", ""),
        title=d.get("title", "Untitled"),
        status=d.get("status", "idea"),
        department=d.get("department", ""),
        created_at=d.get("created_at", _now),
        updated_at=d.get("updated_at", _now),
        intake=intake,
        structured=structured,
        scoring=scoring,
        documents=documents,
        meta=meta,
    )
