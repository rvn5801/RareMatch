import os
import io
import time
import datetime
import requests
import streamlit as st
import html as _html

# PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

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


# ── PDF Report Generator ───────────────────────────────────────
def generate_pdf_report(results: dict, query: dict) -> bytes:
    """
    Generate a professional clinical-style PDF report from search results.
    Returns raw bytes suitable for st.download_button.
    """
    buf = io.BytesIO()

    # ── Colours ───────────────────────────────────────────────
    NAVY      = colors.HexColor("#0D1520")
    BLUE      = colors.HexColor("#1565C0")
    LBLUE     = colors.HexColor("#4FC3F7")
    GREEN_C   = colors.HexColor("#00C853")
    AMBER_C   = colors.HexColor("#FFB300")
    RED_C     = colors.HexColor("#F44336")
    MUTED     = colors.HexColor("#546E7A")
    LIGHT_BG  = colors.HexColor("#F5F8FF")
    MID_GREY  = colors.HexColor("#90A4AE")
    DARK_TEXT = colors.HexColor("#1A2535")
    WHITE     = colors.white
    BLACK     = colors.black

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=20*mm, bottomMargin=20*mm,
        title=f"RareMatch — {results.get('disease_name', 'Report')}",
    )

    W = A4[0] - 36*mm   # usable width

    # ── Paragraph styles ─────────────────────────────────────
    # ParagraphStyle doesn't accept keyword args in constructor —
    # set attributes directly after creation.
    def ps(name, fontName="Helvetica", fontSize=10, textColor=None,
           leading=14, alignment=TA_LEFT, spaceBefore=0, spaceAfter=0):  # type: ignore[assignment]
        s = ParagraphStyle(name)
        s.fontName    = fontName
        s.fontSize    = fontSize
        s.textColor   = textColor or DARK_TEXT
        s.leading     = leading
        s.alignment   = alignment  # type: ignore[assignment]
        s.spaceBefore = spaceBefore
        s.spaceAfter  = spaceAfter
        return s

    S_TITLE   = ps("title",   fontName="Helvetica-Bold", fontSize=22,
                               textColor=BLUE, leading=26)
    S_SUB     = ps("sub",     fontSize=11, textColor=MUTED, leading=15)
    S_H2      = ps("h2",      fontName="Helvetica-Bold", fontSize=13,
                               textColor=BLUE, leading=17, spaceBefore=10)
    S_H3      = ps("h3",      fontName="Helvetica-Bold", fontSize=11, leading=15)
    S_BODY    = ps("body",    fontSize=10, leading=15)
    S_SMALL   = ps("small",   fontSize=9,  textColor=MUTED, leading=13)
    S_ITALIC  = ps("italic",  fontName="Helvetica-Oblique", fontSize=10,
                               textColor=MUTED, leading=14)
    S_MONO    = ps("mono",    fontName="Courier", fontSize=9, leading=13)
    S_WARNING = ps("warn",    fontName="Helvetica-Bold", fontSize=10,
                               textColor=RED_C, leading=14)
    S_CENTER  = ps("center",  fontSize=9, textColor=MUTED,
                               leading=12, alignment=TA_CENTER)

    story = []

    def hr(color=LBLUE, thickness: int = 1):
        story.append(HRFlowable(width="100%", thickness=thickness,
                                color=color, spaceAfter=4, spaceBefore=4))

    def gap(h=6):
        story.append(Spacer(1, h))

    # ── Header ───────────────────────────────────────────────
    now = datetime.datetime.now().strftime("%B %d, %Y · %H:%M")
    disease = results.get("disease_name", "Unknown")

    header_data = [[
        Paragraph(f"<b>RareMatch</b>", ps("logo", fontName="Helvetica-Bold",
                  fontSize=16, textColor=BLUE)),
        Paragraph(f"Generated: {now}", ps("ts", fontSize=9,
                  textColor=MUTED, alignment=TA_RIGHT)),
    ]]
    t = Table(header_data, colWidths=[W*0.6, W*0.4])
    t.setStyle(TableStyle([
        ("VALIGN",    (0,0), (-1,-1), "MIDDLE"),
        ("LINEBELOW", (0,0), (-1,0),  1, BLUE),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    gap(8)

    story.append(Paragraph(f"Drug Repurposing Analysis", S_SUB))
    story.append(Paragraph(f"{disease.upper()}", S_TITLE))
    gap(4)

    # Patient profile summary
    patient_parts = []
    if query.get("patient_age"):
        patient_parts.append(f"Age: {query['patient_age']}")
    if query.get("avoid_liver_toxicity"):
        patient_parts.append("Avoid liver toxicity")
    if query.get("avoid_cardiac_risk"):
        patient_parts.append("Avoid cardiac risk")
    if query.get("avoid_immunosuppression"):
        patient_parts.append("Avoid immunosuppression")
    if query.get("custom_avoid"):
        patient_parts.append(f"Custom avoid: {', '.join(query['custom_avoid'])}")

    if patient_parts:
        story.append(Paragraph(
            f"<b>Patient constraints:</b> {' · '.join(patient_parts)}", S_BODY))
        gap(4)

    hr(BLUE, 2)
    gap(8)

    # ── Mechanism Section ─────────────────────────────────────
    story.append(Paragraph("AI Mechanism Extraction", S_H2))
    gap(4)

    mech_data = [
        ["Field", "Value"],
        ["Mechanism",       results.get("inferred_mechanism", "—")],
        ["Disrupted Pathway", results.get("disrupted_pathway", "—")],
        ["Pathway Status",  results.get("pathway_status", "—")],
        ["Required Action", results.get("required_action", "—")],
        ["Confidence",      f"{results.get('mechanism_confidence', 0)}%"],
        ["Data Source",     results.get("abstract_source", "—")],
    ]
    mt = Table(mech_data, colWidths=[W*0.32, W*0.68])
    mt.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0),  BLUE),
        ("TEXTCOLOR",   (0,0), (-1,0),  WHITE),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("BACKGROUND",  (0,1), (-1,-1), LIGHT_BG),
        ("BACKGROUND",  (0,2), (-1,2),  WHITE),
        ("BACKGROUND",  (0,4), (-1,4),  WHITE),
        ("BACKGROUND",  (0,6), (-1,6),  WHITE),
        ("GRID",        (0,0), (-1,-1), 0.5, MID_GREY),
        ("FONTNAME",    (0,1), (0,-1),  "Helvetica-Bold"),
        ("TEXTCOLOR",   (0,1), (0,-1),  MUTED),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("PADDING",     (0,0), (-1,-1), 6),
    ]))
    story.append(mt)
    gap(6)

    quote = results.get("evidence_quote", "")
    if quote:
        story.append(Paragraph(f'"{_html.escape(quote)}"', S_ITALIC))
    gap(8)

    # ── Safety Summary ────────────────────────────────────────
    summary = results.get("safety_summary", {})
    n_g = summary.get("GREEN", 0)
    n_y = summary.get("YELLOW", 0)
    n_r = summary.get("RED", 0)
    n_t = summary.get("total", 0)

    hr(LBLUE)
    gap(4)
    story.append(Paragraph("Safety Summary", S_H2))
    gap(4)

    sum_data = [[
        Paragraph(f"<b>{n_t}</b><br/>Total Candidates",
                  ps("sc", fontName="Helvetica-Bold", fontSize=14,
                     alignment=TA_CENTER, textColor=DARK_TEXT)),
        Paragraph(f"<b>{n_g}</b><br/>GREEN",
                  ps("sg", fontName="Helvetica-Bold", fontSize=14,
                     alignment=TA_CENTER, textColor=GREEN_C)),
        Paragraph(f"<b>{n_y}</b><br/>YELLOW",
                  ps("sy", fontName="Helvetica-Bold", fontSize=14,
                     alignment=TA_CENTER, textColor=AMBER_C)),
        Paragraph(f"<b>{n_r}</b><br/>RED",
                  ps("sr", fontName="Helvetica-Bold", fontSize=14,
                     alignment=TA_CENTER, textColor=RED_C)),
    ]]
    st_tbl = Table(sum_data, colWidths=[W/4]*4)
    st_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (0,0),  LIGHT_BG),
        ("BACKGROUND",  (1,0), (1,0),  colors.HexColor("#E8FFF0")),
        ("BACKGROUND",  (2,0), (2,0),  colors.HexColor("#FFFDE8")),
        ("BACKGROUND",  (3,0), (3,0),  colors.HexColor("#FFF0F0")),
        ("BOX",         (0,0), (-1,-1), 1, MID_GREY),
        ("INNERGRID",   (0,0), (-1,-1), 0.5, MID_GREY),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("PADDING",     (0,0), (-1,-1), 10),
    ]))
    story.append(st_tbl)
    gap(10)

    # ── Drug Candidates ───────────────────────────────────────
    hr(LBLUE)
    gap(4)
    story.append(Paragraph("Ranked Drug Candidates", S_H2))
    gap(6)

    tl_colors = {"GREEN": GREEN_C, "YELLOW": AMBER_C, "RED": RED_C}
    tl_bg     = {
        "GREEN":  colors.HexColor("#E8FFF0"),
        "YELLOW": colors.HexColor("#FFFDE8"),
        "RED":    colors.HexColor("#FFF0F0"),
    }

    ranked = results.get("ranked_drugs", [])
    for drug in ranked:
        tl      = drug.get("traffic_light", "YELLOW")
        tl_col  = tl_colors.get(tl, AMBER_C)
        tl_bg_c = tl_bg.get(tl, colors.HexColor("#FFFDE8"))
        safety  = drug.get("safety", {})

        # Drug header row
        drug_header = [[
            Paragraph(
                f"<b>#{drug.get('rank',0):02d}  {_html.escape(drug.get('drug_name',''))}</b>",
                ps("dh", fontName="Helvetica-Bold", fontSize=12,
                   textColor=DARK_TEXT)),
            Paragraph(
                f"<b>{tl}</b>",
                ps("tl", fontName="Helvetica-Bold", fontSize=11,
                   textColor=tl_col, alignment=TA_CENTER)),
            Paragraph(
                f"<b>{drug.get('confidence_score', 0)}%</b><br/>confidence",
                ps("conf", fontName="Helvetica-Bold", fontSize=11,
                   alignment=TA_CENTER,
                   textColor=tl_col)),
        ]]
        dh_tbl = Table(drug_header, colWidths=[W*0.55, W*0.2, W*0.25])
        dh_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,0), tl_bg_c),
            ("LINEABOVE",    (0,0), (-1,0), 2, tl_col),
            ("BOX",          (0,0), (-1,-1), 0.5, tl_col),
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("PADDING",      (0,0), (-1,-1), 8),
            ("INNERGRID",    (0,0), (-1,-1), 0.5, MID_GREY),
        ]))
        story.append(dh_tbl)

        # Drug detail rows
        detail_rows = [
            ["Class / Pathway",
             f"{_html.escape(drug.get('drug_class',''))}  ·  {_html.escape(drug.get('target_pathway',''))}"],
            ["Approval",
             _html.escape(drug.get("approval_status", ""))],
            ["Mechanism",
             _html.escape(drug.get("pathway_action", ""))],
            ["Evidence PMIDs",
             "  ".join(drug.get("evidence_links", []))],
        ]

        # Safety flags
        flags = drug.get("patient_flags", [])
        if flags:
            detail_rows.append(["Patient Flags",
                                 "  |  ".join(_html.escape(str(f)) for f in flags)])

        # Direction warning
        if drug.get("direction_flag") in ["BLOCKED", "MISMATCH"]:
            detail_rows.append(["⚠ Direction",
                                 _html.escape(drug.get("match_reason", "")[:120])])

        # Black box
        bbw = safety.get("black_box_warning", "")
        if bbw and bbw not in ["None.", "None", ""]:
            detail_rows.append(["FDA Black Box", _html.escape(bbw[:200])])

        d_tbl_data = [
            [Paragraph(row[0], ps("lbl", fontName="Helvetica-Bold",
                                   fontSize=8, textColor=MUTED)),
             Paragraph(row[1], ps("val", fontSize=9, textColor=DARK_TEXT,
                                   leading=13))]
            for row in detail_rows
        ]
        d_tbl = Table(d_tbl_data, colWidths=[W*0.22, W*0.78])
        d_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,-1), WHITE),
            ("BACKGROUND",   (0,0), (0,-1),  LIGHT_BG),
            ("BOX",          (0,0), (-1,-1), 0.5, MID_GREY),
            ("INNERGRID",    (0,0), (-1,-1), 0.3, colors.HexColor("#DEE8F0")),
            ("VALIGN",       (0,0), (-1,-1), "TOP"),
            ("PADDING",      (0,0), (-1,-1), 5),
        ]))
        story.append(d_tbl)
        gap(8)

    # ── Biological Cousins ────────────────────────────────────
    cousins = results.get("biological_cousins")
    if cousins and cousins.get("matched_known_diseases"):
        hr(LBLUE)
        gap(4)
        story.append(Paragraph("Biological Cousins", S_H2))
        gap(4)
        story.append(Paragraph(
            f"<b>Top match:</b> {_html.escape(str(cousins.get('top_match', 'None')))}",
            S_BODY))
        related = cousins.get("matched_known_diseases", [])
        if isinstance(related, list) and related:
            items = related if isinstance(related[0], str) else \
                    [d.get("disease_name","") for d in related]
            story.append(Paragraph(
                f"<b>Related diseases:</b> {', '.join(_html.escape(i) for i in items if i)}",
                S_BODY))
        gap(8)

    # ── Disclaimer ────────────────────────────────────────────
    hr(MID_GREY, 1)
    gap(6)
    disclaimer = (
        "<b>DISCLAIMER:</b> This report is generated by RareMatch, an AI-assisted "
        "research tool for rare disease drug repurposing. It is intended solely for "
        "research and educational purposes. All drug candidates require physician "
        "review, clinical judgement, and appropriate regulatory approvals before "
        "clinical use. RareMatch does not provide medical advice."
    )
    story.append(Paragraph(disclaimer, S_SMALL))
    gap(4)
    story.append(Paragraph(
        "RareMatch · AI reads · Python decides · Safety gates everything",
        S_CENTER))

    doc.build(story)
    return buf.getvalue()


