# Objective Benchmark v3 — reliability rules v7.2

Il benchmark v3 separa development e test, usa casi oggettivi e conserva un test set bloccato tramite SHA256.

## Regola fondamentale

Un fallimento tecnico non è una risposta scientificamente sbagliata.

Le analisi distinguono:

- `COMPLETE` / `INCOMPLETE`;
- coverage;
- valid accuracy;
- end-to-end accuracy;
- technical failure rate;
- parse failure rate su chiamate tecnicamente riuscite;
- critical reasoning error rate sulle sole righe valutabili.

I confronti appaiati usano esclusivamente casi valutabili per entrambi i sistemi.

## Preflight

```powershell
python -m benchmark.validate_objective
python -m benchmark.preflight --split dev --limit 12 --seed 20260806
python -m benchmark.run_objective --mock --split dev --limit 6
```

## Audit di un run già eseguito

```powershell
python -m benchmark.audit_objective_run objective_results_v3\<timestamp>
```

Non effettua chiamate API.

## Recovery selettivo

```powershell
python -m benchmark.recover_objective objective_results_v3\<timestamp> `
  --systems gemini --real gemini --dry-run
```

Poi, quando il provider è disponibile:

```powershell
python -m benchmark.recover_objective objective_results_v3\<timestamp> `
  --systems gemini --real gemini
```

Le righe riuscite vengono copiate; soltanto quelle fallite sono rieseguite.

## Stop rule

Non passare alle ablation o al locked test quando:

- una baseline è incompleta;
- una o più baseline forti sono al ceiling;
- meno del 20% dei casi produce disaccordo utile;
- non esiste un meccanismo plausibile con cui MAGI possa correggere la baseline.

In questi casi si crea un nuovo protocollo senza aprire il test v3.

Vedi `OBJECTIVE_V4_BLUEPRINT.md`.
