---
title: Chiedi dei miei progetti
emoji: 💬
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.50.0
python_version: "3.11"
app_file: app.py
pinned: false
---

# Portfolio RAG: assistente sui miei progetti

Assistente che risponde a domande sui miei progetti usando solo le schede in `docs/`.
(L'intestazione YAML qui sopra serve a Hugging Face Spaces; GitHub la mostra come tabella.)

## File

| File | Ruolo |
|---|---|
| `docs/*.md` | schede dei progetti (la fonte di verità) |
| `ingest.py` | schede → chunk → embedding → `index.faiss` + `chunks.json` |
| `retrieve.py` | ricerca ibrida (embedding + BM25, fusione RRF) |
| `rag.py` | prompt + LLM locale (llama-cpp-python) + rifiuto sotto soglia |
| `app.py` | interfaccia Gradio, punto di ingresso dello Space |
| `eval.py`, `eval/questions.jsonl` | valutazione di recupero e risposte |
| `requirements.txt` | dipendenze dello Space |
| `requirements-index.txt` | dipendenze per indicizzare e valutare (usate dalla Action) |

## Flusso di lavoro

1. Copia `docs/_TEMPLATE.md`, compila le sezioni (nessun `TODO`) e imposta `status: ready`.
2. `pip install -r requirements.txt`
3. `python ingest.py` crea `index.faiss` e `chunks.json` e stampa i token per chunk.
4. `python retrieve.py "domanda"` prova il retrieval.
5. `python eval.py --retrieval-only` misura hit@k e MRR; `python eval.py --model-repo ... --model-file ...` misura le risposte.
6. `python app.py` avvia l'interfaccia in locale.
7. Con un push su GitHub la Action `rebuild-index` ricostruisce l'indice a ogni modifica di `docs/`.

## Regole di qualità

- Ogni frase deve essere vera e verificabile: il bot ripete ciò che scrivi.
- Nomina il progetto in ogni sezione e usa numeri con unità e periodo.
- Niente chiavi, dati personali o dati con licenza non condivisibile.
- Dopo ogni modifica alle schede rilancia `eval.py` e controlla che i risultati non peggiorino.

## Configurazione (variabili d'ambiente)

`MODEL_REPO`, `MODEL_FILE` (modello GGUF), `TOP_K` (chunk nel prompt), `MIN_COSINE` (soglia di rifiuto), `N_CTX` (contesto).
