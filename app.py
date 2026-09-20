import os
import re
import json
import html
import time
import textwrap
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from html.parser import HTMLParser
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

import tools.gmail_tool as gmail_tool
from tools.supabase_auth import (
    SupabaseAuthError,
    request_password_reset,
    sign_in,
    sign_out,
    sign_up,
)

load_dotenv()


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="MailMind AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# LLM SETUP
# =========================================================

try:
    from llm_service import get_llm_model

    gemini_model = get_llm_model()
except Exception:
    gemini_model = None


# =========================================================
# CONSTANTS
# =========================================================

CATEGORIES = [
    "Urgent",
    "Important",
    "Immediate Reply",
    "Fake / Spam",
    "Newsletter",
    "General",
]

CATEGORY_ICONS = {
    "Urgent": "🔴",
    "Important": "🟠",
    "Immediate Reply": "🟡",
    "Fake / Spam": "🚨",
    "Newsletter": "📰",
    "General": "📩",
}

CATEGORY_CLASSES = {
    "Urgent": "urgent",
    "Important": "important",
    "Immediate Reply": "reply",
    "Fake / Spam": "spam",
    "Newsletter": "newsletter",
    "General": "general",
}

THEMES = {
    "Teal & Amber": {
        "primary": "#237b73",
        "primary_dark": "#1b655f",
        "soft": "#e8f2f0",
        "highlight": "#f2c14e",
    },
    "Cobalt & Coral": {
        "primary": "#285a8f",
        "primary_dark": "#1f476f",
        "soft": "#e8eff7",
        "highlight": "#ef8967",
    },
    "Forest & Gold": {
        "primary": "#3f6f52",
        "primary_dark": "#31573f",
        "soft": "#eaf1eb",
        "highlight": "#d5a928",
    },
}

EMAIL_VALIDATION_API_KEY = os.getenv(
    "ABSTRACT_EMAIL_VALIDATION_API_KEY"
)


# =========================================================
# SESSION STATE
# =========================================================

if "gmail_service" not in st.session_state:
    st.session_state.gmail_service = None

if "emails" not in st.session_state:
    st.session_state.emails = []

if "classified_emails" not in st.session_state:
    st.session_state.classified_emails = []

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "last_sync" not in st.session_state:
    st.session_state.last_sync = "Not synced"

if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "Teal & Amber"

if "show_appearance" not in st.session_state:
    st.session_state.show_appearance = False

if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if "login_mode" not in st.session_state:
    st.session_state.login_mode = "Log in"

if "signup_retry_until" not in st.session_state:
    st.session_state.signup_retry_until = 0.0


def render_html(content):
    """Render custom HTML after removing indentation that Markdown may treat as code."""
    cleaned = textwrap.dedent(content).strip()
    cleaned = "\n".join(line.strip() for line in cleaned.splitlines())
    st.markdown(cleaned, unsafe_allow_html=True)


# =========================================================
# PREMIUM CUSTOM CSS
# =========================================================

