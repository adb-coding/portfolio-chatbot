"""Ricerca ibrida (embedding + BM25, fusi con RRF) sull'indice dei progetti.

Uso da terminale:  python retrieve.py "Che stack hai usato in Tyre-deg?"
"""
import json
import re
import sys

MODEL_NAME = "intfloat/multilingual-e5-small"


def tokenize(text):
    return re.findall(r"\w+", text.lower())


class Retriever:
    def __init__(self, index_path="index.faiss", chunks_path="chunks.json"):
        import faiss
        from rank_bm25 import BM25Okapi
        from sentence_transformers import SentenceTransformer

        self.index = faiss.read_index(index_path)
        with open(chunks_path, encoding="utf-8") as f:
            self.chunks = json.load(f)
        self.model = SentenceTransformer(MODEL_NAME)
        self.bm25 = BM25Okapi([tokenize(c["text"]) for c in self.chunks])

    def search(self, query, k=4, project=None, rrf_k=60):
        import numpy as np

        # il corpus è piccolo: si classificano tutti i chunk, poi si filtra
        n = len(self.chunks)
        q = self.model.encode(["query: " + query], normalize_embeddings=True)
        scores, ids = self.index.search(np.asarray(q, dtype="float32"), n)
        dense = [int(i) for i in ids[0] if i >= 0]
        cosine = {int(i): float(s) for i, s in zip(ids[0], scores[0]) if i >= 0}
        sparse = [int(i) for i in np.argsort(self.bm25.get_scores(tokenize(query)))[::-1]]

        if project:
            allowed = {c["id"] for c in self.chunks if c["project"].lower() == project.lower()}
            dense = [i for i in dense if i in allowed]
            sparse = [i for i in sparse if i in allowed]

        fused = {}
        for ranking in (dense, sparse):
            for rank, i in enumerate(ranking, start=1):
                fused[i] = fused.get(i, 0.0) + 1.0 / (rrf_k + rank)
        best = sorted(fused, key=fused.get, reverse=True)[:k]
        # copia del chunk con due campi in piu': coseno denso (per la soglia di rifiuto) e punteggio RRF
        return [dict(self.chunks[i], cosine=cosine[i], rrf=fused[i]) for i in best]


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Di cosa parla la tesi?"
    for hit in Retriever().search(question):
        print(f"--- {hit['project']} / {hit['section']}  cos={hit['cosine']:.3f} rrf={hit['rrf']:.4f}")
        print(hit["text"][:400], "\n")
