# Audit tecnico-scientifico: v7 → v7.1

## Perché il pilot v7 non distingueva i modelli

Il 100% di tutti i modelli sui primi tre casi non dimostrava equivalenza tra sistemi. L'audit del codice e del dataset ha trovato:

1. `--limit` prendeva il prefisso fisico del JSONL;
2. i primi otto casi appartenevano tutti a validation/leakage;
3. i primi otto MCQ avevano tutti risposta B;
4. tra i 32 MCQ non comparivano risposte C o D;
5. l'ID semantico del caso veniva mostrato nel prompt e poteva suggerire l'abilità testata;
6. la risposta corretta era spesso l'opzione più lunga;
7. development e test non erano separati;
8. la baseline “migliore” poteva essere scelta dopo aver visto il test;
9. il mock stampava metriche facilmente scambiabili per risultati reali;
10. il report non separava errori critici, domini e formati.

## Correzioni v7.1

- 48 casi nuovi: 24 development e 24 locked test;
- 6 domini × 4 casi in ciascuno split;
- 12 MCQ, 6 multi-select, 6 numerici per split;
- MCQ esattamente bilanciati A/B/C/D;
- multi-select bilanciati per numero di risposte corrette;
- controllo automatico dei length cue;
- ID esclusi dai prompt;
- option permutation riproducibile e comune a tutti i sistemi;
- ordine dei sistemi ruotato deterministicamente per caso;
- selezione stratificata indipendente dall'ordine del file;
- test set congelato tramite SHA256;
- test CLI bloccato senza baseline prespecificata;
- exact accuracy come endpoint primario;
- critical-error rate, breakdown, costo/corretto, McNemar esatto e bootstrap appaiato;
- manifest con modelli e impostazioni di generazione;
- mock chiaramente marcato come smoke test non interpretabile;
- protocollo a fasi e stop rules.

## Limiti ancora presenti

1. I casi sono internamente redatti e revisionati, non ancora validati da esperti esterni.
2. Il test da 24 casi è un engineering pilot, non ha potenza sufficiente per claim forti.
3. Il judge può mostrare self/family bias anche con candidati anonimizzati.
4. La confidenza verbalizzata non equivale a una probabilità calibrata validata.
5. I parametri di sampling non sono uniformati tra provider; il manifest lo dichiara.
6. Una futura pubblicazione richiede almeno 100 casi test, answer key indipendenti e preregistrazione.

## Decisione operativa

Non eseguire più mini-run scelti ad hoc. Il prossimo run reale è unico e prespecificato: quattro baseline sull'intero development set. I risultati servono soltanto a scegliere baseline e finalist; il locked test rimane intatto.
