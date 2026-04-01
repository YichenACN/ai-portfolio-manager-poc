# AI Portfolio Manager POC

A Streamlit web application for capturing, evaluating, and managing AI use cases through a structured 5-step pipeline — from initial idea intake to delivery-ready documentation.

Built for R&D teams to align AI initiatives against a consistent prioritisation framework before committing engineering resources.

---

## What It Does

The app guides users through a repeatable workflow:

| Step | Page | Purpose |
|------|------|---------|
| 1 | **Intake** | Conversational AI gathers requirements from the idea owner |
| 2 | **Structure** | AI extracts and normalises fields into a standard schema |
| 3 | **Scoring** | Deterministic scoring places the use case on a 2×2 priority matrix |
| 4 | **Portfolio** | Kanban + table view to manage all use cases across the org |
| 5 | **Handoff** | AI generates a PRD, technical spec, and Jira tickets |

---

## Prioritisation Framework

Scoring is based on four dimensions, producing two composite scores:

| Dimension | Weight | Direction | Scale |
|-----------|--------|-----------|-------|
| Business Impact | ×2 | Higher = better | Low/Med/High → 1/2/3 |
| Foundational Impact | ×1 | Higher = better | Low/Med/High → 1/2/3 |
| Technical Complexity | ×1 | Lower = better | Low/Med/High → 3/2/1 |
| Data Availability | ×1 | Higher = better | Low/Med/High → 1/2/3 |

- **Net Value Score** = (Business Impact × 2) + Foundational Impact — range 3–9, threshold ≥6 = High
- **Net Effort Score** = Technical Complexity + Data Availability — range 2–6, threshold ≥5 = Low Effort

**2×2 Categories:**

| | Low Effort | High Effort |
|-|-----------|------------|
| **High Value** | Quick Win (do now) | Strategic Initiative (plan) |
| **Low Value** | Backlog (monitor) | Deprioritised (park) |

---

## Getting Started

### Prerequisites

