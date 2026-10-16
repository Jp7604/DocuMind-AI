import importlib.util
import os
import subprocess
import sys
import tempfile

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def ensure_requirements():
    required = ["streamlit", "dotenv"]
    missing = [pkg for pkg in required if importlib.util.find_spec(pkg) is None]
    if missing:
        st.warning("Installing missing requirements...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        except subprocess.CalledProcessError:
            st.error("Automatic install failed. Run: pip install -r requirements.txt")
            st.stop()


ensure_requirements()


def get_secret(key: str, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


@st.cache_resource
def load_engine():
    from backend.rag_engine import RAGEngine

    return RAGEngine()


GROQ_API_KEY = get_secret("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("GROQ_API_KEY not configured in Streamlit secrets.")
    st.stop()
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

DEMO_PASSWORD = get_secret("DEMO_PASSWORD", None)
if DEMO_PASSWORD:
    pwd = st.sidebar.text_input("Demo password", type="password")
    if pwd != DEMO_PASSWORD:
        st.warning("Enter the demo password in the sidebar to continue.")
        st.stop()

engine = load_engine()

st.set_page_config(page_title="DocuMind AI", page_icon="📄", layout="wide")

st.markdown(
    """
    <style>
        :root {
            --bg: #f3efe8;
            --panel: #fbf9f5;
            --ink: #1a1a1a;
            --muted: #5d5d5d;
            --line: rgba(17,17,17,0.12);
            --accent: #173f39;
        }
        .stApp { background: var(--bg); color: var(--ink); }
        .block-container { max-width: 1180px; padding-top: 1.4rem; }
        .section { background: rgba(255,255,255,0.35); border: 1px solid var(--line); border-radius: 18px; padding: 1rem 1.1rem; }
        .stChatMessage { border-radius: 14px; background: rgba(255,255,255,0.4); border:1px solid var(--line); }
        .stButton > button { border-radius: 10px; background: var(--accent); color: white; border: none; }
        .outline-btn > button { background: transparent; color: var(--ink); border: 1px solid var(--line); }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div style='display:flex; justify-content:space-between; align-items:center; padding:0.2rem 0 1.1rem 0;'><div style='font-weight:700; letter-spacing:-0.05em; font-size:1.2rem;'>DocuMind AI</div><div style='color:#5d5d5d; font-size:0.9rem;'>PDF intelligence</div></div>", unsafe_allow_html=True)

st.title("Ask questions from your PDFs.")
st.caption("A calmer way to review documents, contracts, and research without losing context.")

col1, col2 = st.columns([1.15, 0.85])
with col1:
    st.markdown("<div class='section'><div style='font-size:0.72rem; letter-spacing:0.12em; text-transform:uppercase; color:#5d5d5d; margin-bottom:0.5rem;'>Product</div><h3 style='margin:0;'>Upload once. Ask naturally. Trace every answer.</h3><p style='margin:0.5rem 0 0 0;'>DocuMind reads the PDF, finds relevant passages, and answers grounded questions with page references.</p></div>", unsafe_allow_html=True)
with col2:
    st.markdown("<div class='section'><div style='font-size:0.72rem; letter-spacing:0.12em; text-transform:uppercase; color:#5d5d5d; margin-bottom:0.6rem;'>Status</div><div style='font-size:2rem; font-weight:700;'>Ready</div><div style='color:#5d5d5d; margin-top:0.3rem;'>Source-backed answers · private keys · PDF upload</div></div>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Upload document")
    pdf = st.file_uploader("Choose a PDF", type="pdf")
    if pdf and st.button("Index document", type="primary"):
        if pdf.size > 10 * 1024 * 1024:
            st.error("File too large. Max 10MB.")
            st.stop()
        with st.spinner("Chunking and indexing..."):
            tmp_path = os.path.join(tempfile.gettempdir(), pdf.name)
            with open(tmp_path, "wb") as f:
                f.write(pdf.getvalue())
            try:
                stats = engine.build_index(tmp_path)
                st.success(f"Indexed {stats['pages']} pages and {stats['chunks']} chunks.")
                st.session_state.messages = []
            except ValueError as exc:
                st.error(str(exc))
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    st.divider()
    st.markdown("**Workflow**\nPDF → chunking → embeddings → retrieval → answer")
    if st.button("Clear chat"):
        st.session_state.messages = []
    if st.button("Reset engine"):
        engine.index = None
        engine.chunks = []
        engine.metadata = []
        engine.cache.clear()
        st.session_state.messages = []
        st.success("Engine reset.")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            with st.expander("Sources"):
                for s in m["sources"]:
                    st.caption(f"**Page {s['page']}** · similarity `{s['score']}`")
                    st.text(s["preview"])

if q := st.chat_input("Ask something about the document..."):
    if len(q) > 1000:
        st.error("Question too long.")
        st.stop()
    st.session_state.messages.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        with st.spinner("Summarizing and answering..."):
            try:
                d = engine.answer(q)
                st.markdown(d["answer"])
                badge = "⚡ cached" if d["cached"] else f"🔢 {d['tokens_used']} tokens"
                st.caption(badge)
                with st.expander("Sources"):
                    for s in d["sources"]:
                        st.caption(f"**Page {s['page']}** · similarity `{s['score']}`")
                        st.text(s["preview"])
                st.session_state.messages.append({"role": "assistant", "content": d["answer"], "sources": d["sources"]})
            except ValueError as exc:
                st.warning(str(exc))
