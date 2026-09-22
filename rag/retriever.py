"""
CLOUDSNARE RAG — retriever (the vector store).

A dependency-free TF-IDF vector index with cosine similarity. This is the
"retrieval" half of Retrieval-Augmented Generation: given a question, it
returns the most relevant documents from the corpus, which are then handed
to the LLM as grounding context.

Why TF-IDF and not neural embeddings? The corpus is small and structured
(event names, IPs, decoy names), so lexical matching is both accurate and
free of heavy dependencies. The retriever is deliberately isolated behind a
simple interface (build / query), so a neural embedder can be dropped in
later without touching the rest of the pipeline.

How it works:
  - tokenize each document into terms
  - term frequency (TF): how often a term appears in a document
  - inverse document frequency (IDF): rare terms are more informative
  - each document becomes a TF-IDF vector; the query too
  - cosine similarity ranks documents by relevance
"""

import re
import math
from collections import Counter


def _tokens(text):
    # split into lowercase word/number tokens; keep things like AKIA... and IPs
    return re.findall(r"[a-z0-9][a-z0-9._-]*", text.lower())


# Light synonym expansion bridges the gap between how analysts phrase questions
# and how the data is worded (e.g. "fix" -> "remediation"). This lifts recall
# for a lexical retriever without any heavy semantic-embedding dependency.
_SYNONYMS = {
    "fix": ["remediation", "remediate", "block"],
    "fixes": ["remediation", "remediate"],
    "exposure": ["exposed", "public", "finding"],
    "exposures": ["exposed", "public", "finding"],
    "exposed": ["public", "finding"],
    "attacker": ["breach", "source", "honeytoken"],
    "attacked": ["breach", "source"],
    "attack": ["breach", "capture"],
    "trap": ["decoy", "honeytoken"],
    "traps": ["decoy", "honeytoken"],
    "credential": ["honeytoken", "key"],
    "credentials": ["honeytoken", "key"],
    "fast": ["time", "minutes", "seconds"],
    "quickly": ["time", "minutes", "seconds"],
    "who": ["source", "ip"],
    "vulnerability": ["exposed", "public", "finding"],
    "vulnerabilities": ["exposed", "public", "finding"],
}


def _expand(terms):
    out = list(terms)
    for t in terms:
        if t in _SYNONYMS:
            out.extend(_SYNONYMS[t])
    return out


class TfidfRetriever:
    def __init__(self):
        self.docs = []
        self.idf = {}
        self.doc_vecs = []

    def build(self, docs):
        """docs: list of {id, text, meta}. Computes IDF and doc vectors."""
        self.docs = docs
        n = len(docs) or 1

        # document frequency per term
        df = Counter()
        doc_terms = []
        for d in docs:
            terms = _tokens(d["text"])
            doc_terms.append(terms)
            for t in set(terms):
                df[t] += 1

        # inverse document frequency (smoothed)
        self.idf = {t: math.log((n + 1) / (dfi + 1)) + 1 for t, dfi in df.items()}

        # tf-idf vector per document (sparse dict)
        self.doc_vecs = [self._vectorize(terms) for terms in doc_terms]
        return self

    def _vectorize(self, terms):
        tf = Counter(terms)
        total = len(terms) or 1
        vec = {}
        for t, c in tf.items():
            if t in self.idf:
                vec[t] = (c / total) * self.idf[t]
        return vec

    @staticmethod
    def _cosine(a, b):
        if not a or not b:
            return 0.0
        # iterate the smaller vector
        if len(b) < len(a):
            a, b = b, a
        dot = sum(w * b.get(t, 0.0) for t, w in a.items())
        na = math.sqrt(sum(w * w for w in a.values()))
        nb = math.sqrt(sum(w * w for w in b.values()))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def query(self, question, k=4):
        """Return the top-k most relevant documents with scores."""
        qvec = self._vectorize(_expand(_tokens(question)))
        scored = []
        for doc, dvec in zip(self.docs, self.doc_vecs):
            s = self._cosine(qvec, dvec)
            if s > 0:
                scored.append((s, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"score": round(s, 4), **doc} for s, doc in scored[:k]]
