"""
Google Antigravity Design Theme for MARIP.
Source of Truth: https://antigravity.google/
Theme-only configuration: Design tokens, CSS variables, typography, and component styling.
"""

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Roboto+Mono:wght@400;500&display=swap');

:root {
    /* Page & Surfaces */
    --bg-page: #FFFFFF;
    --bg-surface: #FFFFFF;
    --bg-alt: #F8F9FC;
    --bg-sidebar: #F8F9FC;
    --border-color: #E3E7EF;
    --border-subtle: #ECEFF5;
    
    /* Typography */
    --text-primary: #1F1F1F;
    --text-secondary: #5F6368;
    --text-muted: #80868B;
    
    /* Accents (Google Brand & Antigravity Gradients) */
    --primary-blue: #1A73E8;
    --primary-hover: #1557B0;
    --primary-tint: #E8F0FE;
    --accent-gradient: linear-gradient(135deg, #4285F4 0%, #A142F4 50%, #F538A0 100%);
    --accent-subtle: linear-gradient(135deg, rgba(66,133,244,0.08) 0%, rgba(161,66,244,0.08) 100%);
    --accent-violet: #A142F4;
    --accent-pink: #F538A0;
    
    /* Semantic Colors */
    --color-success: #34A853;
    --color-success-bg: #E6F4EA;
    --color-success-text: #137333;
    --color-warning: #FBBC04;
    --color-warning-bg: #FEF7E0;
    --color-warning-text: #B06000;
    --color-error: #EA4335;
    --color-error-bg: #FCE8E6;
    --color-error-text: #C5221F;
    
    /* Geometry & Elevation */
    --radius-card: 16px;
    --radius-pill: 999px;
    --radius-input: 12px;
    --shadow-soft: 0 1px 3px rgba(60, 64, 67, 0.08), 0 4px 12px rgba(60, 64, 67, 0.04);
    --shadow-hover: 0 4px 12px rgba(60, 64, 67, 0.12), 0 8px 24px rgba(60, 64, 67, 0.08);
    --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

/* ═══ Global Streamlit Structure ═════════════════════════════════════════════ */
.stApp {
    background-color: var(--bg-page) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-family) !important;
}

.main .block-container {
    background-color: var(--bg-page) !important;
    padding: 1.5rem 2.5rem !important;
    max-width: 1380px !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border-color) !important;
    padding-top: 1rem !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.6rem;
}
[data-testid="stSidebar"] hr {
    border-color: var(--border-color) !important;
}

/* Typography Defaults */
h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-family) !important;
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
}
p, span, label, div {
    font-family: var(--font-family);
}

/* Hide Streamlit Clutter */
#MainMenu, footer, header [data-testid="stToolbar"] {
    display: none !important;
}

/* ═══ Hero Header ══════════════════════════════════════════════════════════ */
.hero-header {
    background: linear-gradient(180deg, #F8F9FC 0%, #FFFFFF 100%);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-card);
    padding: 2.2rem 2.5rem;
    margin-bottom: 1.5rem;
    text-align: center;
    box-shadow: var(--shadow-soft);
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--accent-gradient);
}
.hero-title {
    font-size: 2.25rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: var(--accent-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.hero-subtitle {
    color: var(--text-secondary);
    font-size: 1.05rem;
    margin-top: 0.5rem;
    font-weight: 400;
}
.version-badge {
    display: inline-block;
    background: var(--primary-tint);
    border: 1px solid #D2E3FC;
    color: var(--primary-blue);
    padding: 4px 16px;
    border-radius: var(--radius-pill);
    font-size: 0.78rem;
    font-weight: 600;
    margin-top: 0.8rem;
    letter-spacing: 0.3px;
}

/* ═══ Metric Cards ══════════════════════════════════════════════════════════ */
.metric-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 14px;
    padding: 1.25rem 1.4rem;
    position: relative;
    box-shadow: var(--shadow-soft);
    transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-hover);
    border-color: #D2E3FC;
}
.metric-icon {
    font-size: 1.7rem;
    float: right;
    opacity: 0.85;
}
.metric-value {
    font-size: 2.2rem;
    font-weight: 800;
    color: var(--primary-blue) !important;
    line-height: 1.1;
    margin-bottom: 0.25rem;
    letter-spacing: -0.02em;
}
.metric-label {
    font-size: 0.78rem;
    color: var(--text-secondary) !important;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-weight: 600;
}

/* ═══ Agent Cards ═══════════════════════════════════════════════════════════ */
.agent-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 14px;
    padding: 0.85rem 1.15rem;
    margin-bottom: 0.65rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: var(--shadow-soft);
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.agent-card:hover {
    background: #FAFBFE;
    border-color: #D2E3FC;
    box-shadow: var(--shadow-hover);
    transform: translateY(-1px);
}
.agent-left {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    flex: 1;
}
.agent-icon {
    font-size: 1.4rem;
    min-width: 38px;
    height: 38px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--primary-tint);
    border-radius: 10px;
}
.agent-info {
    flex: 1;
}
.agent-name {
    font-size: 0.92rem;
    font-weight: 700;
    color: var(--text-primary) !important;
    letter-spacing: -0.01em;
}
.agent-task {
    font-size: 0.78rem;
    color: var(--text-secondary) !important;
    margin-top: 2px;
}