- Python 3.10+
- A Google Gemini API key ([get one here](https://aistudio.google.com/))

### Setup

```bash
# Clone the repo
git clone <repo-url>
cd ai-portfolio-manager-poc

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your Google API key:
# GOOGLE_API_KEY=your_key_here
```

### Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Project Structure

```
ai-portfolio-manager-poc/
├── app.py                    # Home page & dashboard
├── requirements.txt
├── .env.example              # Environment variable template
│
├── core/                     # Business logic (no UI)
│   ├── models.py             # Dataclasses, enums, serialisation
│   ├── data_store.py         # JSON persistence with file locking
│   ├── llm_client.py         # Gemini API integration
│   └── scoring.py            # Deterministic scoring engine
│
├── pages/                    # Streamlit multi-page app
│   ├── 1_Intake.py           # Chat-based idea intake
│   ├── 2_Structure.py        # AI-extracted structured fields
│   ├── 3_Scoring.py          # Score display & 2×2 matrix
│   ├── 4_Portfolio.py        # Portfolio dashboard & Kanban
│   └── 5_Handoff.py          # Document generation
│
├── prompts/                  # LLM system prompts & templates
│   ├── intake_system.txt     # System instruction for intake chat
│   ├── structuring.txt       # JSON extraction prompt
│   └── document_generation.txt  # PRD/tech spec/Jira templates
│
└── data/
    └── use_cases.json        # Persistent storage (auto-created)
```

---

## Architecture

### Data Flow

```
Intake chat  →  LLM structuring  →  Deterministic scoring  →  Portfolio  →  LLM doc generation
(Gemini)         (Gemini)             (scoring.py)                            (Gemini)
     ↓                ↓                      ↓
                use_cases.json  (single source of truth)
```

### Key Design Decisions

**JSON file storage** — Avoids database dependencies for a POC. `data_store.py` uses `fcntl.flock()` for file-level locking and atomic writes (write to temp, then rename) to prevent corruption.

**Scoring is deterministic, not AI** — `core/scoring.py` is pure Python logic. This makes scores reproducible, auditable, and not subject to LLM variance.

**AI is used for three things only:**
1. Conversational intake (multi-turn chat, `llm_client.chat_intake`)
2. Structured field extraction from conversation (`llm_client.structure_use_case`)
3. Document generation (`llm_client.generate_documents`)

**Prompts are files, not strings** — All system prompts live in `prompts/` so they can be iterated independently of Python code.

**Backward compatibility layer** — `models.py` includes `use_case_from_dict()` with field aliasing to handle records written by older versions of the schema without crashing.

---

## Core Module Reference

### `core/models.py`

Defines the central `UseCase` dataclass and its nested components:

```
UseCase
├── IntakeData       — chat_history (list), raw_summary (str)
├── StructuredData   — problem, users, data sources, spoke/solution/grouping, 4 scoring inputs
├── ScoringData      — raw scores (1–3), composite scores, 2×2 category
├── DocumentsData    — prd, tech_spec, jira_ticket (each with content + metadata)
└── MetaData         — completion flags, tags
```

Reference enums (edit here to add new options):
- `SPOKES` — organisational alignment (Clinical, Research, Regulatory, etc.)
- `SOLUTION_CATEGORIES` — GenAI, AI/ML, Automation, BI, Search, etc.
- `GROUPINGS` — Content Generation, Knowledge Management, etc.
- `STATUS_ORDER` — `idea → structured → scored → validated → in_progress → deployed`

Use case IDs follow the format: `uc_{YYYYMMDD_HHMMSS}_{8-char-uuid}`.

### `core/data_store.py`

| Function | Description |
|----------|-------------|
| `load_all()` | Returns all `UseCase` objects from `data/use_cases.json` |
| `get_by_id(uc_id)` | Fetches a single record by ID |
| `upsert(uc)` | Insert or update; acquires file lock before writing |
| `delete(uc_id)` | Removes a record and rewrites the file |
| `generate_id()` | Creates a new unique ID |

### `core/llm_client.py`

| Function | Description |
|----------|-------------|
| `chat_intake(history, system_prompt)` | Multi-turn Gemini conversation for intake |
| `structure_use_case(history, template)` | Extracts structured JSON from conversation |
| `generate_summary(history)` | Produces a plain-text recap of the intake |
| `generate_documents(uc_dict, doc_type, template)` | Generates PRD, tech spec, or Jira tickets |

Uses `gemini-2.5-flash`. Includes retry logic: if the model returns malformed JSON, the error is fed back for a single self-correction pass.

### `core/scoring.py`

Single public function: `compute_scores(structured: StructuredData) -> ScoringData`

Converts Low/Med/High → numeric weights → composite scores → 2×2 category. No external dependencies, fully unit-testable.

---

## Contributing

### Adding a New Field to `UseCase`

1. Add the field to the appropriate nested dataclass in `core/models.py`
2. Update `use_case_to_dict()` and `use_case_from_dict()` for serialisation
3. Update the structuring prompt in `prompts/structuring.txt` if the field should be AI-extracted
4. Add the form control in `pages/2_Structure.py`
5. Expose it in the portfolio table/cards in `pages/4_Portfolio.py` if relevant

### Modifying Scoring Logic

All scoring logic is isolated in `core/scoring.py`. Weights, thresholds, and category labels are defined at the top of that file — edit them there. The `ScoringData` dataclass in `models.py` holds the outputs.

### Changing the AI Model

The model name is set in `core/llm_client.py`. Swap `gemini-2.5-flash` for any other `google-generativeai`-compatible model identifier.

### Editing Prompts

Prompts are plain text files in `prompts/`. They are loaded at runtime, so changes take effect without restarting the app (on the next request). The structuring prompt specifies exact JSON output format — if you change field names there, update `models.py` and `use_case_from_dict()` to match.

### Adding a New Document Type

1. Add a new section to `prompts/document_generation.txt`
2. Add a field to `DocumentsData` in `core/models.py`
3. Add a tab in `pages/5_Handoff.py` following the existing pattern

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google Gemini API key |

Copy `.env.example` to `.env` and fill in your key. The `.env` file is gitignored — never commit it.

---

## Known Limitations (POC Scope)

- **No authentication** — assumes a trusted single-user or internal environment
- **Single-file storage** — `use_cases.json` is not suitable for concurrent multi-user write loads
- **No test suite** — scoring logic is the primary candidate for unit tests
- **File locking is Unix-only** — `fcntl` is not available on Windows; would need a cross-platform alternative for Windows deployment

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | [Streamlit](https://streamlit.io/) |
| AI | [Google Gemini 2.5 Flash](https://ai.google.dev/) via `google-generativeai` |
| Storage | JSON file + `fcntl` file locking |
| Data processing | pandas |
| Config | python-dotenv |
