"""Costruisce l'indice vettoriale dalle schede in docs/*.md.

Uso:  python ingest.py
Output: index.faiss e chunks.json

Regole:
- i file che iniziano con "_" (es. _TEMPLATE.md) sono ignorati;
- vengono indicizzate solo le schede con "status: ready" nel front matter;
- una scheda "ready" che contiene ancora "TODO" blocca la build.

Chunking: ogni sezione "## ..." viene divisa in blocchi (paragrafi, voci di
elenco, coppie D/R delle FAQ) che vengono raggruppati fino a MAX_WORDS parole.
Il limite e' volutamente basso: multilingual-e5-small legge al massimo 512
token e l'italiano usa circa 1,5-2 token per parola, quindi 180 parole stanno
con margine nel limite. Il controllo finale in main() segnala i chunk che
superano comunque MAX_MODEL_TOKENS.
"""
import json
import re
import sys
from pathlib import Path

DOCS_DIR = Path("docs")
INDEX_PATH = Path("index.faiss")
CHUNKS_PATH = Path("chunks.json")
MODEL_NAME = "intfloat/multilingual-e5-small"
MAX_WORDS = 180          # dimensione massima di un chunk (parole)
OVERLAP_WORDS = 40       # un blocco finale piu' corto di cosi' viene ripetuto nel chunk dopo
MAX_MODEL_TOKENS = 500   # il modello e5 taglia a 512 token


def parse_front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, m.group(2)


def strip_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def split_sections(body):
    sections, title, buf = [], "Introduzione", []
    for line in body.splitlines():
        if line.startswith("## "):
            if "".join(buf).strip():
                sections.append((title, "\n".join(buf).strip()))
            title, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if "".join(buf).strip():
        sections.append((title, "\n".join(buf).strip()))
    return sections


def n_words(text):
    return len(text.split())


# una nuova voce di elenco o una nuova domanda delle FAQ apre un nuovo blocco
BLOCK_START = re.compile(r"^\s*([-*]\s+|\d+\.\s+|\*\*D:)")


def split_blocks(text):
    """Divide il testo di una sezione in blocchi: paragrafi, voci di elenco, coppie D/R."""
    blocks, cur = [], []
    for line in text.splitlines():
        if not line.strip():
            if cur:
                blocks.append("\n".join(cur))
                cur = []
            continue
        if cur and BLOCK_START.match(line):
            blocks.append("\n".join(cur))
            cur = []
        cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return blocks


def split_long_block(block, max_words=MAX_WORDS):
    """Un blocco piu' lungo del limite viene diviso per frasi (e, in extremis, per parole)."""
    if n_words(block) <= max_words:
        return [block]
    sentences = re.split(r"(?<=[.!?;])\s+", block)
    parts, cur, cur_w = [], [], 0
    for s in sentences:
        w = n_words(s)
        if w > max_words:  # frase enorme: finestre di parole
            if cur:
                parts.append(" ".join(cur))
                cur, cur_w = [], 0
            words = s.split()
            parts.extend(" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words))
            continue
        if cur and cur_w + w > max_words:
            parts.append(" ".join(cur))
            cur, cur_w = [], 0
        cur.append(s)
        cur_w += w
    if cur:
        parts.append(" ".join(cur))
    return parts


def pack_blocks(blocks, max_words=MAX_WORDS, overlap_words=OVERLAP_WORDS):
    """Raggruppa i blocchi in chunk da al massimo max_words parole."""
    expanded = [p for b in blocks for p in split_long_block(b, max_words)]
    chunks, cur, cur_w, fresh = [], [], 0, 0
    for b in expanded:
        w = n_words(b)
        if cur and cur_w + w > max_words:
            chunks.append("\n".join(cur))
            last = cur[-1]
            cur = [last] if n_words(last) <= overlap_words and fresh > 1 else []
            cur_w = sum(n_words(x) for x in cur)
            fresh = 0
        cur.append(b)
        cur_w += w
        fresh += 1
    if cur and fresh > 0:
        chunks.append("\n".join(cur))
    return chunks


def build_chunks(docs_dir=DOCS_DIR):
    chunks = []
    for path in sorted(Path(docs_dir).glob("*.md")):
        if path.name.startswith("_"):
            continue
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        body = strip_comments(body)
        if meta.get("status") != "ready":
            print(f"[skip] {path.name}: status={meta.get('status', 'mancante')}")
            continue
        if "TODO" in body:
            sys.exit(f"[errore] {path.name} e' 'ready' ma contiene ancora TODO")
        project = meta.get("project", path.stem)
        for section, text in split_sections(body):
            for part in pack_blocks(split_blocks(text)):
                chunks.append({
                    "id": len(chunks),
                    "project": project,
                    "section": section,
                    "repo": meta.get("repo", ""),
                    "demo": meta.get("demo", ""),
                    "file": path.name,
                    # il nome del progetto e della sezione nel testo aiuta il retrieval
                    "text": f"{project} - {section}\n{part}",
                    "n_words": n_words(part),
                })
    return chunks


def main():
    chunks = build_chunks()
    if not chunks:
        sys.exit("Nessuna scheda con status: ready. Completa almeno una scheda.")

    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    texts = ["passage: " + c["text"] for c in chunks]

    # controllo del limite di token del modello di embedding
    lengths = [len(model.tokenizer(t)["input_ids"]) for t in texts]
    for c, n in zip(chunks, lengths):
        c["n_tokens"] = n
    too_long = [(c["project"], c["section"], n) for c, n in zip(chunks, lengths) if n > MAX_MODEL_TOKENS]
    print(f"Token per chunk: medio {sum(lengths) / len(lengths):.0f}, massimo {max(lengths)}")
    if too_long:
        print(f"[attenzione] {len(too_long)} chunk oltre {MAX_MODEL_TOKENS} token, la coda verrebbe ignorata:")
        for p, s, n in too_long:
            print(f"  - {p} / {s}: {n} token. Riduci MAX_WORDS o accorcia la sezione.")

    vectors = model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=True)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(np.asarray(vectors, dtype="float32"))
    faiss.write_index(index, str(INDEX_PATH))
    CHUNKS_PATH.write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Indicizzati {len(chunks)} chunk da {len({c['project'] for c in chunks})} progetti")


if __name__ == "__main__":
    main()
