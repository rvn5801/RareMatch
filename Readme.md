# RareMatch 🧬
### AI-Powered Rare Disease Drug Repurposing Engine — Safety First

---

## What It Does
RareMatch helps clinicians identify repurposed drug candidates for rare diseases.
It uses an AI inference engine to extract disease mechanisms from literature,
then applies rule-based matching and an FDA safety filter to rank candidates.

**Core principle: The AI reads. Python decides. Safety gates everything.**

---

## Project Structure

```
RareMatch/
│
├── backend/
│   ├── api/
│   │   └── routes.py           # FastAPI route definitions
│   ├── core/
│   │   ├── inference_engine.py # AI mechanism extraction (Gemini API)
│   │   ├── matching_engine.py  # Rule-based drug-pathway matching
│   │   └── safety_filter.py    # FDA safety filter logic
│   ├── data/
│   │   ├── repurposing_database.json  # Master drug/disease database (Phase 1)
│   │   └── abstracts/          # PubMed abstracts (.txt files per disease)
│   ├── prompts/
│   │   └── mechanism_prompt.py # Master prompt templates for LLM calls
│   └── main.py                 # FastAPI app entrypoint
│
├── frontend/
│   └── app.py                  # Streamlit UI (3 screens)
│
├── tests/
│   ├── test_inference.py       # Test AI extraction on known diseases
│   ├── test_matching.py        # Test rule-based matching logic
│   └── test_safety.py          # Test safety filter rules
│
├── docs/
│   └── architecture.md         # System architecture notes
│
├── .env.example                # Environment variable template
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## Setup

```bash
# 1. Clone and enter project
cd RareMatch

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Add your Gemini API key to .env

# 5. Run backend
uvicorn backend.main:app --port 8000 --reload --reload-dir backend

# 6. Run frontend (separate terminal)
streamlit run frontend/app.py
```

---

## Build Phases

| Phase | Component |
|-------|-----------|
| 1 | Database (JSON) | 
| 2 | AI Inference Engine |
| 3 | Matching + Safety Filter | 
| 4 | FastAPI Backend |
| 5 | Streamlit Frontend | 
| 6 | Tests + Benchmark | 

---

## The Architecture in One Sentence
> Doctor inputs disease → AI reads abstracts → extracts broken pathway →
> Python matches to drug database → Safety filter applies FDA warnings →
> Ranked results displayed with Red/Yellow/Green flags.

---

## Team
Hackathon Project — General Track Challenge