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
short = MODEL_NAME.split("/")[-1].capitalize()
print(short)

PROJECTS = ["Tutti i progetti"] + sorted({c["project"] for c in bot.retriever.chunks})
EXAMPLES = [
    ["Di cosa parla la tesi e quali risultati ha ottenuto?"],
    ["Come stima Tyre-deg il degrado delle gomme?"],
    ["Da dove arrivano i dati di Fuel-analysis e come si aggiornano?"],
    ["Quali limiti hanno i tuoi progetti?"],
    ["Qual è la tua ricetta preferita?"],  # domanda fuori ambito: deve rifiutare
]


def respond(message, history, project, prompt):
    selected = None if project == PROJECTS[0] else project
    result = bot.answer(message, project=selected, stream=True, history=history, prompt=prompt)
    if result["refused"]:
        yield result["answer"]
        return
    text = ""
    for piece in result["answer"]:
        text += piece
        yield text
    links = []
    for s in bot.sources(result["hits"]):
        label = f"{s['project']} / {s['section']} / {s['cosine']}"
        links.append(f"[{label}]({s['repo']})" if s["repo"] else label)
    yield text + "\n\n**Fonti:** " + " · ".join(links)


def toggle_column(state):
    new_state = not state
    return gr.Column(visible=new_state), new_state, "<" if new_state else ">"


theme = gr.themes.Glass(
    primary_hue="blue",
    secondary_hue="slate",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Roboto"), "system-ui", "sans-serif"],
    radius_size="lg",
).set(
    # body_background_fill="neutral_50",
    # button_primary_background_fill="primary_200",
    # button_primary_background_fill_hover="primary_100",
    block_shadow="0 1px 3px rgba(0,0,0,.08)",
)


CSS = """
.model-badge {display: inline-block; padding: 4px 12px; border-radius: 999px;
              background: var(--color-accent-soft); color: var(--color-accent); font-size: .85em;}
footer {display: none !important;}
"""

with gr.Blocks(title="Custom AI ChatBot", theme=theme, css=CSS) as demo:
    # State variable to collpase or show the sidebar
    state_var = gr.State(True)
    gr.Markdown(
        """
        # My Project Scraper
        ### Per conoscermi meglio, esplorando il mio spazio vettoriale.  
        """
    )

    with gr.Row():
        col = gr.Sidebar(open=True)
        with col:
            # btn = gr.Button("<", scale=0.2)
            gr.Markdown("### ⚙️ Impostazioni Bot")
            language = gr.Radio(choices=['IT','EN'], value='IT', label='Seleziona Lingua', interactive=True, visible=False)
            projects = gr.Dropdown(PROJECTS, value=PROJECTS[0], label="Seleziona Progetto")
            prompt_selector = gr.Dropdown(
                choices=[('Default','default'),('Formale','formal'),('Ottocentesco','historical')], 
                value='default', 
                label='Seleziona System Prompt', 
                interactive=True)
            gr.HTML(f"<span class='model-badge'>🧠 {short}</span>")
            with gr.Accordion("ℹ️ Come funziona", open=False):
                gr.Markdown("Retrivial ibrido (FAISS + BM25) con un LLM di piccole dimensioni che gira su CPU")

        with gr.Column(scale=3):

            chatbot_ui = gr.Chatbot(
                height=700,
                type="messages",
                show_copy_button=True,
                avatar_images=(None, "https://em-content.zobj.net/source/twitter/53/robot-face_1f916.png"),
                placeholder="**Chiedimi dei miei progetti**<br>Tesi, Fuel-analysis, Tyre-deg",
            )

            gr.ChatInterface(
                fn=respond,
                type="messages",
                chatbot=chatbot_ui,
                textbox=gr.Textbox(placeholder="Scrivi una domanda sui miei progetti…", submit_btn=True),
                # il dropdown e' gia' renderizzato nella sidebar: Gradio ne passa solo il valore a respond
                additional_inputs=[projects, prompt_selector],
                examples=[[e[0], PROJECTS[0], "default"] for e in EXAMPLES],
                cache_examples=False,
            )


    # btn.click(toggle_column,
            #   inputs=[state_var],
            #   outputs=[col, state_var, btn])
    # btn.click(fn=lambda: gr.Sidebar(open=False), outputs=col)


if __name__ == "__main__":
    demo.launch()
