import os
import requests
import streamlit as st

# ── Config ─────────────────────────────────────────────────────
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_URL     = f"{BACKEND_URL}/api"

# ── Page Config ────────────────────────────────────────────────
st.set_page_config(
    page_title = "RareMatch",
    page_icon  = "🧬",
    layout     = "wide",
    initial_sidebar_state = "collapsed",
)

# ── Global CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #080d14;
    color: #c8d6e8;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 3rem 3rem; max-width: 1400px; }

/* ── Typography ── */
h1, h2, h3 {
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: -0.5px;
}

/* ── Header bar ── */
.rm-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 24px 0 32px 0;
    border-bottom: 1px solid #1a2535;
    margin-bottom: 36px;
}
.rm-logo {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 28px;
    font-weight: 600;
    color: #4fc3f7;
    letter-spacing: -1px;
}
.rm-tagline {
    font-size: 13px;
    color: #4a6080;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding-left: 16px;
    border-left: 2px solid #1a2535;
}
.rm-status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #00e676;
    margin-left: auto;
    box-shadow: 0 0 8px #00e676;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ── Search box ── */
.rm-search-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #4a6080;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 8px;
}
div[data-testid="stTextInput"] input {
    background: #0d1520 !important;
    border: 1px solid #1e3050 !important;
    border-radius: 4px !important;
    color: #e8f0fe !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 18px !important;
    padding: 16px 20px !important;
    transition: border-color 0.2s;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #4fc3f7 !important;
    box-shadow: 0 0 0 3px rgba(79, 195, 247, 0.1) !important;
}

/* ── Constraints panel ── */
.rm-constraints {
    background: #0d1520;
    border: 1px solid #1a2535;
    border-radius: 6px;
    padding: 20px 24px;
    margin-top: 16px;
}
.rm-constraints-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #4a6080;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 16px;
}

/* ── Primary button ── */
div[data-testid="stButton"] button[kind="primary"] {
    background: #4fc3f7 !important;
    color: #080d14 !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
    font-size: 13px !important;
    padding: 12px 32px !important;
    transition: all 0.2s !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover {
    background: #81d4fa !important;
    transform: translateY(-1px);
}

/* ── Mechanism banner ── */
.rm-mechanism {
    background: linear-gradient(135deg, #0d1e35, #0a1828);
    border: 1px solid #1e3a5f;
    border-left: 4px solid #4fc3f7;
    border-radius: 6px;
    padding: 20px 24px;
    margin-bottom: 28px;
}
.rm-mechanism-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #4a6080;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 12px;
}
.rm-mechanism-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
}
.rm-mech-item label {
    font-size: 10px;
    color: #4a6080;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    font-family: 'IBM Plex Mono', monospace;
    display: block;
    margin-bottom: 4px;
}
.rm-mech-item span {
    font-size: 14px;
    color: #e8f0fe;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
}

