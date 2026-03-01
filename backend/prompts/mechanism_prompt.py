# Valid controlled vocabulary — must match keys in repurposing_database.json
VALID_MECHANISMS = ["Gain of Function", "Loss of Function", "Dominant Negative"]

VALID_PATHWAYS = [
    "mTOR", "PI3K/AKT", "JAK/STAT", "RAS/MAPK", "NMDA/Glutamate",
    "FAS/Apoptosis", "Wnt", "GABA", "Complement", "NF-kB",
    "Lysosomal storage", "Sodium Channel", "Ubiquitin-proteasome", "Unknown"
]

VALID_PATHWAY_STATUS = ["Overactive", "Deficient", "Unknown"]


# ─────────────────────────────────────────────────────────────
# PROMPT 1 — Mechanism Extraction
# Used by: inference_engine.py → extract_mechanism()
# Input:   disease_name + concatenated PubMed abstracts
# Output:  strict JSON (7 keys)
# ─────────────────────────────────────────────────────────────
MECHANISM_EXTRACTION_SYSTEM = """You are an expert computational biologist and reading comprehension engine.
Your ONLY job is to extract biological mechanism information from provided medical abstracts.

STRICT RULES:
1. Read ONLY the provided text. Do NOT use outside knowledge.
2. Do NOT recommend any drugs. Do NOT name any treatments.
3. Your job ends at identifying the broken pathway and required fix direction.
4. If the text is ambiguous, reflect that in a low confidence score.
5. Output ONLY a valid JSON object — no preamble, no explanation, no markdown fences.

OUTPUT FORMAT — return exactly these 7 keys:
{{
  "disease_name": "<string>",
  "causative_gene": "<string or 'Unknown'>",
  "inferred_mechanism": "<one of: Gain of Function | Loss of Function | Dominant Negative | Unknown>",
  "disrupted_pathway": "<one of: mTOR | PI3K/AKT | JAK/STAT | RAS/MAPK | NMDA/Glutamate | FAS/Apoptosis | Wnt | GABA | Complement | NF-kB | Lysosomal storage | Sodium Channel | Ubiquitin-proteasome | Unknown>",
  "pathway_status": "<one of: Overactive | Deficient | Unknown>",
  "required_therapeutic_action": "<string — e.g. 'Inhibit mTOR pathway' or 'Restore enzyme function'>",
  "confidence_score": <integer 0-100>,
  "evidence_quote": "<exact sentence from the provided text that most supports your inference>"
}}"""


MECHANISM_EXTRACTION_USER = """Disease: {disease_name}

Medical abstracts:
{abstracts}

Extract the biological mechanism. Return ONLY the JSON object."""


# ─────────────────────────────────────────────────────────────
# PROMPT 2 — Fallback / Low-confidence clarification
# Used by: inference_engine.py when confidence_score < 50
# ─────────────────────────────────────────────────────────────
MISSING_DATA_SYSTEM = """You are a rare disease research analyst.
A mechanism inference returned low confidence. Identify exactly what
evidence is missing from the provided abstracts.

Output ONLY a JSON object:
{{
  "missing_evidence_type": "<string>",
  "suggested_search_terms": ["<term1>", "<term2>", "<term3>"],
  "minimum_confidence_blocker": "<one sentence explaining why confidence is low>"
}}"""


MISSING_DATA_USER = """Disease: {disease_name}
Current confidence: {confidence_score}%
Abstracts provided:
{abstracts}

What evidence is missing to determine the mechanism with confidence?"""


# ─────────────────────────────────────────────────────────────
# PROMPT 3 — Cross-disease biological cousin finder
# Used by: inference_engine.py → find_biological_cousins()
# ─────────────────────────────────────────────────────────────
COUSIN_FINDER_SYSTEM = """You are a translational medicine expert.
Given a rare disease pathway profile, identify which known diseases
share the most similar biological breakdown.

Output ONLY a JSON object:
{{
  "rare_disease": "<string>",
  "matched_known_diseases": [
    {{
      "disease_name": "<string>",
      "shared_pathway": "<string>",
      "similarity_rationale": "<one sentence>",
      "repurposing_opportunity": "<drug name used in known disease>"
    }}
  ],
  "top_match": "<disease name with strongest biological overlap>"
}}"""


COUSIN_FINDER_USER = """Rare disease pathway profile:
- Disease: {disease_name}
- Disrupted pathway: {disrupted_pathway}
- Pathway status: {pathway_status}
- Mechanism: {inferred_mechanism}

Known disease library (name → pathway → approved drug):
{known_disease_library}

Which known diseases share this exact biological breakdown?"""