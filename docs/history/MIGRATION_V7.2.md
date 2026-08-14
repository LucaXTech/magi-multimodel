# Migrazione v7.1 → v7.2

Sovrascrivi i file del progetto conservando:

- `.env`
- `.venv`
- `runs`
- `benchmark_results`
- `objective_results`
- `objective_results_v3`
- `bioaudit_results`

Poi:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
```

Per correggere il report di un run v7.1 senza API:

```powershell
python -m benchmark.audit_objective_run objective_results_v3\<timestamp>
```

Per contare le sole righe da recuperare:

```powershell
python -m benchmark.recover_objective objective_results_v3\<timestamp> `
  --systems gemini --real gemini --dry-run
```

Non eseguire il recupero finché il provider continua a restituire quota/rate limit. Il comando reale interrompe automaticamente il batch al primo nuovo 429.
