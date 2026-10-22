---
project: Tyre-deg
repo: https://github.com/adb-coding/f1-tyre-deg
demo: https://f1-tyre-deg.netlify.app/
status: ready
tags: Formula 1, degrado gomme, FastAPI, React, TypeScript, FastF1, scikit-learn, regressione lineare, full stack
---

<!-- Scheda compilata leggendo README, backend (main.py, f1_data.py, tyre_analysis.py, save_cached.py), docker-compose, Caddyfile e struttura del frontend della repository, il 21 ottobre 2026. -->

## Sintesi

Tyre-deg (repository f1-tyre-deg) è un'applicazione full stack che stima il degrado delle gomme in una gara di Formula 1 e mostra anche la telemetria dei piloti. Il backend in Python (FastAPI, FastF1, pandas, scikit-learn) corregge i tempi sul giro per il carburante e ne ricava una pendenza di degrado per ogni stint, in secondi persi per giro di vita della gomma. Il frontend in React e TypeScript con Recharts è online su Netlify; il backend gira su una macchina virtuale Oracle.

## Problema e obiettivo

L'obiettivo di Tyre-deg è stimare e analizzare il degrado delle gomme e la telemetria delle gare di F1 e presentare i risultati in una dashboard curata. Il progetto copre sia il backend (dati, modello, API) sia il frontend. Il README lo descrive anche come un esercizio per allenare le competenze di analisi dei dati e la capacità di produrre un'applicazione full stack in tempi relativamente brevi.

## Dati e fonti

