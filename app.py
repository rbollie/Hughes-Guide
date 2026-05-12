"""
Hughes Guide — PMO decision-support workbench.

Features:
  • Decision-tree wizards (schedule templates, change requests)
  • Reviewer routing with capacity-aware auto-assignment
  • Document pre-screening via Anthropic API
  • Gantt-style Timeline with SLA breach indicators
  • SLA tracking (business-day and calendar-day aware)
  • Supabase or SQLite backend (auto-detected)
  • Role-based authentication: admin, lead, submitter, viewer
  • Custom landing page
"""

import os
import re
import json
import base64
import sqlite3
import secrets as py_secrets
from datetime import datetime, timedelta, timezone

import streamlit as st
import pandas as pd

# Optional/lazy imports
try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False
try:
    import plotly.express as px
    _PLOTLY_AVAILABLE = True
except ImportError:
    _PLOTLY_AVAILABLE = False
try:
    from supabase import create_client as _supabase_create_client
    _SUPABASE_AVAILABLE = True
except ImportError:
    _SUPABASE_AVAILABLE = False
try:
    import bcrypt
    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Hughes Guide",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="auto",
)

# ============================================================================
# CSS — editorial palette + landing page styles
# ============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Manrope:wght@400;500;600;700&display=swap');

:root {
    --ink: #1A1A1A; --cream: #FAF7F2; --card: #FDFBF6;
    --border: #E5DDC9; --border-strong: #D4CCB9;
    --muted: #5A5A5A; --rust: #A0432C; --rust-soft: #F2E5DE; --moss: #6B7A4F;
}
html, body, [class*="css"], .stApp, .stMarkdown, p, div, label,
.stSelectbox, .stRadio, .stTextInput, .stTextArea, .stButton, .stDownloadButton {
    font-family: 'Manrope', system-ui, sans-serif !important;
}
/* Preserve Material Icons / Symbols fonts — Streamlit uses these for chevrons, upload, close, etc. */
.material-symbols-rounded, .material-symbols-outlined, .material-icons,
[class*="material-symbols"], [class*="material-icons"],
[data-testid*="Icon"], [data-testid*="icon"],
span[aria-hidden="true"][class*="st-emotion"] {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
}
.display, h1.display, h2.display, h3.display {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-weight: 400; color: var(--ink); line-height: 1.15;
}
.eyebrow { font-size: 10px; text-transform: uppercase; letter-spacing: 0.2em;
           color: var(--rust); margin-bottom: 4px; }
.label   { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;
           color: var(--muted); margin-bottom: 4px; font-weight: 500; }
