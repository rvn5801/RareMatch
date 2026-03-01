# 🧬 RareMatch
### AI-Powered Rare Disease Drug Repurposing Engine

> **"AI reads the literature. Python decides the matches. Safety gates everything."**

RareMatch takes a rare disease name, reads the latest PubMed literature using AI, identifies the disrupted biological pathway, and returns a ranked list of repurposable drugs — each with a live FDA safety profile and a GREEN / YELLOW / RED traffic light tailored to the specific patient.

---

## The Problem

95% of rare diseases have no approved treatment. Drug repurposing — using existing approved drugs for new indications — is the highest-leverage intervention, but the knowledge required to identify candidates is scattered across thousands of PubMed abstracts, FDA labels, and pathway databases. No tool synthesizes this in real time.

---

## The Solution: Three Pipelines

```
Disease Name
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  PIPELINE 1 — EXTRACT                                        │
│  PubMed API (live) → 5 abstracts → Gemini extracts JSON     │
│  Output: pathway + mechanism + confidence score              │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  PIPELINE 2 — MATCH (100% deterministic, zero AI)           │
│  pathway_drug_index lookup → GoF/LoF direction filter       │
│  Output: ranked drug candidates from curated database        │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  PIPELINE 3 — SAFETY GATE                                    │
│  OpenFDA API (live) → 9 priority rules → traffic light      │
│  Output: GREEN / YELLOW / RED per drug for this patient      │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
Ranked Results in Streamlit UI
```

### Why AI only reads — never decides

If Gemini is asked "what drug treats ALPS?", it will produce a plausible-sounding answer that may be entirely hallucinated. For a safety-critical application, a confident hallucination is more dangerous than "I don't know."

**RareMatch's solution:** The AI reads unstructured biomedical text — a task it excels at. Drug candidates come entirely from a hand-verified JSON database. The AI never names, suggests, or ranks a drug.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Free Gemini API key from [aistudio.google.com](https://aistudio.google.com)
- Internet connection (PubMed and OpenFDA are called live)

### Install

```bash
# Create and activate virtual environment
python -m venv rare_env
rare_env\Scripts\activate        # Windows
source rare_env/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Add your Gemini API key
cp .env.example .env
# Edit .env → GEMINI_API_KEY=your_key_here
```

### Run

```bash
# Terminal 1 — Backend
uvicorn backend.main:app --port 8000 --reload --reload-dir backend

# Terminal 2 — Frontend
streamlit run frontend/app.py

# Terminal 3 — Tests (optional)
pytest
```

| Service | URL |
|---|---|
| Streamlit Frontend | http://localhost:8501 |
| FastAPI Swagger Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/api/health |

---

## Architecture

```
RareMatch/
├── backend/
│   ├── core/
│   │   ├── inference_engine.py    # Gemini API + Pydantic validation (303 lines)
│   │   ├── matching_engine.py     # Deterministic drug lookup + GoF/LoF rules (282 lines)
│   │   └── safety_filter.py       # 9 safety rules + OpenFDA enrichment (368 lines)
│   ├── services/
│   │   ├── pubmed_client.py       # NCBI E-utilities + disk cache (249 lines)
│   │   └── openfda_client.py      # FDA drug label API (96 lines)
│   ├── api/
│   │   └── routes.py              # 5 FastAPI endpoints (309 lines)
│   ├── prompts/
│   │   └── mechanism_prompt.py    # Gemini system prompt + controlled vocabulary
│   ├── data/
│   │   ├── repurposing_database.json  # 26 drugs, 14 pathways, synonym map
│   │   └── abstracts/             # PubMed cache (auto-populated)
│   └── main.py                    # FastAPI app entrypoint
├── frontend/
│   └── app.py                     # Streamlit UI — 3 screens (923 lines)
├── tests/
│   ├── test_inference.py          # 11 tests — AI extraction layer
│   ├── test_matching.py           # 9 tests — matching engine
│   └── test_safety.py             # 9 tests — safety filter
├── conftest.py                    # Shared pytest fixtures
├── pytest.ini                     # Test config
└── requirements.txt
```

---

## Drug Database

26 drugs across 14 biological pathways. Zero AI involved in drug selection.

