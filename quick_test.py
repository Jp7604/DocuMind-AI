from backend.rag_engine import RAGEngine

engine = RAGEngine()
# Replace with an actual PDF path before running
pdf_path = "sample.pdf"

try:
    stats = engine.build_index(pdf_path)
    print(stats)
    print(engine.answer("What is this document about?"))
except FileNotFoundError:
    print(f"Create a PDF named '{pdf_path}' before running this test.")
