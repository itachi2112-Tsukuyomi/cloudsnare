"""
VEILGUARD RAG — chat pipeline.

Ties retrieval and generation together:
  1. Build the document corpus from VEILGUARD's data.
  2. Retrieve the top-k documents relevant to the analyst's question.
  3. Ask the LLM to answer using ONLY that retrieved context (grounded,
     so it can't invent events that didn't happen).

The LLM step is optional. With an ANTHROPIC_API_KEY it produces a natural
answer. Without one, it falls back to returning the retrieved records
directly — so the retrieval half is always demonstrable on its own.
"""

import os

from rag.documents import build_documents
from rag.retriever import TfidfRetriever


def _paths():
    from config import (
        CAPTURE_FILE, INTEL_FILE, DECOY_STATE_FILE, REMEDIATION_FILE,
        SNAPSHOT_DIR,
    )
    from mapper.snapshot import list_snapshots
    snaps = list_snapshots(SNAPSHOT_DIR)
    return {
        "capture": CAPTURE_FILE,
        "intel": INTEL_FILE,
        "decoys": DECOY_STATE_FILE,
        "remediation": REMEDIATION_FILE,
        "surface_latest": snaps[-1] if snaps else "",
    }


def retrieve(question, k=4):
    """Build corpus + retrieve top-k relevant documents (no LLM)."""
    docs = build_documents(_paths())
    if not docs:
        return [], 0
    retriever = TfidfRetriever().build(docs)
    return retriever.query(question, k=k), len(docs)


def _llm_answer(question, hits, model):
    """Answer with the configured LLM, grounded in retrieved context. None on failure."""
    context = "\n".join(f"- {h['text']}" for h in hits)
    prompt = (
        "You are a SOC analyst assistant for the VEILGUARD cloud deception "
        "platform. Answer the analyst's question using ONLY the context below, "
        "which are real records from the platform. If the context does not "
        "contain the answer, say so plainly — do not invent events.\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {question}\n\n"
        "Answer concisely and factually."
    )
    try:
        from agent.llm import simple_chat, LLMUnavailable
        try:
            return simple_chat(prompt, max_tokens=500)
        except LLMUnavailable:
            return None
    except Exception:
        return None


def answer(question, k=4):
    """
    Full RAG answer. Returns dict:
      { answer, mode, sources: [retrieved docs] }
    """
    from config import ANTHROPIC_MODEL
    hits, corpus_size = retrieve(question, k=k)

    if not hits:
        return {
            "answer": "No relevant records found. Run the loop (deploy, attack, "
                      "capture, intel) so there is data to search.",
            "mode": "empty",
            "sources": [],
        }

    llm = _llm_answer(question, hits, ANTHROPIC_MODEL)
    if llm:
        return {"answer": llm, "mode": "rag", "sources": hits}

    # retrieval-only fallback (no API key): show what was found
    lines = ["(Retrieval-only mode — set ANTHROPIC_API_KEY for natural answers.)",
             "Most relevant records to your question:"]
    for h in hits:
        lines.append(f"  • {h['text']}")
    return {"answer": "\n".join(lines), "mode": "retrieval-only", "sources": hits}
