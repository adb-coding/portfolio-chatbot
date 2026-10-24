"""Valutazione del chatbot su un set di domande con risposta nota.

Due livelli, da tenere separati:

1. RECUPERO (veloce, senza LLM):   python eval.py --retrieval-only
   - hit@k: il chunk giusto (progetto + sezione attesi) e' tra i primi k?
   - MRR: 1 / posizione del primo chunk giusto, mediato sulle domande
   - coseno massimo delle domande senza risposta vs con risposta: serve a scegliere MIN_COSINE

2. RISPOSTE (richiede il modello):   python eval.py --model-repo ... --model-file ...
   - copertura: la risposta contiene le parole chiave attese (campo "must")
   - rifiuto corretto: sulle domande senza risposta il bot dice "Non e' documentato"
   - falso rifiuto: il bot rifiuta una domanda che ha risposta
   - numeri non fondati: numeri nella risposta che non compaiono nel contesto fornito
   - tempo medio di risposta

I risultati vengono aggiunti a eval/results.csv (una riga per configurazione) e il
dettaglio per domanda e' scritto in eval/details_<nome>.csv.
"""
import argparse
import csv
import json
import re
import time
import unicodedata
from pathlib import Path

QUESTIONS = Path("eval/questions.jsonl")
RESULTS = Path("eval/results.csv")


def load_questions(path=QUESTIONS):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def norm(text):
    """Minuscolo, apostrofi tipografici e accenti uniformati: confronto robusto."""
    text = text.lower().replace("’", "'")
    return unicodedata.normalize("NFC", text)


def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def is_refusal(answer):
    """Vero se la risposta contiene la formula di rifiuto ("Non è documentato...")."""
    return "non e documentato" in strip_accents(norm(answer)).replace("'", "")


def numbers_in(text):
    """Numeri (anche con virgola/punto decimale) presenti nel testo."""
    return set(re.findall(r"\d+(?:[.,]\d+)?", text))


def ungrounded_numbers(answer, context):
    """Numeri della risposta che non compaiono nel contesto passato al modello."""
    ctx = numbers_in(context)
    return sorted(n for n in numbers_in(answer) if n not in ctx)


def gold_rank(hits, q):
    """Posizione (da 1) del primo chunk con progetto e sezione attesi; None se assente."""
    for pos, h in enumerate(hits, start=1):
        if q["project"] in h["project"].lower() and h["section"] == q["section"]:
            return pos
    return None


def eval_retrieval(retriever, questions, k=4):
    rows = []
    for q in questions:
        hits = retriever.search(q["question"], k=k)
        row = {"id": q["id"], "answerable": q["answerable"], "max_cosine": max(h["cosine"] for h in hits)}
        if q["answerable"]:
            r = gold_rank(hits, q)
            row.update(rank=r, hit=r is not None, rr=(1 / r) if r else 0.0)
        rows.append(row)
    return rows


def summarize_retrieval(rows, k):
    ans = [r for r in rows if r["answerable"]]
    una = [r for r in rows if not r["answerable"]]
    out = {
        f"hit@{k}": sum(r["hit"] for r in ans) / len(ans),
        "mrr": sum(r["rr"] for r in ans) / len(ans),
        "cos_min_answerable": min(r["max_cosine"] for r in ans),
    }
    if una:
        out["cos_max_unanswerable"] = max(r["max_cosine"] for r in una)
    return out


def eval_answers(bot, questions, prompt="default"):
    rows = []
    for q in questions:
        t0 = time.time()
        res = bot.answer(q["question"])
        dt = time.time() - t0
        answer = res["answer"]
        context = " ".join(h["text"] for h in res["hits"])
        refused = res["refused"] or is_refusal(answer)
        row = {"id": q["id"], "answerable": q["answerable"], "refused": refused,
               "seconds": round(dt, 2), "answer": answer.replace("\n", " ")}
        if q["answerable"]:
            a = norm(answer)
            row["covered"] = (not refused) and all(m in a for m in q["must"])
            row["ungrounded"] = ",".join(ungrounded_numbers(answer, context))
            row["hit"] = gold_rank(res["hits"], q) is not None
        rows.append(row)
    return rows


def summarize_answers(rows):
    ans = [r for r in rows if r["answerable"]]
    una = [r for r in rows if not r["answerable"]]
    out = {
        "coverage": sum(r["covered"] for r in ans) / len(ans),
        "false_refusal": sum(r["refused"] for r in ans) / len(ans),
        "ungrounded_rate": sum(bool(r["ungrounded"]) for r in ans) / len(ans),
        "avg_seconds": sum(r["seconds"] for r in rows) / len(rows),
    }
    if una:
        out["correct_refusal"] = sum(r["refused"] for r in una) / len(una)
    return out


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader()
        w.writerows(rows)


def append_result(name, metrics):
    RESULTS.parent.mkdir(exist_ok=True)
    new = not RESULTS.exists()
    row = {"config": name, **{k: round(v, 3) for k, v in metrics.items()}}
    existing = []
    if not new:
        with open(RESULTS, encoding="utf-8") as f:
            existing = list(csv.DictReader(f))
    existing.append(row)
    write_csv(RESULTS, existing)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retrieval-only", action="store_true")
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--ollama", action="store_true", help="Per utilizzare un modello su Ollama")
    ap.add_argument("--ollama-name")
    ap.add_argument("--model-repo")
    ap.add_argument("--model-file")
    ap.add_argument("--prompt", default="default", help="chiave di rag.PROMPTS")
    ap.add_argument("--min-cosine", type=float, default=0.0)
    ap.add_argument("--name", help="etichetta della configurazione nel CSV")
    args = ap.parse_args()

    questions = load_questions()
    from retrieve import Retriever
    retriever = Retriever()

    if args.retrieval_only:
        rows = eval_retrieval(retriever, questions, args.k)
        metrics = summarize_retrieval(rows, args.k)
        name = args.name or f"retrieval-k{args.k}"
        write_csv(f"eval/details_{name}.csv", rows)
    else:
        if args.ollama:
            from rag import OllamaLLM, RagBot
            llm = OllamaLLM(args.ollama_name)
        else:
            from rag import LocalLLM, RagBot
            llm = LocalLLM(args.model_repo, args.model_file)
        bot = RagBot(retriever=retriever, llm=llm, top_k=args.k, min_cosine=args.min_cosine)
        rows = eval_answers(bot, questions)
        metrics = summarize_answers(rows)
        name = args.name or llm.name
        write_csv(f"eval/details_{re.sub(r'[^A-Za-z0-9_.-]+', '_', name)}.csv", rows)

    append_result(name, metrics)
    print(f"\nConfigurazione: {name}")
    for k, v in metrics.items():
        print(f"  {k:22s} {v:.3f}")


if __name__ == "__main__":
    main()
