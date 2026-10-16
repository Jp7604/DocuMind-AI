import os
import re
from typing import Dict, List, Optional

import faiss
import numpy as np
from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from backend.security import sanitize_pdf_text, sanitize_question

load_dotenv()


class RAGEngine:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model = SentenceTransformer(model_name)
        self.index: Optional[faiss.Index] = None
        self.chunks: List[str] = []
        self.metadata: List[Dict[str, object]] = []
        self.cache: Dict[str, Dict[str, object]] = {}
        self.vector_dim: Optional[int] = None
        self.groq_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    @staticmethod
    def sanitize_text(text: str) -> str:
        cleaned = sanitize_pdf_text(text)
        cleaned = re.sub(r"(?i)(ignore\s+(all\s+)?previous\s+instructions|system\s+prompt|developer\s+message)", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    @staticmethod
    def extract_pdf_text(pdf_path: str) -> List[Dict[str, str]]:
        reader = PdfReader(pdf_path)
        pages: List[Dict[str, str]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            cleaned = RAGEngine.sanitize_text(text)
            if cleaned:
                pages.append({"page": page_number, "text": cleaned})
        return pages

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
        if not text:
            return []
        words = text.split()
        chunks: List[str] = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            if end == len(words):
                break
            start = max(start + chunk_size - overlap, 0)
        return chunks

    def build_index(self, pdf_path: str, max_pages: Optional[int] = None) -> Dict[str, int]:
        pages = self.extract_pdf_text(pdf_path)
        if not pages:
            raise ValueError("No readable text found in the PDF.")
        if max_pages is not None and len(pages) > max_pages:
            raise ValueError(f"PDF exceeds the maximum page limit of {max_pages} pages.")

        chunks: List[str] = []
        metadata: List[Dict[str, object]] = []
        for page in pages:
            page_text = page["text"]
            page_chunks = self.chunk_text(page_text)
            for chunk in page_chunks:
                chunks.append(chunk)
                metadata.append({
                    "page": page["page"],
                    "preview": chunk[:180],
                    "score": 0.0,
                })

        if not chunks:
            raise ValueError("No content chunks were generated from the PDF.")

        embeddings = self.model.encode(chunks, convert_to_numpy=True, normalize_embeddings=True)
        embeddings = np.asarray(embeddings, dtype="float32")
        self.vector_dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(self.vector_dim)
        self.index.add(embeddings)
        self.chunks = chunks
        self.metadata = metadata

        return {"pages": len(pages), "chunks": len(chunks), "dim": self.vector_dim}

    def retrieve_top_k(self, question: str, k: int = 4) -> List[Dict[str, object]]:
        if self.index is None or self.chunks == []:
            raise ValueError("Please upload and index a PDF first.")

        q_vec = self.model.encode([question], convert_to_numpy=True, normalize_embeddings=True)
        q_vec = np.asarray(q_vec, dtype="float32")
        scores, indices = self.index.search(q_vec, k)

        results: List[Dict[str, object]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            item = dict(self.metadata[int(idx)])
            item["score"] = float(score)
            item["content"] = self.chunks[int(idx)]
            results.append(item)
        return results

    def answer(self, question: str) -> Dict[str, object]:
        clean_q = sanitize_question(question, max_len=1000)
        normalized = " ".join(clean_q.strip().split()).lower()
        if not normalized:
            raise ValueError("Question cannot be empty.")

        if normalized in self.cache:
            cached = self.cache[normalized].copy()
            cached["cached"] = True
            return cached

        top_matches = self.retrieve_top_k(clean_q, k=4)
        if not top_matches:
            raise ValueError("No relevant context was found in the indexed PDF.")

        context = "\n\n".join(
            f"[Page {match['page']}] {match['content']}" for match in top_matches
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a careful research assistant. Use the provided PDF context only. "
                    "If the answer is not present, say you cannot determine it from the document. "
                    "Do not invent facts or cite pages you cannot support."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {clean_q}\n\nContext:\n{context}",
            },
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.groq_model,
                messages=messages,
                temperature=0.1,
                max_tokens=512,
            )
        except Exception as exc:
            raise ValueError(f"Groq generation failed for model '{self.groq_model}': {exc}") from exc

        answer_text = response.choices[0].message.content.strip()
        answer_result = {
            "answer": answer_text,
            "sources": [
                {"page": match["page"], "score": round(float(match["score"]), 4), "preview": match["preview"]}
                for match in top_matches
            ],
            "cached": False,
            "tokens_used": getattr(response.usage, "total_tokens", 0) if response.usage else 0,
        }
        self.cache[normalized] = answer_result
        return answer_result
