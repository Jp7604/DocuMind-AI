# DocuMind AI

DocuMind AI is a PDF question-answering app powered by a RAG pipeline: PDF parsing, chunking, embedding, FAISS retrieval, and Groq-based answer generation.

## Architecture

PDF → Chunking → MiniLM embeddings → FAISS retrieval → Groq LLM → Answer + sources

## Features

- Upload a PDF and index it
- Ask questions about the document
- Retrieve the top matching page chunks and show source previews
- Rate limiting and API key protection on the backend
- Streamlit app for a simple frontend
- Optional separate backend/frontend deployment model

## Local setup

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
# Windows:
# venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create your local `.env` file from the example if needed:

```bash
cp .env.example .env
```

4. Start the backend:

```bash
uvicorn backend.main:app --reload
```

5. Start the Streamlit UI:

```bash
streamlit run app.py
```

## Security notes

- Never commit your real `.env` file.
- Keep your Groq secret and custom app secret in environment variables or in Streamlit cloud secrets.
- The FastAPI backend requires the `x-api-key` header for protected routes.
- CORS is restricted to configured origins rather than `*`.
- Rate limiting is enabled on upload and ask endpoints.

## GitHub hosting clarification

GitHub Pages only hosts static frontend content. It cannot run Python, FastAPI, or Streamlit apps. For a live demo, use Streamlit Cloud for the app itself, or a separate backend host like Render and point the Streamlit app at it.

## Demo workflow

- Local: run the FastAPI backend and Streamlit app together.
- Hosted demo: deploy `app_standalone.py` on Streamlit Cloud and set secrets in the dashboard.

## Useful commands

```bash
git status
grep -r "gsk_" . --exclude-dir=venv
```
