---
project: Volatility Connectedness (tesi magistrale)
repo: https://github.com/adb-coding/network-connectedness-volatility-spillover
demo: https://adb-coding.github.io/network-connectedness-volatility-spillover/
status: ready
tags: tesi, riassicurazione, rischio sistemico, BVAR, GFEVD, network analysis, volatilità, R, Python, Quarto
---

<!-- Scheda compilata leggendo il README, l'abstract, il capitolo 2 (metodologia), la conclusione e il codice R/Python della repository, il 21 ottobre 2026. I numeri sono quelli riportati nella tesi. -->

## Sintesi

La tesi magistrale "Volatility Connectedness and Network Topology in the Reinsurance Sector" (Università Ca' Foscari Venezia, autore Andrea De Bortoli) analizza il rischio sistemico e i contagi di volatilità nel mercato globale della riassicurazione. Combina un modello Bayesian VAR (BVAR) con l'analisi di rete su 27 compagnie di riassicurazione quotate, da ottobre 2015 a maggio 2025. Trova una rete molto integrata (Total Connectedness 74,28) in cui le compagnie europee sono le principali trasmettitrici di volatilità, e mostra che le misure di rischio di coda indipendenti (ΔCoVaR, MES) confermano gli stessi hub. La repository contiene dati, codice R e Python e i sorgenti Quarto del testo; la tesi è consultabile online in HTML e PDF.

## Problema e obiettivo

Il contributo della riassicurazione alla stabilità finanziaria è poco studiato nella letteratura sul rischio sistemico, con risultati incerti e discordanti. La tesi colma questa lacuna misurando come la volatilità si trasmette tra le riassicuratrici e chi ne è il principale trasmettitore o ricevitore. Gli obiettivi sono quattro: costruire la rete dei contagi di volatilità, analizzarne la struttura statica e le variazioni nel tempo, valutare come reagisce a eventi finanziari, geopolitici e catastrofali, e verificare se la centralità nella rete corrisponde a una reale importanza sistemica misurata con indicatori di mercato indipendenti.

## Dati e fonti

- **Campione:** 27 riassicuratrici quotate in tutto il mondo (4 continenti), quotate su 8 borse diverse.
- **Prezzi:** prezzi giornalieri OHLC (apertura, massimo, minimo, chiusura) scaricati da Yahoo Finance con la libreria yfinance, a partire da ottobre 2015.
- **Sincronizzazione:** per evitare il problema degli scambi non sincroni tra fusi orari, si tengono solo i giorni in cui tutte le borse sono aperte: il campione scende da circa 2.500 giorni potenziali a circa 2.000 giorni di contrattazione comuni. La serie di log-volatilità usata nell'analisi dinamica va dal 27 novembre 2015 al 30 maggio 2025, con 1.993 osservazioni per società.
- **Dati ausiliari:** indice VIX, volumi, dati di bilancio per il calcolo dello SRISK e un file di 13 eventi (catastrofi naturali, eventi finanziari, geopolitici e un evento cyber) per l'analisi dinamica. Ogni evento è classificato come shock sul lato dell'attivo (asset-side), del passivo (liability-side) o di entrambi.
- **Mancanza dei dati contrattuali:** i dati bilaterali di retrocessione tra riassicuratrici non sono pubblici, quindi la rete è inferita dalla volatilità azionaria e non dai contratti.

## Metodo e architettura

La pipeline va dalla volatilità alla rete, poi alle misure di rischio di coda.

1. **Volatilità di Yang-Zhang.** Dai prezzi OHLC si stima la volatilità con lo stimatore di Yang-Zhang su una finestra di 21 giorni, circa un mese (notebook Python `volatility.ipynb`). Lo stimatore combina la varianza overnight, quella open-to-close e quella di Rogers-Satchell, ed è indipendente dal drift e dai salti di apertura e più efficiente della volatilità close-to-close. Si usano i logaritmi delle volatilità.
2. **Test di stazionarietà.** Test ADF e KPSS sulle 27 serie di log-volatilità: l'ADF rifiuta la radice unitaria per tutte le serie; il KPSS rifiuta la stazionarietà in livello per quasi tutte. Dato che per un VAR conta soprattutto l'assenza di radici unitarie e che i priori SOC e SUR accomodano comportamenti vicini alla radice unitaria, si procede con la stima.
3. **BVAR gerarchico.** Un VAR bayesiano a 27 variabili con priori gerarchici di Minnesota, Sum-of-Coefficients (SOC) e Single-Unit-Root (SUR), stimato con MCMC (Metropolis-Hastings per gli iperparametri e Gibbs per i coefficienti), con il pacchetto R `BVAR`. Sono stati stimati 48 modelli (ritardi da 1 a 6, diversi valori di decadimento della varianza), ciascuno con 15.000 estrazioni di cui 5.000 di burn-in, e valutati con la previsione fuori campione a 10 giorni. Il modello scelto ha 4 ritardi, λ = 0,2 e decadimento lineare (α = 1), con RMSE 0,588 e un vantaggio rispetto al VAR frequentista (ΔRMSE = -0,15). Diagnostiche: tasso di accettazione (0,259, nell'intervallo 0,20-0,40), test di Geweke ed Effective Sample Size.
4. **GFEVD e matrice di adiacenza.** Dalla decomposizione generalizzata della varianza dell'errore di previsione (GFEVD, orizzonte H = 10 giorni, come in Diebold e Yilmaz 2014) si ricava la matrice di connectedness. Il Total Connectedness Index (TCI) è la media dei contributi fuori diagonale: 74,28 con i coefficienti alla media a posteriori; propagando l'incertezza sulle 1.000 estrazioni a posteriori la mediana è 77,09 con intervallo di credibilità al 90% [74,03; 80,61].
5. **Analisi di rete statica.** La rete completa viene sparsificata mantenendo gli archi sopra il 50° percentile dei pesi (verificato con soglie al 25° e al 75°). Si calcolano forza uscente ed entrante, forza netta, centralità autovettoriale, PageRank, hub e autorità (HITS), comunità di Louvain, modularità, assortatività e lunghezza media dei cammini.
6. **Analisi dinamica.** BVAR a finestra mobile di 250 osservazioni con passo di 5 giorni, per 349 finestre, parallelizzato con checkpoint. Test di rottura strutturale (OLS-CUSUM e Bai-Perron) sul TCI, studio degli eventi (catastrofi naturali, COVID-19, guerra in Ucraina, crisi bancaria SVB, dazi di Trump) e analisi della topologia nel tempo.
7. **Rischio sistemico di mercato.** ΔCoVaR (regressione quantile su variabili di stato macro, ai quantili 0,5 e 0,05), MES dinamico con modello GJR-GARCH-DCC, SRISK su bilanci di tre anni fiscali (2022-2024) e stress test con funzioni di risposta all'impulso del BVAR; infine validazione incrociata tra centralità di rete e queste misure.

**Struttura della repository.** `Code/scripts` (script R per capitoli 2-5 e `functions.R` con priori, GFEVD e costruzione del grafo), `Code/notebooks` (notebook Python per volatilità e preparazione dei dati), `Data` (dati di input e oggetti serializzati per ogni capitolo), `Quarto` (sorgenti `.qmd` della tesi) e `docs` (tesi renderizzata in HTML, PDF ed EPUB, pubblicata su GitHub Pages).

**Struttura della tesi in 6 capitoli:** introduzione alla riassicurazione, metodologia e dati, analisi di rete statica, analisi di rete dinamica, importanza sistemica con misure di rischio di coda, conclusioni.

## Stack tecnico

- **R:** pacchetti `BVAR`, `coda`, `igraph`, `xUCINET` e altri per il BVAR, la diagnostica MCMC e l'analisi di rete (script eseguiti dalla radice del progetto con directory di lavoro `C:/TESI`).
- **Python:** pandas e yfinance nei notebook per scaricare i prezzi e calcolare la volatilità di Yang-Zhang.
- **Quarto:** impaginazione della tesi con codice R eseguito dentro i documenti, resa in HTML, PDF ed EPUB.
- **Calcolo:** stima del BVAR parallelizzata, con checkpoint per la stima a finestra mobile (349 finestre).
- **Uso di strumenti AI:** la tesi dichiara in una sezione dedicata di aver usato Claude Code e Gemini CLI per sviluppo e debug del codice, revisione linguistica e controllo metodologico. Le analisi sono eseguite in R e Python; nessuno strumento AI ha prodotto conclusioni, output statistici o immagini.

## Decisioni e alternative scartate

- **Volatilità di Yang-Zhang invece di close-to-close:** stimatore più efficiente con meno dati e indipendente dal drift. Limite dichiarato: le azioni delle riassicuratrici hanno comportamento con salti (annunci di perdite catastrofali), quindi l'indice è un proxy robusto e non una misura perfetta.
- **BVAR gerarchico invece del VAR frequentista:** in un sistema con 27 variabili i parametri sono troppi rispetto alle osservazioni, e i priori Minnesota, SOC e SUR regolarizzano la stima. Nel confronto fuori campione il BVAR batte il VAR fino a 4 ritardi.
- **4 ritardi:** con 1-3 ritardi i modelli sottostimano (RMSE sopra 0,59), con 5-6 il BVAR peggiora rispetto al VAR per eccesso di restringimento dei ritardi lontani.
- **Soglia al 50° percentile per sparsificare la rete:** la rete di Diebold-Yilmaz è completa, quindi si tengono solo i collegamenti più forti, separando canali di trasmissione dal rumore. La scelta è stata verificata con soglie al 25° e al 75°.
- **Finestra mobile di 250 osservazioni:** permette di seguire come cambia la connectedness nel tempo. Con 27 variabili e 4 ritardi i parametri superano le osservazioni, e il Minnesota prior regolarizza la stima. La sensibilità alla lunghezza della finestra non è stata esplorata.
- **Misure di rischio indipendenti (ΔCoVaR, MES):** servono a convalidare la rete con metodi che non condividono lo stimatore con la GFEVD. Lo SII (indice di impatto sistemico) deriva dalla stessa distribuzione a posteriori del BVAR e quindi conferma la coerenza interna del modello, ma non è una validazione indipendente.

## Risultati

- **Rete statica:** il mercato è molto integrato, con TC = 74,28, lunghezza media dei cammini L = 0,39, modularità bassa (Q = 0,162) e struttura disassortativa (r = -0,116). AXA XL, Munich Re e Swiss Re sono i principali contributori di varianza; le società asiatiche e americane sono ricevitori netti. I collegamenti più forti sono tra società giapponesi (blocco regionale quasi autosufficiente) e tra società europee (dorsale globale).
- **Rete dinamica:** il TCI non è stazionario. Il test Bai-Perron individua quattro rotture strutturali e cinque regimi: l'alta connessione legata agli uragani del 2017, una stabilizzazione, il picco del COVID-19, una fase elevata durante la guerra Russia-Ucraina e una graduale normalizzazione. Il valore statico di 74,28 è sopra il 75° percentile del TCI mobile, quindi la stima statica è spostata verso l'alto dalle fasi di alta connessione.
- **Asimmetria:** la rete si contrae circa 2,2 volte più rapidamente di quanto si espande (coefficiente -0,695 sulla lunghezza dei cammini quando il TCI scende, contro -0,314 quando sale), e la modularità scende con il TCI (correlazione -0,78).
- **Eventi:** gli shock sul lato dell'attivo (asset-side: COVID-19, dazi di Trump) sincronizzano la rete e amplificano la gerarchia dei trasmettitori europei; gli shock sul lato del passivo (liability-side: per esempio gli uragani) la frammentano lungo le esposizioni idiosincratiche.
- **Hub persistenti e reattivi:** Chubb e Mapfre sono tra gli hub per centralità autovettoriale in tutte le finestre, pur non essendo ai primi posti nell'analisi statica; RenaissanceRe e AXIS Capital diventano centrali solo durante specifici eventi di stress.
- **Rischio di coda:** ΔCoVaR e MES confermano che le europee generano i maggiori incrementi marginali del rischio di coda del sistema, e la forza netta correla in modo significativo con entrambi.
- **Rischio sistemico senza fragilità di bilancio:** nessuna società ha SRISK positivo in nessuno scenario o anno fiscale analizzato, quindi il rischio sistemico della riassicurazione deriva da interconnessione e propagazione degli shock, non da leva finanziaria o insufficienza di capitale.
- **Stress test:** uno shock di una deviazione standard a Munich Re si propaga in modo ampio e decade lentamente, mentre lo stesso shock a una società asiatica periferica è più locale e breve.

## Limiti noti

- La volatilità azionaria è un proxy dei legami reali di trasferimento del rischio, perché i dati bilaterali di retrocessione non sono pubblici. La rete misura associazione statistica, non esposizioni contrattuali.
- L'orizzonte H = 10 giorni segue la convenzione di Diebold e Yilmaz ma non è giustificato per la riassicurazione, dove regolamento dei sinistri e aggiustamenti di capitale hanno tempi più lunghi; la sensibilità non è stata testata formalmente.
- La finestra mobile ha 250 osservazioni, 27 variabili e 4 ritardi, quindi molti più parametri che osservazioni; il Minnesota prior regolarizza, ma la sensibilità alla lunghezza della finestra non è stata esplorata.
- Bias di sopravvivenza: sono escluse società uscite dal mercato per insolvenza, fusione o delisting.
- Lo SRISK copre solo tre anni fiscali, in un periodo di connectedness moderata, ed è calibrato su bilanci bancari.
- Le società quotate sono un campione ridotto di un settore in buona parte privato.
- Il TCI è coincidente con lo stress di mercato ma non è anticipato dal VIX, quindi il VIX non serve come indicatore anticipatore della connectedness della riassicurazione.

## Cosa ho fatto io

La tesi è un lavoro individuale di Andrea De Bortoli: ho scelto il campione di 27 riassicuratrici, raccolto i dati, scritto il codice per la volatilità, il BVAR, la rete, l'analisi dinamica e le misure di rischio di coda, interpretato i risultati e scritto il testo. Gli strumenti di intelligenza artificiale usati (Claude Code e Gemini CLI) sono dichiarati nella tesi e servivano a sviluppo e debug del codice, revisione linguistica e controllo metodologico, con verifica indipendente degli output.

## Come eseguirlo

1. Clonare la repository `network-connectedness-volatility-spillover`.
2. Eseguire in Python i notebook in `Code/notebooks` (`dataframes_creation.ipynb`, `volatility.ipynb`) per ottenere volatilità e rendimenti, oppure usare i file già presenti in `Data/`.
3. Eseguire gli script R di `Code/scripts` dalla radice del progetto, in ordine di capitolo: `ch2_stationarity.R`, `ch2_BVAR.R`, `ch3.R`, `ch4_analysis_polished.R` (la stima a finestra mobile è lunga, con checkpoint), `ch5.R`. Gli script assumono come directory di lavoro `C:/TESI`, quindi i percorsi vanno adattati.
4. Per rigenerare il testo, eseguire `quarto render` dentro la cartella `Quarto/`.

I risultati intermedi di ogni capitolo sono già salvati in `Data/ch2`, `Data/ch3`, `Data/ch4`, `Data/ch5`. La tesi renderizzata è su https://adb-coding.github.io/network-connectedness-volatility-spillover/ con link al PDF.

## Cosa migliorerei

La tesi indica come sviluppi futuri: modelli BVAR a parametri variabili nel tempo (TVP-BVAR) con volatilità stocastica, al posto della finestra mobile; l'estensione dello SRISK a tutto il periodo; la ricostruzione della rete da dati bilaterali di retrocessione, se resi disponibili, per validarla contro la topologia contrattuale; altre misure sistemiche come la CoES usata nel test di stress dell'EIOPA e test di causalità di Granger tra centralità e misure di rischio; una simulazione di contagio a partire dalle società più importanti.

## Domande frequenti

**D: Di cosa tratta la tesi?**
R: Del rischio sistemico nel mercato globale della riassicurazione: misura come la volatilità delle azioni di 27 riassicuratrici si trasmette tra le società, costruisce una rete di contagio con un BVAR e verifica se le società più centrali sono anche quelle che contribuiscono di più al rischio di coda del sistema.

**D: Perché un BVAR e non un VAR normale?**
R: Con 27 variabili e 4 ritardi i parametri sono molti rispetto alle osservazioni. I priori bayesiani di Minnesota, SOC e SUR regolarizzano la stima, e nel confronto fuori campione a 10 giorni il BVAR ha avuto RMSE più basso del VAR fino a 4 ritardi.

**D: Qual è il risultato principale?**
R: La rete è molto integrata (TC = 74,28), con le riassicuratrici europee, in particolare AXA XL, Munich Re e Swiss Re, come principali trasmettitrici, e la centralità in rete corrisponde ai contributi più alti al rischio di coda misurati con ΔCoVaR e MES. Allo stesso tempo nessuna società ha un SRISK positivo: nel settore il rischio sistemico viene dall'interconnessione, non dalla leva.

**D: Come hai calcolato la volatilità?**
R: Con lo stimatore di Yang-Zhang su prezzi giornalieri di apertura, massimo, minimo e chiusura scaricati da Yahoo Finance. È indipendente dal drift e dai salti di apertura e più efficiente della volatilità close-to-close.

**D: Che limiti ha lo studio?**
R: La rete deriva dalla volatilità azionaria e non da esposizioni contrattuali, che non sono pubbliche; l'orizzonte di 10 giorni e la finestra di 250 giorni non sono stati testati in sensibilità; il campione ha bias di sopravvivenza e lo SRISK copre solo tre anni.

**D: Come hai gestito il fatto che hai usato strumenti di AI?**
R: L'uso è dichiarato in una sezione della tesi: Claude Code e Gemini CLI per sviluppo e debug del codice, revisione linguistica e controllo metodologico. Le analisi sono state eseguite in R e Python, ogni output è stato verificato e nessuno strumento ha generato conclusioni, risultati statistici o immagini.

**D: Come si riproduce il lavoro?**
R: I notebook Python producono volatilità e rendimenti, gli script R dei capitoli 2-5 stimano il BVAR, costruiscono la rete e calcolano le misure di rischio, e `quarto render` rigenera il testo. I risultati intermedi sono già salvati nella cartella Data.
