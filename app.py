import importlib.util
import os
import subprocess
import sys

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def ensure_requirements():
    required = ["streamlit", "requests", "dotenv"]
    missing = [pkg for pkg in required if importlib.util.find_spec(pkg) is None]
    if missing:
        st.warning("Installing missing requirements...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        except subprocess.CalledProcessError:
            st.error("Automatic dependency setup failed. Run: pip install -r requirements.txt")
            st.stop()


ensure_requirements()


def get_secret(key: str, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


def parse_api_response(response, fallback_message):
    try:
        data = response.json()
    except ValueError:
        text = (response.text or "").strip()
        return {"detail": text[:500] if text else fallback_message}
    return data if isinstance(data, dict) else {"detail": fallback_message}


API_URL = get_secret("API_URL", "http://localhost:8000")
APP_API_KEY = get_secret("APP_API_KEY")
DEBUG_MODE = str(get_secret("DEBUG_MODE", "false")).lower() == "true"

if not APP_API_KEY:
    st.error("APP_API_KEY not configured. Add it to .env (local) or Streamlit secrets (hosted).")
    st.stop()

HEADERS = {"x-api-key": APP_API_KEY}

if DEBUG_MODE:
    st.sidebar.caption(f"Backend: {API_URL}")
    st.sidebar.caption("API key: configured ✓")

st.set_page_config(page_title="DocuMind AI", page_icon="📄", layout="wide")

st.markdown(
    """
    <style>
        :root {
            --bg: #f3efe8;
            --panel: #fbf9f5;
            --panel-strong: #f7f4ee;
            --ink: #1a1a1a;
            --muted: #5d5d5d;
            --line: rgba(16, 16, 16, 0.12);
            --accent: #173f39;
            --accent-soft: #dfe9e6;
            --button: #162f2b;
            --navy: #0E1420;
            --navy-soft: rgba(255,255,255,0.78);
        }

        /* Collapse the native Streamlit header instead of fighting it with negative margins */
        header[data-testid="stHeader"] {
            height: 0rem !important;
            min-height: 0rem !important;
            visibility: hidden;
        }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }

        .stApp {
            background: var(--bg);
            color: var(--ink);
            overflow: visible;
        }
        .block-container {
            max-width: 1180px;
            padding-top: 0 !important;
            margin-top: 0 !important;
            padding-bottom: 3rem;
        }

        .navbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 18px 32px;
            background-color: var(--navy);
            margin: 0 0 32px 0;
            position: relative;
            z-index: 10;
            overflow: visible;
            border-radius: 0;
        }
        .navbar .brand {
            font-size: 19px;
            font-weight: 700;
            color: #FFFFFF;
            line-height: 1.4;
            white-space: nowrap;
            letter-spacing: -0.04em;
        }
        .navbar .nav-links {
            display: flex;
            align-items: center;
            gap: 32px;
        }
        .navbar .nav-links a {
            color: var(--navy-soft);
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            transition: color 0.15s ease;
        }
        .navbar .nav-links a:hover {
            color: #FFFFFF;
        }

        .section {
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.35);
            border-radius: 18px;
            padding: 1.1rem 1.2rem;
        }
        .hero-card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 1.25rem;
        }
        .nav-link {
            color: var(--muted);
            text-decoration: none;
            font-size: 0.95rem;
        }
        h1, h2, h3, h4 {
            letter-spacing: -0.04em;
            line-height: 1.1;
            color: var(--ink);
        }
        p {
            color: var(--muted);
            line-height: 1.7;
        }
        div[data-testid="stChatMessage"] {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255,255,255,0.42);
        }
        div[data-testid="stFileUploaderDropzone"] {
            border: 1px dashed rgba(17, 24, 39, 0.25);
            border-radius: 16px;
            background: rgba(255,255,255,0.2);
        }
        section[data-testid="stSidebar"] {
            background: #0E1420;
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1rem !important;
        }
        section[data-testid="stSidebar"] button {
            color: #FFFFFF !important;
            font-weight: 600 !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
        }
        section[data-testid="stSidebar"] button:hover {
            border-color: rgba(255,255,255,0.3) !important;
        }
        .sidebar-header {
            color: rgba(255,255,255,0.84);
            font-size: 12px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin: 0.5rem 0 0.75rem 0;
            font-weight: 700;
        }
        .sidebar-badge {
            background: rgba(127, 224, 168, 0.12);
            border: 1px solid rgba(127, 224, 168, 0.28);
            border-radius: 8px;
            padding: 10px 12px;
            color: #7FE0A8;
            font-size: 13px;
            font-weight: 600;
            margin: 12px 0;
        }
        .stButton > button {
            border-radius: 10px;
            background: var(--button);
            color: white;
            border: none;
            font-weight: 600;
        }
        .stButton > button:hover {
            background: #112a28;
        }
        .outline-btn > button {
            background: transparent;
            color: var(--ink);
            border: 1px solid var(--line);
        }
        .outline-btn > button:hover {
            background: rgba(23, 63, 57, 0.04);
        }

        @media (max-width: 640px) {
            .navbar {
                flex-direction: column;
                align-items: flex-start;
                gap: 12px;
                padding: 16px 20px;
            }
            .navbar .nav-links {
                gap: 20px;
                flex-wrap: wrap;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "indexed_doc" not in st.session_state:
    st.session_state.indexed_doc = None
if "show_upload_panel" not in st.session_state:
    st.session_state.show_upload_panel = False

st.markdown(
    """
    <div class="navbar">
        <div class="brand">DocuMind AI</div>
        <div class="nav-links">
            <a href="#product">Product</a>
            <a href="#workflow">Workflow</a>
            <a href="#security">Security</a>
            <a href="#demo">Demo</a>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div id='product'></div>", unsafe_allow_html=True)

col_hero_left, col_hero_right = st.columns([1.3, 0.9])

with col_hero_left:
    st.markdown("<div style='padding: 0.4rem 0 0.8rem 0; color:#5d5d5d; font-size: 0.8rem; letter-spacing:0.12em; text-transform:uppercase;'>PDF intelligence for busy teams</div>", unsafe_allow_html=True)
    st.markdown("<h1 style='margin:0 0 1rem 0; font-size: clamp(2.7rem, 5vw, 5rem);'>Ask questions from your documents in seconds.</h1>", unsafe_allow_html=True)
    st.markdown(
        """
        <p style='font-size:1.08rem; max-width:620px; margin:0 0 1.5rem 0;'>DocuMind AI turns contracts, reports, proposals, and research into instant answers. Upload any PDF, index it once, and ask grounded questions with page-level source references.</p>
        """,
        unsafe_allow_html=True,
    )
    cta1, cta2 = st.columns([0.22, 0.2])
    with cta1:
        if st.button("Upload PDF", key="hero_upload_pdf", use_container_width=True):
            st.session_state.show_upload_panel = True
    with cta2:
        if st.button("See workflow", key="hero_see_workflow", use_container_width=True):
            st.session_state.show_upload_panel = False
    st.markdown("<div style='margin-top:1.2rem; color:#4c4c4c; font-size:0.9rem;'>Built for legal, operations, research, and internal knowledge teams.</div>", unsafe_allow_html=True)

with col_hero_right:
    st.markdown(
        """
        <div class='hero-card'>
            <div style='font-size:0.74rem; letter-spacing:0.12em; text-transform:uppercase; color:#5d5d5d; margin-bottom:0.7rem;'>Live document</div>
            <div style='display:flex; justify-content:space-between; align-items:center; padding:0.85rem 0.95rem; border:1px solid rgba(17,17,17,0.12); border-radius:12px; background:#f7f4ef; margin-bottom:0.8rem;'>
                <div>
                    <div style='font-weight:600; color:#1a1a1a;'>Quarterly roadmap.pdf</div>
                    <div style='font-size:0.8rem; color:#5d5d5d;'>12 pages · indexed</div>
                </div>
                <div style='font-size:0.84rem; background:#e6efe8; color:#173f39; padding:0.35rem 0.6rem; border-radius:999px;'>Ready</div>
            </div>
            <div style='padding:0.8rem 0.9rem; border:1px solid rgba(17,17,17,0.12); border-radius:12px; background:#fffdf9;'>
                <div style='font-size:0.72rem; letter-spacing:0.12em; text-transform:uppercase; color:#5d5d5d; margin-bottom:0.45rem;'>Question</div>
                <div style='font-size:1rem; color:#1a1a1a; margin-bottom:0.75rem;'>What are the main delivery risks and dependencies?</div>
                <div style='font-size:0.72rem; letter-spacing:0.12em; text-transform:uppercase; color:#5d5d5d; margin-bottom:0.45rem;'>Answer</div>
                <div style='font-size:0.96rem; color:#222; line-height:1.6;'>The roadmap depends on vendor approvals, infrastructure readiness, and the launch checklist for the sales enablement kit.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

metrics = st.columns(3)
with metrics[0]:
    st.metric("Review time", "minutes")
with metrics[1]:
    st.metric("Source tracking", "page-level")
with metrics[2]:
    st.metric("Security", "API + app auth")

st.markdown("<div id='workflow'></div>", unsafe_allow_html=True)

st.subheader("A clear workflow, from document to answer")
workflow = st.columns(4)
steps = [
    ("01", "Upload", "Drop in a PDF or contract and keep the original source intact."),
    ("02", "Index", "Extract text, split context into chunks, and embed it for smarter retrieval."),
    ("03", "Ask", "Ask natural language questions about the document without hunting through pages."),
    ("04", "Verify", "Review source passages, similarity scores, and grounded answers before sharing."),
]
for i, (n, title, detail) in enumerate(steps):
    with workflow[i]:
        st.markdown(f"""
        <div class='section'>
            <div style='font-size:0.72rem; letter-spacing:0.12em; text-transform:uppercase; color:#5d5d5d; margin-bottom:0.5rem;'>{n}</div>
            <div style='font-weight:700; font-size:1.2rem; margin-bottom:0.4rem; color:#1a1a1a;'>{title}</div>
            <div style='color:#5d5d5d; line-height:1.6;'>{detail}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height:1.1rem;'></div>", unsafe_allow_html=True)

feature_left, feature_right = st.columns([1.0, 1.0])
with feature_left:
    st.markdown(
        """
        <div class='section'>
            <div style='font-size:0.74rem; letter-spacing:0.12em; text-transform:uppercase; color:#5d5d5d; margin-bottom:0.5rem;'>Use cases</div>
            <h3 style='margin:0 0 0.7rem 0;'>The right answer, with context.</h3>
            <p style='margin:0;'>Whether you are checking a contract, summarizing a research brief, or reviewing internal policy, DocuMind keeps the answer anchored to the document rather than guesswork.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with feature_right:
    st.markdown(
        """
        <div class='section'>
            <div style='font-size:0.74rem; letter-spacing:0.12em; text-transform:uppercase; color:#5d5d5d; margin-bottom:0.5rem;'>Built for</div>
            <h3 style='margin:0 0 0.7rem 0;'>Teams working with long-form knowledge.</h3>
            <p style='margin:0;'>Legal ops, product teams, research groups, and internal stakeholders all benefit from a faster, simpler way to digest PDFs without losing traceability.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div id='security'></div>", unsafe_allow_html=True)
security_panel = st.columns(3)
security_copy = [
    ("Private by default", "Keys stay in environment variables and hosted secret stores. The backend validates a custom API key before serving sensitive endpoints."),
    ("Rate limiting", "Upload and ask routes are throttled to reduce abuse and control spend."),
    ("Secure file handling", "Uploads are restricted to PDF files, limited in size, and checked before indexing."),
]
for i, (title, body) in enumerate(security_copy):
    with security_panel[i]:
        st.markdown(
            f"""
            <div class='section'>
                <div style='font-weight:700; font-size:1.08rem; color:#1a1a1a; margin-bottom:0.45rem;'>{title}</div>
                <div style='color:#5d5d5d; line-height:1.6;'>{body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<div id='demo'></div>", unsafe_allow_html=True)

st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)
st.subheader("Try the product")

if st.session_state.get("show_upload_panel"):
    st.markdown(
        """
        <div style='margin: 0 0 1rem 0; padding: 0.75rem 0.9rem; border: 1px solid rgba(17,17,17,0.12); border-radius: 12px; background: rgba(255,255,255,0.35);'>
            <div style='font-size:0.72rem; letter-spacing:0.12em; text-transform:uppercase; color:#5d5d5d;'>Upload</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pdf = st.file_uploader("Choose a PDF to index", type="pdf", label_visibility="collapsed")
    if pdf and st.button("Index document", type="primary", key="hero_index_document"):
        if pdf.size > 10 * 1024 * 1024:
            st.error("File too large. Maximum size is 10MB.")
        else:
            with st.spinner("Indexing document..."):
                try:
                    r = requests.post(
                        f"{API_URL}/upload",
                        files={"file": (pdf.name, pdf.getvalue(), "application/pdf")},
                        headers={"x-api-key": APP_API_KEY},
                        timeout=120,
                    )
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach the backend. Start the FastAPI service and confirm the URL.")
                    st.stop()
                if r.ok:
                    d = parse_api_response(r, "Upload succeeded but no payload was returned.")
                    st.session_state.indexed_doc = pdf.name
                    st.session_state.messages = []
                    st.success(f"Indexed {pdf.name}: {d.get('pages')} pages, {d.get('chunks')} chunks.")
                elif r.status_code == 401:
                    st.error("Unauthorized — check your API key.")
                elif r.status_code == 429:
                    st.error("Rate limit hit. Please wait a moment and try again.")
                else:
                    payload = parse_api_response(r, "Upload failed")
                    st.error(payload.get("detail", "Upload failed"))

with st.sidebar:
    st.markdown('<div class="sidebar-header">Document</div>', unsafe_allow_html=True)
    pdf = st.file_uploader("Upload a PDF", type="pdf", label_visibility="collapsed")
    if pdf:
        st.markdown(
            f'<div class="sidebar-badge">✓ {pdf.name}</div>',
            unsafe_allow_html=True,
        )

    if pdf and st.button("Index document", type="primary", use_container_width=True):
        if pdf.size > 10 * 1024 * 1024:
            st.error("File too large. Maximum size is 10MB.")
        else:
            with st.spinner("Indexing document..."):
                try:
                    r = requests.post(
                        f"{API_URL}/upload",
                        files={"file": (pdf.name, pdf.getvalue(), "application/pdf")},
                        headers={"x-api-key": APP_API_KEY},
                        timeout=120,
                    )
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach the backend. Start the FastAPI service and confirm the URL.")
                    st.stop()
                if r.ok:
                    d = parse_api_response(r, "Upload succeeded but no payload was returned.")
                    st.session_state.indexed_doc = pdf.name
                    st.session_state.messages = []
                    st.success(f"Indexed {pdf.name}: {d.get('pages')} pages, {d.get('chunks')} chunks.")
                elif r.status_code == 401:
                    st.error("Unauthorized — check your API key.")
                elif r.status_code == 429:
                    st.error("Rate limit hit. Please wait a moment and try again.")
                else:
                    payload = parse_api_response(r, "Upload failed")
                    st.error(payload.get("detail", "Upload failed"))

    st.markdown("---")
    st.markdown('<div class="sidebar-header">Controls</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
    with c2:
        if st.button("Reset index", use_container_width=True):
            st.session_state.indexed_doc = None
            st.session_state.messages = []
            st.success("Index cleared.")


demo_col_right = st.columns([1.1])[0]

with demo_col_right:
    samples = [
        "Summarize the document in plain language.",
        "What are the risks or blockers?",
        "What should I prioritize first?",
    ]
    for sample in samples:
        if st.button(sample, key=f"demo_{sample}"):
            st.session_state.pending_question = sample

    if "pending_question" in st.session_state and st.session_state.pending_question:
        q = st.session_state.pending_question
        st.session_state.pending_question = None
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("Answering..."):
                try:
                    r = requests.post(
                        f"{API_URL}/ask",
                        json={"question": q},
                        headers={"x-api-key": APP_API_KEY},
                        timeout=60,
                    )
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach the backend.")
                    st.stop()
                if r.ok:
                    d = parse_api_response(r, "Answer failed")
                    st.markdown(d["answer"])
                    with st.expander("📎 Sources"):
                        for s in d.get("sources", []):
                            st.caption(f"**Page {s['page']}** · similarity `{s['score']}`")
                            st.text(s["preview"])
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": d["answer"],
                        "sources": d.get("sources", []),
                    })
                elif r.status_code == 401:
                    st.error("Unauthorized — check your API key.")
                elif r.status_code == 429:
                    st.error("Rate limit hit. Please wait a minute and try again.")
                elif r.status_code == 409:
                    st.warning("Please upload and index a PDF first.")
                else:
                    payload = parse_api_response(r, "Error")
                    st.error(payload.get("detail", "Error"))

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("sources"):
                with st.expander("Sources"):
                    for s in m["sources"]:
                        st.caption(f"**Page {s['page']}** · similarity `{s['score']}`")
                        st.text(s["preview"])

    if q := st.chat_input("Ask a question about the uploaded document..."):
        if len(q) > 1000:
            st.error("Question too long. Keep it below 1000 characters.")
            st.stop()
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("Generating answer..."):
                try:
                    r = requests.post(
                        f"{API_URL}/ask",
                        json={"question": q},
                        headers={"x-api-key": APP_API_KEY},
                        timeout=60,
                    )
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach the backend.")
                    st.stop()
                if r.ok:
                    d = parse_api_response(r, "Answer failed")
                    st.markdown(d["answer"])
                    with st.expander("Sources"):
                        for s in d.get("sources", []):
                            st.caption(f"**Page {s['page']}** · similarity `{s['score']}`")
                            st.text(s["preview"])
                    st.session_state.messages.append({"role": "assistant", "content": d["answer"], "sources": d.get("sources", [])})
                elif r.status_code == 401:
                    st.error("Unauthorized — check your API key.")
                elif r.status_code == 429:
                    st.error("Rate limit hit. Please wait a minute and try again.")
                elif r.status_code == 409:
                    st.warning("Please upload and index a PDF first.")
                else:
                    payload = parse_api_response(r, "Error")
                    st.error(payload.get("detail", "Error"))

st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

st.markdown("---")

st.subheader("Legal")
st.caption("Drafts for review before production launch.")
with st.expander("Terms of Service"):
    st.markdown(open("docs/terms_of_service.md", encoding="utf-8").read())
with st.expander("Privacy Policy"):
    st.markdown(open("docs/privacy_policy.md", encoding="utf-8").read())
