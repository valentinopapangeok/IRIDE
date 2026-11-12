# Piano di validazione S5-02

## Slide 1 - Piano di validazione S5-02

Dataset di riferimento, unità di osservazione e requisiti minimi.

Orizzonte di valutazione: 3 mesi.

GEO-K / IRIDE

Versione consolidata | 8 ottobre 2026

## Slide 2 - Piano di osservazione del riferimento

I volumi minimi sono espressi secondo l'unità appropriata per ciascun dataset.

- Prodotti 01, 02, 10 e 11, Landsat 8/9: 15 acquisizioni valide, 5 per sub-AOI. La disponibilità dipende da revisit, nuvolosità, controlli di qualità e sovrapposizione.
- Prodotto 03, ERA5: 30 produzioni orarie. La disponibilità elevata consente di rappresentare condizioni di irraggiamento differenti.
- Prodotto 04, reti pluviometriche: 30 eventi regionali ora, selezionati per includere precipitazioni osservate e casi asciutti utili alla verifica delle false detection.
- Prodotto 05, Sentinel-2 SCL: 15 acquisizioni valide, 5 per sub-AOI, includendo neve quando disponibile e casi senza neve.
- Prodotto 06, MSG/SEVIRI Cloud Mask: 30 produzioni orarie, distribuite tra condizioni di nuvolosità differenti.
- Prodotti 07 e 08, GOSAT FTS L3: fino a 3 mensilità utilizzabili, in funzione della copertura GOSAT valida.
- Prodotto 09, AERONET: 15 station-day validi, 5 per sub-AOI, distribuiti ove possibile su giornate e condizioni atmosferiche differenti.

Questi volumi descrivono i dati da confrontare con il riferimento. Non definiscono periodicità, aggregazione o modalità di calcolo dei KPI.

## Slide 3 - Sette dataset di riferimento

Ogni famiglia di prodotto usa una diversa unità di confronto e regole di selezione coerenti con il riferimento disponibile.

- Landsat 8/9, prodotti 01, 02, 10 e 11: acquisizione per sub-AOI con pixel coincidenti, cloud/QC e sovrapposizione adeguati. Minimo: 15.
- ERA5, prodotto 03: ora diurna con radiazione significativa, elevazioni solari diverse e cloud cover considerata. Minimo: 30.
- Reti pluviometriche, prodotto 04: evento regionale ora con misura osservata, includendo eventi piovosi e casi asciutti utili alla false detection. Minimo: 30.
- Sentinel-2 SCL, prodotto 05: acquisizione dopo cloud/QC, con neve rappresentata quando disponibile e casi senza neve. Minimo: 15.
- MSG/SEVIRI Cloud Mask, prodotto 06: ora scelta tra condizioni serene, parzialmente nuvolose e nuvolose. Minimo: 30.
- GOSAT FTS L3, prodotti 07 e 08: mensilità con almeno il 20% dell'Italy AOI e, se possibile, due sub-AOI; sono inclusi tutti i matchup validi. Fino a 3 mensilità utilizzabili.
- AERONET, prodotto 09: station-day dopo cloud screening e controlli di qualità, distribuiti su giorni e condizioni differenti. Minimo: 15.

La granularità temporale e spaziale del riferimento determina l'unità e i filtri applicati.

## Slide 4 - Landsat 8/9 per 01, 02, 10 e 11

Cinque acquisizioni valide in ciascuna delle tre sub-AOI.

- Circa 11 opportunità teoriche per area in 3 mesi, considerando il revisit combinato di Landsat 8 e 9.
- 5 acquisizioni valide richieste per sub-AOI.
- 15 acquisizioni valide complessive per prodotto.

Le sub-AOI North, Center e South sono terrestri per 01 e 10 e marine per 02 e 11. Le sub-AOI servono perché una singola acquisizione del riferimento non garantisce la copertura valida dell'intera AOI.

Si confrontano soltanto i pixel S5-02 coincidenti con pixel Landsat validi. Nuvolosità, quality flag e sovrapposizione spaziale riducono le opportunità teoriche. Per 10 e 11, la risoluzione Landsat permette anche di verificare il dettaglio spaziale aggiunto dal downscaling.

## Slide 5 - Campionamento dei prodotti orari

Trenta produzioni distribuite tra aree e condizioni rappresentative.

- Prodotto 03, Solar Radiation, ERA5: ore diurne con radiazione significativa, diverse elevazioni solari e cloud cover considerata. Minimo: 30 produzioni.
- Prodotto 04, Precipitation, reti pluviometriche: eventi regionali con precipitazione osservata e casi asciutti utili alla verifica delle false detection. Minimo: 30 eventi-ora.
- Prodotto 06, Cloud Cover, MSG/SEVIRI Cloud Mask: condizioni serene, parzialmente nuvolose e nuvolose. Minimo: 30 produzioni.

Per 03, le ore con radiazione diretta nulla o quasi nulla hanno bassa capacità discriminante. Per 04, la selezione deve includere eventi precipitativi, perché una selezione non stratificata rischierebbe di privilegiare ore asciutte. Per 06, la distribuzione tra classi di nuvolosità evita che una singola condizione domini il confronto.

## Slide 6 - Snow cover e aerosol

Due unità di osservazione diverse per prodotti giornalieri.

Prodotto 05, Snow Cover, Sentinel-2 SCL: 5 acquisizioni valide per North, Center e South, per un totale minimo di 15. I casi senza neve servono a verificare le false detection; la neve deve essere rappresentata quando disponibile.

Prodotto 09, Aerosol/AOD, AERONET: 5 station-day validi per North, Center e South, per un totale minimo di 15. Le osservazioni saranno distribuite, ove possibile, su giornate e condizioni atmosferiche differenti.

Cloud screening, controlli di qualità e indisponibilità temporanee rendono discontinue le misure AERONET. Il minimo di 15 mantiene la copertura territoriale; tutti gli ulteriori matchup validi disponibili saranno inclusi.

## Slide 7 - Disponibilità del riferimento per CH4 e CO2

Le mensilità utilizzabili dipendono dalla copertura GOSAT.

Nel periodo di tre mesi possono essere disponibili fino a tre produzioni mensili utili per prodotto. Il mese è l'unità temporale perché la copertura GOSAT è spazialmente discontinua.

Una mensilità è utilizzabile se almeno il 20% dell'Italy AOI è coperto da celle GOSAT valide e, dove possibile, la copertura interessa almeno due aree tra North, Center e South. Per ciascuna mensilità accettata entrano nel confronto tutti gli spatial matchup validi disponibili, senza ridurli a un unico valore.

- Prodotto 07, Methane: GOSAT FTS L3 CH4.
- Prodotto 08, CO2: GOSAT FTS L3 CO2.

La periodicità e l'aggregazione del KPI restano da concordare e non vengono definite in questa proposta.

## Slide 8 - Chiusura

Grazie

Domande
