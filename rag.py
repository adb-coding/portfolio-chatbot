"""Pipeline RAG: recupero dei chunk + generazione della risposta con un LLM piccolo.

L'LLM e' un modello GGUF quantizzato eseguito in CPU con llama-cpp-python (nessun
server esterno, nessun Ollama). Modello e parametri si cambiano con variabili
d'ambiente, senza toccare il codice:

    MODEL_REPO   repository Hugging Face del GGUF     (default Qwen/Qwen2.5-1.5B-Instruct-GGUF)
    MODEL_FILE   nome del file .gguf                  (default qwen2.5-1.5b-instruct-q4_k_m.gguf)
    TOP_K        numero di chunk passati al modello  (default 4)
    MIN_COSINE   sotto questa similarita' coseno del miglior chunk il bot rifiuta
                 senza chiamare l'LLM (default 0.0 = disattivato; si calibra con eval.py)
    N_CTX        finestra di contesto del modello     (default 4096)

Backend (LLM_BACKEND): "llama_cpp" (CPU, GGUF), "ollama" (server locale) oppure
"zerogpu" (modello Hugging Face con transformers su GPU ZeroGPU). Su uno Space
ZeroGPU il backend viene scelto in automatico. Per "zerogpu":

    HF_MODEL     modello Hugging Face (non GGUF)       (default Qwen/Qwen2.5-3B-Instruct)
    GPU_SECONDS  durata richiesta della GPU a ogni risposta (default 60)
"""
import os

SYSTEM_PROMPT = (
    "Sei l'assistente del portfolio di Andrea. Rispondi in italiano alle domande sui suoi progetti "
    "usando SOLO il contesto fornito.\n"
    "Regole:\n"
    "1. Se l'informazione non e' nel contesto, rispondi esattamente: "
    "\"Non è documentato nelle schede dei progetti.\"\n"
    "2. Non inventare numeri, date, tecnologie o competenze che non compaiono nel contesto.\n"
    "3. Cita sempre il progetto e la sezione tra parentesi quadre, per esempio [Tyre-deg / Limiti noti].\n"
    "4. Rispondi in modo breve e diretto, in prima persona quando parli del lavoro svolto."
)

FORMAL_PROMPT = (
    "Sei l'assistente del portfolio di Andrea. Rispondi in italiano in tono ESTREMAMENTE FORMALE alle domande sui suoi progetti "
    "usando SOLO il contesto fornito. \n"
    "Regole:\n"
    "1. Se l'informazione non e' nel contesto, rispondi esattamente: "
    "\"Non è documentato nelle schede dei progetti.\"\n"
    "2. Non inventare numeri, date, tecnologie o competenze che non compaiono nel contesto.\n"
    "3. Cita sempre il progetto e la sezione tra parentesi quadre, per esempio [Tyre-deg / Limiti noti].\n"
    "4. Rispondi in modo breve e formale."
)

HISTORICAL_PROMPT = (
    "Sei un poeta ottocentesco che racconta i progetti di Andrea. Rispondi in italiano antico ed in rima alle domande fatte sui progetti "
    "usando SOLO il contesto fornito. \n"
    "Regole:\n"
    "1. Se l'informazione non è nel contesto, rispondi con una rima dicendo che l'informazione non è documentata. \n"
    "2. Non inventare numeri, date, tecnologie o competenze che non compaiono nel contesto.\n"
    "3. Cita sempre il progetto e la sezione tra parentesi quadre, per esempio [Tyre-deg / Limiti noti].\n"
    "4. Rispondi sempre in rima e con un lessico ottocentesco."
)

PROMPTS = {
    "default": SYSTEM_PROMPT,
    "formal": FORMAL_PROMPT,
    "historical": HISTORICAL_PROMPT,
}

REFUSAL = "Non è documentato nelle schede dei progetti."


def retrieval_query(question, history):
    prev = [m['content'] for m in history if m['role'] == 'user']
    return f"{prev[-1]} {question}" if prev else question


def build_messages(question, hits, history=None, max_turns=3, system_prompt=SYSTEM_PROMPT):
    """Costruisce i messaggi per il modello: regole nel system, contesto + domanda nello user."""
    blocks = []
    for h in hits:
        blocks.append(f"[{h['project']} / {h['section']}]\n{h['text'].split(chr(10), 1)[-1]}")
    context = "\n\n".join(blocks)
    user = f"Contesto:\n{context}\n\nDomanda: {question}"
    msgs = [{"role": "system", "content": system_prompt}]
    for m in (history or [])[-2 * max_turns:]:
        msgs.append({"role": m["role"], "content": m["content"].split("\n\n**Fonti:**")[0]})
    msgs.append({"role": "user", "content": user})
    return msgs


class LocalLLM:
    """Wrapper minimo su llama-cpp-python."""

    def __init__(self, repo=None, filename=None, n_ctx=None):
        from huggingface_hub import hf_hub_download
        from llama_cpp import Llama

        repo = repo or os.getenv("MODEL_REPO", "unsloth/Qwen3.5-4B-GGUF")
        filename = filename or os.getenv("MODEL_FILE", "Qwen3.5-4B-Q4_K_M.gguf")
        path = hf_hub_download(repo_id=repo, filename=filename)
        self.name = f"{repo}/{filename}"
        self.llm = Llama(
            model_path=path,
            n_ctx=n_ctx or int(os.getenv("N_CTX", "4096")),
            n_threads=os.cpu_count() or 2,
            verbose=False,
        )

    def chat(self, messages, max_tokens=350, temperature=0.1, stream=False):
        out = self.llm.create_chat_completion(
            messages=messages, max_tokens=max_tokens, temperature=temperature, stream=stream
        )
        if stream:
            return (c["choices"][0]["delta"].get("content", "") for c in out)
        return out["choices"][0]["message"]["content"].strip()



