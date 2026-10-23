"""Interfaccia Gradio del chatbot (e punto di ingresso dello Space su Hugging Face)."""
import os
import subprocess
import sys

import gradio as gr

if not (os.path.exists("index.faiss") and os.path.exists("chunks.json")):
    # primo avvio senza indice committato: lo costruisce dalle schede
    subprocess.run([sys.executable, "ingest.py"], check=True)

from rag import RagBot  # noqa: E402  (import dopo la creazione dell'indice)

bot = RagBot()

MODEL_NAME = bot.llm.name
short = MODEL_NAME.split("/")[-1]
print(short)

PROJECTS = ["Tutti i progetti"] + sorted({c["project"] for c in bot.retriever.chunks})
EXAMPLES = [
    ["Di cosa parla la tesi e quali risultati ha ottenuto?"],
    ["Come stima Tyre-deg il degrado delle gomme?"],
    ["Da dove arrivano i dati di Fuel-analysis e come si aggiornano?"],
    ["Quali limiti hanno i tuoi progetti?"],
    ["Qual è la tua ricetta preferita?"],  # domanda fuori ambito: deve rifiutare
]


def respond(message, history, project):
    selected = None if project == PROJECTS[0] else project
    result = bot.answer(message, project=selected, stream=True, history=history)
    if result["refused"]:
        yield result["answer"]
        return
    text = ""
    for piece in result["answer"]:
        text += piece
        yield text
    links = []
    for s in bot.sources(result["hits"]):
        label = f"{s['project']} / {s['section']}"
        links.append(f"[{label}]({s['repo']})" if s["repo"] else label)
    yield text + "\n\n**Fonti:** " + " · ".join(links)


theme = gr.themes.Glass(
    primary_hue="blue",
    secondary_hue="slate",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Roboto"), "system-ui", "sans-serif"],
    radius_size="lg",
)

demo = gr.ChatInterface(
    fn=respond,
    type="messages",
    additional_inputs=[gr.Dropdown(PROJECTS, value=PROJECTS[0], label="Limita a un progetto")],
    examples=[[e[0], PROJECTS[0]] for e in EXAMPLES],
    title="Chiedi dei miei progetti",
    description=(
        "Rispondo solo in base alle schede dei miei progetti (tesi, Fuel-analysis, Tyre-deg). "
        "Il modello è piccolo e gira su CPU gratuita: la prima risposta può richiedere qualche secondo."
        f"<span class='badge'>{short}</span>"
    ),
    cache_examples=False,
    theme=theme,
)

if __name__ == "__main__":
    demo.launch()
