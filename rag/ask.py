"""
CLOUDSNARE RAG — ask (CLI).

Ask the SOC console a plain-English question about your own data.

Usage (project root, venv active):
    python -m rag.ask "what happened with the prod-db-backup decoy?"
    python -m rag.ask "which IP attacked us and what did they do?"
    python -m rag.ask "are there any exposures I still need to fix?"
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.chat import answer


def main():
    if len(sys.argv) < 2:
        print('Usage: python -m rag.ask "your question"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    print(f"\nQ: {question}\n")
    result = answer(question)
    print(f"A: {result['answer']}\n")
    print(f"[mode: {result['mode']} · {len(result['sources'])} sources retrieved]")


if __name__ == "__main__":
    main()