/* ── Safety summary bar ── */
.rm-summary {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
    align-items: center;
}
.rm-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 3px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
}
.rm-badge-green  { background: rgba(0,230,118,0.12); color: #00e676; border: 1px solid rgba(0,230,118,0.3); }
.rm-badge-yellow { background: rgba(255,214,0,0.12);  color: #ffd600; border: 1px solid rgba(255,214,0,0.3); }
.rm-badge-red    { background: rgba(255,82,82,0.12);  color: #ff5252; border: 1px solid rgba(255,82,82,0.3); }
.rm-badge-info   { background: rgba(79,195,247,0.10); color: #4fc3f7; border: 1px solid rgba(79,195,247,0.2); }

/* ── Drug card ── */
.rm-card {
    background: #0d1520;
    border: 1px solid #1a2535;
    border-radius: 6px;
    padding: 20px 24px;
    margin-bottom: 12px;
    position: relative;
    transition: border-color 0.2s;
}
.rm-card:hover { border-color: #2a3f5f; }
.rm-card-green  { border-left: 4px solid #00e676; }
.rm-card-yellow { border-left: 4px solid #ffd600; }
.rm-card-red    { border-left: 4px solid #ff5252; }

.rm-card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 12px;
}
.rm-card-rank {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #2a3f5f;
    margin-right: 12px;
    min-width: 28px;
}
.rm-card-name {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 16px;
    font-weight: 600;
    color: #e8f0fe;
}
.rm-card-class {
    font-size: 12px;
    color: #4a6080;
    margin-top: 2px;
}
.rm-traffic-light {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 3px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}
.tl-green  { background: rgba(0,230,118,0.15); color: #00e676; }
.tl-yellow { background: rgba(255,214,0,0.15);  color: #ffd600; }
.tl-red    { background: rgba(255,82,82,0.15);  color: #ff5252; }

.rm-confidence {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 22px;
    font-weight: 600;
    color: #4fc3f7;
    text-align: right;
}
.rm-confidence-label {
    font-size: 10px;
    color: #4a6080;
    text-transform: uppercase;
    letter-spacing: 1px;
    text-align: right;
    font-family: 'IBM Plex Mono', monospace;
}

/* ── Evidence bar ── */
.rm-evidence {
    background: #080d14;
    border: 1px solid #1a2535;
    border-radius: 4px;
    padding: 12px 16px;
    margin-top: 12px;
    font-size: 12px;
    color: #6a8aaa;
    font-style: italic;
    line-height: 1.6;
}
.rm-evidence::before {
    content: '"';
    color: #4fc3f7;
    font-size: 18px;
    font-style: normal;
    margin-right: 4px;
}

/* ── Patient flag ── */
.rm-flag {
    background: rgba(255,82,82,0.08);
    border: 1px solid rgba(255,82,82,0.2);
    border-radius: 3px;
    padding: 6px 12px;
    font-size: 11px;
    color: #ff5252;
    font-family: 'IBM Plex Mono', monospace;
    margin-top: 8px;
}

/* ── Deep dive ── */
.rm-deep-section {
    background: #0d1520;
    border: 1px solid #1a2535;
    border-radius: 6px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.rm-deep-section-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #4a6080;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1a2535;
}
.rm-pmid {
    display: inline-block;
    background: rgba(79,195,247,0.1);
    border: 1px solid rgba(79,195,247,0.2);
    border-radius: 3px;
    padding: 3px 10px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #4fc3f7;
    margin: 3px 4px 3px 0;
    cursor: pointer;
}
.rm-blackbox {
    background: rgba(255,82,82,0.08);
    border: 1px solid rgba(255,82,82,0.25);
    border-radius: 4px;
    padding: 12px 16px;
    font-size: 12px;
    color: #ff8a80;
    line-height: 1.6;
}
.rm-blackbox::before {
    content: '⚠ BLACK BOX WARNING  ';
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
    font-size: 10px;
    letter-spacing: 1.5px;
    color: #ff5252;
    display: block;
    margin-bottom: 6px;
}

/* ── Source pill ── */
.rm-source-live {
    display: inline-block;
    background: rgba(0,230,118,0.1);
    border: 1px solid rgba(0,230,118,0.25);
    border-radius: 3px;
    padding: 2px 10px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #00e676;
    letter-spacing: 1px;
}
.rm-source-cache {
    display: inline-block;
    background: rgba(79,195,247,0.1);
    border: 1px solid rgba(79,195,247,0.2);
    border-radius: 3px;
    padding: 2px 10px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #4fc3f7;
    letter-spacing: 1px;
}

/* ── Divider ── */
.rm-divider {
    border: none;
    border-top: 1px solid #1a2535;
    margin: 24px 0;
}

/* ── Spinner override ── */
.stSpinner > div { border-top-color: #4fc3f7 !important; }

/* ── Metric override ── */
[data-testid="stMetric"] {
    background: #0d1520;
    border: 1px solid #1a2535;
    border-radius: 4px;
    padding: 12px 16px;
}
[data-testid="stMetricLabel"] p {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    color: #4a6080 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    color: #4fc3f7 !important;
}

/* ── Error box ── */
.rm-error {
    background: rgba(255,82,82,0.08);
    border: 1px solid rgba(255,82,82,0.3);
    border-radius: 4px;
    padding: 16px 20px;
    color: #ff5252;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
}

/* ── No results ── */
.rm-no-results {
    text-align: center;
    padding: 60px 20px;
    color: #2a3f5f;
    font-family: 'IBM Plex Mono', monospace;
}
.rm-no-results-icon { font-size: 40px; margin-bottom: 16px; }
.rm-no-results-text { font-size: 14px; }
</style>
""", unsafe_allow_html=True)


# ── Helper Functions ───────────────────────────────────────────

def call_api(endpoint: str, method: str = "GET", payload: dict | None = None) -> dict | None:
    """Single point for all API calls — handles errors cleanly."""
    try:
        url = f"{API_URL}/{endpoint}"
        if method == "POST":
            resp = requests.post(url, json=payload, timeout=60)
        else:
            resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.session_state["api_error"] = "Cannot connect to backend. Is uvicorn running on port 8000?"
        return None
    except requests.exceptions.Timeout:
        st.session_state["api_error"] = "Request timed out. The AI is taking too long — try again."
        return None
    except Exception as e:
        st.session_state["api_error"] = f"API error: {str(e)}"
        return None


def traffic_html(light: str) -> str:
    icons = {"GREEN": "●", "YELLOW": "●", "RED": "●"}
    cls   = {"GREEN": "tl-green", "YELLOW": "tl-yellow", "RED": "tl-red"}
    return f'<span class="rm-traffic-light {cls.get(light, "tl-yellow")}">{icons.get(light, "●")} {light}</span>'


def source_html(source: str) -> str:
    if source == "pubmed_live":
        return '<span class="rm-source-live">⬤ LIVE PUBMED</span>'
    elif source == "cache":
        return '<span class="rm-source-cache">⬤ CACHED</span>'
    return '<span class="rm-source-cache">⬤ FALLBACK</span>'


def confidence_color(score: int) -> str:
    if score >= 80: return "#00e676"
    if score >= 50: return "#ffd600"
    return "#ff5252"


# ── Session State Init ─────────────────────────────────────────
if "results"    not in st.session_state: st.session_state["results"]    = None
if "deep_drug"  not in st.session_state: st.session_state["deep_drug"]  = None
if "api_error"  not in st.session_state: st.session_state["api_error"]  = None
if "last_query" not in st.session_state: st.session_state["last_query"] = ""


# ── Header ─────────────────────────────────────────────────────
health = call_api("health")
is_online = health and health.get("status") == "ok"

st.markdown(f"""
<div class="rm-header">
    <div class="rm-logo">🧬 RareMatch</div>
    <div class="rm-tagline">AI-Powered Drug Repurposing Engine</div>
    <div style="margin-left:auto; display:flex; align-items:center; gap:12px;">
        <span style="font-family:'IBM Plex Mono',monospace; font-size:11px; color:#4a6080;">
            {"API ONLINE" if is_online else "API OFFLINE"}
        </span>
        <div class="rm-status-dot" style="background:{'#00e676' if is_online else '#ff5252'};
             box-shadow:0 0 8px {'#00e676' if is_online else '#ff5252'};"></div>
    </div>
</div>
""", unsafe_allow_html=True)

if not is_online:
    st.markdown("""
    <div class="rm-error">
        Backend offline — start it with:<br>
        <code>uvicorn backend.main:app --port 8000 --reload --reload-dir backend</code>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── Deep Dive Screen ───────────────────────────────────────────
if st.session_state["deep_drug"]:
    drug = st.session_state["deep_drug"]

    # Back button
    if st.button("← Back to Results", key="back_btn"):
        st.session_state["deep_drug"] = None
        st.rerun()

    st.markdown("<hr class='rm-divider'>", unsafe_allow_html=True)

    # Drug title
    tl_class = {"GREEN": "rm-card-green", "YELLOW": "rm-card-yellow", "RED": "rm-card-red"}.get(drug["traffic_light"], "rm-card-yellow")
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:16px; margin-bottom:24px;">
        <div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:24px; font-weight:600; color:#e8f0fe;">
                {drug["drug_name"]}
            </div>
            <div style="font-size:13px; color:#4a6080; margin-top:4px;">
                {drug["generic_name"]} &nbsp;·&nbsp; {drug["drug_class"]}
            </div>
        </div>
        <div style="margin-left:auto; text-align:right;">
            {traffic_html(drug["traffic_light"])}
            <div style="font-family:'IBM Plex Mono',monospace; font-size:28px; font-weight:600;
                 color:{confidence_color(drug['confidence_score'])}; margin-top:4px;">
                {drug["confidence_score"]}%
            </div>
            <div style="font-size:10px; color:#4a6080; letter-spacing:1px;">CONFIDENCE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        # Match rationale
        st.markdown(f"""
        <div class="rm-deep-section">
            <div class="rm-deep-section-title">Match Rationale</div>
            <div style="font-size:13px; color:#8aabcc; line-height:1.7;">
                {drug["match_reason"]}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Evidence
        st.markdown(f"""
        <div class="rm-deep-section">
            <div class="rm-deep-section-title">Evidence Links</div>
            <div>
                {"".join(f'<span class="rm-pmid">{pmid}</span>' for pmid in drug["evidence_links"])}
            </div>
            <div style="margin-top:12px; font-size:12px; color:#6a8aaa; line-height:1.7; font-style:italic;">
                {drug["evidence_summary"]}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Validation plan
        st.markdown(f"""
        <div class="rm-deep-section">
            <div class="rm-deep-section-title">Validation Plan</div>
            <div style="font-size:13px; color:#8aabcc; line-height:1.7;">
                {drug["validation_plan"]}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        safety = drug["safety"]

        # Black box warning
        if safety["black_box_warning"] and safety["black_box_warning"] not in ["None.", "None"]:
            st.markdown(f"""
            <div class="rm-deep-section">
                <div class="rm-deep-section-title">FDA Safety</div>
                <div class="rm-blackbox">{safety["black_box_warning"]}</div>
            </div>
            """, unsafe_allow_html=True)

        # Pediatric
        ped_color = {"GREEN": "#00e676", "YELLOW": "#ffd600", "RED": "#ff5252"}.get(safety["pediatric_flag"], "#ffd600")
        st.markdown(f"""
        <div class="rm-deep-section">
            <div class="rm-deep-section-title">Pediatric Profile</div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
                <span style="font-family:'IBM Plex Mono',monospace; font-size:12px; font-weight:600;
                      color:{ped_color};">● {safety["pediatric_flag"]}</span>
            </div>
            <div style="font-size:12px; color:#8aabcc; line-height:1.6;">
                {safety["pediatric_note"]}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Side effects
        side_effects = safety.get("major_side_effects", [])
        if side_effects:
            tags = "".join(
                f'<span style="display:inline-block; background:#0d1e35; border:1px solid #1e3a5f; '
                f'border-radius:3px; padding:3px 10px; font-size:11px; color:#8aabcc; '
                f'font-family:IBM Plex Mono,monospace; margin:3px 4px 3px 0;">{se}</span>'
                for se in side_effects
            )
            st.markdown(f"""
            <div class="rm-deep-section">
                <div class="rm-deep-section-title">Major Side Effects</div>
                {tags}
            </div>
            """, unsafe_allow_html=True)

        # Contraindications
        contras = safety.get("contraindications", [])
        if contras:
            items = "".join(f'<li style="margin-bottom:4px;">{c}</li>' for c in contras)
            st.markdown(f"""
            <div class="rm-deep-section">
                <div class="rm-deep-section-title">Contraindications</div>
                <ul style="font-size:12px; color:#ff8a80; line-height:1.8; margin:0; padding-left:16px;">
                    {items}
                </ul>
            </div>
            """, unsafe_allow_html=True)

        # Missing data
        if safety.get("missing_data"):
            st.markdown(f"""
            <div class="rm-deep-section">
                <div class="rm-deep-section-title">Missing Data / Gaps</div>
                <div style="font-size:12px; color:#6a8aaa; line-height:1.6; font-style:italic;">
                    {safety["missing_data"]}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Patient flags
        if drug.get("patient_flags"):
            flags_html = "".join(
                f'<div class="rm-flag">{flag}</div>'
                for flag in drug["patient_flags"]
            )
            st.markdown(f"""
            <div class="rm-deep-section">
                <div class="rm-deep-section-title">Patient-Specific Flags</div>
                {flags_html}
            </div>
            """, unsafe_allow_html=True)

    st.stop()


# ── Main Search Screen ─────────────────────────────────────────
col_search, col_info = st.columns([3, 1])

with col_search:
    st.markdown('<div class="rm-search-label">Enter Rare Disease Name</div>', unsafe_allow_html=True)
    disease_input = st.text_input(
        label     = "disease",
        value     = st.session_state["last_query"],
        placeholder = "e.g. ALPS, SYNGAP1, Dravet Syndrome, Noonan Syndrome...",
        label_visibility = "collapsed",
        key       = "disease_input",
    )

with col_info:
    if is_online and health:
        st.metric("Drugs in DB",    health.get("database_drugs", 0))

# ── Patient Constraints ────────────────────────────────────────
with st.expander("⚙  Patient Constraints  (optional)", expanded=False):
    st.markdown('<div class="rm-constraints-title">Filter results for a specific patient profile</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        patient_age = st.number_input("Patient Age", min_value=0, max_value=120,
                                       value=None, placeholder="Any age", key="age_input")
    with c2:
        avoid_liver = st.checkbox("Avoid Liver Toxicity", key="liver_cb")
    with c3:
        avoid_cardiac = st.checkbox("Avoid Cardiac Risk", key="cardiac_cb")
    with c4:
        avoid_immuno = st.checkbox("Avoid Immunosuppression", key="immuno_cb")

    custom_avoid_raw = st.text_input(
        "Custom Avoid (comma-separated)",
        placeholder="e.g. rash, pneumonitis",
        key="custom_avoid_input"
    )
    custom_avoid = [x.strip() for x in custom_avoid_raw.split(",") if x.strip()]

# ── Search Button ──────────────────────────────────────────────
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

btn_col, hint_col = st.columns([1, 4])
with btn_col:
    search_clicked = st.button("🔬  ANALYZE", type="primary", use_container_width=True)

with hint_col:
    st.markdown(
        "<div style='padding-top:12px; font-size:11px; color:#2a3f5f; font-family:IBM Plex Mono,monospace;'>"
        "PubMed → Gemini extracts pathway → Python matches drugs → OpenFDA safety check"
        "</div>",
        unsafe_allow_html=True
    )

# ── Handle Search ──────────────────────────────────────────────
if search_clicked and str(disease_input or "").strip():
    st.session_state["api_error"] = None
    st.session_state["last_query"] = str(disease_input or "").strip()

    with st.spinner(f"Analyzing {str(disease_input or '')}..."):
        payload = {
            "disease_name":           str(disease_input or "").strip(),
            "patient_age":            int(patient_age) if patient_age else None,
            "avoid_liver_toxicity":   avoid_liver,
            "avoid_cardiac_risk":     avoid_cardiac,
            "avoid_immunosuppression": avoid_immuno,
            "custom_avoid":           custom_avoid,
        }
        data = call_api("search", method="POST", payload=payload)

    if data:
        if data.get("success"):
            st.session_state["results"] = data["result"]
        else:
            st.session_state["api_error"] = data.get("error", "Unknown error")
            st.session_state["results"] = None

elif search_clicked and not str(disease_input or "").strip():
    st.warning("Please enter a disease name.")

# ── Error display ──────────────────────────────────────────────
if st.session_state.get("api_error"):
    st.markdown(f"""
    <div class="rm-error">{st.session_state["api_error"]}</div>
    """, unsafe_allow_html=True)

# ── Results Screen ─────────────────────────────────────────────
results = st.session_state.get("results")

if results:
    st.markdown("<hr class='rm-divider'>", unsafe_allow_html=True)

    # ── Mechanism Banner ───────────────────────────────────────
    conf_color = confidence_color(results["mechanism_confidence"])
    src_html   = source_html(results.get("abstract_source", "cache"))

    st.markdown(f"""
    <div class="rm-mechanism">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
            <div class="rm-mechanism-title">AI Mechanism Extraction — {results["disease_name"].upper()}</div>
            <div style="display:flex; align-items:center; gap:10px;">
                {src_html}
                <span style="font-family:'IBM Plex Mono',monospace; font-size:11px;
                      color:{conf_color}; font-weight:600;">
                    {results["mechanism_confidence"]}% CONFIDENCE
                </span>
            </div>
        </div>
        <div class="rm-mechanism-grid">
            <div class="rm-mech-item">
                <label>Mechanism</label>
                <span>{results["inferred_mechanism"]}</span>
            </div>
            <div class="rm-mech-item">
                <label>Pathway</label>
                <span>{results["disrupted_pathway"]}</span>
            </div>
            <div class="rm-mech-item">
                <label>Pathway Status</label>
                <span>{results["pathway_status"]}</span>
            </div>
            <div class="rm-mech-item">
                <label>Required Action</label>
                <span style="font-size:12px;">{results["required_action"]}</span>
            </div>
        </div>
        <div style="margin-top:14px; padding-top:12px; border-top:1px solid #1a2535;
             font-size:12px; color:#4a6080; font-style:italic; line-height:1.5;">
            "{results.get('evidence_quote', '')}"
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Safety Summary Bar ─────────────────────────────────────
    summary = results.get("safety_summary", {})
    n_green  = summary.get("GREEN", 0)
    n_yellow = summary.get("YELLOW", 0)
    n_red    = summary.get("RED", 0)
    n_total  = summary.get("total", 0)

    st.markdown(f"""
    <div class="rm-summary">
        <span style="font-family:'IBM Plex Mono',monospace; font-size:11px;
              color:#4a6080; letter-spacing:1px; text-transform:uppercase; margin-right:4px;">
            {n_total} Candidates
        </span>
        <span class="rm-badge rm-badge-green">● {n_green} GREEN</span>
        <span class="rm-badge rm-badge-yellow">● {n_yellow} YELLOW</span>
        <span class="rm-badge rm-badge-red">● {n_red} RED</span>
        <span style="font-family:'IBM Plex Mono',monospace; font-size:11px; color:#2a3f5f;
              margin-left:auto;">CLICK ANY CARD FOR FULL EVIDENCE</span>
    </div>
    """, unsafe_allow_html=True)

    # ── No results case ────────────────────────────────────────
    if n_total == 0:
        st.markdown("""
        <div class="rm-no-results">
            <div class="rm-no-results-icon">🔬</div>
            <div class="rm-no-results-text">
                No pathway match found in database.<br>
                The AI extracted a pathway but it doesn't map to any known drugs yet.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Drug Cards ─────────────────────────────────────────────
    ranked_drugs = results.get("ranked_drugs", [])

    for drug in ranked_drugs:
        tl     = drug["traffic_light"]
        tl_cls = {"GREEN": "rm-card-green", "YELLOW": "rm-card-yellow", "RED": "rm-card-red"}.get(tl, "rm-card-yellow")
        c_color = confidence_color(drug["confidence_score"])

        # Direction warning
        direction_warning = ""
        if drug["direction_flag"] in ["BLOCKED", "MISMATCH"]:
            direction_warning = f"""
            <div style="background:rgba(255,82,82,0.08); border:1px solid rgba(255,82,82,0.2);
                 border-radius:3px; padding:6px 12px; font-size:11px; color:#ff5252;
                 font-family:IBM Plex Mono,monospace; margin-top:8px;">
                ⚠ DIRECTION {drug["direction_flag"]} — {drug["match_reason"][:120]}...
            </div>"""

        # Patient flags
        flags_html = ""
        if drug.get("patient_flags"):
            flags_html = "".join(
                f'<div class="rm-flag">{flag}</div>'
                for flag in drug["patient_flags"][:2]  # Show max 2 in card view
            )

        col_card, col_btn = st.columns([10, 1])

        with col_card:
            st.markdown(f"""
            <div class="rm-card {tl_cls}">
                <div class="rm-card-header">
                    <div style="display:flex; align-items:flex-start;">
                        <span class="rm-card-rank">#{drug["rank"]:02d}</span>
                        <div>
                            <div class="rm-card-name">{drug["drug_name"]}</div>
                            <div class="rm-card-class">
                                {drug["drug_class"]} &nbsp;·&nbsp; {drug["target_pathway"]}
                                &nbsp;·&nbsp; {drug["approval_status"][:60]}{'...' if len(drug["approval_status"]) > 60 else ''}
                            </div>
                        </div>
                    </div>
                    <div style="text-align:right; margin-left:16px;">
                        {traffic_html(tl)}
                        <div class="rm-confidence" style="color:{c_color};">{drug["confidence_score"]}%</div>
                        <div class="rm-confidence-label">confidence</div>
                    </div>
                </div>
                <div style="font-size:12px; color:#6a8aaa; line-height:1.6; margin-bottom:8px;">
                    {drug["pathway_action"][:180]}{'...' if len(drug["pathway_action"]) > 180 else ''}
                </div>
                <div style="font-size:11px; color:#2a3f5f; font-family:IBM Plex Mono,monospace;">
                    {"  ".join(drug.get("evidence_links", [])[:3])}
                </div>
                {direction_warning}
                {flags_html}
            </div>
            """, unsafe_allow_html=True)

        with col_btn:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            if st.button("→", key=f"dive_{drug['drug_id']}", help=f"Deep dive: {drug['drug_name']}"):
                st.session_state["deep_drug"] = drug
                st.rerun()

    # ── Biological Cousins ─────────────────────────────────────
    cousins = results.get("biological_cousins")
    if cousins and cousins.get("matched_known_diseases"):
        st.markdown("<hr class='rm-divider'>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="rm-deep-section">
            <div class="rm-deep-section-title">Biological Cousins — Same Pathway in Known Diseases</div>
            <div style="font-size:13px; color:#8aabcc; line-height:1.8;">
                <strong style="color:#4fc3f7;">Top match:</strong> {cousins.get("top_match", "None")}
                <br>
                <strong style="color:#4a6080;">Related diseases:</strong>
                {", ".join(cousins.get("matched_known_diseases", []))}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Footer ──────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:60px; padding-top:20px; border-top:1px solid #0d1520;
     text-align:center; font-family:IBM Plex Mono,monospace; font-size:10px;
     color:#1e2d40; letter-spacing:1px;">
    RAREMATCH · AI READS · PYTHON DECIDES · SAFETY GATES EVERYTHING
</div>
""", unsafe_allow_html=True)