st.markdown(
    """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(
                circle at 15% 0%,
                rgba(99, 102, 241, 0.16),
                transparent 28%
            ),
            radial-gradient(
                circle at 90% 8%,
                rgba(139, 92, 246, 0.12),
                transparent 25%
            ),
            #080b14;
        color: #f8fafc;
    }

    *, *::before, *::after {
        box-sizing: border-box;
    }

    html, body, [data-testid="stAppViewContainer"], .stApp {
        overflow-x: hidden !important;
    }

    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        padding-left: clamp(1rem, 3vw, 3rem) !important;
        padding-right: clamp(1rem, 3vw, 3rem) !important;
        max-width: 1450px;
        width: 100% !important;
    }

    .stat-card, .glass-card, .email-card, .hero-panel {
        width: 100%;
        max-width: 100%;
        overflow-wrap: anywhere;
    }

    /* SIDEBAR */

    section[data-testid="stSidebar"] {
        background:
            linear-gradient(
                180deg,
                #111827 0%,
                #090d17 100%
            );
        border-right: 1px solid rgba(148, 163, 184, 0.14);
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 1.5rem;
    }

    .sidebar-logo {
        font-size: 25px;
        font-weight: 800;
        letter-spacing: -1px;
        color: #f8fafc;
        margin-bottom: 5px;
    }

    .sidebar-logo span {
        color: #a5b4fc;
    }

    .sidebar-subtitle {
        color: #7f8ba3;
        font-size: 12px;
        line-height: 1.5;
        margin-bottom: 30px;
    }

    .sidebar-section {
        color: #64748b;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1.7px;
        font-weight: 800;
        margin: 25px 0 10px 4px;
    }

    section[data-testid="stSidebar"] .stButton > button {
        border: 1px solid transparent;
        background: transparent;
        color: #aeb9cc;
        text-align: left;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
        transition: all 0.25s ease;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(99, 102, 241, 0.14);
        border-color: rgba(129, 140, 248, 0.25);
        color: #ffffff;
        transform: translateX(4px);
    }

    /* MAIN BUTTONS */

    .stButton > button {
        min-height: 42px;
        border-radius: 11px;
        border: 1px solid rgba(148, 163, 184, 0.18);
        background: rgba(30, 41, 59, 0.65);
        color: #dbe4f2;
        font-weight: 650;
        transition:
            transform 0.25s ease,
            box-shadow 0.25s ease,
            border-color 0.25s ease,
            background 0.25s ease;
    }

    .stButton > button:hover {
        transform: translateY(-3px);
        border-color: rgba(129, 140, 248, 0.75);
        background: rgba(79, 70, 229, 0.22);
        box-shadow: 0 8px 24px rgba(79, 70, 229, 0.20);
    }

    .stButton > button:active {
        transform: translateY(0px) scale(0.98);
    }

    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border: none;
        color: white;
        box-shadow: 0 8px 22px rgba(99, 102, 241, 0.20);
    }

    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #818cf8, #a78bfa);
        box-shadow: 0 10px 30px rgba(99, 102, 241, 0.35);
    }

    /* HERO PANEL */

    .hero-panel {
        position: relative;
        overflow: hidden;
        padding: 34px 38px 36px 38px;
        margin-bottom: 25px;
        border-radius: 24px;
        border: 1px solid rgba(129, 140, 248, 0.20);
        background:
            linear-gradient(
                135deg,
                rgba(30, 41, 72, 0.92),
                rgba(15, 23, 42, 0.95)
            );
        box-shadow:
            0 18px 60px rgba(0, 0, 0, 0.25),
            inset 0 1px 0 rgba(255,255,255,0.04);
        animation: floatingPanel 6s ease-in-out infinite;
    }

    .hero-panel::before {
        content: "";
        position: absolute;
        width: 260px;
        height: 260px;
        top: -130px;
        right: -70px;
        border-radius: 50%;
        background: rgba(99, 102, 241, 0.15);
        filter: blur(10px);
        animation: orbMove 8s ease-in-out infinite;
    }

    .hero-panel::after {
        content: "";
        position: absolute;
        width: 180px;
        height: 180px;
        bottom: -100px;
        left: 35%;
        border-radius: 50%;
        background: rgba(139, 92, 246, 0.10);
        filter: blur(20px);
        animation: orbMoveReverse 10s ease-in-out infinite;
    }

    .hero-topline {
        position: relative;
        z-index: 2;
        display: flex;
        align-items: center;
        gap: 9px;
        color: #a5b4fc;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 2px;
        margin-bottom: 23px;
    }

    .live-dot {
        width: 8px;
        height: 8px;
        background: #4ade80;
        border-radius: 50%;
        box-shadow: 0 0 0 5px rgba(74, 222, 128, 0.10);
        animation: livePulse 2s infinite;
    }

    .hero-content {
        position: relative;
        z-index: 2;
    }

    .hero-logo-row {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 14px;
    }

    .hero-logo {
        width: 62px;
        height: 62px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 18px;
        font-size: 35px;
        color: #ffffff;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        box-shadow: 0 10px 30px rgba(99, 102, 241, 0.30);
        animation: logoFloat 4s ease-in-out infinite;
    }

    .hero-title {
        font-size: 43px;
        line-height: 1;
        font-weight: 800;
        letter-spacing: -2.5px;
        color: #ffffff;
    }

    .hero-title span {
        background: linear-gradient(90deg, #a5b4fc, #c4b5fd);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-description {
        max-width: 650px;
        color: #a8b4ca;
        font-size: 15px;
        line-height: 1.8;
        margin-left: 78px;
    }

    .hero-status {
        display: inline-flex;
        margin-top: 20px;
        margin-left: 78px;
        padding: 8px 13px;
        border-radius: 30px;
        color: #86efac;
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(74, 222, 128, 0.18);
        font-size: 11px;
        font-weight: 700;
    }

    /* SECTION TITLES */

    .section-title {
        font-size: 22px;
        font-weight: 800;
        color: #f8fafc;
        letter-spacing: -0.7px;
        margin-top: 30px;
        margin-bottom: 8px;
    }

    .section-caption {
        color: #718096;
        font-size: 13px;
        margin-bottom: 18px;
    }

    /* STAT CARDS */

    .stat-card {
        position: relative;
        overflow: hidden;
        min-height: 128px;
        padding: 21px;
        border-radius: 17px;
        border: 1px solid rgba(148, 163, 184, 0.16);
        background:
            linear-gradient(
                145deg,
                rgba(24, 34, 56, 0.95),
                rgba(14, 20, 34, 0.98)
            );
        box-shadow: 0 10px 35px rgba(0,0,0,0.13);
        transition: all 0.3s ease;
    }

    .stat-card:hover {
        transform: translateY(-5px);
        border-color: rgba(129, 140, 248, 0.45);
        box-shadow: 0 14px 35px rgba(79, 70, 229, 0.15);
    }

    .stat-card::after {
        content: "";
        position: absolute;
        width: 90px;
        height: 90px;
        right: -35px;
        bottom: -40px;
        border-radius: 50%;
        background: rgba(99, 102, 241, 0.10);
        filter: blur(5px);
    }

    .stat-icon {
        float: right;
        font-size: 21px;
        opacity: 0.9;
    }

    .stat-label {
        color: #8491a7;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.7px;
        margin-bottom: 13px;
    }

    .stat-value {
        color: #f8fafc;
        font-size: 34px;
        font-weight: 800;
        letter-spacing: -1px;
    }

    /* GLASS CARD */

    .glass-card {
        padding: 24px;
        border-radius: 18px;
        border: 1px solid rgba(148, 163, 184, 0.15);
        background:
            linear-gradient(
                145deg,
                rgba(24, 34, 56, 0.90),
                rgba(13, 18, 31, 0.96)
            );
        box-shadow: 0 12px 35px rgba(0,0,0,0.15);
    }

    .glass-card h3 {
        color: #f8fafc;
        margin-top: 0;
    }

    /* EMAIL CARDS */

    .email-card {
        padding: 19px;
        margin: 12px 0;
        border-radius: 16px;
        border: 1px solid rgba(148, 163, 184, 0.14);
        background:
            linear-gradient(
                145deg,
                rgba(22, 31, 51, 0.95),
                rgba(12, 17, 29, 0.98)
            );
        transition: all 0.28s ease;
    }

    .email-card:hover {
        transform: translateX(4px);
        border-color: rgba(129, 140, 248, 0.55);
        box-shadow: 0 10px 28px rgba(79, 70, 229, 0.12);
    }

    .email-subject {
        color: #f8fafc;
        font-size: 15px;
        font-weight: 750;
        margin-bottom: 7px;
    }

    .email-sender {
        color: #7f8da5;
        font-size: 12px;
        margin-bottom: 12px;
    }

    .email-snippet {
        color: #aebbd0;
        font-size: 13px;
        line-height: 1.65;
    }

    /* BADGES */

    .badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 30px;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 0.3px;
        margin-bottom: 12px;
    }

    .badge-urgent {
        color: #fca5a5;
        background: rgba(239,68,68,0.14);
        border: 1px solid rgba(239,68,68,0.18);
    }

    .badge-important {
        color: #fdba74;
        background: rgba(249,115,22,0.14);
        border: 1px solid rgba(249,115,22,0.18);
    }

    .badge-reply {
        color: #fde68a;
        background: rgba(234,179,8,0.14);
        border: 1px solid rgba(234,179,8,0.18);
    }

    .badge-spam {
        color: #fda4af;
        background: rgba(225,29,72,0.14);
        border: 1px solid rgba(225,29,72,0.18);
    }

    .badge-newsletter {
        color: #93c5fd;
        background: rgba(59,130,246,0.14);
        border: 1px solid rgba(59,130,246,0.18);
    }

    .badge-general {
        color: #c4b5fd;
        background: rgba(139,92,246,0.14);
        border: 1px solid rgba(139,92,246,0.18);
    }

    /* AI BOX */

    .ai-box {
        padding: 17px;
        margin-top: 13px;
        border-radius: 14px;
        background: rgba(99, 102, 241, 0.07);
        border: 1px solid rgba(129, 140, 248, 0.20);
    }

    .ai-title {
        color: #a5b4fc;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }

    .ai-text {
        color: #b8c4d9;
        font-size: 13px;
        line-height: 1.65;
    }

    .muted {
        color: #8491a7;
        font-size: 13px;
    }

    /* STATUS BOXES */

    .success-box {
        padding: 11px 14px;
        border-radius: 10px;
        color: #86efac;
        background: rgba(34,197,94,0.09);
        border: 1px solid rgba(34,197,94,0.20);
        font-size: 12px;
        font-weight: 650;
    }

    .warning-box {
        padding: 11px 14px;
        border-radius: 10px;
        color: #fcd34d;
        background: rgba(245,158,11,0.09);
        border: 1px solid rgba(245,158,11,0.20);
        font-size: 12px;
        font-weight: 650;
    }

    /* EXPANDER */

    div[data-testid="stExpander"] {
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 14px;
        background: rgba(15, 23, 42, 0.45);
    }

    /* INPUTS */

    .stTextInput input,
    .stTextArea textarea {
        background: rgba(15, 23, 42, 0.75) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(148, 163, 184, 0.20) !important;
        border-radius: 10px !important;
    }

    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border-color: #818cf8 !important;
        box-shadow: 0 0 0 1px #818cf8 !important;
    }

    /* FOOTER */

    .footer {
        text-align: center;
        color: #4b5563;
        font-size: 11px;
        margin-top: 65px;
        padding: 20px 0;
        border-top: 1px solid rgba(148, 163, 184, 0.08);
    }

    /* ANIMATIONS */

    @keyframes floatingPanel {
        0%, 100% {
            transform: translateY(0px);
        }

        50% {
            transform: translateY(-4px);
        }
    }

    @keyframes logoFloat {
        0%, 100% {
            transform: translateY(0px) rotate(0deg);
        }

        50% {
            transform: translateY(-6px) rotate(2deg);
        }
    }

    @keyframes livePulse {
        0%, 100% {
            opacity: 1;
            box-shadow: 0 0 0 5px rgba(74, 222, 128, 0.10);
        }

        50% {
            opacity: 0.55;
            box-shadow: 0 0 0 9px rgba(74, 222, 128, 0.03);
        }
    }

    @keyframes orbMove {
        0%, 100% {
            transform: translate(0, 0);
        }

        50% {
            transform: translate(-30px, 25px);
        }
    }

    @keyframes orbMoveReverse {
        0%, 100% {
            transform: translate(0, 0);
        }

        50% {
            transform: translate(35px, -20px);
        }
    }


    @media (max-width: 700px) {
        .hero-panel {
            padding: 26px 22px !important;
        }

        .hero-title {
            font-size: 32px !important;
            letter-spacing: -1.5px !important;
        }

        .hero-logo {
            width: 50px !important;
            height: 50px !important;
            font-size: 28px !important;
        }

        .hero-description,
        .hero-status {
            margin-left: 0 !important;
        }

        .hero-description {
            font-size: 14px !important;
        }
    }

    /* PROFESSIONAL WORKSPACE THEME */

    .stApp {
        background: #f4f1eb;
        color: #172033;
    }

    section[data-testid="stSidebar"] {
        background: #172b3a;
        border-right-color: rgba(255, 255, 255, 0.10);
    }

    .sidebar-logo,
    .hero-title,
    .section-title,
    .stat-value,
    .glass-card h3 {
        color: #172033;
    }

    section[data-testid="stSidebar"] .sidebar-logo {
        color: #f7f4ee;
    }

    .sidebar-logo span,
    .hero-topline {
        color: #f2c14e;
    }

    .sidebar-subtitle,
    .section-caption,
    .muted {
        color: #687486;
    }

    section[data-testid="stSidebar"] .sidebar-subtitle,
    section[data-testid="stSidebar"] .sidebar-section {
        color: #aebbc2;
    }

    section[data-testid="stSidebar"] .stButton > button {
        color: #d9e2e2;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(242, 193, 78, 0.14);
        border-color: rgba(242, 193, 78, 0.35);
        color: #ffffff;
    }

    .stButton > button {
        background: #ffffff;
        border-color: #d7d8d3;
        color: #203047;
    }

    .stButton > button:hover {
        background: #e8f2f0;
        border-color: #2a7f78;
        box-shadow: 0 8px 24px rgba(42, 127, 120, 0.14);
    }

    div.stButton > button[kind="primary"] {
        background: #237b73;
        color: #ffffff;
        box-shadow: 0 8px 22px rgba(35, 123, 115, 0.20);
    }

    div.stButton > button[kind="primary"]:hover {
        background: #1b655f;
        box-shadow: 0 10px 30px rgba(35, 123, 115, 0.25);
    }

    .hero-panel {
        border-color: rgba(42, 127, 120, 0.35);
        background: linear-gradient(135deg, #173247, #1e5360);
        box-shadow: 0 18px 60px rgba(23, 43, 58, 0.20);
    }

    .hero-panel::before {
        background: rgba(242, 193, 78, 0.12);
    }

    .hero-panel::after {
        background: rgba(42, 127, 120, 0.12);
    }

    .hero-logo {
        background: #f2c14e;
        color: #173247;
        box-shadow: 0 10px 30px rgba(242, 193, 78, 0.24);
    }

    .hero-title span {
        background: none;
        -webkit-text-fill-color: #f2c14e;
    }

    .hero-title {
        color: #f7f4ee;
    }

    .hero-description {
        color: #d5e1e0;
    }

    .stat-card,
    .glass-card,
    .email-card {
        border-color: #dfe1dc;
        background: #ffffff;
        box-shadow: 0 10px 35px rgba(23, 32, 51, 0.07);
    }

    .stat-label,
    .email-sender {
        color: #687486;
    }

    .email-subject {
        color: #172033;
    }

    .email-snippet {
        color: #465467;
    }

    .stat-card:hover,
    .email-card:hover {
        border-color: rgba(42, 127, 120, 0.45);
        box-shadow: 0 14px 35px rgba(42, 127, 120, 0.12);
    }

    .ai-box {
        background: #edf6f4;
        border-color: #c6e1dc;
    }

    .ai-title {
        color: #237b73;
    }

    .ai-text {
        color: #40575a;
    }

    .stTextInput input,
    .stTextArea textarea {
        background: #ffffff !important;
        color: #172033 !important;
        border-color: #d2d7d4 !important;
    }

    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border-color: #2a7f78 !important;
        box-shadow: 0 0 0 1px #2a7f78 !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

active_theme = THEMES.get(
    st.session_state.ui_theme,
    THEMES["Teal & Amber"],
)

st.markdown(
    f"""
    <style>
    :root {{
        --accent: {active_theme['primary']};
        --accent-dark: {active_theme['primary_dark']};
        --accent-soft: {active_theme['soft']};
        --highlight: {active_theme['highlight']};
    }}

    .stButton > button:hover {{
        background: var(--accent-soft);
        border-color: var(--accent);
        box-shadow: 0 8px 24px color-mix(in srgb, var(--accent) 14%, transparent);
    }}

    div.stButton > button[kind="primary"] {{
        background: var(--accent);
        box-shadow: 0 8px 22px color-mix(in srgb, var(--accent) 20%, transparent);
    }}

    div.stButton > button[kind="primary"]:hover {{
        background: var(--accent-dark);
    }}

    .hero-panel {{
        border-color: color-mix(in srgb, var(--accent) 35%, transparent);
    }}

    .hero-panel::before {{
        background: color-mix(in srgb, var(--highlight) 12%, transparent);
    }}

    .hero-logo {{
        background: var(--highlight);
    }}

    .hero-title span,
    .hero-topline,
    .sidebar-logo span,
    .ai-title {{
        color: var(--highlight);
    }}

    .hero-title span {{
        -webkit-text-fill-color: var(--highlight);
    }}

    .robo-mascot {{
        position: absolute;
        left: 4%;
        right: auto;
        bottom: 8%;
        z-index: 2;
        width: 92px;
        height: 104px;
        animation: roboFloat 4s ease-in-out infinite;
    }}

    .robo-logo {{
        position: relative;
        left: auto;
        right: auto;
        bottom: auto;
        flex: 0 0 92px;
    }}

    .hero-description {{
        max-width: 500px;
    }}

    .hero-logo-row {{
        margin-left: 0;
    }}

    .robo-antenna {{
        position: absolute;
        top: 0;
        left: 43px;
        width: 6px;
        height: 18px;
        background: #d5e1e0;
    }}

    .robo-antenna::before {{
        content: "";
        position: absolute;
        top: -7px;
        left: -4px;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: var(--highlight);
        box-shadow: 0 0 0 5px color-mix(in srgb, var(--highlight) 18%, transparent);
        animation: roboSignal 1.8s ease-in-out infinite;
    }}

    .robo-head {{
        position: absolute;
        top: 15px;
        left: 12px;
        width: 68px;
        height: 54px;
        border: 4px solid #d5e1e0;
        border-radius: 18px;
        background: #173247;
        box-shadow: inset 0 -7px 0 rgba(0, 0, 0, 0.12);
    }}

    .robo-eye {{
        position: absolute;
        top: 18px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--highlight);
        animation: roboBlink 4s infinite;
    }}

    .robo-eye.left {{
        left: 15px;
    }}

    .robo-eye.right {{
        right: 15px;
    }}

    .robo-mouth {{
        position: absolute;
        left: 24px;
        bottom: 9px;
        width: 20px;
        height: 4px;
        border-radius: 4px;
        background: #6ed3c9;
    }}

    .robo-body {{
        position: absolute;
        left: 22px;
        bottom: 0;
        width: 48px;
        height: 38px;
        border-radius: 12px 12px 15px 15px;
        background: var(--highlight);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.16);
    }}

    .robo-body::before,
    .robo-body::after {{
        content: "";
        position: absolute;
        top: 12px;
        width: 8px;
        height: 20px;
        border-radius: 8px;
        background: #d5e1e0;
    }}

    .robo-body::before {{
        left: -9px;
        transform: rotate(18deg);
    }}

    .robo-body::after {{
        right: -9px;
        transform: rotate(-18deg);
    }}

    @keyframes roboFloat {{
        0%, 100% {{ transform: translateY(0) rotate(-2deg); }}
        50% {{ transform: translateY(-9px) rotate(2deg); }}
    }}

    @keyframes roboSignal {{
        0%, 100% {{ opacity: 0.55; transform: scale(0.85); }}
        50% {{ opacity: 1; transform: scale(1.1); }}
    }}

    @keyframes roboBlink {{
        0%, 44%, 48%, 100% {{ transform: scaleY(1); }}
        46% {{ transform: scaleY(0.1); }}
    }}

    @media (max-width: 700px) {{
        .robo-mascot {{
            display: none;
        }}
    }}

    .ai-box {{
        background: color-mix(in srgb, var(--accent) 8%, white);
        border-color: color-mix(in srgb, var(--accent) 25%, white);
    }}

    .stTextInput input:focus,
    .stTextArea textarea:focus {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 1px var(--accent) !important;
    }}

    .stTextInput label,
    .stTextArea label,
    .stSelectbox label {{
        color: #465467 !important;
    }}

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {{
        color: #7a8694 !important;
        opacity: 1 !important;
    }}

    @keyframes revealUp {{
        from {{
            opacity: 0;
            transform: translateY(14px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    .hero-topline,
    .hero-content,
    .section-title,
    .section-caption,
    .stat-card,
    .email-card,
    .glass-card {{
        animation: revealUp 0.55s ease-out both;
    }}

    .hero-content {{
        animation-delay: 0.10s;
    }}

    .stat-card {{
        animation-delay: 0.18s;
    }}

    .email-card {{
        animation-delay: 0.12s;
    }}

    @media (prefers-reduced-motion: reduce) {{
        *, *::before, *::after {{
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            scroll-behavior: auto !important;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def safe_text(value):
    return html.escape(str(value or ""))


class EmailHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        if data.strip():
            self.text_parts.append(data.strip())

    def get_text(self):
        return "\n".join(self.text_parts)


def readable_email_body(value):
    body = str(value or "")

    if not re.search(r"<\s*[a-zA-Z][^>]*>", body):
        return body

    parser = EmailHTMLParser()

    try:
        parser.feed(body)
        parsed_body = parser.get_text().strip()
        return parsed_body or html.unescape(body)
    except Exception:
        return html.unescape(re.sub(r"<[^>]+>", "", body)).strip()


def get_category_badge(category):
    category_class = CATEGORY_CLASSES.get(category, "general")
    icon = CATEGORY_ICONS.get(category, "📩")

    return (
        f'<span class="badge badge-{category_class}">'
        f"{icon} {safe_text(category)}"
        f"</span>"
    )


def fallback_classifier(subject, content):
    text = f"{subject} {content}".lower()

    urgent_words = [
        "urgent",
        "immediately",
        "suspended",
        "deadline today",
        "expires today",
        "security alert",
        "account blocked",
        "final warning",
        "within 24 hours",
    ]

    important_words = [
        "assignment",
        "project",
        "exam",
        "college",
        "meeting",
        "interview",
        "registration",
        "deadline",
        "important",
    ]

    reply_words = [
        "please confirm",
        "reply",
        "respond",
        "let me know",
        "attendance",
        "confirmation required",
        "can you",
        "request",
    ]

    spam_words = [
        "lottery",
        "winner",
        "prize",
        "million",
        "claim reward",
        "click here",
        "congratulations you won",
        "free money",
        "bank details",
        "otp",
    ]

    newsletter_words = [
        "unsubscribe",
        "newsletter",
        "weekly digest",
        "updates",
        "offers",
        "promotion",
        "sale",
        "new articles",
    ]

    if any(word in text for word in urgent_words):
        return "Urgent"

    if any(word in text for word in spam_words):
        return "Fake / Spam"

    if any(word in text for word in reply_words):
        return "Immediate Reply"

    if any(word in text for word in important_words):
        return "Important"

    if any(word in text for word in newsletter_words):
        return "Newsletter"

    return "General"


def fallback_analysis(category, source):
    category_details = {
        "Urgent": (
            "The subject or message contains time-sensitive or security-related language.",
            "Verify the sender and handle the deadline or security request first.",
        ),
        "Important": (
            "The message appears related to work, study, meetings, or a meaningful deadline.",
            "Review the details and add any required deadline or meeting to your calendar.",
        ),
        "Immediate Reply": (
            "The sender appears to be asking for a confirmation, response, or decision.",
            "Reply with the requested confirmation or information.",
        ),
        "Fake / Spam": (
            "The message contains suspicious reward, payment, credential, or click-related language.",
            "Do not click links or share information; report or delete the message.",
        ),
        "Newsletter": (
            "The message looks like a recurring update, promotion, or subscription email.",
            "Skim it when convenient or unsubscribe if it is no longer useful.",
        ),
        "General": (
            "No strong urgency, reply, spam, or newsletter signals were detected.",
            "Review the message and decide whether it needs a reply or follow-up.",
        ),
    }

    reason, action = category_details.get(
        category,
        category_details["General"],
    )

    return {
        "reason": f"{source} {reason}",
        "action": action,
    }


def classify_email(subject, snippet="", body=""):
    content = body.strip() if body and body.strip() else snippet.strip()

    if gemini_model is None:
        category = fallback_classifier(subject, content)
        analysis = fallback_analysis(
            category,
            "Keyword-based analysis was used because Gemini is unavailable.",
        )

        return {
            "category": category,
            "confidence": 65,
            **analysis,
        }

    prompt = f"""
You are an intelligent email triage assistant.

Analyze the following email.

Subject:
{subject}

Email Content:
{content[:12000]}

Choose exactly one category from:

- Urgent
- Important
- Immediate Reply
- Fake / Spam
- Newsletter
- General

Return ONLY valid JSON in this exact format:

{{
  "category": "Urgent",
  "confidence": 95,
  "reason": "Short explanation.",
  "action": "Recommended next action."
}}

Rules:
- confidence must be between 0 and 100.
- Do not use markdown.
- Do not add extra text outside JSON.
"""

    try:
        response = gemini_model.generate_content(prompt)

        result_text = response.text.strip()
        result_text = result_text.replace("```json", "")
        result_text = result_text.replace("```", "")
        result_text = result_text.strip()

        result = json.loads(result_text)

        category = result.get("category", "General")

        if category not in CATEGORIES:
            category = fallback_classifier(subject, content)

        try:
            confidence = int(result.get("confidence", 80))
        except Exception:
            confidence = 80

        confidence = max(0, min(confidence, 100))

        return {
            "category": category,
            "confidence": confidence,
            "reason": result.get(
                "reason",
                "Email analyzed using Gemini AI.",
            ),
            "action": result.get(
                "action",
                "Review this email.",
            ),
        }

    except Exception:
        category = fallback_classifier(subject, content)
        analysis = fallback_analysis(
            category,
            "AI response could not be parsed. Fallback classification was used.",
        )

        return {
            "category": category,
            "confidence": 60,
            **analysis,
        }


def generate_ai_reply(email):
    subject = email.get("subject", "")
    sender = email.get("sender", "")
    body = email.get("body", "") or email.get("snippet", "")

    if gemini_model is None:
        return (
            "Hi,\n\n"
            "Thank you for your email. I have received your message "
            "and will get back to you shortly.\n\n"
            "Regards"
        )

    prompt = f"""
Generate a professional and concise email reply.

Original sender:
{sender}

Subject:
{subject}

Email:
{body[:10000]}

Requirements:
- Keep it natural and polite.
- Do not invent facts.
- Keep it under 120 words.
- Return only the reply body.
"""

    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()

    except Exception:
        return (
            "Hi,\n\n"
            "Thank you for your email. I have received your message "
            "and will respond shortly.\n\n"
            "Regards"
        )


def generate_ai_mail(recipient, subject, purpose, tone):
    if gemini_model is None:
        return (
            f"Hi,\n\n{purpose.strip()}\n\n"
            "Please let me know if you have any questions.\n\n"
            "Regards"
        )

    prompt = f"""
Write a complete professional email.

Recipient: {recipient}
Subject: {subject}
Purpose: {purpose}
Tone: {tone}

Requirements:
- Include a suitable greeting and sign-off.
- Keep it concise and natural.
- Do not invent facts, dates, names, or commitments.
- Return only the email body, without a subject line or markdown.
"""

    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return (
            f"Hi,\n\n{purpose.strip()}\n\n"
            "Please let me know if you have any questions.\n\n"
            "Regards"
        )


def get_email_address(sender):
    match = re.search(r"<([^>]+)>", sender or "")

    if match:
        return match.group(1).strip()

    return sender.strip()


def validate_email_address(email):
    """Validate an address format and, when configured, verify its deliverability."""
    normalized_email = email.strip().lower()

    if not re.fullmatch(
        r"[^\s@]+@[^\s@]+\.[^\s@]+",
        normalized_email,
    ):
        return False, "Enter a valid email address."

    if not EMAIL_VALIDATION_API_KEY:
        return True, ""

    query = urlencode(
        {
            "api_key": EMAIL_VALIDATION_API_KEY,
            "email": normalized_email,
        }
    )
    request = Request(
        f"https://emailvalidation.abstractapi.com/v1/?{query}",
        headers={"Accept": "application/json"},
    )

    try:
        with urlopen(request, timeout=8) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return (
            True,
            "Email verification is temporarily unavailable. Format checked.",
        )

    format_valid = result.get("is_valid_format", {}).get("value", False)
    smtp_valid = result.get("is_smtp_valid", {}).get("value", False)
    mx_found = result.get("is_mx_found", {}).get("value", False)
    is_disposable = result.get("is_disposable_email", {}).get("value", False)

    if not format_valid or not mx_found or not smtp_valid:
        return False, "This email address could not be verified. Check it and try again."

    if is_disposable:
        return False, "Disposable email addresses are not supported."

    return True, ""


def classify_all_emails():
    if not st.session_state.emails:
        st.warning("No emails available for analysis.")
        return

    classified = []

    progress = st.progress(0)
    status = st.empty()

    total = len(st.session_state.emails)

    for index, email in enumerate(st.session_state.emails):
        status.write(
            f"Analyzing email {index + 1} of {total}..."
        )

        ai_result = classify_email(
            email.get("subject", ""),
            email.get("snippet", ""),
            email.get("body", ""),
        )

        email_copy = email.copy()

        email_copy["category"] = ai_result["category"]
        email_copy["confidence"] = ai_result["confidence"]
        email_copy["reason"] = ai_result["reason"]
        email_copy["action"] = ai_result["action"]

        classified.append(email_copy)

        progress.progress((index + 1) / total)

    progress.empty()
    status.empty()

    st.session_state.classified_emails = classified


def get_filtered_emails(search_query="", category_filter="All"):
    emails = st.session_state.classified_emails

    if st.session_state.page in CATEGORIES:
        emails = [
            email for email in emails
            if email.get("category") == st.session_state.page
        ]

    search_query = search_query.strip().lower()

    if category_filter != "All":
        emails = [
            email for email in emails
            if email.get("category") == category_filter
        ]

    if search_query:
        searchable_fields = ("subject", "sender", "snippet", "body")
        emails = [
            email
            for email in emails
            if search_query in " ".join(
                str(email.get(field, ""))
                for field in searchable_fields
            ).lower()
        ]

    return emails


# =========================================================
# LOGIN PAGE
# =========================================================

if not st.session_state.user_email:
    st.markdown(
        """
        <style>
        .login-page {
            max-width: 1180px;
            margin: 0 auto;
            padding: 2.5rem 1rem 3rem;
            position: relative;
        }

        header[data-testid="stHeader"] {
            display: none !important;
        }

        [data-testid="stAppViewContainer"] > .main {
            padding-top: 0 !important;
        }

        .login-visual {
            min-height: 590px;
            padding: 48px 46px 38px;
            border-radius: 28px;
            background:
                radial-gradient(circle at 88% 12%, rgba(242, 193, 78, 0.22), transparent 24%),
                linear-gradient(145deg, #102b3b 0%, #173247 46%, #237b73 100%);
            color: #f8fafc;
            box-shadow: 0 28px 70px rgba(23, 50, 71, 0.22);
            overflow: hidden;
            position: relative;
        }

        .login-visual::before {
            content: "";
            position: absolute;
            inset: 0;
            opacity: 0.2;
            background-image: linear-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px);
            background-size: 34px 34px;
            mask-image: linear-gradient(135deg, black, transparent 70%);
            pointer-events: none;
        }

        .login-visual::after {
            content: "";
            position: absolute;
            width: 220px;
            height: 220px;
            right: -70px;
            bottom: -80px;
            border: 1px solid rgba(242, 193, 78, 0.38);
            border-radius: 50%;
            box-shadow: 0 0 0 28px rgba(242, 193, 78, 0.08),
                0 0 0 58px rgba(242, 193, 78, 0.05);
        }

        .login-kicker {
            position: relative;
            z-index: 1;
            color: #f2c14e;
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }

        .login-visual h1 {
            position: relative;
            z-index: 1;
            max-width: 420px;
            margin: 72px 0 16px;
            color: #f8fafc;
            font-size: clamp(2.4rem, 4.2vw, 4rem);
            letter-spacing: -0.04em;
            line-height: 1.05;
        }

        .login-visual p {
            position: relative;
            z-index: 1;
            max-width: 390px;
            color: #d5e1e0;
            font-size: 1.05rem;
            line-height: 1.65;
        }

        .login-benefits {
            position: relative;
            z-index: 1;
            margin-top: 48px;
            color: #f8fafc;
            font-size: 0.92rem;
            line-height: 2.2;
        }

        .login-benefits span {
            color: #f2c14e;
            margin-right: 8px;
        }

        .login-preview {
            position: absolute;
            right: 28px;
            bottom: 30px;
            z-index: 1;
            width: 220px;
            padding: 14px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            background: rgba(9, 25, 37, 0.52);
            box-shadow: 0 18px 36px rgba(7, 22, 32, 0.2);
            backdrop-filter: blur(12px);
            transform: rotate(-3deg);
        }

        .login-preview-label {
            margin-bottom: 10px;
            color: rgba(255, 255, 255, 0.62);
            font-size: 0.65rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .login-preview-row {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 0;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #f8fafc;
            font-size: 0.75rem;
        }

        .login-preview-dot {
            width: 7px;
            height: 7px;
            flex: 0 0 7px;
            border-radius: 50%;
            background: #f2c14e;
            box-shadow: 0 0 0 4px rgba(242, 193, 78, 0.12);
        }

        .login-form-heading {
            margin: 0 0 0.35rem;
            color: #172033;
            font-size: 1.8rem;
            font-weight: 800;
            letter-spacing: -0.03em;
        }

        .login-form-copy {
            margin: 0 0 1.2rem;
            color: #687486;
            font-size: 0.94rem;
        }

        .login-note {
            margin-top: 1rem;
            color: #687486;
            font-size: 0.82rem;
            text-align: center;
        }

        .login-page [data-testid="stForm"] {
            padding: 1.5rem 1.55rem 1.35rem;
            border: 1px solid rgba(215, 222, 219, 0.9);
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.72);
            box-shadow: 0 20px 48px rgba(23, 50, 71, 0.08);
            backdrop-filter: blur(12px);
        }

        .login-page [data-testid="stFormSubmitButton"] button {
            min-height: 50px;
            margin-top: 0.4rem;
            border: 1px solid #c6e1dc !important;
            border-radius: 13px !important;
            background: #edf6f4 !important;
            color: #237b73 !important;
            letter-spacing: 0.01em;
        }

        .login-page [data-testid="stFormSubmitButton"] button:hover {
            border-color: #237b73 !important;
            background: #e1f0ed !important;
            color: #1b655f !important;
        }

        .login-page [data-testid="stFormSubmitButton"] button[kind="primary"] {
            border-color: #ff4b4b !important;
            background: #ff4b4b !important;
            color: #ffffff !important;
        }

        .login-page [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
            border-color: #e33f3f !important;
            background: #e33f3f !important;
            color: #ffffff !important;
        }

        .login-page [data-testid="stTextInput"] label {
            color: #536273;
            font-size: 0.78rem;
            font-weight: 700;
        }

        .login-page div.stButton > button {
            min-height: 46px;
            border: 1px solid #c6e1dc !important;
            border-radius: 12px !important;
            background: #edf6f4 !important;
            color: #237b73 !important;
            box-shadow: none !important;
            font-weight: 700;
        }

        .login-page div.stButton > button:hover {
            border-color: #237b73 !important;
            background: #e1f0ed !important;
        }

        .login-page div.stButton > button[kind="primary"] {
            border-color: #237b73 !important;
            background: #237b73 !important;
            color: #ffffff !important;
        }

        .login-page .stTextInput input {
            border: 0 !important;
            border-radius: 12px !important;
            background: transparent !important;
            box-shadow: none !important;
        }

        .login-page div[data-testid="stTextInput"] div[data-baseweb="input"] {
            min-height: 48px;
            border: 1px solid #d7dedb !important;
            border-radius: 12px !important;
            background: #ffffff !important;
            outline: none !important;
            box-shadow: 0 4px 14px rgba(23, 50, 71, 0.05) !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .login-page div[data-baseweb="input"] {
            border: 1px solid #d7dedb !important;
            outline: none !important;
        }

        .login-page div[data-baseweb="base-input"] {
            border: 0 !important;
            outline: none !important;
            box-shadow: none !important;
        }

        .login-page div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
        .login-page div[data-baseweb="input"]:focus-within {
            border-color: #d7dedb !important;
            box-shadow: 0 0 0 2px rgba(215, 222, 219, 0.45) !important;
        }

        .login-page .react-aria-TextField > div:focus,
        .login-page .react-aria-TextField > div:focus-visible,
        .login-page .react-aria-TextField input:focus,
        .login-page .react-aria-TextField input:focus-visible {
            outline: none !important;
            border-color: #d7dedb !important;
            box-shadow: none !important;
        }

        div[data-testid="stTextInput"] input {
            border: 0 !important;
            outline: none !important;
            box-shadow: none !important;
            background: transparent !important;
        }

        div[data-testid="stTextInput"] div[data-baseweb="input"] {
            border: 1px solid #d7dedb !important;
            outline: none !important;
            border-radius: 12px !important;
            background: #ffffff !important;
            box-shadow: 0 4px 14px rgba(23, 50, 71, 0.05) !important;
        }

        div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
            border-color: #d7dedb !important;
            box-shadow: 0 0 0 2px rgba(215, 222, 219, 0.45) !important;
        }

        .react-aria-TextField > div {
            min-height: 48px;
            border: 1px solid #d7dedb !important;
            border-radius: 12px !important;
            background: #ffffff !important;
            box-shadow: 0 4px 14px rgba(23, 50, 71, 0.05) !important;
        }

        .react-aria-TextField > div:focus-within {
            border-color: #d7dedb !important;
            box-shadow: 0 0 0 2px rgba(215, 222, 219, 0.45) !important;
        }

        div[data-baseweb="input"]:has(input[type="password"]),
        div[data-baseweb="input"]:has(input[type="text"]) {
            background: #ffffff !important;
            border: 1px solid #d7dedb !important;
            border-radius: 12px !important;
        }

        input[type="password"],
        input[type="text"] {
            color: #172033 !important;
            background: #ffffff !important;
        }

        button[aria-label="Show password"] {
            background: #ffffff !important;
            color: #237b73 !important;
        }

        header[data-testid="stHeader"] {
            background: #172b3a !important;
        }

        header[data-testid="stHeader"] button {
            color: #ffffff !important;
        }

        header[data-testid="stHeader"] button:hover {
            background: rgba(255, 255, 255, 0.12) !important;
        }

        @media (max-width: 800px) {
            .login-page {
                margin-top: 1rem;
                padding-top: 0;
                padding-left: 0;
                padding-right: 0;
            }

            .login-visual {
                min-height: auto;
                padding: 32px 26px;
            }

            .login-visual h1 {
                margin-top: 32px;
            }

            .login-preview {
                position: relative;
                right: auto;
                bottom: auto;
                width: min(220px, 100%);
                margin: 34px 0 0 auto;
            }

            .login-benefits {
                margin-top: 24px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="login-page">', unsafe_allow_html=True)
    visual_column, form_column = st.columns([1.1, 0.9], gap="large")

    with visual_column:
        st.markdown(
            """
            <div class="login-visual">
                <div class="login-kicker">✦ MailMind AI</div>
                <h1>Your inbox, made clearer.</h1>
                <p>Turn a busy inbox into a focused daily queue with intelligent triage, calm organization, and faster replies.</p>
                <div class="login-benefits">
                    <div><span>✓</span> See what needs your attention first</div>
                    <div><span>✓</span> Draft thoughtful replies in less time</div>
                    <div><span>✓</span> Keep your workflow moving</div>
                </div>
                <div class="login-preview" aria-hidden="true">
                    <div class="login-preview-label">Today in your inbox</div>
                    <div class="login-preview-row">
                        <span class="login-preview-dot"></span>
                        3 messages need a reply
                    </div>
                    <div class="login-preview-row">
                        <span class="login-preview-dot"></span>
                        12 newsletters sorted
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with form_column:
        login_mode_column, new_user_mode_column = st.columns(2, gap="small")
        with login_mode_column:
            login_mode_clicked = st.button(
                "Log in",
                key="login_mode_button",
                type=(
                    "primary"
                    if st.session_state.login_mode == "Log in"
                    else "secondary"
                ),
                use_container_width=True,
            )

        with new_user_mode_column:
            new_user_mode_clicked = st.button(
                "New user",
                key="new_user_mode_button",
                type=(
                    "primary"
                    if st.session_state.login_mode == "New user"
                    else "secondary"
                ),
                use_container_width=True,
            )

        if login_mode_clicked and st.session_state.login_mode != "Log in":
            st.session_state.login_mode = "Log in"
            st.rerun()

        if new_user_mode_clicked and st.session_state.login_mode != "New user":
            st.session_state.login_mode = "New user"
            st.rerun()

        if st.session_state.login_mode == "Log in":
            st.markdown(
                """
                <div class="login-form-heading">Welcome back</div>
                <p class="login-form-copy">Sign in to open your inbox workspace.</p>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="login-form-heading">Create your workspace</div>
                <p class="login-form-copy">Set up your account and bring calm to your inbox.</p>
                """,
                unsafe_allow_html=True,
            )

        if st.session_state.login_mode == "Log in":
            with st.form("login_form"):
                email = st.text_input(
                    "Email address",
                    placeholder="you@example.com",
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                )
                submitted = st.form_submit_button(
                    "Log in",
                    type="primary",
                    use_container_width=True,
                )
                reset_requested = st.form_submit_button(
                    "Forgot password?",
                    use_container_width=True,
                )

            if reset_requested:
                normalized_email = email.strip().lower()
                email_is_valid, email_error = validate_email_address(
                    normalized_email
                )
                if not email_is_valid:
                    st.error(email_error)
                else:
                    try:
                        request_password_reset(normalized_email)
                    except SupabaseAuthError as error:
                        st.error(str(error))
                    else:
                        st.success(
                            "If this email is registered, a password reset link has been sent."
                        )

            if submitted:
                normalized_email = email.strip().lower()
                email_is_valid, email_error = validate_email_address(
                    normalized_email
                )

                if not email_is_valid:
                    st.error(email_error)
                else:
                    try:
                        user = sign_in(normalized_email, password)
                    except SupabaseAuthError as error:
                        st.error(str(error))
                    else:
                        st.session_state.user_email = user.email or normalized_email
                        st.rerun()
        else:
            signup_retry_remaining = max(
                0,
                int(st.session_state.signup_retry_until - time.monotonic()),
            )

            with st.form("register_form"):
                name = st.text_input(
                    "Your name",
                    placeholder="Alex Morgan",
                )
                email = st.text_input(
                    "Email address",
                    placeholder="you@example.com",
                )
                password = st.text_input(
                    "Create password",
                    type="password",
                    placeholder="At least 8 characters",
                )
                confirm_password = st.text_input(
                    "Confirm password",
                    type="password",
                    placeholder="Repeat your password",
                )
                submitted = st.form_submit_button(
                    "Create account",
                    type="primary",
                    use_container_width=True,
                    disabled=signup_retry_remaining > 0,
                )

            if signup_retry_remaining > 0:
                st.info(
                    f"Please wait {signup_retry_remaining} seconds before trying again."
                )

            if submitted:
                normalized_email = email.strip().lower()
                email_is_valid, email_error = validate_email_address(
                    normalized_email
                )

                if not name.strip():
                    st.error("Enter your name.")
                elif not email_is_valid:
                    st.error(email_error)
                elif len(password) < 8:
                    st.error("Use a password with at least 8 characters.")
                elif password != confirm_password:
                    st.error("The passwords do not match.")
                else:
                    try:
                        user, session = sign_up(normalized_email, password)
                    except SupabaseAuthError as error:
                        if error.retry_after_seconds:
                            st.session_state.signup_retry_until = (
                                time.monotonic() + error.retry_after_seconds
                            )
                            st.warning(
                                "Please wait before trying again. "
                                f"Supabase rate limit: {error.retry_after_seconds} seconds."
                            )
                        else:
                            st.error(str(error))
                    else:
                        if session is None:
                            st.success(
                                "Account created. Confirm your email, then log in."
                            )
                        else:
                            st.session_state.user_email = user.email or normalized_email
                            st.rerun()

        st.markdown(
            '<div class="login-note">Private workspace access for your email triage.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <div class="sidebar-logo">
            ✦ MailMind <span>AI</span>
        </div>

        <div class="sidebar-subtitle">
            Intelligent inbox automation<br>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-section">Workspace</div>',
        unsafe_allow_html=True,
    )

    sidebar_items = [
        ("Dashboard", "⌂"),
        ("Inbox", "✉"),
        ("Urgent", "🔴"),
        ("Important", "🟠"),
        ("Immediate Reply", "🟡"),
        ("Fake / Spam", "🚨"),
        ("Newsletter", "📰"),
    ]

    for item, icon in sidebar_items:
        if st.button(
            f"{icon}  {item}",
            key=f"nav_{item}",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.page == item
                else "secondary"
            ),
        ):
            st.session_state.page = item
            st.rerun()

    st.markdown(
        '<div class="sidebar-section">Tools</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "🧹  Clear Workspace",
        use_container_width=True,
    ):
        st.session_state.emails = []
        st.session_state.classified_emails = []
        st.session_state.page = "Dashboard"
        st.session_state.last_sync = "Not synced"
        st.session_state.show_appearance = False

        reset_keys = [
            "email_search",
            "email_category_filter",
            "auto_mail_body",
            "auto_mail_recipient",
            "auto_mail_subject",
            "auto_mail_purpose",
            "auto_mail_tone",
        ]

        for key in list(st.session_state):
            if (
                key in reset_keys
                or key.startswith("generated_reply_")
            ):
                del st.session_state[key]

        st.rerun()

    if st.button(
        "🎨  Appearance",
        use_container_width=True,
    ):
        st.session_state.show_appearance = (
            not st.session_state.show_appearance
        )
        st.rerun()

    if st.session_state.show_appearance:
        st.markdown(
            '<div class="sidebar-section">Accent Theme</div>',
            unsafe_allow_html=True,
        )

        st.selectbox(
            "Accent theme",
            list(THEMES),
            key="ui_theme",
            label_visibility="collapsed",
        )

    st.markdown(
        '<div class="sidebar-section">Connection</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.gmail_service:
        st.markdown(
            '<div class="success-box">● Gmail Connected</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="warning-box">○ Gmail Not Connected</div>',
            unsafe_allow_html=True,
        )

# =========================================================
# HERO SECTION
# =========================================================

if st.session_state.gmail_service:
    hero_status = (
        f"● Gmail connected · Last sync: {st.session_state.last_sync}"
    )
else:
    hero_status = "○ Connect Gmail to begin inbox triage"

hero_visibility = (
    ""
    if st.session_state.page == "Dashboard"
    else ' style="display: none;"'
)

render_html(
    f"""
    <div class="hero-panel"{hero_visibility}>

        <div class="hero-topline">
            <span class="live-dot"></span>
            AI-POWERED EMAIL INTELLIGENCE
        </div>

        <div class="hero-content">

            <div class="hero-logo-row">
                <div class="robo-mascot robo-logo" aria-hidden="true">
                    <div class="robo-antenna"></div>
                    <div class="robo-head">
                        <span class="robo-eye left"></span>
                        <span class="robo-eye right"></span>
                        <span class="robo-mouth"></span>
                    </div>
                    <div class="robo-body"></div>
                </div>

                <div class="hero-title">
                    MailMind <span>AI</span>
                </div>
            </div>

            <div class="hero-description">
                Your intelligent email command center.<br>
                Automatically classify, prioritize, understand,
                and respond to your emails with AI.
            </div>

            <div class="hero-status">
                {safe_text(hero_status)}
            </div>

        </div>

    </div>
    """,
)


# =========================================================
# TOP ACTIONS
# =========================================================

col1, col2, col3 = st.columns([1.2, 1.2, 3])

with col1:
    connect_clicked = st.button(
        "🔗 Connect Gmail",
        use_container_width=True,
    )

with col2:
    sync_clicked = st.button(
        "↻ Sync Inbox",
        use_container_width=True,
    )

if connect_clicked:
    try:
        st.session_state.gmail_service = (
            gmail_tool.get_gmail_service()
        )
        st.success("Gmail connected successfully.")

    except Exception as error:
        st.error(f"Gmail connection failed: {error}")


if sync_clicked:
    if not st.session_state.gmail_service:
        st.warning("Please connect Gmail first.")

    else:
        with st.spinner("Fetching unread emails..."):
            fetched_emails = gmail_tool.get_unread_emails(
                st.session_state.gmail_service
            )

        st.session_state.emails = fetched_emails
        st.session_state.classified_emails = []
        st.session_state.last_sync = "Just now"

        st.success(
            f"Fetched {len(fetched_emails)} unread email(s)."
        )


st.caption(
    f"Workspace: {len(st.session_state.emails)} email(s) loaded · "
    f"{len(st.session_state.classified_emails)} analyzed · "
    f"Last sync: {st.session_state.last_sync}"
)


# =========================================================
# DASHBOARD PAGE
# =========================================================

if st.session_state.page == "Dashboard":

    total_emails = len(st.session_state.emails)
    classified_count = len(
        st.session_state.classified_emails
    )

    urgent_count = len(
        [
            email
            for email in st.session_state.classified_emails
            if email.get("category") == "Urgent"
        ]
    )

    reply_count = len(
        [
            email
            for email in st.session_state.classified_emails
            if email.get("category") == "Immediate Reply"
        ]
    )

    st.markdown(
        """
        <div class="section-title">Workspace Overview</div>
        <div class="section-caption">
            A real-time snapshot of your email intelligence system
        </div>
        """,
        unsafe_allow_html=True,
    )

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        render_html(
            f"""
            <div class="stat-card">
                <div class="stat-icon">📨</div>
                <div class="stat-label">TOTAL EMAILS</div>
                <div class="stat-value">{total_emails}</div>
            </div>
            """
        )

    with s2:
        render_html(
            f"""
            <div class="stat-card">
                <div class="stat-icon">🤖</div>
                <div class="stat-label">AI ANALYZED</div>
                <div class="stat-value">{classified_count}</div>
            </div>
            """
        )

    with s3:
        render_html(
            f"""
            <div class="stat-card">
                <div class="stat-icon">🔴</div>
                <div class="stat-label">URGENT EMAILS</div>
                <div class="stat-value">{urgent_count}</div>
            </div>
            """
        )

    with s4:
        render_html(
            f"""
            <div class="stat-card">
                <div class="stat-icon">✍️</div>
                <div class="stat-label">REQUIRES REPLY</div>
                <div class="stat-value">{reply_count}</div>
            </div>
            """
        )

    if st.session_state.emails and not st.session_state.classified_emails:

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
            <div class="glass-card">
                <h3>Ready to analyze your inbox?</h3>
                <p class="muted">
                    Let MailMind AI understand your emails and organize
                    them into intelligent categories.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "✨ Analyze Inbox with AI",
            type="primary",
            use_container_width=True,
        ):
            classify_all_emails()
            st.rerun()

    if st.session_state.classified_emails:

        st.markdown(
            """
            <div class="section-title">Priority Attention</div>
            <div class="section-caption">
                Emails that may need your immediate action
            </div>
            """,
            unsafe_allow_html=True,
        )

        attention_emails = [
            email
            for email in st.session_state.classified_emails
            if email.get("category") in [
                "Urgent",
                "Immediate Reply",
                "Important",
            ]
        ][:5]

        if not attention_emails:
            st.info("No priority emails require your attention.")

        for email in attention_emails:
            category = email.get("category", "General")

            render_html(
                f"""
                <div class="email-card">
                    {get_category_badge(category)}

                    <div class="email-subject">
                        {safe_text(email.get("subject", "No subject"))}
                    </div>

                    <div class="email-sender">
                        {safe_text(email.get("sender", "Unknown sender"))}
                    </div>

                    <div class="email-snippet">
                        {safe_text(email.get("snippet", ""))}
                    </div>
                </div>
                """
            )


# =========================================================
# INBOX / CATEGORY PAGE
# =========================================================

else:

    page_title = st.session_state.page

    st.markdown(
        f"""
        <div class="section-title">{safe_text(page_title)}</div>
        <div class="section-caption">
            Review and manage your categorized emails
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.emails:

        render_html(
            """
            <div class="glass-card">
                <h3>Your inbox is ready</h3>
                <p class="muted">
                    Connect Gmail from the action bar above, then sync your
                    unread messages to start triage.
                </p>
            </div>
            """
        )

    elif not st.session_state.classified_emails:

        st.warning(
            "Emails are loaded but not analyzed yet."
        )

        if st.button(
            "✨ Analyze Emails with AI",
            type="primary",
        ):
            classify_all_emails()
            st.rerun()

    else:

        filter_col1, filter_col2 = st.columns([2, 1])

        with filter_col1:
            search_query = st.text_input(
                "Search emails",
                placeholder="Search subject, sender, or message content",
                key="email_search",
            )

        with filter_col2:
            category_filter = st.selectbox(
                "Filter by category",
                ["All"] + CATEGORIES,
                key="email_category_filter",
            )

        filtered_emails = get_filtered_emails(
            search_query,
            category_filter,
        )

        if not filtered_emails:
            st.info("No emails match the current search and filters.")

        for index, email in enumerate(filtered_emails):

            category = email.get("category", "General")
            confidence = email.get("confidence", 0)
            email_id = email.get("id", str(index))

            render_html(
                f"""
                <div class="email-card">
                    {get_category_badge(category)}

                    <div class="email-subject">
                        {safe_text(email.get("subject", "No subject"))}
                    </div>

                    <div class="email-sender">
                        {safe_text(email.get("sender", "Unknown sender"))}
                    </div>

                    <div class="email-snippet">
                        {safe_text(email.get("snippet", ""))}
                    </div>
                </div>
                """
            )

            reply_key = f"generated_reply_{email_id}"
            read_key = f"read_email_{email_id}"

            quick_col1, quick_col2 = st.columns(2)

            with quick_col1:
                if st.button(
                    "📖 Read Full Mail",
                    key=f"read_{email_id}",
                    use_container_width=True,
                ):
                    st.session_state[read_key] = True

            with quick_col2:
                if st.button(
                    "⚡ Instant Reply",
                    key=f"instant_reply_{email_id}",
                    use_container_width=True,
                ):
                    with st.spinner("Generating instant reply..."):
                        st.session_state[reply_key] = generate_ai_reply(email)

                    st.session_state[read_key] = True

            with st.expander(
                "View Email & AI Analysis",
                expanded=(
                    st.session_state.get(read_key, False)
                    or reply_key in st.session_state
                ),
            ):

                st.markdown("### 📧 Email Content")

                if email.get("html_body"):
                    components.html(
                        email["html_body"],
                        height=520,
                        scrolling=True,
                    )
                else:
                    email_body = readable_email_body(
                        email.get("body")
                        or email.get("snippet")
                        or "No email body available."
                    )

                    st.write(email_body)

                st.markdown("---")

                st.markdown("### 🤖 AI Analysis")

                st.write(
                    f"**AI Confidence: {confidence}%**"
                )

                st.progress(
                    min(max(confidence, 0), 100) / 100
                )

                render_html(
                    f"""
                    <div class="ai-box">

                        <div class="ai-title">
                            🧠 WHY THIS CLASSIFICATION?
                        </div>

                        <div class="ai-text">
                            {safe_text(
                                email.get(
                                    "reason",
                                    "No explanation available.",
                                )
                            )}
                        </div>

                        <br>

                        <div class="ai-title">
                            ⚡ RECOMMENDED ACTION
                        </div>

                        <div class="ai-text">
                            {safe_text(
                                email.get(
                                    "action",
                                    "Review this email manually.",
                                )
                            )}
                        </div>

                    </div>
                    """
                )

                st.markdown("---")

                action_col1, action_col2 = st.columns(2)

                with action_col1:

                    if st.button(
                        "✍️ Generate AI Reply",
                        key=f"reply_{email_id}",
                        use_container_width=True,
                    ):

                        with st.spinner("Generating reply..."):
                            generated_reply = generate_ai_reply(email)

                        st.session_state[
                            f"generated_reply_{email_id}"
                        ] = generated_reply

                with action_col2:

                    if st.button(
                        "✓ Mark as Reviewed",
                        key=f"review_{email_id}",
                        use_container_width=True,
                    ):
                        st.success("Email marked as reviewed.")

                if reply_key in st.session_state:

                    st.markdown("### ✍️ AI-Generated Reply")

                    edited_reply = st.text_area(
                        "Edit reply before creating draft",
                        value=st.session_state[reply_key],
                        height=180,
                        key=f"edit_reply_{email_id}",
                    )

                    recipient = get_email_address(
                        email.get("sender", "")
                    )

                    if st.button(
                        "📨 Create Gmail Draft",
                        key=f"draft_{email_id}",
                        type="primary",
                    ):

                        if st.session_state.gmail_service is None:

                            st.warning(
                                "Connect Gmail first to create a draft."
                            )

                        else:

                            try:

                                gmail_tool.create_draft(
                                    st.session_state.gmail_service,
                                    recipient,
                                    email.get("subject", ""),
                                    edited_reply,
                                )

                                st.success(
                                    "Draft created successfully in Gmail."
                                )

                            except Exception as error:

                                st.error(
                                    f"Could not create draft: {error}"
                                )


# =========================================================
# CUSTOM REPLY AREA
# =========================================================

if st.session_state.page == "Dashboard":

    st.markdown(
        """
        <div class="section-title">Auto Mail Generator</div>
        <div class="section-caption">
            Create a professional email from a short description
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Generate a new email with AI"):

        recipient = st.text_input(
            "Recipient email",
            placeholder="name@example.com",
            key="auto_mail_recipient",
        )

        custom_subject = st.text_input(
            "Email subject",
            placeholder="Example: Project meeting confirmation",
            key="auto_mail_subject",
        )

        custom_body = st.text_area(
            "What should the email say?",
            height=160,
            placeholder="Example: Ask the team to confirm the project meeting time.",
            key="auto_mail_purpose",
        )

        tone = st.selectbox(
            "Tone",
            ["Professional", "Friendly", "Concise", "Formal"],
            key="auto_mail_tone",
        )

        if st.button(
            "✨ Generate Email",
            type="primary",
            key="generate_auto_mail",
        ):

            if not recipient or not custom_subject or not custom_body:

                st.warning(
                    "Please fill in the recipient, subject, and email purpose."
                )

            else:

                with st.spinner("Generating reply..."):
                    generated_mail = generate_ai_mail(
                        recipient,
                        custom_subject,
                        custom_body,
                        tone,
                    )

                st.session_state.auto_mail_body = generated_mail

        if st.session_state.get("auto_mail_body"):
            generated_mail = st.text_area(
                "Edit generated email before sending",
                value=st.session_state.auto_mail_body,
                height=220,
                key="auto_mail_body_editor",
            )

            if st.button(
                "📨 Create Gmail Draft",
                key="create_auto_mail_draft",
            ):
                if not st.session_state.gmail_service:
                    st.warning("Connect Gmail first to create a draft.")
                else:
                    try:
                        gmail_tool.create_draft(
                            st.session_state.gmail_service,
                            recipient,
                            custom_subject,
                            generated_mail,
                        )
                        st.success("Email draft created successfully in Gmail.")
                    except Exception as error:
                        st.error(f"Could not create draft: {error}")


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer">
        ✦ MailMind AI
        <br>
        Intelligent Inbox Automation 
    </div>
    """,
    unsafe_allow_html=True,
)