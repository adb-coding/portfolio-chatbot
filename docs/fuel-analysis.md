---
project: Fuel-analysis
repo: https://github.com/adb-coding/fuel-analysis
demo: https://adbcoding.pythonanywhere.com/
status: ready
tags: dashboard, energia, prezzi carburanti, Europa, Python, Plotly Dash, Brent, pandas
---

<!-- Scheda compilata leggendo README, codice (app.py, helper.py, pages/*.py), workflow GitHub e dati della repository, il 21 ottobre 2026. Le frasi sono tratte da ciò che è nel codice o nel README. -->

## Sintesi

Fuel-analysis è una dashboard interattiva online che confronta i prezzi settimanali di benzina (Euro95) e gasolio nei Paesi dell'Unione Europea e li mette in relazione con il prezzo del petrolio Brent. È scritta in Python con Plotly Dash e pandas, i dati della Commissione Europea si aggiornano da soli ogni settimana tramite GitHub Actions, e la versione live è pubblicata su PythonAnywhere.

## Problema e obiettivo

La domanda di partenza del progetto è come differiscono i prezzi di benzina e gasolio tra i Paesi dell'Unione Europea e quanto sono correlati con il prezzo del petrolio. L'obiettivo è offrire una dashboard semplice ma efficace per confrontare l'evoluzione storica, capire gli ultimi picchi di prezzo e aumentare la consapevolezza della situazione europea. Una parte del lavoro si concentra sulle politiche fiscali italiane sui carburanti e sul loro effetto.

## Dati e fonti

In Fuel-analysis i dati arrivano da quattro fonti:
- **Prezzi di benzina Euro95 e gasolio:** Weekly Oil Bulletin della Commissione Europea, file Excel con prezzi settimanali al consumo, con e senza tasse e accise. Nella versione della repository la serie parte dal 3 gennaio 2005 ed è settimanale.
- **Petrolio Brent e cambio EUR/USD:** scaricati da Yahoo Finance con la libreria yfinance (ticker BZ=F ed EUR=X) e usati per esprimere il prezzo del greggio in euro per litro.
- **Inflazione:** tasso annuo HICP dell'area euro, pubblicato dalla Banca Centrale Europea.
- **Eventi:** una cronologia di 42 eventi tra il 2007 e il 2026 (geopolitici, di mercato, fiscali e legati alle politiche di Trump), con descrizione e categoria prodotte con l'aiuto di ChatGPT. Il dettaglio è maggiore per gli ultimi anni, con particolare attenzione al recente conflitto tra USA e Iran e alle misure fiscali italiane sui carburanti.

Solo Euro95 e gasolio sono analizzati. Il prezzo del GPL non è considerato.

## Metodo e architettura

La dashboard è organizzata in tre pagine, gestite da `app.py` e contenute nella cartella `pages/`:
- **Price Chart** (pagina principale): grafico a linee dei prezzi settimanali con confronto tra Paesi e con la media UE; si può scegliere tra prezzo pieno, prezzo al netto delle tasse e componente fiscale (differenza tra i due). Mostra anche la variazione percentuale settimanale, la volatilità, la correlazione e l'inflazione.
- **Map:** mappa coropletica dell'Europa per confrontare il prezzo di ogni Paese, attuale o in una data passata, con la media delle ultime 10 settimane.
- **Events:** impatto degli eventi sul prezzo della benzina in Italia e confronto con le misure fiscali del governo italiano.

I calcoli principali, in `helper.py`:
- I prezzi del bollettino sono espressi per 1000 litri e vengono divisi per 1000 per ottenere euro al litro.
- Il Brent in dollari al barile viene convertito in euro per litro moltiplicando per il cambio EUR/USD e dividendo per 158,987 (litri in un barile).
- La variazione percentuale settimanale usa la funzione `pct_change`.
- La volatilità è la deviazione standard mobile su 4 settimane delle variazioni percentuali.
- La correlazione è quella di Pearson tra prezzo del petrolio, benzina e gasolio nella finestra di date scelta dall'utente. Appare come matrice di correlazione (heatmap) e come grafico a dispersione con retta OLS.
- L'impatto di un evento è la variazione percentuale del prezzo Euro95 italiano tra la settimana più vicina alla data dell'evento e la settimana successiva.

## Stack tecnico

Python con pandas per la pulizia dei dati, yfinance per Brent e cambio, openpyxl per leggere i file Excel, Plotly e Dash (con dash-bootstrap-components) per grafici e interfaccia. Tutto il codice è in un'unica applicazione Dash con più pagine (`use_pages=True`). L'applicazione è pubblicata su PythonAnywhere. I file Excel e CSV sono nella cartella `data/` della repository.

## Aggiornamento automatico

Un workflow di GitHub Actions (`update-weekly-oil-bulletin.yml`) parte ogni giovedì (cron `30 10 * * 4`, in UTC) e anche manualmente. Cerca nella pagina della Commissione Europea il link al file Excel dei prezzi storici, lo scarica, verifica che sia un vero file XLSX valido (controlla l'intestazione ZIP, la presenza di `xl/workbook.xml` e l'integrità del file) e lo committa nella repository solo se è cambiato. Così i dati sono aggiornati senza intervento manuale.

## Decisioni e alternative scartate

- **Dashboard interattiva con Plotly Dash:** l'utente sceglie Paesi, carburanti, tipo di prezzo e finestra temporale direttamente nell'interfaccia.
- **Prezzi con e senza tasse:** il progetto usa entrambi i fogli del bollettino e calcola la componente fiscale come differenza.
- **Brent convertito in euro per litro:** il README spiega che la conversione serve a esprimere il greggio in euro e a studiarne la relazione con i prezzi dei carburanti.
- **Aggiornamento tramite GitHub Actions:** il file della Commissione viene scaricato e validato in automatico e committato solo se cambia.
- **Fuori dal perimetro:** il GPL, per mancanza di dati omogenei tra Paesi (motivazione riportata nel README), e l'analisi degli eventi per Paesi diversi dall'Italia.

## Risultati

Fuel-analysis è uno strumento esplorativo e non riporta risultati numerici fissi nella documentazione. Permette di vedere l'evoluzione dei prezzi di benzina e gasolio in ogni Paese rispetto alla media UE, quanto pesano le tasse sul prezzo finale, quanto i prezzi seguono il Brent e quale variazione settimanale è associata a eventi come crisi geopolitiche o tagli alle accise in Italia. La correlazione è di Pearson e, come avverte la dashboard, non implica causalità.

## Limiti noti

- Le incongruenze tra Paesi possono dipendere dai metodi con cui ogni Stato membro misura il proprio mercato e comunica i dati alla Commissione.
- Solo Euro95 e gasolio sono analizzati; il GPL è escluso.
- La cronologia degli eventi è stata generata con l'aiuto di ChatGPT e si concentra sul conflitto USA-Iran e sulle politiche fiscali italiane.
- L'analisi degli eventi è limitata all'Italia; non include i mercati interni di altri Paesi.
- L'impatto di un evento è misurato su una sola settimana dopo la data dell'evento, quindi non isola altri fattori che muovono il prezzo nello stesso periodo.
- La correlazione di Pearson misura l'associazione, non la causalità.

## Cosa ho fatto io

Il progetto è individuale: tutta la repository è opera di un solo autore (adb-coding). Ho scelto le fonti, scritto la pulizia dei dati e i calcoli, costruito le tre pagine della dashboard, impostato il workflow di aggiornamento automatico e pubblicato l'applicazione online us PythonAnywhere.

## Come eseguirlo

1. `git clone https://github.com/adb-coding/fuel-analysis.git` e `cd fuel-analysis`
2. `pip install -r requirements.txt` (pandas, numpy, dash, dash-bootstrap-components, plotly, yfinance, openpyxl). Si consiglia un ambiente virtuale.
3. `python app.py` e aprire il link mostrato nel terminale.

Serve la connessione a internet perché al caricamento viene scaricata da Yahoo Finance la serie storica del Brent. La versione online è consultabile su https://adbcoding.pythonanywhere.com/.

## Cosa migliorerei

La documentazione indica come sviluppo principale un'analisi degli eventi più completa, estesa anche ai mercati interni di altri Paesi oltre all'Italia. Nel codice è presente anche la funzione `adjust_for_inflation`, ancora vuota, pensata per la correzione dei prezzi per l'inflazione.

## Domande frequenti

**D: Che cosa mostra Fuel-analysis?**
R: Mostra l'andamento dei prezzi settimanali di benzina Euro95 e gasolio nei Paesi UE, con e senza tasse, confrontati con la media europea e con il prezzo del Brent espresso in euro per litro.

**D: Da dove arrivano i dati e come restano aggiornati?**
R: I prezzi vengono dal Weekly Oil Bulletin della Commissione Europea, il Brent e il cambio da Yahoo Finance, l'inflazione dalla BCE. Un workflow di GitHub Actions scarica e valida il file della Commissione ogni giovedì.

**D: Come hai analizzato la relazione con il prezzo del petrolio?**
R: Con la correlazione di Pearson tra petrolio, benzina e gasolio sulla finestra di date scelta dall'utente, mostrata come matrice e come grafico a dispersione con retta OLS. Misura l'associazione, non la causalità.

**D: Come misuri l'effetto di un evento sul prezzo?**
R: Calcolo la variazione percentuale del prezzo Euro95 italiano tra la settimana più vicina all'evento e la successiva, poi confronto gli eventi per categoria. È una misura semplice e non isola altri fattori.

**D: Quali limiti ha il progetto?**
R: I dati nazionali possono essere misurati in modo diverso, il GPL è escluso, gli eventi sono stati classificati con l'aiuto di ChatGPT e l'analisi degli eventi riguarda solo l'Italia.