# ── Session State Init ─────────────────────────────────────────
if "results"    not in st.session_state: st.session_state["results"]    = None
if "deep_drug"  not in st.session_state: st.session_state["deep_drug"]  = None
if "api_error"  not in st.session_state: st.session_state["api_error"]  = None
if "last_query" not in st.session_state: st.session_state["last_query"] = ""
if "last_query_payload" not in st.session_state: st.session_state["last_query_payload"] = {}


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
                {_html.escape(str(drug["evidence_summary"]))}
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
                f'<div class="rm-flag">{_html.escape(str(flag))}</div>'
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

    disease_name_clean = str(disease_input or "").strip()
    payload = {
        "disease_name":            disease_name_clean,
        "patient_age":             int(patient_age) if patient_age else None,
        "avoid_liver_toxicity":    avoid_liver,
        "avoid_cardiac_risk":      avoid_cardiac,
        "avoid_immunosuppression": avoid_immuno,
        "custom_avoid":            custom_avoid,
    }
    st.session_state["last_query_payload"] = payload

    with st.spinner(f"Analyzing {disease_name_clean}..."):
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

    # ── Safety Trap Banner ─────────────────────────────────────
    ranked_drugs = results.get("ranked_drugs", [])
    trapped_drugs = [
        d for d in ranked_drugs
        if d.get("confidence_score") == 0 or d.get("direction_flag") == "BLOCKED"
    ]
    if trapped_drugs:
        trap_items = ""
        for d in trapped_drugs:
            dname   = _html.escape(d.get("drug_name", ""))
            reason  = _html.escape(d.get("match_reason", "")[:200])
            trap_items += (
                '<div style="display:flex;align-items:flex-start;gap:10px;'
                'margin-top:10px;padding-top:10px;'
                'border-top:1px solid rgba(244,67,54,0.2);">'
                '<span style="font-size:18px;">&#9940;</span>'
                '<div>'
                f'<div style="font-family:monospace;font-size:12px;font-weight:700;'
                f'color:#FF5252;letter-spacing:0.5px;">{dname} — CONTRAINDICATED</div>'
                f'<div style="font-size:11px;color:#FF8A80;margin-top:4px;line-height:1.6;">'
                f'{reason}</div>'
                '<div style="font-size:10px;color:#B71C1C;margin-top:6px;font-family:monospace;">'
                'This drug is included intentionally as a safety reference. '
                'A physician must NEVER prescribe a BLOCKED drug for this mechanism.'
                '</div></div></div>'
            )
        st.html(
            '<div style="background:rgba(183,28,28,0.08);border:2px solid #F44336;'
            'border-radius:8px;padding:16px 20px;margin:12px 0;">'
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
            '<span style="font-size:22px;">&#128680;</span>'
            '<div>'
            '<div style="font-family:monospace;font-size:13px;font-weight:700;'
            'color:#F44336;letter-spacing:1px;">SAFETY TRAP TRIGGERED</div>'
            f'<div style="font-size:11px;color:#FF8A80;margin-top:2px;">'
            f'{len(trapped_drugs)} drug(s) detected that are contraindicated '
            f'for this disease mechanism. They appear RED below.</div>'
            '</div></div>'
            + trap_items +
            '</div>'
        )

    # ── PDF Download Button ────────────────────────────────────
    pdf_col, spacer_col = st.columns([2, 5])
    with pdf_col:
        try:
            query_payload = st.session_state.get("last_query_payload", {})
            pdf_bytes = generate_pdf_report(results, query_payload)
            fname = f"RareMatch_{results.get('disease_name','report').replace(' ','_')}.pdf"
            st.download_button(
                label="📄  Download PDF Report",
                data=pdf_bytes,
                file_name=fname,
                mime="application/pdf",
                use_container_width=True,
                help="Download a full clinical-style PDF report of these results",
            )
        except Exception as e:
            st.caption(f"PDF unavailable: {e}")

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
                ⚠ DIRECTION {drug["direction_flag"]} — {drug["match_reason"][:120].replace(chr(0x2014), "&mdash;").replace(chr(0x2013), "&ndash;")}...
            </div>"""



        col_card, col_btn = st.columns([10, 1])

        with col_card:
            # Build pathway_action safely - no escaping needed, st.html renders direct
            pathway_txt = drug["pathway_action"][:180].replace('\u2014', '&mdash;').replace('\u2013', '&ndash;') + ('...' if len(drug["pathway_action"]) > 180 else '')
            approval_txt = drug["approval_status"][:60] + ('...' if len(drug["approval_status"]) > 60 else '')
            pmids_txt = "  ".join(drug.get("evidence_links", [])[:3])
            rank_txt  = f'#{drug["rank"]:02d}'
            tl_html   = traffic_html(tl)

            # Patient flags — inline styles (st.html sandboxes CSS classes)
            flags_html = ""
            if drug.get("patient_flags"):
                flags_html = "".join(
                    f'<div style="background:rgba(255,82,82,0.08);border:1px solid rgba(255,82,82,0.2);'
                    f'border-radius:3px;padding:6px 12px;font-size:11px;color:#ff5252;'
                    f'font-family:IBM Plex Mono,monospace;margin-top:8px;">{str(flag)}</div>'
                    for flag in drug["patient_flags"][:2]
                )

            st.html(f"""
            <div class="rm-card {tl_cls}">
                <div class="rm-card-header">
                    <div style="display:flex; align-items:flex-start;">
                        <span class="rm-card-rank">{rank_txt}</span>
                        <div>
                            <div class="rm-card-name">{drug["drug_name"]}</div>
                            <div class="rm-card-class">
                                {drug["drug_class"]} &nbsp;&middot;&nbsp; {drug["target_pathway"]}
                                &nbsp;&middot;&nbsp; {approval_txt}
                            </div>
                        </div>
                    </div>
                    <div style="text-align:right; margin-left:16px;">
                        {tl_html}
                        <div class="rm-confidence" style="color:{c_color};">{drug["confidence_score"]}%</div>
                        <div class="rm-confidence-label">confidence</div>
                    </div>
                </div>
                <div style="font-size:12px; color:#6a8aaa; line-height:1.6; margin-bottom:8px;">
                    {pathway_txt}
                </div>
                <div style="font-size:11px; color:#2a3f5f; font-family:IBM Plex Mono,monospace;">
                    {pmids_txt}
                </div>
                {direction_warning}
                {flags_html}
            </div>
            """)

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