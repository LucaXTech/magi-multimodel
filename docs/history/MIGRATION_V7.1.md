# Aggiornamento da v7 a v7.1

Copia il contenuto del pacchetto nella cartella del progetto e conserva:

- `.env`
- `.venv`
- `runs`
- `benchmark_results`
- `objective_results`
- `objective_results_v3`
- `bioaudit_results`

Poi esegui soltanto i controlli locali:

```powershell
python -m pip install -r requirements.txt
python -m benchmark.validate_objective
python -m benchmark.preflight --split dev --limit 12 --seed 20260806
python -m benchmark.run_objective --mock --split dev --limit 6 --seed 20260806
```

Non lanciare ancora il test set. Il primo run reale previsto dal protocollo è documentato in `benchmark\PROTOCOL_V3.md`.