| Pathway | Drugs | Example Diseases |
|---|---|---|
| mTOR | Sirolimus, Everolimus, Metformin | ALPS, TSC, PHTS |
| PI3K/AKT | Alpelisib, Idelalisib, Everolimus | PIK3CA syndromes, CLOVES |
| RAS/MAPK | Selumetinib, Trametinib, Lovastatin, Growth Hormone | SYNGAP1, NF1, Noonan |
| FAS/Apoptosis | Mycophenolate Mofetil, Rituximab, Hydroxychloroquine | ALPS, lymphoproliferative |
| GABA | Cannabidiol, Clobazam, Fenfluramine, Vigabatrin | Dravet, Lennox-Gastaut |
| Sodium Channel | Sodium Valproate, Carbamazepine*, Lamotrigine | Dravet, SCN epilepsies |
| Complement | Eculizumab, Ravulizumab | aHUS, PNH |
| NMDA/Glutamate | Memantine | SYNGAP1, Rett Syndrome |
| Lysosomal storage | Laronidase | MPS I, LSDs |
| Ubiquitin-proteasome | Minocycline | Angelman |

*Carbamazepine is a safety trap — confidence=0 in Dravet Syndrome (SCN1A LoF). Included to demonstrate the safety filter correctly assigns RED.

### Adding a New Drug (No Code Required)

Open `backend/data/repurposing_database.json` and follow the `_how_to_add_data` template. Add a drug object to `drugs[]` and its ID to `pathway_drug_index`. No Python changes needed.

---

## Safety System

### Traffic Light Rules (Priority Order)

| Priority | Rule | Condition | Result |
|---|---|---|---|
| 1 | Safety Trap | confidence_score == 0 | 🔴 RED |
| 2 | Direction Blocked | direction_flag == BLOCKED | 🔴 RED |
| 3 | Pediatric RED | ped_flag==RED + age < 18 | 🔴 RED |
| 4 | Liver Constraint | liver==SEVERE + avoid_liver | 🔴 RED |
| 5 | Cardiac Constraint | cardiac_risk + avoid_cardiac | 🔴 RED |
| 6 | Custom Avoid | drug matches custom list | 🔴 RED |
| 7 | Pediatric Monitor | ped_flag==YELLOW + age < 18 | 🟡 YELLOW |
| 8 | Black Box Warning | FDA boxed_warning exists | 🟡 YELLOW |
| 9 | All Clear | none of the above | 🟢 GREEN |

RED drugs are never hidden — suppressing them would be more dangerous.

### GoF / LoF Direction Rules

- **Gain of Function** (pathway too active) → blocks Activators, Agonists, Enhancers
- **Loss of Function** (pathway deficient) → blocks Inhibitors, Blockers, Antagonists
- **Dominant Negative** → treated as Loss of Function

---

## API Reference

### POST /api/search

```json
{
  "disease_name": "ALPS",
  "patient_age": 8,
  "avoid_liver_toxicity": false,
  "avoid_cardiac_risk": false,
  "avoid_immunosuppression": false,
  "custom_avoid": ["rash", "pneumonitis"]
}
```

### Other Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/health | Engine status + database stats |
| GET | /api/diseases | Known diseases for autocomplete |
| GET | /api/pathways | All supported pathways |
| GET | /api/drug/{id} | Single drug deep-dive |

---

## Testing

```bash
pytest                          # All 29 tests (~5 seconds)
pytest -m unit -v               # Unit tests only, verbose
pytest tests/test_matching.py   # Matching engine only
pytest tests/test_safety.py     # Safety filter only
```

All 29 tests run **without a real Gemini API key** and without network access. The Gemini API is fully mocked.

### The Most Important Test

`test_carbamazepine_blocked_in_dravet` — Carbamazepine blocks sodium channels. Dravet Syndrome (SCN1A LoF) has deficient sodium channels. This test verifies the system assigns `confidence=0` and `RED`. If it ever fails, a critical safety regression has been introduced.

---

## Technology Stack

| Component | Technology | Why |
|---|---|---|
| AI / LLM | Google Gemini 2.5-flash | Free tier, large context, JSON mode |
| Backend | FastAPI 0.111 | Auto-Swagger, Pydantic v2, async |
| Validation | Pydantic v2 | Enforces controlled vocabulary on LLM output |
| Frontend | Streamlit 1.35 | Single Python file, no build step |
| Literature | NCBI PubMed (free) | 30M+ abstracts, no API key |
| Safety Data | OpenFDA (free) | Official FDA labels, no API key |
| Testing | pytest + unittest.mock | All mocked, 5 second run |

**No external infrastructure.** No database server. No Docker. No cloud account required.

---

## Disclaimer

RareMatch is a research tool built for a hackathon. It is **not** a clinical decision support tool and does not provide medical advice. All outputs require physician review.