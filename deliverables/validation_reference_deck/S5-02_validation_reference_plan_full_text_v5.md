# Piano di validazione S5-02

## Slide 1 - Piano di validazione S5-02

Dataset di riferimento, unità di campionamento e requisiti minimi.

Orizzonte di valutazione: 3 mesi.

GEO-K / IRIDE

Versione consolidata | 6 ottobre 2026

## Slide 2 - Campagna in sintesi

Campioni minimi richiesti per prodotto nel periodo di tre mesi.

- 01: 15
- 02: 15
- 03: 30
- 04: 30
- 05: 15
- 06: 30
- 07: 3
- 08: 3
- 09: 15
- 10: 15
- 11: 15

Totale: 186 campioni minimi complessivi.

Regole comuni di selezione:

- Ogni campione supera i controlli di qualità del proprio riferimento.
- Il minimo definisce la soglia della campagna, non un limite massimo.
- Tutti i matchup validi aggiuntivi entrano nella validazione.

## Slide 3 - Sette dataset di riferimento

Ogni famiglia di prodotto usa una diversa unità di confronto.

- Landsat 8/9, prodotti 01, 02, 10 e 11: acquisizione per sub-AOI con pixel coincidenti, cloud/QC e overlap adeguati. Minimo: 15.
- ERA5, prodotto 03: ora diurna con radiazione significativa, elevazioni solari diverse e cloud cover considerata. Minimo: 30.
- Reti pluviometriche, prodotto 04: ora con misura osservata, includendo eventi piovosi e casi asciutti utili alla false detection. Minimo: 30.
- Sentinel-2 SCL, prodotto 05: acquisizione dopo cloud/QC, con neve rappresentata quando disponibile e casi snow-free. Minimo: 15.
- MSG/SEVIRI Cloud Mask, prodotto 06: ora scelta tra condizioni serene, parzialmente nuvolose e nuvolose. Minimo: 30.
- GOSAT FTS L3, prodotti 07 e 08: mese con almeno il 20% dell'Italy AOI e, se possibile, due sub-AOI; sono inclusi tutti i matchup validi. Minimo: 3 per prodotto.
- AERONET, prodotto 09: station-day dopo cloud screening e controlli di qualità, distribuiti su giorni e condizioni differenti. Minimo: 15.

La granularità temporale e spaziale del riferimento determina sia l'unità sia i filtri applicati.

## Slide 4 - Landsat 8/9 per 01, 02, 10 e 11

Cinque acquisizioni valide in ciascuna delle tre sub-AOI.

- 11 opportunità teoriche per area in 3 mesi.
- 5 acquisizioni valide richieste per sub-AOI.
- 15 campioni minimi per prodotto.

Le sub-AOI North, Center e South sono terrestri per 01 e 10 e marine per 02 e 11.

Filtro di validità: si confrontano soltanto i pixel S5-02 coincidenti con pixel Landsat validi. Cloud cover, quality flags e sovrapposizione spaziale riducono le opportunità teoriche.

Dettaglio del downscaling: per 10 e 11 la risoluzione Landsat permette di verificare il dettaglio spaziale aggiunto rispetto ai prodotti 01 e 02.

## Slide 5 - Campionamento dei prodotti orari

Dieci ore valide per sub-AOI, trenta campioni per prodotto.

- 03 Solar Radiation, ERA5: ore diurne, diverse elevazioni solari e cloud cover considerata. Minimo: 10 × 3 = 30.
- 04 Precipitation, reti pluviometriche: ore con precipitazione osservata, più casi asciutti per false detection. Minimo: 10 × 3 = 30.
- 06 Cloud Cover, MSG/SEVIRI Cloud Mask: condizioni serene, parzialmente nuvolose e nuvolose. Minimo: 10 × 3 = 30.

Per 03, le ore con radiazione diretta nulla o quasi nulla hanno bassa capacità discriminante.

Per 04, il campione deve includere eventi precipitativi. Una selezione casuale rischia di privilegiare ore asciutte.

Per 06, la distribuzione tra classi di nuvolosità evita che una singola condizione domini il risultato.

## Slide 6 - Snow cover e aerosol

Due unità di campionamento diverse per prodotti giornalieri.

Prodotto 05, Snow Cover, Sentinel-2 SCL: 5 acquisizioni valide per North, Center e South. Totale minimo: 15. I campioni senza neve servono a misurare le false detection; la neve deve essere rappresentata quando disponibile.

Prodotto 09, Aerosol/AOD, AERONET: 5 station-day validi per North, Center e South. Totale minimo: 15. I campioni saranno distribuiti, ove possibile, su giornate e condizioni atmosferiche differenti.

Criterio operativo: cloud screening, controlli di qualità e indisponibilità temporanee rendono discontinue le misure AERONET. Il minimo di 15 mantiene la copertura territoriale; tutti i matchup validi aggiuntivi saranno inclusi.

## Slide 7 - Validazione mensile di CH4 e CO2

Tre campioni temporali per prodotto, subordinati alla copertura GOSAT.

Il mese è l'unità temporale perché la copertura GOSAT è spazialmente discontinua. Ogni mese accettato costituisce un campione temporale. Il confronto usa i matchup spaziali disponibili nel mese, non una singola osservazione rappresentativa.

Verifica della copertura: il mese è valido se almeno il 20% dell'Italy AOI è coperto da celle GOSAT valide; dove possibile, la copertura interessa almeno due aree tra North, Center e South.

Costruzione del campione: per ciascun mese accettato entrano nel confronto tutti gli spatial matchup validi disponibili, senza ridurli a un unico valore.

- 07 Methane: GOSAT FTS L3 CH4.
- 08 CO2: GOSAT FTS L3 CO2.

## Slide 8 - Chiusura

Grazie

Domande
