from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class IntakeData:
    chat_history: List[dict] = field(default_factory=list)
    raw_summary: str = ""


@dataclass
class StructuredData:
    problem_statement: str = ""
    use_case_category: str = "other"
    impacted_users: str = ""
    available_data_sources: List[str] = field(default_factory=list)
    expected_benefit_type: str = ""
    expected_benefit_description: str = ""
    complexity_estimate: str = "medium"
    suggested_approach: str = ""
    strategic_alignment: List[str] = field(default_factory=list)
    structuring_completed_at: Optional[str] = None


@dataclass
class ScoringData:
    business_impact: int = 0
    feasibility: int = 0
    data_readiness: int = 0
    risk_compliance: int = 0
    composite_score: int = 0
    effort_estimate_weeks: int = 0
    roi_projection_12mo: int = 0
    roi_currency: str = "USD"
    priority_tier: str = "P3"
    scoring_version: str = "mock_v1"
    scored_at: Optional[str] = None


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


# Status lifecycle
STATUS_ORDER = ["idea", "structured", "scored", "validated", "in_progress", "deployed"]

USE_CASE_CATEGORIES = [
    "automation", "nlp", "forecasting", "computer_vision",
    "recommendation", "anomaly_detection", "other"
]

BENEFIT_TYPES = ["revenue", "cost_reduction", "risk", "other"]

COMPLEXITY_OPTIONS = ["low", "medium", "high"]

STRATEGIC_ALIGNMENT_OPTIONS = [
    "operational_efficiency", "cost_reduction", "revenue_growth",
    "risk_management", "customer_experience", "compliance"
]


def use_case_to_dict(uc: UseCase) -> dict:
    import dataclasses
    return dataclasses.asdict(uc)


def use_case_from_dict(d: dict) -> UseCase:
    intake = IntakeData(
        chat_history=d.get("intake", {}).get("chat_history", []),
        raw_summary=d.get("intake", {}).get("raw_summary", ""),
    )

    s = d.get("structured", {})
    structured = StructuredData(
        problem_statement=s.get("problem_statement", ""),
        use_case_category=s.get("use_case_category", "other"),
        impacted_users=s.get("impacted_users", ""),
        available_data_sources=s.get("available_data_sources", []),
        expected_benefit_type=s.get("expected_benefit_type", ""),
        expected_benefit_description=s.get("expected_benefit_description", ""),
        complexity_estimate=s.get("complexity_estimate", "medium"),
        suggested_approach=s.get("suggested_approach", ""),
        strategic_alignment=s.get("strategic_alignment", []),
        structuring_completed_at=s.get("structuring_completed_at"),
    )

    sc = d.get("scoring", {})
    scoring = ScoringData(
        business_impact=sc.get("business_impact", 0),
        feasibility=sc.get("feasibility", 0),
        data_readiness=sc.get("data_readiness", 0),
        risk_compliance=sc.get("risk_compliance", 0),
        composite_score=sc.get("composite_score", 0),
        effort_estimate_weeks=sc.get("effort_estimate_weeks", 0),
        roi_projection_12mo=sc.get("roi_projection_12mo", 0),
        roi_currency=sc.get("roi_currency", "USD"),
        priority_tier=sc.get("priority_tier", "P3"),
        scoring_version=sc.get("scoring_version", "mock_v1"),
        scored_at=sc.get("scored_at"),
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
        id=d["id"],
        title=d["title"],
        status=d["status"],
        department=d.get("department", ""),
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        intake=intake,
        structured=structured,
        scoring=scoring,
        documents=documents,
        meta=meta,
    )