.pill { display: inline-block; padding: 2px 8px; font-size: 10px;
        text-transform: uppercase; letter-spacing: 0.05em; border-radius: 2px;
        background: #E8E2D5; color: #3A3A3A; margin-right: 4px; margin-bottom: 4px; }
.pill.rust { background: var(--rust-soft); color: var(--rust); }
.pill.ink  { background: var(--ink); color: var(--cream); }
.pill.moss { background: #E0E5DA; color: #4A5A3A; }
.pill.warn { background: #F5E6CC; color: #8a5a1a; }
.pill.danger { background: #F2D9D2; color: #8a2515; font-weight: 600; }
.card { background: var(--card); border: 1px solid var(--border);
        border-radius: 3px; padding: 16px 20px; margin-bottom: 12px; }
.stat-card { background: var(--card); border: 1px solid var(--border);
             border-radius: 3px; padding: 14px; }
.stat-card.accent { background: var(--rust-soft); border-color: var(--rust); }
.stat-card.danger { background: #F2D9D2; border-color: #8a2515; }
.stat-value { font-family: 'Instrument Serif', Georgia, serif; font-size: 36px;
              line-height: 1; color: var(--ink); }
.stat-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em;
              color: var(--muted); margin-bottom: 4px; }
.risk-bar { height: 4px; background: var(--border); border-radius: 2px;
            overflow: hidden; margin: 6px 0; }
.risk-fill { height: 100%; }
[data-testid="stSidebar"] { background: var(--card) !important; border-right: 1px solid var(--border); }
[data-testid="stSidebar"] .display { font-size: 22px; }

/* Force light theme everywhere — overrides Streamlit dark mode if user/system has it on */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main, .block-container {
    background-color: var(--cream) !important;
    color: var(--ink) !important;
}
[data-testid="stHeader"] { background-color: var(--cream) !important; }
[data-testid="stSidebar"] *, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] .stRadio label, [data-testid="stSidebar"] [data-baseweb="radio"] label {
    color: var(--ink) !important;
}
.stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp span:not(.pill):not(.role-pill):not(.backend-badge) {
    color: var(--ink);
}
/* Form inputs — light background, ink text */
.stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"],
.stNumberInput input, .stPassword input {
    background-color: var(--card) !important;
    color: var(--ink) !important;
}
/* Expander headers */
[data-testid="stExpander"] summary { color: var(--ink) !important; }

/* File uploader — fix dark default styling that didn't match cream theme */
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {
    background-color: var(--card) !important;
    border: 1px dashed var(--border-strong) !important;
    color: var(--ink) !important;
}
[data-testid="stFileUploader"] section *,
[data-testid="stFileUploaderDropzone"] * { color: var(--ink) !important; }
[data-testid="stFileUploader"] section button {
    background-color: var(--rust) !important;
    color: var(--cream) !important;
    border: none !important;
}
[data-testid="stFileUploader"] section button * { color: var(--cream) !important; }
[data-testid="stFileUploader"] section small { color: var(--muted) !important; }

/* Tooltips and help icons */
[data-testid="stTooltipIcon"] { color: var(--muted) !important; }
.stButton button, .stFormSubmitButton button,
button[kind="primary"], button[kind="primaryFormSubmit"] {
    background: var(--rust) !important;
    color: var(--cream) !important;
    border: none !important;
    border-radius: 2px !important;
    font-weight: 500 !important;
    transition: background 0.15s;
}
.stButton button *, .stFormSubmitButton button *,
button[kind="primary"] *, button[kind="primaryFormSubmit"] * {
    color: var(--cream) !important;
}
.stButton button:hover, .stFormSubmitButton button:hover,
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
    background: #8a3a25 !important;
    color: var(--cream) !important;
}

/* Secondary buttons — outlined, ink text on cream */
.stButton button[kind="secondary"], .stFormSubmitButton button[kind="secondaryFormSubmit"],
button[kind="secondary"], button[kind="secondaryFormSubmit"] {
    background: transparent !important;
    color: var(--ink) !important;
    border: 1px solid var(--border-strong) !important;
}
.stButton button[kind="secondary"] *, .stFormSubmitButton button[kind="secondaryFormSubmit"] *,
button[kind="secondary"] *, button[kind="secondaryFormSubmit"] * {
    color: var(--ink) !important;
}
.stButton button[kind="secondary"]:hover, .stFormSubmitButton button[kind="secondaryFormSubmit"]:hover,
button[kind="secondary"]:hover, button[kind="secondaryFormSubmit"]:hover {
    background: #E8E2D5 !important;
    color: var(--ink) !important;
}

/* Fix browser autofill colour — was rendering olive/yellow */
input:-webkit-autofill, input:-webkit-autofill:hover, input:-webkit-autofill:focus,
input:-webkit-autofill:active, textarea:-webkit-autofill, select:-webkit-autofill {
    -webkit-box-shadow: 0 0 0 30px var(--card) inset !important;
    -webkit-text-fill-color: var(--ink) !important;
    caret-color: var(--ink) !important;
    transition: background-color 5000s ease-in-out 0s;
}

.stDownloadButton button { background: transparent; color: var(--ink);
                           border: 1px solid var(--border-strong); border-radius: 2px; }
hr { border-color: var(--border); }
.backend-badge { display: inline-block; font-size: 9px; text-transform: uppercase;
                 letter-spacing: 0.15em; padding: 2px 6px; border-radius: 2px;
                 background: #E0E5DA; color: #4A5A3A; }
.backend-badge.local { background: #F5E6CC; color: #8a5a1a; }
.role-pill { display: inline-block; font-size: 9px; text-transform: uppercase;
             letter-spacing: 0.15em; padding: 2px 6px; border-radius: 2px;
             margin-left: 4px; font-weight: 600; }
.role-pill.admin { background: var(--ink); color: var(--cream); }
.role-pill.lead { background: var(--rust-soft); color: var(--rust); }
.role-pill.submitter { background: #E0E5DA; color: #4A5A3A; }
.role-pill.viewer { background: #E8E2D5; color: #5A5A5A; }

/* Streamlit chrome cleanup */
footer { visibility: hidden; height: 0; }
#MainMenu { visibility: hidden; }

/* ===== Landing page ===== */
.landing-wrap { max-width: 1100px; margin: 0 auto; padding: 24px 24px 80px; }
.landing-nav { display: flex; justify-content: space-between; align-items: center;
               padding: 24px 0 60px; border-bottom: 1px solid var(--border); margin-bottom: 0; }
.landing-brand { display: flex; align-items: center; gap: 14px; }
.landing-brand-mark { width: 32px; height: 32px; background: var(--ink); border-radius: 3px;
                      display: flex; align-items: center; justify-content: center; color: var(--cream);
                      font-family: 'Instrument Serif', serif; font-size: 18px; font-style: italic; }
.landing-brand-text { font-family: 'Instrument Serif', serif; font-size: 24px; line-height: 1; }
.landing-brand-sub { font-size: 9px; text-transform: uppercase; letter-spacing: 0.25em;
                     color: var(--muted); margin-top: 3px; }

.landing-hero { padding: 80px 0 100px; display: grid; grid-template-columns: 1.4fr 1fr;
                gap: 80px; align-items: center; }
.landing-hero-title { font-family: 'Instrument Serif', serif; font-size: 78px;
                      line-height: 0.95; margin: 18px 0 28px; color: var(--ink); font-weight: 400; }
.landing-hero-title em { color: var(--rust); font-style: italic; }
.landing-hero-sub { font-size: 17px; line-height: 1.6; color: var(--muted); max-width: 480px;
                    margin-bottom: 0; }

.landing-visual { padding: 24px; }
.landing-visual-track { position: relative; padding: 24px 0; }
.landing-visual-stage { display: flex; align-items: center; gap: 16px; margin-bottom: 22px;
                         opacity: 0.5; transition: opacity 0.3s; }
.landing-visual-stage.active { opacity: 1; }
.landing-visual-dot { width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0;
                       background: var(--border-strong); }
.landing-visual-stage.done .landing-visual-dot { background: var(--moss); }
.landing-visual-stage.active .landing-visual-dot { background: var(--rust);
                                                    box-shadow: 0 0 0 4px var(--rust-soft); }
.landing-visual-label { font-family: 'Instrument Serif', serif; font-size: 22px; color: var(--ink); }
.landing-visual-meta { font-size: 11px; color: var(--muted); margin-left: 8px;
                        text-transform: uppercase; letter-spacing: 0.1em; }

.landing-features { padding: 60px 0 40px; border-top: 1px solid var(--border);
                    display: grid; grid-template-columns: repeat(3, 1fr); gap: 40px; }
.landing-feature h3 { font-family: 'Instrument Serif', serif; font-size: 32px;
                       margin: 0 0 12px; color: var(--ink); }
.landing-feature p  { font-size: 14px; color: var(--muted); line-height: 1.6; margin: 0; }
.landing-feature .feature-num { font-family: 'Instrument Serif', serif; font-style: italic;
                                  color: var(--rust); font-size: 14px; }
.landing-feature .feature-icon { color: var(--rust); margin-bottom: 16px;
                                  display: inline-flex; align-items: center; justify-content: center;
                                  width: 56px; height: 56px; border-radius: 50%;
                                  background: var(--rust-soft); }

.landing-closing { padding: 80px 0 40px; border-top: 1px solid var(--border); }
.landing-closing-title { font-family: 'Instrument Serif', serif; font-size: 42px; line-height: 1.1;
                          color: var(--ink); margin: 0 0 16px; max-width: 700px; }
.landing-closing-title em { font-style: italic; color: var(--rust); }
.landing-closing-body { font-size: 15px; color: var(--muted); line-height: 1.6; max-width: 580px; }

.landing-footer { padding: 40px 0 0; border-top: 1px solid var(--border); margin-top: 60px;
                   font-size: 10px; text-transform: uppercase; letter-spacing: 0.2em;
                   color: #A89E85; }

@media (max-width: 900px) {
    .landing-hero { grid-template-columns: 1fr; gap: 40px; padding: 40px 0 60px; }
    .landing-hero-title { font-size: 52px; }
    .landing-features { grid-template-columns: 1fr; gap: 32px; padding: 40px 0; }
    .landing-closing-title { font-size: 30px; }
}

/* Login card */
.login-card-wrap { max-width: 440px; margin: 80px auto; padding: 0 24px; }
.login-card { background: var(--card); border: 1px solid var(--border);
              border-radius: 4px; padding: 44px 36px; }
.login-title { font-family: 'Instrument Serif', serif; font-size: 38px; margin: 8px 0 6px; }
.login-sub { font-size: 13px; color: var(--muted); margin-bottom: 24px; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DEFAULTS
# ============================================================================

DEFAULT_FEATURES = {
    "documentAnalysis": True, "riskScoring": True, "autoAssignment": True,
    "csvExport": True, "workExport": True, "slaTracking": True,
    "timelineView": True, "emailNotifications": False,
}
DEFAULT_WORKFLOWS = [
    {"id": "fast", "name": "Fast-Track", "stages": ["draft", "final_qa"]},
    {"id": "standard", "name": "Standard", "stages": ["draft", "lead_review", "final_qa"]},
    {"id": "extended", "name": "Extended", "stages": ["draft", "peer_review", "lead_review", "final_qa"]},
]
STAGE_LABELS = {"draft": "Draft", "peer_review": "Peer Review", "lead_review": "Team Lead Review",
                "final_qa": "Final QA / QC", "approved": "Approved", "returned": "Returned"}
STAGE_COLORS = {"Draft": "#D4CCB9", "Peer Review": "#C58A30", "Team Lead Review": "#A0432C",
                "Final QA / QC": "#1A1A1A", "Approved": "#6B7A4F", "Returned": "#8a5a1a"}

DEFAULT_TEMPLATES = [
    {"id": "waterfall", "name": "Waterfall — Linear Phase-Gate",
     "description": "Sequential phases with formal gate reviews. Best for well-defined scope with regulatory or audit requirements.",
     "tags": ["infra", "long-duration", "regulated", "large-team", "fixed-scope"],
     "defaultWorkflow": "extended",
     "checkpoints": ["Requirements gate", "Design gate", "Build gate", "Test gate", "Deploy gate", "Closure review"],
     "sla": "15 business days", "riskBase": 3},
    {"id": "agile-sprint", "name": "Agile Sprint Schedule",
     "description": "Iterative 2-week sprints with retrospectives. Suits software work with evolving scope.",
     "tags": ["software", "medium-duration", "iterative", "small-team", "medium-team"],
     "defaultWorkflow": "standard",
     "checkpoints": ["Sprint planning", "Daily standup", "Sprint review", "Retrospective", "Backlog refinement"],
     "sla": "7 business days", "riskBase": 2},
    {"id": "rolling-wave", "name": "Rolling-Wave Planning",
     "description": "Detailed near-term planning, high-level long-term. For projects with downstream uncertainty.",
     "tags": ["research", "long-duration", "uncertain-scope", "medium-team"],
     "defaultWorkflow": "standard",
     "checkpoints": ["Initial baseline", "Wave 1 detail", "Wave 2 plan", "Periodic re-baselining"],
     "sla": "10 business days", "riskBase": 3},
    {"id": "short-turnaround", "name": "Short-Turnaround Schedule",
     "description": "Compressed schedule for sub-3-month efforts with a small team and clear scope.",
     "tags": ["software", "process", "short-duration", "small-team", "low-risk", "fixed-scope"],
     "defaultWorkflow": "fast",
     "checkpoints": ["Kickoff", "Midpoint review", "Pre-handover check", "Closeout"],
     "sla": "5 business days", "riskBase": 1},
    {"id": "program-master", "name": "Program Master Schedule",
     "description": "Multi-project coordination with cross-stream dependencies and integrated milestones.",
     "tags": ["infra", "software", "long-duration", "large-team", "high-dependency"],
     "defaultWorkflow": "extended",
     "checkpoints": ["Program charter", "Stream integration points", "Quarterly stage gates", "Benefits realization"],
     "sla": "20 business days", "riskBase": 4},
]

DEFAULT_CHANGE_TYPES = [
    {"id": "standard", "name": "Standard Change",
     "description": "Pre-approved, low-risk, follows established procedure with predictable outcome.",
     "conditions": ["routine", "low", "team", "easy", "yes"], "defaultWorkflow": "fast",
     "requiredApprovals": ["Team Lead"], "sla": "5 business days", "riskBase": 1},
    {"id": "normal", "name": "Normal Change",
     "description": "Non-emergency change requiring CAB review and full risk assessment.",
     "conditions": ["routine", "medium", "multi-team", "moderate", "no"], "defaultWorkflow": "standard",
     "requiredApprovals": ["Team Lead", "Change Manager"], "sla": "10 business days", "riskBase": 3},
    {"id": "major", "name": "Major Change",
     "description": "High-impact change affecting multiple systems or org-wide processes.",
     "conditions": ["expedited", "high", "org", "hard", "no"], "defaultWorkflow": "extended",
     "requiredApprovals": ["Team Lead", "Change Manager", "Executive Sponsor"],
     "sla": "20 business days", "riskBase": 4},
    {"id": "emergency", "name": "Emergency Change",
     "description": "Urgent change to restore service or prevent imminent harm.",
     "conditions": ["emergency", "high"], "defaultWorkflow": "standard",
     "requiredApprovals": ["On-call Lead", "Change Manager"],
     "sla": "Same business day", "riskBase": 5},
]

SCHEDULE_QUESTIONS = [
    {"id": "type", "q": "What is the primary project type?", "options": [
        ("infra", "Infrastructure / Engineering / Construction"),
        ("software", "Software / Digital product"),
        ("process", "Process / Operational change"),
        ("research", "Research / Discovery / R&D")]},
    {"id": "duration", "q": "Expected duration?", "options": [
        ("short-duration", "Under 3 months"),
        ("medium-duration", "3 to 12 months"),
        ("long-duration", "Over 12 months")]},
    {"id": "team", "q": "Team size?", "options": [
        ("small-team", "Fewer than 5 people"),
        ("medium-team", "5 to 15 people"),
        ("large-team", "More than 15 people")]},
    {"id": "scope", "q": "How well-defined is the scope?", "options": [
        ("fixed-scope", "Clearly defined, low likelihood of change"),
        ("iterative", "Will evolve as we learn"),
        ("uncertain-scope", "Significant downstream uncertainty")]},
    {"id": "compliance", "q": "Regulatory or audit requirements?", "options": [
        ("low-risk", "None or minimal"),
        ("regulated", "Yes — formal compliance needed")]},
    {"id": "deps", "q": "Cross-team dependencies?", "options": [
        ("low-dependency", "Few — mostly self-contained"),
        ("high-dependency", "Many — multiple streams must align")]},
]
CHANGE_QUESTIONS = [
    {"id": "urgency", "q": "How urgent is this change?", "options": [
        ("routine", "Routine — normal lead time available"),
        ("expedited", "Expedited — needed sooner than standard"),
        ("emergency", "Emergency — service restoration or imminent harm")]},
    {"id": "risk", "q": "Assessed risk level?", "options": [
        ("low", "Low — predictable, proven, isolated"),
        ("medium", "Medium — some unknowns, partial precedent"),
        ("high", "High — novel, broad blast radius, or limited testing")]},
    {"id": "scope", "q": "Impact scope?", "options": [
        ("team", "Single team only"), ("multi-team", "Multiple teams"),
        ("org", "Organisation-wide")]},
    {"id": "reversibility", "q": "How reversible if something goes wrong?", "options": [
        ("easy", "Easy — rollback is trivial"),
        ("moderate", "Moderate — rollback possible but costly"),
        ("hard", "Difficult or irreversible")]},
    {"id": "precedent", "q": "Has a similar change been done before?", "options": [
        ("yes", "Yes — pre-approved or repeatable"),
        ("no", "No — novel change")]},
]
DEFAULT_REVIEWERS = [
    {"id": "r1", "name": "Aisha Okonkwo", "role": "Team Lead",
     "expertise": ["software", "iterative", "medium-team"], "capacity": 4},
    {"id": "r2", "name": "Daniel Reyes", "role": "Team Lead",
     "expertise": ["infra", "regulated", "large-team", "fixed-scope"], "capacity": 4},
    {"id": "r3", "name": "Priya Shankar", "role": "Team Lead",
     "expertise": ["process", "research", "small-team", "uncertain-scope"], "capacity": 3},
]

HIGH_RISK_TAGS = {"high", "emergency", "org", "hard", "uncertain-scope", "regulated",
                  "high-dependency", "large-team", "long-duration", "no"}
MEDIUM_RISK_TAGS = {"medium", "expedited", "multi-team", "moderate", "iterative",
                    "medium-team", "medium-duration"}

ROLE_LABELS = {"admin": "Administrator", "lead": "Team Lead",
               "submitter": "Submitter", "viewer": "Viewer"}
ROLE_PERMS = {
    "admin": {"submit", "view_all", "review_peer", "review_lead", "final_qa",
              "return", "reopen", "manage_users", "manage_templates",
              "manage_settings", "export", "analyze_docs"},
    "lead":  {"submit", "view_all", "review_peer", "review_lead",
              "return", "export", "analyze_docs"},
    "submitter": {"submit", "view_own", "analyze_docs"},
    "viewer": {"view_all"},
}

# ============================================================================
# STORAGE
# ============================================================================
DB_PATH = "hughes_guide.db"
SUPABASE_TABLE = "hughes_guide_kv"

def _get_secret(key):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key)

@st.cache_resource(show_spinner=False)
def get_supabase_client():
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_KEY")
    if not url or not key or not _SUPABASE_AVAILABLE:
        return None
    try:
        return _supabase_create_client(url, key)
    except Exception as e:
        st.warning(f"Supabase init failed: {e}. Using local SQLite.")
        return None

@st.cache_resource(show_spinner=False)
def get_sqlite_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn

def get_backend():
    return "supabase" if get_supabase_client() is not None else "sqlite"

def kv_get(key, default):
    client = get_supabase_client()
    if client is not None:
        try:
            res = client.table(SUPABASE_TABLE).select("value").eq("key", key).execute()
            if res.data and len(res.data) > 0:
                v = res.data[0]["value"]
                return v if v is not None else default
            return default
        except Exception as e:
            st.error(f"Supabase read error ({key}): {e}")
            return default
    conn = get_sqlite_conn()
    row = conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
    return json.loads(row[0]) if row else default

def kv_set(key, value):
    client = get_supabase_client()
    if client is not None:
        try:
            client.table(SUPABASE_TABLE).upsert({"key": key, "value": value}).execute()
            return
        except Exception as e:
            st.error(f"Supabase write error ({key}): {e}")
            return
    conn = get_sqlite_conn()
    conn.execute("INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
                 (key, json.dumps(value)))
    conn.commit()

def load_all_state():
    mapping = {
        "features": DEFAULT_FEATURES, "workflows": DEFAULT_WORKFLOWS,
        "templates": DEFAULT_TEMPLATES, "change_types": DEFAULT_CHANGE_TYPES,
        "reviewers": DEFAULT_REVIEWERS, "submissions": [], "users": [],
    }
    for k, default in mapping.items():
        if k not in st.session_state:
            st.session_state[k] = kv_get(k, default)
    for fk, fv in DEFAULT_FEATURES.items():
        if fk not in st.session_state.features:
            st.session_state.features[fk] = fv

def persist(key):
    kv_set(key, st.session_state[key])

# ============================================================================
# AUTHENTICATION
# ============================================================================

def hash_password(pw: str) -> str:
    if not _BCRYPT_AVAILABLE:
        raise RuntimeError("bcrypt not installed — add bcrypt>=4.1.0 to requirements.txt")
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

def verify_password(pw: str, hashed: str) -> bool:
    if not _BCRYPT_AVAILABLE:
        return False
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def find_user(username: str):
    return next((u for u in st.session_state.users
                 if u.get("username", "").lower() == username.lower()), None)

def login(username: str, password: str):
    user = find_user(username)
    if not user:
        return False, "Unknown username or password."
    if not user.get("active", True):
        return False, "Account is deactivated. Contact your administrator."
    if not verify_password(password, user.get("password_hash", "")):
        return False, "Unknown username or password."
    user["lastLogin"] = int(datetime.utcnow().timestamp() * 1000)
    persist("users")
    st.session_state.current_user = user
    st.session_state.auth_view = None
    return True, None

def logout():
    st.session_state.current_user = None
    st.session_state.auth_view = "landing"
    for k in list(st.session_state.keys()):
        if k.startswith(("wizard_", "detail_", "page")):
            del st.session_state[k]

def current_user():
    return st.session_state.get("current_user")

def is_authenticated():
    return current_user() is not None

def has_perm(action: str) -> bool:
    u = current_user()
    if not u:
        return False
    return action in ROLE_PERMS.get(u.get("role", "viewer"), set())

def is_admin():
    u = current_user()
    return u and u.get("role") == "admin"

def visible_items(items):
    """Filter items based on the current user's view scope."""
    u = current_user()
    if not u:
        return []
    if "view_all" in ROLE_PERMS.get(u.get("role", "viewer"), set()):
        return items
    if "view_own" in ROLE_PERMS.get(u.get("role", "viewer"), set()):
        return [i for i in items if i.get("submitterUserId") == u["id"]]
    return []

def create_user(username, password, name, role, active=True):
    if find_user(username):
        return False, "Username already exists."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.match(r"^[A-Za-z0-9_.-]{3,30}$", username):
        return False, "Username must be 3–30 chars, letters/digits/._-"
    if role not in ROLE_PERMS:
        return False, "Invalid role."
    user = {
        "id": f"user_{py_secrets.token_hex(6)}",
        "username": username, "name": name.strip() or username,
        "password_hash": hash_password(password),
        "role": role, "active": active,
        "createdAt": int(datetime.utcnow().timestamp() * 1000),
        "lastLogin": None,
    }
    st.session_state.users = [*st.session_state.users, user]
    persist("users")
    return True, user

def update_user(user_id, updates: dict):
    users = st.session_state.users
    for i, u in enumerate(users):
        if u["id"] == user_id:
            users[i] = {**u, **updates}
            st.session_state.users = users
            persist("users")
            return users[i]
    return None

def delete_user(user_id):
    me = current_user()
    if me and me["id"] == user_id:
        return False, "You can't delete your own account."
    users = st.session_state.users
    target = next((u for u in users if u["id"] == user_id), None)
    if not target:
        return False, "User not found."
    if target.get("role") == "admin":
        admins = [u for u in users if u.get("role") == "admin" and u["id"] != user_id and u.get("active", True)]
        if not admins:
            return False, "Can't delete the last active admin."
    st.session_state.users = [u for u in users if u["id"] != user_id]
    persist("users")
    return True, None

def needs_first_run():
    return not st.session_state.get("users")

# ============================================================================
# SLA UTILITIES
# ============================================================================
_BD_RE = re.compile(r"(\d+)\s*business\s*day", re.IGNORECASE)
_CD_RE = re.compile(r"(\d+)\s*day", re.IGNORECASE)
_SAME_DAY_RE = re.compile(r"same\s*(business\s*)?day", re.IGNORECASE)

def parse_sla(sla_string):
    if not sla_string or not isinstance(sla_string, str):
        return (None, None)
    s = sla_string.strip()
    if _SAME_DAY_RE.search(s):
        return (0, True)
    m = _BD_RE.search(s)
    if m:
        return (int(m.group(1)), True)
    m = _CD_RE.search(s)
    if m:
        return (int(m.group(1)), False)
    return (None, None)

def business_days_between(start_ts_ms, end_ts_ms):
    start = datetime.fromtimestamp(start_ts_ms / 1000, tz=timezone.utc).date()
    end = datetime.fromtimestamp(end_ts_ms / 1000, tz=timezone.utc).date()
    if end <= start: return 0
    days = 0; cur = start
    while cur < end:
        cur += timedelta(days=1)
        if cur.weekday() < 5: days += 1
    return days

def calendar_days_between(start_ts_ms, end_ts_ms):
    return max(0, int((end_ts_ms - start_ts_ms) // (1000 * 86400)))

def get_item_type_sla(item):
    pool = (st.session_state.templates if item["type"] == "schedule"
            else st.session_state.change_types)
    t = next((x for x in pool if x["id"] == item.get("typeId")), None)
    return t.get("sla") if t else None

def item_end_time_ms(item):
    if item.get("currentStage") in ("approved", "returned"):
        hist = item.get("history") or []
        if hist: return hist[-1]["at"]
        return item.get("createdAt", 0)
    return None

def sla_status(item):
    sla_str = get_item_type_sla(item)
    days_total, is_business = parse_sla(sla_str)
    if days_total is None:
        return {"state": "n/a", "label": "No SLA", "color": "#8A8A8A",
                "days_used": 0, "days_total": 0, "is_business": False}
    end_ts = item_end_time_ms(item)
    completed = end_ts is not None
    measure_to = end_ts if completed else int(datetime.utcnow().timestamp() * 1000)
    fn = business_days_between if is_business else calendar_days_between
    elapsed = fn(item.get("createdAt", measure_to), measure_to)
    breached = elapsed > days_total
    near = (days_total > 0 and elapsed >= 0.8 * days_total)
    if completed:
        if breached:
            return {"state": "frozen_breached", "label": f"Closed +{elapsed - days_total}d over",
                    "color": "#8a2515", "days_used": elapsed, "days_total": days_total,
                    "is_business": is_business}
        return {"state": "frozen_ok", "label": f"Closed in {elapsed}d", "color": "#4A5A3A",
                "days_used": elapsed, "days_total": days_total, "is_business": is_business}
    if breached:
        return {"state": "breached", "label": f"BREACHED · {elapsed - days_total}d over",
                "color": "#8a2515", "days_used": elapsed, "days_total": days_total,
                "is_business": is_business}
    if near:
        return {"state": "warning", "label": f"Due soon · {days_total - elapsed}d left",
                "color": "#8a5a1a", "days_used": elapsed, "days_total": days_total,
                "is_business": is_business}
    return {"state": "ok", "label": f"On track · {days_total - elapsed}d left",
            "color": "#4A5A3A", "days_used": elapsed, "days_total": days_total,
            "is_business": is_business}

def count_breaches(items):
    return sum(1 for i in items if sla_status(i)["state"] == "breached")

# ============================================================================
# SCORING
# ============================================================================
def compute_risk(answers, base=0):
    score = base
    for v in (answers or {}).values():
        if v in HIGH_RISK_TAGS: score += 2
        elif v in MEDIUM_RISK_TAGS: score += 1
    return min(10, score)

def rank_templates(templates, answers):
    values = set(answers.values())
    ranked = [{**t, "score": sum(1 for tag in t.get("tags", []) if tag in values)}
              for t in templates]
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked

def rank_change_types(types, answers):
    values = set(answers.values())
    ranked = [{**t, "score": sum(1 for c in t.get("conditions", []) if c in values)}
              for t in types]
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked

def pick_reviewer(reviewers, items, template_or_type):
    tags = template_or_type.get("tags") or template_or_type.get("conditions") or []
    active = [i for i in items if i.get("assignedReviewer")
              and i.get("currentStage") not in ("approved", "returned")]
    load = {}
    for i in active:
        load[i["assignedReviewer"]] = load.get(i["assignedReviewer"], 0) + 1
    scored = []
    for r in reviewers:
        cur_load = load.get(r["id"], 0)
        if cur_load >= r.get("capacity", 1): continue
        overlap = sum(1 for e in r.get("expertise", []) if e in tags)
        headroom = r.get("capacity", 1) - cur_load
        scored.append((r, overlap * 2 + headroom))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0] if scored else (reviewers[0] if reviewers else None)

# ============================================================================
# UI HELPERS
# ============================================================================
def pill(text, tone="neutral"):
    return f'<span class="pill {tone}">{text}</span>'

def section_title(eyebrow, title):
    st.markdown(f'<div class="eyebrow">{eyebrow}</div>'
                f'<h1 class="display" style="font-size:36px;margin:0 0 24px 0">{title}</h1>',
                unsafe_allow_html=True)

def stat_card(label, value, tone=None):
    cls = "stat-card"
    if tone == "accent": cls += " accent"
    if tone == "danger": cls += " danger"
    return f'<div class="{cls}"><div class="stat-label">{label}</div>'\
           f'<div class="stat-value">{value}</div></div>'

def risk_bar(score):
    pct = (score / 10) * 100
    color = "#A0432C" if score >= 7 else "#C58A30" if score >= 4 else "#6B7A4F"
    return f'<div class="risk-bar"><div class="risk-fill" '\
           f'style="width:{pct}%;background:{color}"></div></div>'\
           f'<div style="font-family:\'Instrument Serif\',serif;font-size:24px;color:var(--ink)">{score}'\
           f'<span style="font-size:12px;color:#8A8A8A">/10</span></div>'

def stage_track(workflow, current):
    if not workflow: return ""
    stages = list(workflow["stages"])
    if current == "returned": stages.append("returned")
    elif "approved" not in stages: stages.append("approved")
    try:
        cur_idx = stages.index(current)
    except ValueError:
        cur_idx = -1
    parts = []
    for idx, s in enumerate(stages):
        is_done = idx < cur_idx or (current == "approved" and idx <= cur_idx)
        is_current = idx == cur_idx
        is_returned = s == "returned" and current == "returned"
        color = ("#C58A30" if is_returned else "#6B7A4F" if is_done
                 else "#A0432C" if is_current else "#D4CCB9")
        parts.append(f'<span style="display:inline-block;width:10px;height:10px;'
                     f'border-radius:50%;background:{color};margin:0 4px" '
                     f'title="{STAGE_LABELS.get(s, s)}"></span>')
        if idx < len(stages) - 1:
            line_color = "#6B7A4F" if idx < cur_idx else "#D4CCB9"
            parts.append(f'<span style="display:inline-block;width:24px;height:2px;'
                         f'background:{line_color};vertical-align:middle"></span>')
    return f'<div>{"".join(parts)}</div>'\
           f'<div style="font-size:10px;color:var(--muted);margin-top:4px;'\
           f'text-transform:uppercase;letter-spacing:0.05em">'\
           f'{STAGE_LABELS.get(current, current)}</div>'

def sla_pill(item):
    if not st.session_state.features.get("slaTracking"): return ""
    status = sla_status(item)
    if status["state"] == "n/a": return ""
    tone_map = {"ok": "moss", "warning": "warn", "breached": "danger",
                "frozen_ok": "moss", "frozen_breached": "warn"}
    return pill(status["label"], tone_map.get(status["state"], "neutral"))

def role_badge(role):
    return f'<span class="role-pill {role}">{ROLE_LABELS.get(role, role)}</span>'

# ============================================================================
# LANDING PAGE
# ============================================================================

def render_landing():
    # Top nav: brand + Sign In button (Streamlit columns for the button)
    nav_l, nav_r = st.columns([5, 1])
    with nav_l:
        st.markdown('<div class="landing-brand" style="padding:24px 0">'
                    '<div class="landing-brand-mark"><em>H</em></div>'
                    '<div><div class="landing-brand-text">Hughes Guide</div>'
                    '<div class="landing-brand-sub">PMO decision support</div></div>'
                    '</div>', unsafe_allow_html=True)
    with nav_r:
        st.markdown('<div style="padding-top:30px">', unsafe_allow_html=True)
        if st.button("Sign in →", key="landing_signin_top"):
            st.session_state.auth_view = "login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<hr style="margin:0;border-color:var(--border)">', unsafe_allow_html=True)

    # Hero
    st.markdown("""
    <div class="landing-wrap">
      <div class="landing-hero">
        <div>
          <div class="eyebrow">A workbench for project teams</div>
          <h1 class="landing-hero-title">Hand the<br><em>routine work</em><br>to the structure.</h1>
          <p class="landing-hero-sub">Decision-tree wizards for scheduling and change management.
             Reviewer routing. Document pre-screening. SLA breach alerts.
             Built for supervisors averaging 60-hour weeks who'd like to stop.</p>
        </div>
        <div class="landing-visual">
          <svg viewBox="0 0 400 460" width="100%" xmlns="http://www.w3.org/2000/svg"
               style="display:block; max-width: 440px; margin: 0 auto">
            <!-- Title -->
            <text x="200" y="22" text-anchor="middle"
                  font-family="Manrope" font-size="9" letter-spacing="3"
                  fill="#A89E85">D E C I S I O N · T R E E</text>

            <!-- Question 1 -->
            <text x="200" y="52" text-anchor="middle"
                  font-family="Instrument Serif" font-style="italic" font-size="14"
                  fill="#5A5A5A">What's being submitted?</text>

            <!-- Root node -->
            <circle cx="200" cy="80" r="7" fill="#1A1A1A"/>
            <text x="200" y="103" text-anchor="middle"
                  font-family="Manrope" font-size="10" font-weight="600"
                  letter-spacing="2" fill="#1A1A1A">SUBMISSION</text>

            <!-- Branches to level 1 — Change path highlighted -->
            <line x1="200" y1="87" x2="100" y2="148" stroke="#D4CCB9" stroke-width="1.5"/>
            <line x1="200" y1="87" x2="300" y2="148" stroke="#A0432C" stroke-width="2.5"/>

            <!-- Level 1 nodes -->
            <circle cx="100" cy="154" r="5" fill="#D4CCB9"/>
            <text x="100" y="174" text-anchor="middle"
                  font-family="Manrope" font-size="11" fill="#8A8A8A">Schedule</text>

            <circle cx="300" cy="154" r="6" fill="#A0432C">
              <animate attributeName="r" values="6;9;6" dur="2.4s" repeatCount="indefinite"/>
              <animate attributeName="fill-opacity" values="1;0.5;1" dur="2.4s" repeatCount="indefinite"/>
            </circle>
            <text x="300" y="174" text-anchor="middle"
                  font-family="Manrope" font-size="11" font-weight="600" fill="#1A1A1A">Change request</text>

            <!-- Question 2 -->
            <text x="300" y="208" text-anchor="middle"
                  font-family="Instrument Serif" font-style="italic" font-size="13"
                  fill="#5A5A5A">How urgent? How risky?</text>

            <!-- Branches to level 2 — Normal path highlighted -->
            <line x1="300" y1="160" x2="220" y2="240" stroke="#D4CCB9" stroke-width="1.5"/>
            <line x1="300" y1="160" x2="300" y2="240" stroke="#A0432C" stroke-width="2.5"/>
            <line x1="300" y1="160" x2="380" y2="240" stroke="#D4CCB9" stroke-width="1.5"/>

            <!-- Level 2 nodes -->
            <circle cx="220" cy="246" r="4" fill="#D4CCB9"/>
            <text x="220" y="263" text-anchor="middle"
                  font-family="Manrope" font-size="10" fill="#8A8A8A">Standard</text>

            <circle cx="300" cy="246" r="5" fill="#A0432C">
              <animate attributeName="r" values="5;8;5" dur="2.4s" begin="0.3s" repeatCount="indefinite"/>
              <animate attributeName="fill-opacity" values="1;0.5;1" dur="2.4s" begin="0.3s" repeatCount="indefinite"/>
            </circle>
            <text x="300" y="263" text-anchor="middle"
                  font-family="Manrope" font-size="10" font-weight="600" fill="#1A1A1A">Normal</text>

            <circle cx="380" cy="246" r="4" fill="#D4CCB9"/>
            <text x="380" y="263" text-anchor="middle"
                  font-family="Manrope" font-size="10" fill="#8A8A8A">Major</text>

            <!-- Connector to outcome -->
            <line x1="300" y1="251" x2="300" y2="310" stroke="#A0432C"
                  stroke-width="2" stroke-dasharray="3 4"/>

            <!-- Outcome card -->
            <rect x="120" y="312" width="280" height="118" rx="4"
                  fill="#F2E5DE" stroke="#A0432C" stroke-width="1"/>
            <text x="260" y="338" text-anchor="middle"
                  font-family="Manrope" font-size="9" letter-spacing="2.5" fill="#A0432C">R O U T E D · T O</text>
            <text x="260" y="370" text-anchor="middle"
                  font-family="Instrument Serif" font-size="26" fill="#1A1A1A">Normal Change</text>
            <text x="260" y="398" text-anchor="middle"
                  font-family="Manrope" font-size="11" fill="#5A5A5A">10 business day SLA</text>
            <text x="260" y="418" text-anchor="middle"
                  font-family="Manrope" font-size="11" fill="#5A5A5A">Team Lead + Change Manager</text>

            <!-- Travelling dot along active path -->
            <circle r="3.5" fill="#A0432C">
              <animateMotion dur="3.2s" repeatCount="indefinite"
                              path="M 0,0 L 100,61 L 100,159 L 100,225"
                              rotate="auto"/>
              <animate attributeName="opacity" values="0;1;1;1;0" dur="3.2s" repeatCount="indefinite"/>
            </circle>
          </svg>
        </div>
      </div>

      <div class="landing-features">
        <div class="landing-feature">
          <div class="feature-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" fill="currentColor" fill-opacity="0.15"/>
            </svg>
          </div>
          <div class="feature-num">i.</div>
          <h3>Guide</h3>
          <p>Six checkpoint questions route your team to the right schedule template. Five route them to the right change classification. The decision tree is configurable — adjust tags to change routing without touching code.</p>
        </div>
        <div class="landing-feature">
          <div class="feature-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="18" cy="5" r="3"/>
              <circle cx="6" cy="12" r="3"/>
              <circle cx="18" cy="19" r="3"/>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
            </svg>
          </div>
          <div class="feature-num">ii.</div>
          <h3>Route</h3>
          <p>Submissions auto-assign to the best-fit reviewer based on expertise overlap and current load. Three workflow types, configurable approval chains, capacity-aware. Reviewers see only their queue.</p>
        </div>
        <div class="landing-feature">
          <div class="feature-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </div>
          <div class="feature-num">iii.</div>
          <h3>Surface</h3>
          <p>SLA breaches flag in red on every page. The Gantt timeline reveals aging items at a glance. Claude pre-screens uploaded documents so your team leads see focused reviews instead of blank pages.</p>
        </div>
      </div>

      <div class="landing-closing">
        <h2 class="landing-closing-title">You'll see <em>only what reaches Final QA</em>.</h2>
        <p class="landing-closing-body">That's the point. Everything else is handled by structure, scoring, and reviewers who know what they're looking at. Sixty-hour weeks become forty when the routine work stops landing on your desk.</p>
      </div>

      <div class="landing-footer">Hughes Guide · v1.2</div>
    </div>
    """, unsafe_allow_html=True)

    # Bottom CTA
    cta_l, cta_c, cta_r = st.columns([2, 1, 2])
    with cta_c:
        if st.button("Sign in →", key="landing_signin_bottom",
                     use_container_width=True):
            st.session_state.auth_view = "login"
            st.rerun()
        st.markdown('<div style="text-align:center;font-size:11px;color:var(--muted);'
                    'margin-top:8px">Invite only — ask your administrator for an account.</div>',
                    unsafe_allow_html=True)


def render_login():
    st.markdown('<div class="login-card-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">'
                '<div class="eyebrow">Hughes Guide</div>'
                '<div class="login-title">Welcome back.</div>'
                '<div class="login-sub">Sign in to continue.</div>', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", key="login_user", autocomplete="username")
        password = st.text_input("Password", type="password", key="login_pw",
                                  autocomplete="current-password")
        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button("Sign in", use_container_width=True)
        with col2:
            back = st.form_submit_button("← Back", type="secondary", use_container_width=True)

        if back:
            st.session_state.auth_view = "landing"
            st.rerun()
        if submit:
            if not username.strip() or not password:
                st.error("Enter both username and password.")
            else:
                ok, err = login(username.strip(), password)
                if ok:
                    st.rerun()
                else:
                    st.error(err)

    st.markdown('</div></div>', unsafe_allow_html=True)


def render_first_run():
    """Bootstrap flow when no users exist yet."""
    st.markdown('<div class="login-card-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">'
                '<div class="eyebrow">First-run setup</div>'
                '<div class="login-title">Create the first administrator.</div>'
                '<div class="login-sub">This account has full access. You can add more users '
                'with limited roles from Settings.</div>', unsafe_allow_html=True)

    if not _BCRYPT_AVAILABLE:
        st.error("**bcrypt is required for authentication.** Add `bcrypt>=4.1.0` to "
                 "`requirements.txt` and redeploy.")
        st.markdown('</div></div>', unsafe_allow_html=True)
        return

    with st.form("first_run_form"):
        name = st.text_input("Your display name", placeholder="Alex Hughes")
        username = st.text_input("Username", placeholder="alex",
                                  help="3–30 characters, letters/digits/._-")
        password = st.text_input("Password", type="password",
                                  help="Minimum 8 characters")
        password2 = st.text_input("Confirm password", type="password")
        submit = st.form_submit_button("Create administrator account",
                                        use_container_width=True)
        if submit:
            if not name.strip():
                st.error("Display name is required.")
            elif password != password2:
                st.error("Passwords don't match.")
            else:
                ok, result = create_user(username.strip(), password, name.strip(), "admin")
                if not ok:
                    st.error(result)
                else:
                    st.success("Administrator created. Sign in below.")
                    st.session_state.auth_view = "login"
                    st.rerun()

    st.markdown('</div></div>', unsafe_allow_html=True)


# ============================================================================
# PAGE: HOME
# ============================================================================
def render_home():
    user = current_user()
    greet = f"Welcome back, {user['name']}." if user else "Hand the routine work to the structure."

    st.markdown('<div class="eyebrow">Today at the bench</div>'
                f'<h1 class="display" style="font-size:42px;margin:0 0 8px 0">{greet}</h1>'
                '<p style="color:var(--muted);max-width:640px;margin-bottom:32px">'
                "Wizards guide your teams to the right template or change type. "
                "Reviewers see clean, scored submissions. You see only what reaches Final QA.</p>",
                unsafe_allow_html=True)

    all_items = st.session_state.submissions
    items = visible_items(all_items)
    total = len(items)
    by_type = {"schedule": 0, "change": 0}
    mine_qa = 0; approved = 0
    for i in items:
        by_type[i["type"]] = by_type.get(i["type"], 0) + 1
        if i["currentStage"] == "final_qa": mine_qa += 1
        if i["currentStage"] == "approved": approved += 1

    breaches = count_breaches(items) if st.session_state.features.get("slaTracking") else 0
    qa_label = "Awaiting your QA" if is_admin() else "At Final QA"

    cols = st.columns(5 if st.session_state.features.get("slaTracking") else 4)
    cols[0].markdown(stat_card("In pipeline", total - approved), unsafe_allow_html=True)
    cols[1].markdown(stat_card(qa_label, mine_qa, tone="accent" if is_admin() else None),
                     unsafe_allow_html=True)
    cols[2].markdown(stat_card("Schedules", by_type.get("schedule", 0)), unsafe_allow_html=True)
    cols[3].markdown(stat_card("Change requests", by_type.get("change", 0)), unsafe_allow_html=True)
    if st.session_state.features.get("slaTracking"):
        cols[4].markdown(stat_card("SLA breaches", breaches,
                                   tone="danger" if breaches > 0 else None),
                         unsafe_allow_html=True)

    if breaches > 0:
        st.markdown(f'<div class="card" style="background:#F2D9D2;border-color:#8a2515;'
                    f'margin-top:16px"><strong style="color:#8a2515">⚠ {breaches} '
                    f'item{"s" if breaches != 1 else ""} past SLA.</strong> '
                    f'<span style="color:var(--muted)">Open the Pipeline tab and filter '
                    f'by SLA to clear them.</span></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    actions_cols = []
    if has_perm("submit"): actions_cols.append("submit")
    if has_perm("view_all") or has_perm("view_own"): actions_cols.append("pipeline")
    if actions_cols:
        cols = st.columns(len(actions_cols))
        for i, key in enumerate(actions_cols):
            with cols[i]:
                if key == "submit":
                    st.markdown('<div class="card"><div class="eyebrow">Get started</div>'
                                '<div class="display" style="font-size:22px;margin-bottom:6px">'
                                "Submit something new</div>"
                                "<p style='color:var(--muted);font-size:14px;margin-bottom:12px'>"
                                "Run a team member through the schedule or change request wizard.</p></div>",
                                unsafe_allow_html=True)
                    if st.button("Open Submit →", key="goto_submit"):
                        st.session_state.page = "Submit"
                        st.rerun()
                else:
                    st.markdown('<div class="card"><div class="eyebrow">Track</div>'
                                '<div class="display" style="font-size:22px;margin-bottom:6px">'
                                "Check the pipeline</div>"
                                "<p style='color:var(--muted);font-size:14px;margin-bottom:12px'>"
                                "See where every item is, who's reviewing, and what's blocked.</p></div>",
                                unsafe_allow_html=True)
                    if st.button("Open Pipeline →", key="goto_pipeline"):
                        st.session_state.page = "Pipeline"
                        st.rerun()

    # Reviewer load (visible to admin/lead/viewer)
    if has_perm("view_all"):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="label">Reviewer load</div>', unsafe_allow_html=True)
        for r in st.session_state.reviewers:
            load = sum(1 for i in all_items if i.get("assignedReviewer") == r["id"]
                       and i["currentStage"] not in ("approved", "returned"))
            cap = r.get("capacity", 1)
            pct = min(100, (load / cap) * 100) if cap else 0
            c1, c2, c3 = st.columns([3, 6, 1])
            c1.markdown(f"<div style='padding-top:4px'>{r['name']}</div>",
                        unsafe_allow_html=True)
            c2.markdown(f'<div style="margin-top:10px"><div class="risk-bar">'
                        f'<div class="risk-fill" style="width:{pct}%;background:#A0432C"></div></div></div>',
                        unsafe_allow_html=True)
            c3.markdown(f"<div style='padding-top:4px;text-align:right;color:var(--muted)'>"
                        f"{load} / {cap}</div>", unsafe_allow_html=True)

    if st.session_state.features.get("workExport") and has_perm("export"):
        st.markdown("<br>", unsafe_allow_html=True)
        export_data = {
            "exportedAt": datetime.utcnow().isoformat(),
            "features": st.session_state.features, "workflows": st.session_state.workflows,
            "templates": st.session_state.templates, "change_types": st.session_state.change_types,
            "reviewers": st.session_state.reviewers, "submissions": st.session_state.submissions,
        }
        if is_admin():
            # Include users only in admin export (with hashes intact)
            export_data["users"] = st.session_state.users
        st.download_button(
            "⬇ Export workspace (JSON)",
            data=json.dumps(export_data, indent=2),
            file_name=f"hughes-guide-workspace-{int(datetime.utcnow().timestamp())}.json",
            mime="application/json", type="secondary",
        )

# ============================================================================
# PAGE: SUBMIT
# ============================================================================
def render_submit():
    if not has_perm("submit"):
        st.warning("You don't have permission to submit items.")
        return

    if "wizard_kind" not in st.session_state:
        st.session_state.wizard_kind = None

    if st.session_state.wizard_kind is None:
        section_title("New submission", "What are you submitting?")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="card" style="text-align:center;padding:32px 20px">'
                        '<div style="display:inline-flex;align-items:center;justify-content:center;'
                        'width:56px;height:56px;border-radius:50%;background:#E0E5DA;'
                        'color:#4A5A3A;margin-bottom:12px">'
                        '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
                        '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>'
                        '<line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>'
                        '<line x1="3" y1="10" x2="21" y2="10"/></svg></div>'
                        '<div class="eyebrow">Scheduling team</div>'
                        '<div class="display" style="font-size:24px;margin:6px 0">'
                        "Schedule template</div>"
                        "<p style='color:var(--muted);font-size:13px;line-height:1.5;margin:0'>"
                        "Walk through 6 checkpoints to pick the right schedule template "
                        "for your project.</p></div>",
                        unsafe_allow_html=True)
            if st.button("Start schedule wizard →", key="start_schedule",
                          use_container_width=True):
                st.session_state.wizard_kind = "schedule"
                st.session_state.wizard_step = 0
                st.session_state.wizard_answers = {}
                st.rerun()
        with c2:
            st.markdown('<div class="card" style="text-align:center;padding:32px 20px">'
                        '<div style="display:inline-flex;align-items:center;justify-content:center;'
                        'width:56px;height:56px;border-radius:50%;background:var(--rust-soft);'
                        'color:var(--rust);margin-bottom:12px">'
                        '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
                        '<polyline points="17 1 21 5 17 9"/>'
                        '<path d="M3 11V9a4 4 0 0 1 4-4h14"/>'
                        '<polyline points="7 23 3 19 7 15"/>'
                        '<path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg></div>'
                        '<div class="eyebrow">Change management team</div>'
                        '<div class="display" style="font-size:24px;margin:6px 0">'
                        "Change request</div>"
                        "<p style='color:var(--muted);font-size:13px;line-height:1.5;margin:0'>"
                        "Classify a change correctly before submitting — Standard, Normal, "
                        "Major, or Emergency.</p></div>",
                        unsafe_allow_html=True)
            if st.button("Start change wizard →", key="start_change",
                          use_container_width=True):
                st.session_state.wizard_kind = "change"
                st.session_state.wizard_step = 0
                st.session_state.wizard_answers = {}
                st.rerun()
        return

    render_wizard(st.session_state.wizard_kind)


def render_wizard(kind):
    questions = SCHEDULE_QUESTIONS if kind == "schedule" else CHANGE_QUESTIONS
    options = st.session_state.templates if kind == "schedule" else st.session_state.change_types
    user = current_user()

    if st.button("← Pick a different wizard", type="secondary", key="back_picker"):
        st.session_state.wizard_kind = None
        st.rerun()

    section_title("Scheduling" if kind == "schedule" else "Change management",
                  "Schedule Template Wizard" if kind == "schedule" else "Change Request Wizard")

    step = st.session_state.wizard_step
    total = len(questions)
    answers = st.session_state.wizard_answers

    if step < total:
        bars = "".join(
            f'<div style="flex:1;height:2px;background:{"#A0432C" if i <= step else "#E5DDC9"};'
            f'margin:0 2px"></div>' for i in range(total)
        )
        st.markdown(f'<div style="display:flex;margin-bottom:24px">{bars}</div>',
                    unsafe_allow_html=True)
        cur = questions[step]
        st.markdown(f'<div class="eyebrow">Question {step + 1} of {total}</div>'
                    f'<h2 class="display" style="font-size:26px;margin:0 0 20px 0">'
                    f'{cur["q"]}</h2>', unsafe_allow_html=True)
        labels = [opt[1] for opt in cur["options"]]
        values = [opt[0] for opt in cur["options"]]
        current_value = answers.get(cur["id"])
        default_idx = values.index(current_value) if current_value in values else None
        choice = st.radio("Select:", labels, index=default_idx,
                          key=f"q_{cur['id']}_{step}", label_visibility="collapsed")
        if choice:
            answers[cur["id"]] = values[labels.index(choice)]
            st.session_state.wizard_answers = answers
        nav1, _, nav3 = st.columns([1, 4, 1])
        with nav1:
            if step > 0:
                if st.button("← Back", key="wiz_back", type="secondary"):
                    st.session_state.wizard_step -= 1
                    st.rerun()
        with nav3:
            if cur["id"] in answers:
                label = "See recommendation →" if step == total - 1 else "Next →"
                if st.button(label, key="wiz_next"):
                    st.session_state.wizard_step += 1
                    st.rerun()
        return

    ranked = (rank_templates(options, answers) if kind == "schedule"
              else rank_change_types(options, answers))
    chosen_id = st.session_state.get("wizard_chosen", ranked[0]["id"] if ranked else None)

    st.markdown('<div class="eyebrow">Recommendation</div>'
                '<h2 class="display" style="font-size:28px;margin:0 0 16px 0">'
                "Based on your answers</h2>", unsafe_allow_html=True)

    cols = st.columns(min(3, len(ranked)))
    for idx, opt in enumerate(ranked[:3]):
        with cols[idx]:
            badge = "Top match" if idx == 0 else f"Option {idx + 1}"
            is_chosen = opt["id"] == chosen_id
            border = "var(--rust)" if is_chosen else "var(--border-strong)"
            bg = "var(--rust-soft)" if is_chosen else "var(--card)"
            st.markdown(f'<div class="card" style="border-color:{border};background:{bg};'
                        f'min-height:160px">{pill(badge, "rust" if idx == 0 else "neutral")}'
                        f'<div class="display" style="font-size:18px;margin:8px 0 6px 0">'
                        f'{opt["name"]}</div>'
                        f'<div style="font-size:12px;color:var(--muted);line-height:1.4">'
                        f'{opt["description"]}</div>'
                        f'<div style="margin-top:8px;font-family:\'Instrument Serif\',serif;'
                        f'font-size:20px;color:var(--rust)">Match: {opt["score"]}</div></div>',
                        unsafe_allow_html=True)
            if st.button("Select", key=f"choose_{opt['id']}"):
                st.session_state.wizard_chosen = opt["id"]
                st.rerun()

    chosen = next((o for o in ranked if o["id"] == chosen_id), ranked[0] if ranked else None)
    if not chosen:
        st.warning("No matching template/type. Edit templates in Settings.")
        return

    risk = compute_risk(answers, chosen.get("riskBase", 0))

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="display" style="font-size:22px;margin-bottom:4px">{chosen["name"]}</div>'
                f'<p style="color:var(--muted);font-size:14px">{chosen["description"]}</p>',
                unsafe_allow_html=True)

    if chosen.get("checkpoints"):
        st.markdown('<div class="label">Built-in checkpoints</div>', unsafe_allow_html=True)
        st.markdown("".join(pill(c) for c in chosen["checkpoints"]), unsafe_allow_html=True)
    if chosen.get("requiredApprovals"):
        st.markdown('<div class="label" style="margin-top:12px">Required approvals</div>',
                    unsafe_allow_html=True)
        st.markdown("".join(pill(a, "ink") for a in chosen["requiredApprovals"]),
                    unsafe_allow_html=True)
    if chosen.get("sla"):
        st.markdown(f'<div style="margin-top:12px;font-size:14px;color:var(--ink)">'
                    f'⏱ SLA: {chosen["sla"]}</div>', unsafe_allow_html=True)
    if st.session_state.features.get("riskScoring"):
        st.markdown('<div class="label" style="margin-top:16px">Risk profile</div>',
                    unsafe_allow_html=True)
        st.markdown(risk_bar(risk), unsafe_allow_html=True)
        if risk >= 7:
            st.markdown('<div style="color:var(--rust);font-size:12px;margin-top:4px">'
                        "⚠ High risk — recommend Extended workflow with executive review.</div>",
                        unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.form("submission_form"):
        st.markdown('<div class="label">Submission details</div>', unsafe_allow_html=True)
        title = st.text_input("Submission title", key="sub_title",
                              placeholder="e.g. Q3 platform migration schedule" if kind == "schedule"
                              else "e.g. Database failover procedure update")
        c1, c2 = st.columns(2)
        with c1:
            submitter_name = st.text_input("Submitted by", value=user["name"],
                                            key="sub_by",
                                            help="Defaults to your display name.")
        with c2:
            wf_ids = [w["id"] for w in st.session_state.workflows]
            default_idx = (wf_ids.index(chosen.get("defaultWorkflow", "standard"))
                           if chosen.get("defaultWorkflow") in wf_ids else 0)
            workflow_id = st.selectbox(
                "Workflow", wf_ids, index=default_idx,
                format_func=lambda x: next(
                    (w["name"] + f" ({len(w['stages'])} stages)"
                     for w in st.session_state.workflows if w["id"] == x), x),
            )
        notes = st.text_area("Notes for reviewers (optional)", key="sub_notes", height=80)

        auto_rev = None
        if st.session_state.features.get("autoAssignment"):
            auto_rev = pick_reviewer(st.session_state.reviewers,
                                     st.session_state.submissions, chosen)
            if auto_rev:
                st.markdown(f"<div style='font-size:12px;color:var(--muted);margin-top:4px'>"
                            f"👤 Auto-assigned reviewer: "
                            f"<strong style='color:var(--ink)'>{auto_rev['name']}</strong> "
                            f"({auto_rev['role']})</div>", unsafe_allow_html=True)

        col_a, col_b = st.columns([1, 5])
        with col_a:
            cancel = st.form_submit_button("← Back", type="secondary")
        with col_b:
            submit = st.form_submit_button("Submit to pipeline →")

        if cancel:
            st.session_state.wizard_step -= 1
            st.rerun()
        if submit:
            if not title.strip():
                st.error("Title is required.")
            else:
                wf = next(w for w in st.session_state.workflows if w["id"] == workflow_id)
                item = {
                    "id": f"item_{int(datetime.utcnow().timestamp() * 1000)}",
                    "title": title.strip(), "submittedBy": submitter_name.strip() or user["name"],
                    "submitterUserId": user["id"],
                    "notes": notes.strip(), "type": kind,
                    "typeId": chosen["id"], "typeName": chosen["name"],
                    "workflowId": workflow_id, "answers": answers, "riskScore": risk,
                    "assignedReviewer": auto_rev["id"] if auto_rev else None,
                    "currentStage": wf["stages"][0], "history": [],
                    "createdAt": int(datetime.utcnow().timestamp() * 1000),
                }
                st.session_state.submissions = [item, *st.session_state.submissions]
                persist("submissions")
                for k in ("wizard_kind", "wizard_step", "wizard_answers", "wizard_chosen"):
                    if k in st.session_state: del st.session_state[k]
                st.session_state.page = "Pipeline"
                st.rerun()

# ============================================================================
# PAGE: PIPELINE + DETAIL
# ============================================================================
def can_advance_from(stage):
    if stage in ("draft", "peer_review"):
        return has_perm("review_peer") or has_perm("review_lead") or has_perm("final_qa")
    if stage == "lead_review":
        return has_perm("review_lead") or has_perm("final_qa")
    if stage == "final_qa":
        return has_perm("final_qa")
    return False


def render_pipeline():
    items = visible_items(st.session_state.submissions)

    if st.session_state.get("detail_id"):
        item = next((i for i in items if i["id"] == st.session_state.detail_id), None)
        if item:
            render_item_detail(item)
            return
        st.session_state.detail_id = None

    section_title("In flight", "Pipeline")

    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
    search = c1.text_input("Search", placeholder="Search title or submitter…",
                           label_visibility="collapsed")
    stage_filter = c2.selectbox("Stage", ["All stages"] + list(STAGE_LABELS.keys()),
                                format_func=lambda x: x if x == "All stages" else STAGE_LABELS[x],
                                label_visibility="collapsed")
    type_filter = c3.selectbox("Type", ["All types", "schedule", "change"],
                               label_visibility="collapsed")
    sla_filter = "All SLA"
    if st.session_state.features.get("slaTracking"):
        sla_filter = c4.selectbox("SLA",
                                  ["All SLA", "On track", "Due soon", "Breached", "Closed"],
                                  label_visibility="collapsed")

    filtered = []
    for i in items:
        if stage_filter != "All stages" and i["currentStage"] != stage_filter: continue
        if type_filter != "All types" and i["type"] != type_filter: continue
        if search and search.lower() not in i["title"].lower() \
                and search.lower() not in i["submittedBy"].lower():
            continue
        if sla_filter != "All SLA":
            s = sla_status(i)["state"]
            if sla_filter == "On track" and s != "ok": continue
            if sla_filter == "Due soon" and s != "warning": continue
            if sla_filter == "Breached" and s != "breached": continue
            if sla_filter == "Closed" and s not in ("frozen_ok", "frozen_breached"): continue
        filtered.append(i)
    filtered.sort(key=lambda x: x.get("createdAt", 0), reverse=True)

    c5.markdown(f"<div style='text-align:right;color:var(--muted);font-size:12px;padding-top:8px'>"
                f"{len(filtered)} of {len(items)}</div>", unsafe_allow_html=True)

    if st.session_state.features.get("csvExport") and has_perm("export") and filtered:
        df = pd.DataFrame([{
            "ID": i["id"], "Title": i["title"], "Type": i["type"],
            "Template": i["typeName"], "Workflow": i["workflowId"],
            "Stage": STAGE_LABELS.get(i["currentStage"], i["currentStage"]),
            "Risk": i.get("riskScore", ""), "SLA status": sla_status(i)["label"],
            "Submitted by": i["submittedBy"],
            "Reviewer": next((r["name"] for r in st.session_state.reviewers
                              if r["id"] == i.get("assignedReviewer")), ""),
            "Created": datetime.fromtimestamp(i["createdAt"] / 1000).isoformat(),
            "Notes": i.get("notes", ""),
        } for i in filtered])
        st.download_button("⬇ Export CSV", df.to_csv(index=False).encode(),
                           file_name=f"pipeline-{int(datetime.utcnow().timestamp())}.csv",
                           mime="text/csv", type="secondary")

    st.markdown("---")

    if not filtered:
        msg_title = "No submissions visible" if not items else "Nothing matches those filters"
        msg_body = ("Submitters see their own items. Submit one to see it here."
                    if has_perm("view_own") and not has_perm("view_all")
                    else "Use the Submit page to add your first item." if not items
                    else "Try clearing the filters above.")
        st.markdown(f'<div class="card" style="text-align:center;padding:48px">'
                    f'<div class="display" style="font-size:20px;margin-bottom:4px">{msg_title}</div>'
                    f'<div style="color:var(--muted);font-size:14px;margin-bottom:16px">{msg_body}</div></div>',
                    unsafe_allow_html=True)
        if not items and has_perm("submit"):
            c_l, c_c, c_r = st.columns([2, 1, 2])
            with c_c:
                if st.button("→ Start a submission", key="empty_to_submit",
                              use_container_width=True):
                    st.session_state.page = "Submit"
                    st.rerun()
        return

    for item in filtered:
        wf = next((w for w in st.session_state.workflows
                   if w["id"] == item["workflowId"]), None)
        reviewer = next((r for r in st.session_state.reviewers
                         if r["id"] == item.get("assignedReviewer")), None)
        c1, c2, c3, c4 = st.columns([4, 3, 1, 1])
        with c1:
            tone_type = "moss" if item["type"] == "schedule" else "rust"
            pills_html = pill(item["type"], tone_type) + pill(item["typeName"])
            if item["currentStage"] == "approved": pills_html += pill("✓ Approved", "moss")
            if item["currentStage"] == "returned": pills_html += pill("Returned", "warn")
            pills_html += sla_pill(item)
            st.markdown(f'<div class="card" style="margin-bottom:8px">{pills_html}'
                        f'<div class="display" style="font-size:17px;margin:6px 0 2px 0">'
                        f'{item["title"]}</div>'
                        f'<div style="font-size:11px;color:var(--muted)">{item["submittedBy"]} · '
                        f'{datetime.fromtimestamp(item["createdAt"]/1000).strftime("%b %d, %Y")}'
                        f'{" · " + reviewer["name"] if reviewer else ""}</div></div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div style="padding-top:18px">{stage_track(wf, item["currentStage"])}</div>',
                        unsafe_allow_html=True)
        with c3:
            if st.session_state.features.get("riskScoring"):
                st.markdown(f'<div style="text-align:center;padding-top:14px">'
                            f'<div style="font-size:10px;color:var(--muted);'
                            f'text-transform:uppercase;letter-spacing:0.05em">Risk</div>'
                            f'<div style="font-family:\'Instrument Serif\',serif;'
                            f'font-size:22px;color:var(--ink)">'
                            f'{item.get("riskScore", "—")}</div></div>',
                            unsafe_allow_html=True)
        with c4:
            st.markdown("<div style='padding-top:18px'>", unsafe_allow_html=True)
            if st.button("Open →", key=f"open_{item['id']}"):
                st.session_state.detail_id = item["id"]
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


def render_item_detail(item):
    if st.button("← Back to pipeline", type="secondary", key="back_to_pipeline"):
        st.session_state.detail_id = None
        st.rerun()

    wf = next((w for w in st.session_state.workflows
               if w["id"] == item["workflowId"]), None)
    reviewer = next((r for r in st.session_state.reviewers
                     if r["id"] == item.get("assignedReviewer")), None)

    tone_type = "moss" if item["type"] == "schedule" else "rust"
    st.markdown(f'<div style="margin-top:16px">{pill(item["type"], tone_type)}{sla_pill(item)}'
                f'<span style="font-size:11px;color:var(--muted);margin-left:8px">{item["id"]}</span></div>'
                f'<h1 class="display" style="font-size:32px;margin:8px 0 4px 0">{item["title"]}</h1>'
                f'<div style="color:var(--muted);font-size:13px;margin-bottom:24px">'
                f'{item["typeName"]} · Submitted by {item["submittedBy"]} · '
                f'{datetime.fromtimestamp(item["createdAt"]/1000).strftime("%b %d, %Y %H:%M")}</div>',
                unsafe_allow_html=True)

    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.markdown('<div class="card"><div class="label">Workflow progress</div>'
                    f'{stage_track(wf, item["currentStage"])}</div>', unsafe_allow_html=True)
        if item.get("notes"):
            st.markdown(f'<div class="card"><div class="label">Submitter notes</div>'
                        f'<div style="font-size:14px;white-space:pre-wrap">{item["notes"]}</div></div>',
                        unsafe_allow_html=True)
        if item.get("answers"):
            answers_html = "".join(pill(f"{k}: {v}") for k, v in item["answers"].items())
            st.markdown(f'<div class="card"><div class="label">Selected criteria</div>'
                        f'{answers_html}</div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="label">Activity</div>', unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:12px;color:var(--muted);margin-bottom:8px'>"
                    f"<strong style='color:var(--ink)'>Created</strong> · "
                    f"{datetime.fromtimestamp(item['createdAt']/1000).strftime('%b %d, %Y %H:%M')}</div>",
                    unsafe_allow_html=True)
        for h in item.get("history", []):
            note_html = (f"<div style='color:var(--ink);margin-top:2px'>{h['note']}</div>"
                         if h.get("note") else "")
            actor = f" · by {h['by']}" if h.get("by") else ""
            st.markdown(f"<div style='font-size:12px;color:var(--muted);padding-left:12px;"
                        f"border-left:2px solid var(--border);margin-bottom:8px'>"
                        f"<strong style='color:var(--ink)'>{h['action']}</strong> · "
                        f"{datetime.fromtimestamp(h['at']/1000).strftime('%b %d, %Y %H:%M')}{actor}"
                        f"{note_html}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        if st.session_state.features.get("slaTracking"):
            status = sla_status(item)
            if status["state"] != "n/a":
                unit = "business days" if status["is_business"] else "days"
                pct = (min(status["days_used"], status["days_total"]) /
                       max(status["days_total"], 1)) * 100
                st.markdown(
                    f'<div class="card"><div class="label">SLA tracking</div>'
                    f'<div style="font-size:14px;font-weight:500;color:{status["color"]}">'
                    f'{status["label"]}</div>'
                    f'<div class="risk-bar" style="margin-top:8px"><div class="risk-fill" '
                    f'style="width:{pct}%;background:{status["color"]}"></div></div>'
                    f'<div style="font-size:11px;color:var(--muted);margin-top:4px">'
                    f'{status["days_used"]} of {status["days_total"]} {unit} elapsed</div></div>',
                    unsafe_allow_html=True)

        if st.session_state.features.get("riskScoring"):
            st.markdown(f'<div class="card"><div class="label">Risk profile</div>'
                        f'{risk_bar(item.get("riskScore", 0))}</div>', unsafe_allow_html=True)

        if reviewer:
            st.markdown(f'<div class="card"><div class="label">Assigned reviewer</div>'
                        f'<div style="font-size:14px"><strong>{reviewer["name"]}</strong></div>'
                        f'<div style="font-size:12px;color:var(--muted)">{reviewer["role"]}</div></div>',
                        unsafe_allow_html=True)

        # Actions — gated by role
        can_advance = (item["currentStage"] not in ("approved", "returned")
                       and can_advance_from(item["currentStage"]))
        can_return = (item["currentStage"] not in ("approved", "returned")
                      and has_perm("return"))
        can_reopen = (item["currentStage"] in ("approved", "returned")
                      and has_perm("reopen"))

        if can_advance or can_return or can_reopen:
            st.markdown('<div class="card"><div class="label">Take action</div>',
                        unsafe_allow_html=True)
            with st.form(f"action_{item['id']}"):
                note = st.text_area("Note (optional)", height=80,
                                    key=f"note_{item['id']}", label_visibility="collapsed")
                stages = wf["stages"] if wf else []
                try:
                    cur_idx = stages.index(item["currentStage"])
                except ValueError:
                    cur_idx = -1
                next_stage = None
                if can_advance and stages:
                    next_stage = "approved" if cur_idx == len(stages) - 1 else stages[cur_idx + 1]

                adv = st.form_submit_button(
                    f"✓ Advance to {STAGE_LABELS.get(next_stage, '')}" if next_stage else "—",
                    disabled=next_stage is None)
                ret = st.form_submit_button("Return to submitter", type="secondary",
                                            disabled=not can_return)
                reopen = st.form_submit_button("Reopen", type="secondary",
                                               disabled=not can_reopen)

                event_made = None
                if adv and next_stage:
                    event_made = (next_stage, f"Advanced to {STAGE_LABELS[next_stage]}")
                elif ret:
                    event_made = ("returned", "Returned to submitter")
                elif reopen and stages:
                    event_made = (stages[0], f"Reopened to {STAGE_LABELS[stages[0]]}")

                if event_made:
                    items = st.session_state.submissions
                    user = current_user()
                    for idx, i in enumerate(items):
                        if i["id"] == item["id"]:
                            items[idx]["currentStage"] = event_made[0]
                            items[idx].setdefault("history", []).append({
                                "at": int(datetime.utcnow().timestamp() * 1000),
                                "action": event_made[1],
                                "by": user["name"] if user else "—",
                                "note": note.strip(),
                            })
                            break
                    st.session_state.submissions = items
                    persist("submissions")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card"><div class="label">Actions</div>'
                        '<div style="font-size:12px;color:var(--muted)">'
                        "Your role doesn't permit action on this item at its current stage.</div></div>",
                        unsafe_allow_html=True)

# ============================================================================
# PAGE: TIMELINE
# ============================================================================
def render_timeline():
    section_title("Pipeline aging", "Timeline")
    items = visible_items(st.session_state.submissions)
    if not items:
        st.markdown('<div class="card" style="text-align:center;padding:48px">'
                    '<div style="color:var(--muted)">'
                    "Submit something first — the timeline will fill in.</div></div>",
                    unsafe_allow_html=True)
        return
    if not _PLOTLY_AVAILABLE:
        st.error("Plotly isn't installed. Add `plotly>=5.0.0` to requirements.txt.")
        return

    c1, c2, _ = st.columns([2, 2, 4])
    type_f = c1.selectbox("Type", ["All", "schedule", "change"], key="tl_type")
    show_completed = c2.checkbox("Include completed", value=True, key="tl_completed")

    rows = []
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    for it in items:
        if type_f != "All" and it["type"] != type_f: continue
        end_ms = item_end_time_ms(it)
        if end_ms is None: end_ms = now_ms
        elif not show_completed: continue
        status = sla_status(it)
        rows.append({
            "title": it["title"][:80], "id": it["id"], "submitter": it["submittedBy"],
            "type": it["type"], "typeName": it["typeName"],
            "stage": STAGE_LABELS.get(it["currentStage"], it["currentStage"]),
            "risk": it.get("riskScore", 0), "sla": status["label"],
            "start": pd.Timestamp(it["createdAt"], unit="ms"),
            "end": pd.Timestamp(end_ms, unit="ms"),
        })

    if not rows:
        st.markdown('<div class="card" style="text-align:center;padding:48px">'
                    '<div style="color:var(--muted)">No items match the filters.</div></div>',
                    unsafe_allow_html=True)
        return

    df = pd.DataFrame(rows).sort_values("start", ascending=False)
    fig = px.timeline(
        df, x_start="start", x_end="end", y="title", color="stage",
        color_discrete_map=STAGE_COLORS,
        hover_data={"submitter": True, "typeName": True, "risk": True, "sla": True,
                    "start": "|%b %d, %Y", "end": "|%b %d, %Y", "title": False},
        category_orders={"stage": list(STAGE_COLORS.keys())},
    )
    fig.update_yaxes(autorange="reversed", title=None,
                     tickfont=dict(family="Manrope", size=11, color="#1A1A1A"))
    fig.update_xaxes(title=None, tickfont=dict(family="Manrope", size=11, color="#5A5A5A"),
                     gridcolor="#E5DDC9")
    fig.update_layout(
        plot_bgcolor="#FAF7F2", paper_bgcolor="#FAF7F2", font_family="Manrope",
        height=max(360, len(rows) * 36 + 120),
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
    )
    for r in [r for r in rows if "BREACHED" in r["sla"]]:
        fig.add_annotation(x=r["end"], y=r["title"], xref="x", yref="y",
                           text="⚠", showarrow=False,
                           font=dict(size=14, color="#8a2515"),
                           xshift=10, yshift=0)
    st.plotly_chart(fig, use_container_width=True)

    breaches = count_breaches(items) if st.session_state.features.get("slaTracking") else 0
    if breaches > 0:
        st.markdown(f'<div class="card" style="background:#F2D9D2;border-color:#8a2515">'
                    f'<strong style="color:#8a2515">⚠ {breaches} item'
                    f'{"s" if breaches != 1 else ""} past SLA</strong> '
                    f'<span style="color:var(--muted)">— marked with ⚠ on the chart.</span></div>',
                    unsafe_allow_html=True)

# ============================================================================
# PAGE: DOCUMENTS
# ============================================================================
def get_anthropic_client():
    api_key = _get_secret("ANTHROPIC_API_KEY")
    if not api_key or not _ANTHROPIC_AVAILABLE: return None
    return anthropic.Anthropic(api_key=api_key)

ANALYSIS_PROMPTS = {
    "schedule": """You are reviewing a project schedule document for a PMO. Evaluate it across these dimensions:

1. Completeness — are key sections present (scope, milestones, dependencies, resources, assumptions, risks)?
2. Realism — are durations, resource loads, and dependencies plausible?
3. Risk flags — single points of failure, unstated assumptions, unresolved dependencies?
4. Template fit — based on the structure shown, what kind of schedule template was used and does it fit the apparent work?
5. Quality issues to surface to the team lead before final QA

Return your analysis as: TOP-LINE VERDICT (1-2 sentences), then STRENGTHS, ISSUES (ordered by severity), and RECOMMENDED NEXT ACTIONS. Be specific. Cite what you see.""",
    "change": """You are reviewing a change request document for a PMO. Evaluate it as a change manager would, covering:

1. Classification check — does this look like a Standard, Normal, Major, or Emergency change? Is the classification appropriate?
2. Risk and impact assessment — completeness, identified blast radius, mitigation
3. Rollback plan — present, credible, tested?
4. Approval chain — does the requested approval level match the assessed risk?
5. Testing and validation evidence

Return your analysis as: TOP-LINE VERDICT (1-2 sentences), then STRENGTHS, ISSUES (ordered by severity), and RECOMMENDED NEXT ACTIONS. Be specific. Cite what you see.""",
}

def render_documents():
    if not has_perm("analyze_docs"):
        st.warning("You don't have permission to use Document Analysis.")
        return
    if not st.session_state.features.get("documentAnalysis"):
        section_title("Document analysis", "Disabled")
        st.markdown('<div class="card" style="text-align:center;padding:48px">'
                    '<div style="color:var(--muted)">'
                    "Enable Document Analysis in Settings to use this tab.</div></div>",
                    unsafe_allow_html=True)
        return
    client = get_anthropic_client()
    if not client:
        section_title("Document analysis", "Configuration needed")
        st.error("**ANTHROPIC_API_KEY not configured.** Add it to your Streamlit secrets.")
        return

    section_title("Pre-screen", "Document Analysis")
    st.markdown('<p style="color:var(--muted);max-width:640px;margin-bottom:24px">'
                "Upload a schedule, change request, or any document below. Claude pre-screens "
                "it against the relevant criteria.</p>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="label">Analysis lens</div>', unsafe_allow_html=True)
        lens = st.selectbox("Lens",
                            ["Schedule template review", "Change request review", "Custom criteria"],
                            label_visibility="collapsed")
        lens_key = {"Schedule template review": "schedule",
                    "Change request review": "change",
                    "Custom criteria": "custom"}[lens]
        custom_criteria = ""
        if lens_key == "custom":
            custom_criteria = st.text_area("Your criteria", height=120,
                                            placeholder="Tell Claude what to look for…")
        st.markdown('<div class="label" style="margin-top:8px">Upload PDF</div>',
                    unsafe_allow_html=True)
        pdf_file = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")
        st.markdown('<div class="label" style="margin-top:8px">Or paste text</div>',
                    unsafe_allow_html=True)
        text = st.text_area("Text", height=240, placeholder="Paste document content here…",
                            label_visibility="collapsed")
        run = st.button("✨ Run analysis", key="run_analysis",
                        disabled=(not pdf_file and not text.strip())
                                  or (lens_key == "custom" and not custom_criteria.strip()))

    with col2:
        st.markdown('<div class="label">Result</div>', unsafe_allow_html=True)
        result_placeholder = st.empty()
        if run:
            prompt = ANALYSIS_PROMPTS.get(lens_key) or custom_criteria
            content = []
            if pdf_file:
                pdf_b64 = base64.standard_b64encode(pdf_file.read()).decode("utf-8")
                content.append({"type": "document",
                                "source": {"type": "base64",
                                           "media_type": "application/pdf",
                                           "data": pdf_b64}})
            elif text.strip():
                content.append({"type": "text", "text": f"Document content:\n\n{text}"})
            content.append({"type": "text", "text": prompt})
            with result_placeholder.container():
                with st.spinner("Claude is reading the document…"):
                    try:
                        resp = client.messages.create(
                            model="claude-sonnet-4-5",
                            max_tokens=1500,
                            messages=[{"role": "user", "content": content}])
                        text_out = "\n".join(b.text for b in resp.content if hasattr(b, "text"))
                        st.markdown(f'<div class="card" style="white-space:pre-wrap;'
                                    f'font-size:14px;line-height:1.6">{text_out}</div>',
                                    unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
        else:
            result_placeholder.markdown(
                '<div class="card" style="min-height:300px;color:#8A8A8A;font-style:italic">'
                "Analysis output will appear here.</div>", unsafe_allow_html=True)

# ============================================================================
# PAGE: SETTINGS
# ============================================================================
FEATURE_META = [
    ("documentAnalysis", "Document Analysis",
     "AI pre-screens uploaded documents against your criteria."),
    ("riskScoring", "Risk Scoring",
     "Auto-computes 0–10 risk score from wizard answers."),
    ("autoAssignment", "Reviewer Auto-Assignment",
     "Picks best-fit reviewer based on expertise and current load."),
    ("slaTracking", "SLA Tracking",
     "Tracks each item against its template/type SLA. Flags breaches."),
    ("timelineView", "Timeline (Gantt) View",
     "Visualises pipeline aging with a horizontal timeline."),
    ("csvExport", "CSV Export", "Export filtered pipeline as CSV."),
    ("workExport", "Workspace Export (JSON)",
     "Export full data for backup or handover."),
    ("emailNotifications", "Email Notifications (preview)",
     "Email reviewers on assignment. Needs backend integration."),
]


def render_settings():
    # Everyone can see their own profile; only admin sees the full settings
    user = current_user()

    if not is_admin():
        # Limited settings for non-admins: own profile only
        section_title("Your account", user["name"])
        st.markdown(f'<div class="card"><div class="label">Profile</div>'
                    f'<div style="font-size:14px"><strong>{user["name"]}</strong> '
                    f'{role_badge(user["role"])}</div>'
                    f'<div style="font-size:12px;color:var(--muted);margin-top:4px">'
                    f'@{user["username"]}</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="label">Change password</div>',
                    unsafe_allow_html=True)
        with st.form("self_pw"):
            old = st.text_input("Current password", type="password")
            new = st.text_input("New password (min 8 chars)", type="password")
            new2 = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Update password"):
                if not verify_password(old, user["password_hash"]):
                    st.error("Current password is incorrect.")
                elif new != new2:
                    st.error("New passwords don't match.")
                elif len(new) < 8:
                    st.error("New password must be at least 8 characters.")
                else:
                    update_user(user["id"], {"password_hash": hash_password(new)})
                    # Refresh current_user reference
                    st.session_state.current_user = find_user(user["username"])
                    st.success("Password updated.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # ---- Full settings (admin only) ----
    section_title("Configure", "Settings")

    backend = get_backend()
    if backend == "supabase":
        st.markdown('<div class="card" style="background:#E0E5DA;border-color:#4A5A3A">'
                    '<span class="backend-badge">● Supabase</span> '
                    '<span style="margin-left:8px">Connected. Data persists across restarts.</span>'
                    '</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card" style="background:#F5E6CC;border-color:#8a5a1a">'
                    '<span class="backend-badge local">● Local SQLite</span> '
                    '<span style="margin-left:8px">Add SUPABASE_URL + SUPABASE_KEY to secrets '
                    "for durable storage. See README.</span></div>",
                    unsafe_allow_html=True)

    # User management
    render_user_management()

    # Features
    st.markdown('<div class="card"><div class="label">Features</div>', unsafe_allow_html=True)
    for key, name, desc in FEATURE_META:
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"<div style='padding-top:4px'><div style='font-size:14px;font-weight:500'>"
                    f"{name}</div><div style='font-size:12px;color:var(--muted)'>{desc}</div></div>",
                    unsafe_allow_html=True)
        disabled = "preview" in name.lower()
        val = c2.toggle("", value=st.session_state.features.get(key, False),
                        key=f"feat_{key}", disabled=disabled, label_visibility="collapsed")
        if val != st.session_state.features.get(key) and not disabled:
            st.session_state.features[key] = val
            persist("features")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    render_editable_list("Schedule templates", "templates", "template")
    render_editable_list("Change request types", "change_types", "changeType")
    render_editable_list("Team leads / reviewers", "reviewers", "reviewer")

    # Workspace import
    st.markdown('<div class="card"><div class="label">Import workspace</div>'
                '<p style="font-size:12px;color:var(--muted);margin-bottom:8px">'
                "Load a previously-exported JSON to restore your workspace.</p>",
                unsafe_allow_html=True)
    uploaded = st.file_uploader("Workspace JSON", type=["json"],
                                label_visibility="collapsed", key="ws_import")
    if uploaded:
        try:
            data = json.load(uploaded)
            # Backward compat: older exports used "items" instead of "submissions"
            if "items" in data and "submissions" not in data:
                data["submissions"] = data.pop("items")
            for k in ("features", "workflows", "templates", "change_types",
                      "reviewers", "submissions", "users"):
                if k in data:
                    st.session_state[k] = data[k]
                    persist(k)
            st.success("Workspace imported.")
            st.rerun()
        except Exception as e:
            st.error(f"Import failed: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

    # Reset
    st.markdown('<div class="card" style="border-color:rgba(160,67,44,0.3)">'
                '<div class="label">Reset</div>'
                '<p style="font-size:12px;color:var(--muted);margin-bottom:8px">'
                "Wipe all submissions and restore defaults. Users are preserved.</p>",
                unsafe_allow_html=True)
    confirm = st.checkbox("I understand this is permanent.", key="reset_confirm")
    if st.button("Reset data (keep users)", type="secondary", disabled=not confirm):
        st.session_state.features = DEFAULT_FEATURES.copy()
        st.session_state.templates = [t.copy() for t in DEFAULT_TEMPLATES]
        st.session_state.change_types = [t.copy() for t in DEFAULT_CHANGE_TYPES]
        st.session_state.reviewers = [r.copy() for r in DEFAULT_REVIEWERS]
        st.session_state.workflows = [w.copy() for w in DEFAULT_WORKFLOWS]
        st.session_state.submissions = []
        for k in ("features", "templates", "change_types", "reviewers", "workflows", "submissions"):
            persist(k)
        st.success("Data reset.")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def render_user_management():
    me = current_user()
    st.markdown('<div class="card"><div class="label">Users & access</div>',
                unsafe_allow_html=True)

    users = sorted(st.session_state.users, key=lambda u: (u.get("role", ""), u.get("name", "")))
    if not users:
        st.markdown('<div style="font-size:12px;color:var(--muted)">No users.</div>',
                    unsafe_allow_html=True)
    else:
        for u in users:
            is_me = me and u["id"] == me["id"]
            active = u.get("active", True)
            last_login = (datetime.fromtimestamp(u["lastLogin"]/1000).strftime("%b %d, %Y %H:%M")
                          if u.get("lastLogin") else "never")
            label_parts = [f"<strong>{u['name']}</strong>", role_badge(u['role'])]
            if is_me: label_parts.append('<span class="pill" style="margin-left:4px">you</span>')
            if not active: label_parts.append('<span class="pill warn">deactivated</span>')

            with st.expander(f"{u['name']}  ·  @{u['username']}  ·  {ROLE_LABELS[u['role']]}",
                             expanded=False):
                st.markdown(' '.join(label_parts), unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:11px;color:var(--muted);margin-top:4px'>"
                            f"Last login: {last_login}</div>", unsafe_allow_html=True)

                with st.form(f"edit_user_{u['id']}"):
                    new_name = st.text_input("Display name", value=u["name"])
                    new_role = st.selectbox("Role", list(ROLE_LABELS.keys()),
                                             index=list(ROLE_LABELS.keys()).index(u["role"]),
                                             format_func=lambda r: ROLE_LABELS[r],
                                             disabled=is_me,
                                             help="You can't change your own role.")
                    new_active = st.checkbox("Active", value=active, disabled=is_me)
                    st.markdown('<div class="label" style="margin-top:8px">Reset password '
                                "(optional)</div>", unsafe_allow_html=True)
                    new_pw = st.text_input("New password", type="password", key=f"pw_{u['id']}")

                    col1, col2 = st.columns([1, 1])
                    save = col1.form_submit_button("Save")
                    delete = col2.form_submit_button("Delete user", type="secondary",
                                                     disabled=is_me)

                    if save:
                        updates = {"name": new_name.strip() or u["name"]}
                        if not is_me:
                            updates["role"] = new_role
                            updates["active"] = new_active
                        if new_pw:
                            if len(new_pw) < 8:
                                st.error("Password must be at least 8 characters.")
                            else:
                                updates["password_hash"] = hash_password(new_pw)
                        if "password_hash" in updates or len(new_pw) == 0:
                            update_user(u["id"], updates)
                            st.success("Saved.")
                            st.rerun()

                    if delete:
                        ok, err = delete_user(u["id"])
                        if ok:
                            st.success("User deleted.")
                            st.rerun()
                        else:
                            st.error(err)

    # Add user
    with st.expander("+ Add new user", expanded=False):
        with st.form("add_user_form"):
            n_name = st.text_input("Display name", placeholder="Jamie Patel")
            n_user = st.text_input("Username", placeholder="jamie",
                                    help="3–30 characters, letters/digits/._-")
            n_pw = st.text_input("Initial password (min 8 chars)", type="password")
            n_role = st.selectbox("Role", list(ROLE_LABELS.keys()),
                                   format_func=lambda r: f"{ROLE_LABELS[r]} — "
                                   + {"admin": "full access",
                                      "lead": "review & approve up to lead-review",
                                      "submitter": "submit & see own items",
                                      "viewer": "read-only"}[r])
            if st.form_submit_button("Create user"):
                if not n_name.strip() or not n_user.strip() or not n_pw:
                    st.error("All fields are required.")
                else:
                    ok, result = create_user(n_user.strip(), n_pw, n_name.strip(), n_role)
                    if not ok:
                        st.error(result)
                    else:
                        st.success(f"Created user '{n_user}'. Share the password with them securely.")
                        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def render_editable_list(title, state_key, kind):
    st.markdown(f'<div class="card"><div class="label">{title}</div>', unsafe_allow_html=True)
    items = st.session_state[state_key]
    for i, item in enumerate(items):
        with st.expander(item["name"], expanded=False):
            edited = render_item_editor(item, kind, key_prefix=f"{state_key}_{i}")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Save", key=f"save_{state_key}_{i}"):
                    items[i] = edited
                    st.session_state[state_key] = items
                    persist(state_key)
                    st.success("Saved")
                    st.rerun()
            with c2:
                if st.button("Delete", key=f"del_{state_key}_{i}", type="secondary"):
                    st.session_state[state_key] = [x for j, x in enumerate(items) if j != i]
                    persist(state_key)
                    st.rerun()
    with st.expander(f"+ Add new {kind}", expanded=False):
        blank = blank_item(kind)
        edited = render_item_editor(blank, kind, key_prefix=f"new_{state_key}")
        if st.button("Create", key=f"create_{state_key}"):
            if edited.get("name", "").strip():
                edited["id"] = f"{kind}_{int(datetime.utcnow().timestamp() * 1000)}"
                st.session_state[state_key] = [*items, edited]
                persist(state_key)
                st.success("Added")
                st.rerun()
            else:
                st.error("Name required.")
    st.markdown('</div>', unsafe_allow_html=True)


def blank_item(kind):
    if kind == "reviewer":
        return {"name": "", "role": "Team Lead", "expertise": [], "capacity": 4}
    return {"name": "", "description": "", "tags": [], "defaultWorkflow": "standard",
            "checkpoints": [], "requiredApprovals": [], "sla": "", "conditions": [],
            "riskBase": 2}


def render_item_editor(item, kind, key_prefix):
    draft = dict(item)
    draft["name"] = st.text_input("Name", value=draft.get("name", ""), key=f"{key_prefix}_name")
    if kind != "reviewer":
        draft["description"] = st.text_area("Description", value=draft.get("description", ""),
                                             key=f"{key_prefix}_desc", height=80)
    if kind == "reviewer":
        draft["role"] = st.text_input("Role", value=draft.get("role", ""), key=f"{key_prefix}_role")
        draft["expertise"] = [s.strip() for s in st.text_input(
            "Expertise tags (comma-separated)", value=", ".join(draft.get("expertise", [])),
            key=f"{key_prefix}_exp",
            help="e.g. software, regulated, large-team").split(",") if s.strip()]
        draft["capacity"] = st.number_input("Capacity (max concurrent items)",
                                             value=int(draft.get("capacity", 4)),
                                             min_value=1, max_value=20,
                                             key=f"{key_prefix}_cap")
    if kind == "template":
        draft["tags"] = [s.strip() for s in st.text_input(
            "Tags (comma-separated — match wizard answers)",
            value=", ".join(draft.get("tags", [])), key=f"{key_prefix}_tags",
            help="e.g. software, medium-duration, iterative").split(",") if s.strip()]
        draft["checkpoints"] = [s.strip() for s in st.text_input(
            "Checkpoints (comma-separated)", value=", ".join(draft.get("checkpoints", [])),
            key=f"{key_prefix}_cp").split(",") if s.strip()]
        wf_ids = [w["id"] for w in st.session_state.workflows]
        draft["defaultWorkflow"] = st.selectbox(
            "Default workflow", wf_ids,
            index=wf_ids.index(draft.get("defaultWorkflow", "standard"))
                  if draft.get("defaultWorkflow") in wf_ids else 0,
            key=f"{key_prefix}_wf")
        draft["sla"] = st.text_input("SLA (e.g. '5 business days', 'Same business day')",
                                      value=draft.get("sla", ""), key=f"{key_prefix}_sla_tpl")
        draft["riskBase"] = st.number_input("Risk base (0–5)",
                                             value=int(draft.get("riskBase", 2)),
                                             min_value=0, max_value=5,
                                             key=f"{key_prefix}_risk")
    if kind == "changeType":
        draft["conditions"] = [s.strip() for s in st.text_input(
            "Conditions (comma-separated — match wizard answers)",
            value=", ".join(draft.get("conditions", [])),
            key=f"{key_prefix}_cond").split(",") if s.strip()]
        draft["requiredApprovals"] = [s.strip() for s in st.text_input(
            "Required approvals (comma-separated)",
            value=", ".join(draft.get("requiredApprovals", [])),
            key=f"{key_prefix}_appr").split(",") if s.strip()]
        draft["sla"] = st.text_input("SLA", value=draft.get("sla", ""),
                                      key=f"{key_prefix}_sla")
        wf_ids = [w["id"] for w in st.session_state.workflows]
        draft["defaultWorkflow"] = st.selectbox(
            "Default workflow", wf_ids,
            index=wf_ids.index(draft.get("defaultWorkflow", "standard"))
                  if draft.get("defaultWorkflow") in wf_ids else 0,
            key=f"{key_prefix}_wf2")
        draft["riskBase"] = st.number_input("Risk base (0–5)",
                                             value=int(draft.get("riskBase", 2)),
                                             min_value=0, max_value=5,
                                             key=f"{key_prefix}_risk2")
    return draft

# ============================================================================
# MAIN
# ============================================================================
def render_authenticated_app():
    """Renders the main app — sidebar + content — for an authenticated user."""
    user = current_user()
    if "page" not in st.session_state:
        st.session_state.page = "Home"

    with st.sidebar:
        st.markdown('<div style="padding:8px 0 12px 0">'
                    '<div class="display" style="font-size:26px;line-height:1.1">Hughes Guide</div>'
                    '<div style="font-size:9px;text-transform:uppercase;letter-spacing:0.2em;'
                    'color:#8A8A8A;margin-top:2px">Decision support · Routing · QA</div></div>',
                    unsafe_allow_html=True)

        # User card
        st.markdown(f'<div class="card" style="padding:10px 12px;margin-bottom:8px">'
                    f'<div style="font-size:13px"><strong>{user["name"]}</strong> '
                    f'{role_badge(user["role"])}</div>'
                    f'<div style="font-size:11px;color:var(--muted);margin-top:2px">'
                    f'@{user["username"]}</div></div>', unsafe_allow_html=True)

        # Backend badge
        backend = get_backend()
        if backend == "supabase":
            st.markdown('<span class="backend-badge">● Supabase</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="backend-badge local">● Local</span>', unsafe_allow_html=True)

        st.markdown("---")

        # Build pages by permission
        pages = ["Home"]
        if has_perm("submit"): pages.append("Submit")
        if has_perm("view_all") or has_perm("view_own"):
            pages.append("Pipeline")
            if st.session_state.features.get("timelineView"):
                pages.append("Timeline")
        if has_perm("analyze_docs") and st.session_state.features.get("documentAnalysis"):
            pages.append("Documents")
        pages.append("Settings")

        new_page = st.radio("Navigate", pages,
                            index=pages.index(st.session_state.page)
                                  if st.session_state.page in pages else 0,
                            label_visibility="collapsed")
        if new_page != st.session_state.page:
            st.session_state.page = new_page
            st.session_state.detail_id = None
            for k in ("wizard_kind", "wizard_step", "wizard_answers", "wizard_chosen"):
                if k in st.session_state: del st.session_state[k]
            st.rerun()

        # SLA breach badge
        if st.session_state.features.get("slaTracking") and has_perm("view_all"):
            breaches = count_breaches(st.session_state.submissions)
            if breaches > 0:
                st.markdown(f'<div style="margin-top:16px;padding:8px 12px;'
                            f'background:#F2D9D2;border:1px solid #8a2515;border-radius:2px;'
                            f'font-size:11px;color:#8a2515">'
                            f'⚠ <strong>{breaches}</strong> SLA breach'
                            f'{"es" if breaches != 1 else ""}</div>',
                            unsafe_allow_html=True)

        st.markdown("---")
        if st.button("Sign out", type="secondary", use_container_width=True):
            logout()
            st.rerun()
        st.markdown('<div style="font-size:10px;color:#A89E85;text-transform:uppercase;'
                    'letter-spacing:0.15em;margin-top:12px">Hughes Guide · v1.2</div>',
                    unsafe_allow_html=True)

    page = st.session_state.page
    if page == "Home": render_home()
    elif page == "Submit": render_submit()
    elif page == "Pipeline": render_pipeline()
    elif page == "Timeline": render_timeline()
    elif page == "Documents": render_documents()
    elif page == "Settings": render_settings()


def main():
    load_all_state()

    # Auth state machine
    if not is_authenticated():
        # Hide sidebar entirely for public pages
        st.markdown("""<style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="collapsedControl"] {display: none;}
            .main .block-container { padding-top: 0 !important; max-width: 100% !important; }
        </style>""", unsafe_allow_html=True)

        if "auth_view" not in st.session_state:
            st.session_state.auth_view = "landing"

        if needs_first_run():
            render_first_run()
        elif st.session_state.auth_view == "login":
            render_login()
        else:
            render_landing()
        return

    render_authenticated_app()


if __name__ == "__main__":
    main()