I dati grezzi delle gare arrivano da FastF1, una libreria Python che accede ai dati di timing e telemetria della Formula 1. I server di live timing della F1 bloccano le richieste provenienti da indirizzi IP di provider cloud, quindi la macchina virtuale non può scaricare le gare al momento della richiesta. Per questo le gare vengono scaricate in anticipo, in locale, con lo script `save_cached.py` (per un'intera stagione o per un solo round) e salvate in una cache FastF1 su disco; la cartella `backend/cache` viene poi copiata sulla macchina virtuale e montata nel container.

## Metodo e architettura

**Modello di degrado.** Il cuore del progetto è un modello in tre passi:
1. **Pulizia dei giri.** Si tengono solo i giri puliti del pilota: sono esclusi i giri con ingresso o uscita dai box, i giri sotto Safety Car o Virtual Safety Car e il primo giro.
2. **Correzione per il carburante.** Si assume una partenza con 110 kg di carburante e 1 kg rimasto a fine gara, bruciati a ritmo costante giro per giro. L'effetto del carburante sul tempo (secondi per kg) è stimato dai dati del pilota come media delle differenze di tempo tra giri consecutivi rapportate al carburante bruciato. Il tempo corretto è il tempo sul giro più l'effetto del carburante già bruciato.
3. **Regressione lineare per stint.** Per ogni stint si adatta con scikit-learn una regressione lineare del tempo corretto sull'età della gomma (`TyreLife`). La pendenza è il degrado in secondi persi per giro di vita della gomma, l'intercetta è il tempo corretto a gomma nuova.

**API.** Il backend usa FastAPI con Pydantic per validare e serializzare i dati. Gli endpoint sono sotto `/api/`: `tyre-degradation` (degrado, telemetria, posizione delle curve e posizioni in gara per un pilota), `tyre-degradation/multi` (gli stessi dati per più piloti), `driver-data` (piloti con i colori delle squadre), `session-info` (informazioni sulla gara, meteo e risultati) e `rounds-list` (le gare disponibili in cache, raggruppate per anno).

**Altre analisi.** L'applicazione calcola anche i box plot dei tempi sul giro per mescola, la telemetria del giro più veloce (velocità, marce, acceleratore, giri motore), le posizioni in gara e la posizione delle curve del tracciato.

**Struttura del backend:** `main.py` (punto di ingresso FastAPI), `save_cached.py` (scarica le gare in cache), `services/f1_data.py` (accesso a FastF1, pulizia, correzione carburante e regressione) e `services/tyre_analysis.py` (modelli Pydantic e costruzione dei dati per il frontend).

**Frontend.** React e TypeScript con Recharts per i grafici, costruito con Vite. Comunica con il backend via HTTP. Le funzioni principali sono l'analisi per stint (consumo delle gomme per mescola, strategia e tempi sul giro), la modalità confronto tra due o più piloti sui tempi corretti, la telemetria del giro più veloce e una barra laterale con le informazioni sul Gran Premio e il tracciato.

## Stack tecnico

- **Backend:** Python 3.11 o superiore, FastAPI, Pydantic, FastF1, pandas, scikit-learn, Uvicorn. Le dipendenze sono gestite con il gestore di pacchetti uv (`pyproject.toml` e `uv.lock`).
- **Frontend:** React, TypeScript, Recharts, Vite, con deploy su Netlify. La variabile d'ambiente `VITE_API_URL` indica l'indirizzo del backend.
- **Deploy del backend:** container Docker su una macchina virtuale Oracle, con `docker compose`. Un reverse proxy Caddy gestisce HTTPS con certificato Let's Encrypt automatico e inoltra il traffico al container del backend. Il container ha un limite di memoria di 4 GB.
- **Licenza:** MIT.

## Decisioni e alternative scartate

- **Cache delle gare scaricata in anticipo:** i server F1 bloccano gli IP cloud, quindi la macchina virtuale legge sessioni già salvate invece di scaricarle a richiesta. L'endpoint `rounds-list` legge la cartella della cache, così il frontend offre solo le gare effettivamente disponibili.
- **Massimo 3 sessioni in memoria:** le sessioni caricate sono grandi e, per restare nei limiti di RAM della macchina virtuale, il server tiene al massimo 3 sessioni già elaborate (`lru_cache`). Cambiando tra più di tre gare le sessioni vengono ricaricate. Il numero è modificabile in `f1_data.py`. Il compromesso è la latenza al cambio gara contro un uso di memoria contenuto.
- **Carburante stimato con ipotesi semplici:** i dati sul consumo non sono pubblici, quindi si assumono 110 kg iniziali, 1 kg finale e consumo costante.
- **Regressione lineare per stint:** un modello semplice e interpretabile, con la pendenza che si legge direttamente come secondi persi per giro. Il costo è che non cattura il calo non lineare di fine vita della gomma.
- **Backend e frontend separati:** secondo il README il backend è su una macchina virtuale Oracle per gestire le esigenze di calcolo degli script Python e dell'elaborazione dei dati, mentre il frontend è su Netlify per accessibilità globale e interattività.

## Risultati

Tyre-deg produce, per ogni pilota e per ogni stint di una gara in cache, la pendenza di degrado in secondi per giro di vita della gomma, i tempi sul giro corretti per il carburante, i box plot per mescola e la telemetria del giro più veloce. La documentazione non riporta una validazione quantitativa del modello (per esempio un errore su giri non usati nell'adattamento) né un confronto con una baseline, quindi le stime vanno lette come indicative.

## Limiti noti

- Le stime derivano da semplificazioni delle condizioni reali di gara.
- I dati sul consumo di carburante non sono pubblici, quindi si assumono 110 kg iniziali, 1 kg finale e consumo costante per giro.
- Il modello non considera la temperatura della pista né la riduzione o l'aumento di resistenza dovuti al traffico.
- Il degrado è adattato con un modello lineare per stint, che non coglie il calo non lineare di fine vita della gomma.
- La modalità confronto tra più piloti è ancora in sviluppo: la vista Distribution non è implementata per più piloti.
- Le gare disponibili sono solo quelle scaricate in cache in anticipo.

## Cosa ho fatto io

Il progetto è individuale: la repository ha un solo autore (adb-coding). Ho sviluppato sia il backend (pulizia dei dati, modello di degrado, API) sia il frontend, e ho configurato il deploy con Docker, Caddy, Oracle e Netlify.

## Come eseguirlo

Requisiti: Node.js per il frontend, Python 3.11 o superiore e uv per il backend.
1. `git clone https://github.com/adb-coding/f1-tyre-deg` e `cd f1-tyre-deg`
2. Backend: `cd backend` e `uv sync`.
3. Facoltativo, scaricare alcune gare in cache dalla radice della repository: `uv run backend/app/save_cached.py 2026` per tutte le gare della stagione fino a oggi, oppure con `--round 3` per un solo round.
4. Avviare il server dalla cartella backend: `uv run uvicorn app.main:app --reload --port 8000`. Si può provare su `localhost:8000`, sull'interfaccia FastAPI a `127.0.0.1:8000/docs/` o con `curl http://localhost:8000/api/rounds-list`.
5. Creare `frontend/.env` con `VITE_API_URL=http://localhost:8000`.
6. Frontend: `cd frontend`, `npm install` e `npm run dev`; la dashboard è su `localhost:5173`.

Il `docker-compose.yml` nella radice serve al deploy sulla macchina virtuale e richiede la variabile `DOMAIN` e le porte 80 e 443, quindi non è pensato come avvio locale rapido. La versione online è su https://f1-tyre-deg.netlify.app/.

## Cosa migliorerei

Il README indica come sviluppi naturali l'implementazione della vista Distribution per più piloti e il superamento delle semplificazioni attuali: temperatura della pista, traffico e un modello non lineare per la fine vita della gomma.

## Domande frequenti

**D: Come stimi il degrado delle gomme?**
R: Tolgo i giri non rappresentativi (box, Safety Car e Virtual Safety Car, primo giro), correggo i tempi per il carburante che cala e adatto per ogni stint una regressione lineare del tempo corretto sull'età della gomma. La pendenza è il degrado in secondi per giro.

**D: Perché usi una cache e non scarichi i dati a richiesta?**
R: I server di live timing della F1 bloccano gli indirizzi IP dei provider cloud, quindi la macchina virtuale non può scaricare le gare al volo. Le gare vengono scaricate in anticipo in locale e la cartella di cache viene copiata sulla macchina.

**D: Quali sono i limiti del modello?**
R: Il carburante è stimato con ipotesi semplici (110 kg iniziali, consumo costante), temperatura della pista e traffico non sono considerati e la regressione lineare non coglie il calo non lineare di fine vita della gomma.

**D: Che stack hai usato e perché è separato in backend e frontend?**
R: Python con FastAPI, FastF1, pandas e scikit-learn per il calcolo, React con TypeScript e Recharts per l'interfaccia. Il backend gira su una macchina virtuale Oracle con Docker e Caddy, il frontend su Netlify.

**D: Come gestisci la memoria del server?**
R: Il server tiene al massimo 3 sessioni di gara in memoria con una cache `lru_cache`; cambiando tra più di tre gare le sessioni vengono ricaricate dalla cache su disco.