class OllamaLLM:
    """Wrapper su un server Ollama locale (https://ollama.com/docs/)."""

    def __init__(self, model=None, n_ctx=None):
        import ollama

        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
        self.name = f"ollama/{self.model}"
        self.n_ctx = n_ctx or int(os.getenv("N_CTX", "4096"))
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434").replace("0.0.0.0", "127.0.0.1")
        self.client = ollama.Client(host=host)


    def chat(self, messages, max_tokens=350, temperature=0.1, stream=False):
        out = self.client.chat(
            model=self.model,
            messages=messages,
            stream=stream,
            think=False,
            options={"num_predict": max_tokens, "temperature": temperature, "num_ctx": self.n_ctx},
        )
        if stream:
            return (c["message"]["content"] for c in out)
        return out["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Backend ZeroGPU: modello Hugging Face (non GGUF) con transformers.
# Il modello si carica una volta all'avvio e va su "cuda"; la generazione e' in
# una funzione decorata con @spaces.GPU, che chiede la GPU solo per la durata
# della risposta. Fuori da uno Space (senza il pacchetto `spaces`) il decoratore
# non fa nulla e il codice gira su cio' che torch trova.
# ---------------------------------------------------------------------------
try:
    import spaces

    _gpu = spaces.GPU(duration=int(os.getenv("GPU_SECONDS", "60")))
except ImportError:  # esecuzione locale
    def _gpu(fn):
        return fn

_ZERO = {}  # tokenizer e modello, riempiti da ZeroGPULLM


@_gpu
def _gpu_generate(messages, max_tokens, temperature):
    """Generatore di pezzi di testo. Gira dentro la finestra di GPU concessa da ZeroGPU."""
    from threading import Thread

    from transformers import TextIteratorStreamer

    tok, model = _ZERO["tok"], _ZERO["model"]
    text = tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
        enable_thinking=False,  # ignorato dai modelli senza modalita' "thinking"
    )
    inputs = tok([text], return_tensors="pt").to(model.device)
    streamer = TextIteratorStreamer(tok, skip_prompt=True, skip_special_tokens=True)
    kwargs = dict(**inputs, streamer=streamer, max_new_tokens=max_tokens, do_sample=temperature > 0)
    if temperature > 0:
        kwargs["temperature"] = temperature
    Thread(target=model.generate, kwargs=kwargs).start()
    for piece in streamer:
        yield piece


class ZeroGPULLM:
    """Wrapper su transformers per Spaces ZeroGPU."""

    def __init__(self, model_id=None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model_id = model_id or os.getenv("HF_MODEL", "Qwen/Qwen2.5-3B-Instruct")
        self.name = self.model_id
        _ZERO["tok"] = AutoTokenizer.from_pretrained(self.model_id)
        model = AutoModelForCausalLM.from_pretrained(self.model_id, torch_dtype=torch.bfloat16)
        # su ZeroGPU .to("cuda") a livello di avvio e' consentito: la GPU reale arriva dentro _gpu_generate
        _ZERO["model"] = model.to("cuda") if torch.cuda.is_available() else model

    def chat(self, messages, max_tokens=350, temperature=0.1, stream=False):
        pieces = _gpu_generate(messages, max_tokens, temperature)
        if stream:
            return pieces
        return "".join(pieces).strip()


def make_llm():
    # su uno Space ZeroGPU Hugging Face imposta SPACES_ZERO_GPU: il backend si sceglie da solo
    default = "zerogpu" if os.getenv("SPACES_ZERO_GPU") else "llama_cpp"
    backend = os.getenv("LLM_BACKEND", default)
    if backend == "ollama":
        return OllamaLLM()
    if backend == "zerogpu":
        return ZeroGPULLM()
    return LocalLLM()


class RagBot:
    def __init__(self, retriever=None, llm=None, top_k=None, min_cosine=None):
        if retriever is None:
            from retrieve import Retriever
            retriever = Retriever()
        self.retriever = retriever
        self.llm = llm if llm is not None else make_llm()
        self.top_k = top_k or int(os.getenv("TOP_K", "4"))
        self.min_cosine = float(os.getenv("MIN_COSINE", "0.0")) if min_cosine is None else min_cosine

    def retrieve(self, question, project=None):
        return self.retriever.search(question, k=self.top_k, project=project)

    def answer(self, question, project=None, stream=False, history=None, prompt="default"):
        """Restituisce dict: answer (o generatore se stream), hits, refused."""
        search_q = retrieval_query(question, history) if history else question
        hits = self.retrieve(search_q, project)
        if not hits or max(h["cosine"] for h in hits) < self.min_cosine:
            return {"answer": REFUSAL, "hits": hits, "refused": True}
        messages = build_messages(question, hits, history, system_prompt=PROMPTS[prompt])
        out = self.llm.chat(messages, stream=stream)
        return {"answer": out, "hits": hits, "refused": False}

    @staticmethod
    def sources(hits):
        """Elenco unico di fonti (progetto / sezione, link al repository)."""
        seen, rows = set(), []
        for h in hits:
            key = (h["project"], h["section"], round(h['cosine'], 2))
            if key in seen:
                continue
            seen.add(key)
            rows.append({"project": h["project"], "section": h["section"], "cosine": h["cosine"], "repo": h["repo"]})
        return rows
