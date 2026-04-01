import fcntl
import json
import os
import uuid
import warnings
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from core.models import UseCase, use_case_to_dict, use_case_from_dict

DATA_FILE = Path(__file__).parent.parent / "data" / "use_cases.json"
LOCK_FILE = DATA_FILE.with_suffix(".json.lock")


def _ensure_data_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]")


def _load_raw() -> list[UseCase]:
    """Read and parse the data file. Returns [] on corruption with a warning."""
    raw = DATA_FILE.read_text()
    if not raw.strip():
        return []
    try:
        records = json.loads(raw)
    except json.JSONDecodeError:
        warnings.warn(
            f"Data file {DATA_FILE} is corrupted and could not be parsed. "
            "Returning empty list to keep the app running.",
            RuntimeWarning,
            stacklevel=3,
        )
        return []
    return [use_case_from_dict(r) for r in records]


def load_all() -> list[UseCase]:
    _ensure_data_file()
    return _load_raw()


def save_all(use_cases: list[UseCase]) -> None:
    _ensure_data_file()
    data = [use_case_to_dict(uc) for uc in use_cases]
    tmp_file = DATA_FILE.with_suffix(".json.tmp")
    try:
        tmp_file.write_text(json.dumps(data, indent=2))
        os.replace(tmp_file, DATA_FILE)
    except Exception:
        if tmp_file.exists():
            tmp_file.unlink(missing_ok=True)
        raise


def get_by_id(uc_id: str) -> Optional[UseCase]:
    for uc in load_all():
        if uc.id == uc_id:
            return uc
    return None


def upsert(uc: UseCase) -> None:
    uc.updated_at = datetime.now(timezone.utc).isoformat()
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            _ensure_data_file()
            use_cases = _load_raw()
            for i, existing in enumerate(use_cases):
                if existing.id == uc.id:
                    use_cases[i] = uc
                    save_all(use_cases)
                    return
            use_cases.append(uc)
            save_all(use_cases)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def delete(uc_id: str) -> bool:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            _ensure_data_file()
            use_cases = _load_raw()
            filtered = [uc for uc in use_cases if uc.id != uc_id]
            if len(filtered) == len(use_cases):
                return False
            save_all(filtered)
            return True
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def generate_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    rand = uuid.uuid4().hex[:8]
    return f"uc_{ts}_{rand}"
