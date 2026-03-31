import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import hashlib

from core.models import UseCase, use_case_to_dict, use_case_from_dict

DATA_FILE = Path(__file__).parent.parent / "data" / "use_cases.json"


def _ensure_data_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]")


def load_all() -> list[UseCase]:
    _ensure_data_file()
    raw = DATA_FILE.read_text()
    if not raw.strip():
        return []
    records = json.loads(raw)
    return [use_case_from_dict(r) for r in records]


def save_all(use_cases: list[UseCase]) -> None:
    _ensure_data_file()
    data = [use_case_to_dict(uc) for uc in use_cases]
    tmp_file = DATA_FILE.with_suffix(".json.tmp")
    tmp_file.write_text(json.dumps(data, indent=2))
    os.replace(tmp_file, DATA_FILE)


def get_by_id(uc_id: str) -> Optional[UseCase]:
    for uc in load_all():
        if uc.id == uc_id:
            return uc
    return None


def upsert(uc: UseCase) -> None:
    uc.updated_at = datetime.now(timezone.utc).isoformat()
    use_cases = load_all()
    for i, existing in enumerate(use_cases):
        if existing.id == uc.id:
            use_cases[i] = uc
            save_all(use_cases)
            return
    use_cases.append(uc)
    save_all(use_cases)


def delete(uc_id: str) -> bool:
    use_cases = load_all()
    filtered = [uc for uc in use_cases if uc.id != uc_id]
    if len(filtered) == len(use_cases):
        return False
    save_all(filtered)
    return True


def generate_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    rand = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:4]
    return f"uc_{ts}_{rand}"