/* Status Badges */
.status-badge {
    padding: 4px 12px;
    border-radius: var(--radius-pill);
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
}
.status-idle      { background: #F1F3F4; color: #5F6368 !important; border: 1px solid #DADCE0; }
.status-working   { background: #E8F0FE; color: #1A73E8 !important; border: 1px solid #D2E3FC; animation: pulse 2s infinite; }
.status-completed { background: #E6F4EA; color: #137333 !important; border: 1px solid #CEEAD6; }
.status-failed    { background: #FCE8E6; color: #C5221F !important; border: 1px solid #FAD2CF; }
.status-waiting   { background: #FEF7E0; color: #B06000 !important; border: 1px solid #FEEFC3; animation: pulse 2s infinite; }

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.65; }
}

/* ═══ Timeline ══════════════════════════════════════════════════════════════ */
.timeline-entry {
    display: flex;
    align-items: flex-start;
    gap: 0.85rem;
    margin-bottom: 0.65rem;
    padding: 0.85rem 1.1rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    border-left: 3.5px solid var(--primary-blue);
    box-shadow: var(--shadow-soft);
    animation: fadeIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.timeline-entry.error    { border-left-color: var(--color-error); background: #FFF8F7; }
.timeline-entry.feedback { border-left-color: var(--color-warning); background: #FFFDF5; }
.timeline-entry.approval { border-left-color: var(--color-success); background: #F7FCF8; }
.timeline-time {
    font-size: 0.72rem;
    color: var(--text-muted);
    min-width: 55px;
    padding-top: 2px;
    font-family: 'Roboto Mono', monospace;
}
.timeline-icon {
    font-size: 1.1rem;
    min-width: 26px;
    text-align: center;
}
.timeline-content {
    flex: 1;
}
.timeline-agent {
    font-size: 0.82rem;
    font-weight: 700;
    color: var(--primary-blue) !important;
}
.timeline-text {
    font-size: 0.84rem;
    color: #3C4043 !important;
    margin-top: 2px;
    line-height: 1.5;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateX(-6px); }
    to { opacity: 1; transform: translateX(0); }
}

/* ═══ Report Viewer ═════════════════════════════════════════════════════════ */
.report-container {
    background: #FFFFFF;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-card);
    padding: 2.2rem 2.5rem;
    max-height: 640px;
    overflow-y: auto;
    color: #202124;
    line-height: 1.7;
    box-shadow: var(--shadow-soft);
}
.report-container h1, .report-container h2, .report-container h3 {
    color: var(--text-primary) !important;
    margin-top: 1.3rem;
}

/* ═══ Fact Check Cards ══════════════════════════════════════════════════════ */
.fc-card {
    padding: 0.85rem 1.15rem;
    border-radius: 12px;
    margin-bottom: 0.6rem;
    background: #FFFFFF;
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-soft);
}
.fc-verified    { border-left: 3.5px solid var(--color-success); }
.fc-unsupported { border-left: 3.5px solid var(--color-warning); }
.fc-conflicting { border-left: 3.5px solid var(--color-error); }
.fc-unverifiable{ border-left: 3.5px solid var(--text-muted); }
.fc-claim { font-size: 0.86rem; color: var(--text-primary) !important; font-weight: 600; }
.fc-evidence { font-size: 0.8rem; color: var(--text-secondary) !important; margin-top: 3px; }

/* ═══ Progress Bar ══════════════════════════════════════════════════════════ */
.progress-container {
    background: #E8EAED;
    border-radius: var(--radius-pill);
    height: 8px;
    overflow: hidden;
    margin: 0.6rem 0;
}
.progress-fill {
    height: 100%;
    background: var(--accent-gradient);
    border-radius: var(--radius-pill);
    transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ═══ Streamlit Native Controls ═════════════════════════════════════════════ */
/* Buttons */
.stButton > button {
    border-radius: var(--radius-pill) !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.5rem 1.4rem !important;
    border: 1px solid transparent !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    letter-spacing: 0.2px !important;
}

.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background: var(--primary-blue) !important;
    color: #FFFFFF !important;
    box-shadow: 0 1px 3px rgba(26, 115, 232, 0.25) !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    background: var(--primary-hover) !important;
    box-shadow: 0 3px 8px rgba(26, 115, 232, 0.35) !important;
    transform: translateY(-1px) !important;
}

.stButton > button[kind="secondary"],
.stButton > button[data-testid="baseButton-secondary"] {
    background: #FFFFFF !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-color) !important;
}
.stButton > button[kind="secondary"]:hover,
.stButton > button[data-testid="baseButton-secondary"]:hover {
    background: #F8F9FA !important;
    border-color: #BDC1C6 !important;
    transform: translateY(-1px) !important;
}

/* Section Headers */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border-color);
}
.section-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em;
}

/* Form Inputs */
.stTextInput input,
.stTextArea textarea,
.stSelectbox [data-baseweb="select"] {
    background: #FFFFFF !important;
    border: 1px solid #DADCE0 !important;
    color: var(--text-primary) !important;
    border-radius: var(--radius-input) !important;
    box-shadow: none !important;
    font-size: 0.9rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--primary-blue) !important;
    box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.18) !important;
}

/* Expanders */
[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 14px !important;
    box-shadow: var(--shadow-soft) !important;
    margin-bottom: 0.75rem !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: var(--text-primary) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px !important;
    border-bottom: 1px solid var(--border-color) !important;
    padding-bottom: 6px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-pill) !important;
    padding: 6px 18px !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    color: var(--text-secondary) !important;
    background: transparent !important;
    border: none !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: var(--primary-tint) !important;
    color: var(--primary-blue) !important;
    font-weight: 600 !important;
}

/* Alert Boxes (Info, Success, Warning, Error) */
div[data-testid="stAlert"] {
    border-radius: 12px !important;
    box-shadow: var(--shadow-soft) !important;
}
</style>
"""


def apply_antigravity_theme():
    """Inject Google Antigravity design theme into Streamlit app."""
    import streamlit as st
    st.markdown(THEME_CSS, unsafe_allow_html=True)

