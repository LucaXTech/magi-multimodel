from __future__ import annotations

import argparse
import csv
import json
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel


HTML = r'''<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MAGI — Revisione semplice</title>
<style>
:root{color-scheme:dark;--bg:#060a10;--panel:#111a26;--panel2:#0b111a;--line:#26364b;--text:#eef5ff;--muted:#9db0c8;--cyan:#42d8ff;--green:#50e38b;--yellow:#ffd166;--red:#ff687f;--gray:#718096}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top,#112137 0,#060a10 48%);color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif}
header{position:sticky;top:0;z-index:5;background:rgba(6,10,16,.94);border-bottom:1px solid var(--line);padding:12px 18px;backdrop-filter:blur(8px)}
.top{max-width:1350px;margin:auto;display:flex;align-items:center;gap:14px}.brand{font-weight:900;color:var(--cyan);letter-spacing:.08em}.bar{height:12px;background:#1b2737;border-radius:99px;overflow:hidden;flex:1}.fill{height:100%;width:0;background:linear-gradient(90deg,var(--cyan),var(--green))}.count{font-weight:800;white-space:nowrap}
main{max-width:1350px;margin:auto;padding:18px;display:grid;grid-template-columns:minmax(0,1fr) 390px;gap:18px}.card{background:linear-gradient(180deg,rgba(17,26,38,.98),rgba(10,16,24,.98));border:1px solid var(--line);border-radius:18px;box-shadow:0 14px 44px rgba(0,0,0,.3)}.content{padding:22px}.side{padding:18px;position:sticky;top:76px;height:max-content}
.label{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.12em;font-weight:900}.question{font-size:1.22rem;line-height:1.4;margin:8px 0 16px}.reference{background:rgba(80,227,139,.08);border:1px solid rgba(80,227,139,.35);border-radius:14px;padding:15px;margin-bottom:16px}.reference b{color:var(--green)}.response{white-space:pre-wrap;line-height:1.58;background:var(--panel2);border:1px solid #223147;border-radius:14px;padding:18px;max-height:62vh;overflow:auto}
.block{margin-bottom:20px}.block h2{font-size:1rem;margin:0 0 7px}.help{margin:0 0 10px;color:var(--muted);font-size:.82rem;line-height:1.4}.choices{display:grid;gap:8px}.choice{border:1px solid #34465f;background:#121d2b;color:var(--text);border-radius:12px;padding:12px;text-align:left;cursor:pointer;font-weight:800}.choice small{display:block;color:var(--muted);font-weight:500;margin-top:4px}.choice:hover{border-color:var(--cyan)}.choice.selected.good{background:rgba(80,227,139,.18);border-color:var(--green)}.choice.selected.mid{background:rgba(255,209,102,.16);border-color:var(--yellow)}.choice.selected.bad{background:rgba(255,104,127,.18);border-color:var(--red)}.choice.selected.unknown{background:rgba(113,128,150,.22);border-color:var(--gray)}
textarea{width:100%;min-height:76px;background:var(--panel2);color:var(--text);border:1px solid #34465f;border-radius:12px;padding:11px;resize:vertical}.actions{display:grid;grid-template-columns:1fr 1.5fr;gap:8px}.btn{border:0;border-radius:12px;padding:12px;font-weight:900;cursor:pointer}.secondary{background:#28364b;color:var(--text)}.primary{background:linear-gradient(90deg,var(--cyan),var(--green));color:#001016}.btn:disabled{opacity:.35;cursor:not-allowed}.status{min-height:24px;text-align:center;color:var(--muted);font-size:.82rem;padding-top:7px}.tools{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}.mini{border:1px solid var(--line);background:#101925;color:var(--muted);border-radius:9px;padding:7px 9px;cursor:pointer}.done{display:none;max-width:700px;margin:70px auto;padding:40px;text-align:center}.done h1{color:var(--green)}
@media(max-width:900px){main{grid-template-columns:1fr}.side{position:static}.response{max-height:none}}@media(max-width:520px){main{padding:10px}.content,.side{padding:14px}.question{font-size:1.05rem}.response{font-size:.92rem;padding:13px}}
</style>
</head>
<body>
<header><div class="top"><div class="brand">MAGI REVIEW</div><div class="bar"><div id="fill" class="fill"></div></div><div id="count" class="count">0 / 0</div></div></header>
<main id="workspace">
<section class="card content">
<div class="label">Domanda</div><div id="question" class="question">Caricamento…</div>
<div class="reference"><div class="label">Cosa dovrebbe dire una buona risposta</div><div id="reference"></div></div>
<div class="label">Risposta anonima da valutare</div><div id="response" class="response"></div>
</section>
<aside class="card side">
<div class="tools"><button id="first" class="mini">Prima non valutata</button><button id="download" class="mini">Scarica valutazioni</button></div>
<div class="block"><h2>1. Nel complesso questa risposta è…</h2><p class="help">Non serve giudicare ogni frase: scegli l’impressione complessiva confrontandola con il riquadro verde.</p><div class="choices" data-field="verdict">
<button class="choice good" data-value="correct">Corretta<small>La userei così com’è o con ritocchi minimi.</small></button>
<button class="choice mid" data-value="minor">Quasi corretta<small>Buona idea di fondo, ma ha un difetto o un’omissione.</small></button>
<button class="choice bad" data-value="wrong">Sbagliata<small>Porta a una conclusione metodologicamente errata.</small></button>
<button class="choice unknown" data-value="unsure">Non so valutarla<small>La risposta è troppo tecnica o ambigua.</small></button>
</div></div>
<div class="block"><h2>2. C’è un errore grave?</h2><p class="help">“Sì” solo se seguire la risposta potrebbe rendere invalido l’esperimento o la decisione.</p><div class="choices" data-field="serious_error">
<button class="choice good" data-value="no">No</button><button class="choice bad" data-value="yes">Sì</button><button class="choice unknown" data-value="unsure">Non so</button>
</div></div>
<div class="block"><h2>3. Manca qualcosa di importante?</h2><p class="help">Confronta la risposta con il riferimento verde.</p><div class="choices" data-field="missing_important">
<button class="choice good" data-value="no">No</button><button class="choice mid" data-value="yes">Sì</button><button class="choice unknown" data-value="unsure">Non so</button>
</div></div>
<div class="block"><h2>Nota facoltativa</h2><textarea id="notes" placeholder="Es.: corretta, ma troppo categorica su LOSO"></textarea></div>
<div class="actions"><button id="prev" class="btn secondary">← Indietro</button><button id="save" class="btn primary">Salva e prossima →</button></div><div id="status" class="status"></div>
</aside>
</main>
<section id="done" class="card done"><h1>Finito ✓</h1><p>Le valutazioni sono già salvate.</p><button id="downloadDone" class="btn primary">Scarica il file</button></section>
<script>
let state=null,item=null,index=0;const values={};const fields=['verdict','serious_error','missing_important'];
async function req(url,opt={}){const r=await fetch(url,opt);if(!r.ok){let t='Errore';try{t=(await r.json()).detail}catch{}throw new Error(t)}return r.json()}
function select(field,value){values[field]=value;document.querySelectorAll(`[data-field="${field}"] .choice`).forEach(b=>b.classList.toggle('selected',b.dataset.value===value));document.getElementById('save').disabled=!fields.every(f=>values[f])}
function txt(id,v){document.getElementById(id).textContent=v||''}
async function load(i){item=await req(`/api/item/${i}`);index=i;txt('question',item.question);txt('reference',item.reference_answer);txt('response',item.response);fields.forEach(f=>select(f,item[f]||''));document.getElementById('notes').value=item.reviewer_notes||'';document.getElementById('count').textContent=`${i+1} / ${state.total}`;document.getElementById('fill').style.width=`${state.completed/state.total*100}%`;document.getElementById('prev').disabled=i===0;document.getElementById('response').scrollTop=0;txt('status',item.completed?'Già salvata: puoi modificarla.':'')}
async function refresh(){state=await req('/api/state');document.getElementById('fill').style.width=`${state.completed/state.total*100}%`}
async function save(){if(!fields.every(f=>values[f]))return;document.getElementById('save').disabled=true;txt('status','Salvataggio…');await req(`/api/item/${index}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...values,reviewer_notes:document.getElementById('notes').value})});await refresh();if(state.completed===state.total){document.getElementById('workspace').style.display='none';document.getElementById('done').style.display='block';document.getElementById('count').textContent=`${state.total} / ${state.total}`;document.getElementById('fill').style.width='100%';return}let next=index+1;if(next>=state.total)next=state.first_incomplete;await load(next)}
document.querySelectorAll('.choice').forEach(b=>b.onclick=()=>select(b.parentElement.dataset.field,b.dataset.value));document.getElementById('save').onclick=()=>save().catch(e=>txt('status',e.message));document.getElementById('prev').onclick=()=>load(Math.max(0,index-1));document.getElementById('first').onclick=async()=>{await refresh();load(state.first_incomplete)};document.getElementById('download').onclick=()=>location.href='/api/download';document.getElementById('downloadDone').onclick=()=>location.href='/api/download';
(async()=>{await refresh();if(state.completed===state.total){document.getElementById('workspace').style.display='none';document.getElementById('done').style.display='block'}else await load(state.first_incomplete)})().catch(e=>txt('status',e.message));
</script>
</body></html>'''


@dataclass
class ReviewStore:
    source_path: Path
    cases_path: Path

    def __post_init__(self) -> None:
        self.output_path = self.source_path.with_name("human_review_simple.csv")
        self.cases = self._load_cases()
        self.rows = self._load_or_create_rows()

    def _load_cases(self) -> dict[str, dict[str, Any]]:
        cases: dict[str, dict[str, Any]] = {}
        with self.cases_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    case = json.loads(line)
                    cases[str(case["id"])] = case
        return cases

    def _load_source(self) -> list[dict[str, str]]:
        with self.source_path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def _load_or_create_rows(self) -> list[dict[str, str]]:
        if self.output_path.exists():
            with self.output_path.open("r", encoding="utf-8-sig", newline="") as handle:
                return list(csv.DictReader(handle))
        rows: list[dict[str, str]] = []
        for source in self._load_source():
            case = self.cases.get(source.get("case_id", ""), {})
            rows.append({
                "review_id": source.get("review_id", ""),
                "case_id": source.get("case_id", ""),
                "question": source.get("question", ""),
                "reference_answer": str(case.get("reference_answer", "Riferimento non disponibile.")),
                "response": source.get("response", ""),
                "verdict": "",
                "serious_error": "",
                "missing_important": "",
                "reviewer_notes": "",
            })
        self.rows = rows
        self._save()
        return rows

    @staticmethod
    def complete(row: dict[str, str]) -> bool:
        return all(row.get(k, "").strip() for k in ("verdict", "serious_error", "missing_important"))

    def state(self) -> dict[str, int]:
        incomplete = [i for i, row in enumerate(self.rows) if not self.complete(row)]
        return {
            "total": len(self.rows),
            "completed": len(self.rows) - len(incomplete),
            "first_incomplete": incomplete[0] if incomplete else 0,
        }

    def item(self, index: int) -> dict[str, Any]:
        if index < 0 or index >= len(self.rows):
            raise IndexError(index)
        row = dict(self.rows[index])
        row["completed"] = self.complete(row)
        return row

    def update(self, index: int, payload: dict[str, str]) -> None:
        allowed = {
            "verdict": {"correct", "minor", "wrong", "unsure"},
            "serious_error": {"no", "yes", "unsure"},
            "missing_important": {"no", "yes", "unsure"},
        }
        if index < 0 or index >= len(self.rows):
            raise IndexError(index)
        for key, options in allowed.items():
            value = payload.get(key, "")
            if value not in options:
                raise ValueError(f"Valore non valido per {key}")
            self.rows[index][key] = value
        self.rows[index]["reviewer_notes"] = payload.get("reviewer_notes", "").strip()
        self._save()

    def _save(self) -> None:
        fields = ["review_id", "case_id", "question", "reference_answer", "response", "verdict", "serious_error", "missing_important", "reviewer_notes"]
        with self.output_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self.rows)


class ReviewPayload(BaseModel):
    verdict: str
    serious_error: str
    missing_important: str
    reviewer_notes: str = ""


def build_app(store: ReviewStore) -> FastAPI:
    app = FastAPI(title="MAGI simple review")

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return HTML

    @app.get("/api/state")
    def state() -> dict[str, int]:
        return store.state()

    @app.get("/api/item/{index}")
    def item(index: int) -> dict[str, Any]:
        try:
            return store.item(index)
        except IndexError as exc:
            raise HTTPException(404, "Risposta non trovata") from exc

    @app.post("/api/item/{index}")
    def update(index: int, payload: ReviewPayload) -> dict[str, Any]:
        try:
            store.update(index, payload.model_dump())
            return store.state()
        except IndexError as exc:
            raise HTTPException(404, "Risposta non trovata") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/download")
    def download() -> FileResponse:
        return FileResponse(store.output_path, filename=store.output_path.name, media_type="text/csv")

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Revisione umana semplice e cieca del benchmark MAGI")
    parser.add_argument("csv_path", type=Path, help="human_review_blinded.csv")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.csv_path.resolve()
    if not source.exists():
        raise SystemExit(f"File non trovato: {source}")
    cases_path = Path(__file__).with_name("cases_v1.jsonl")
    store = ReviewStore(source, cases_path)
    app = build_app(store)
    url = f"http://{args.host}:{args.port}"
    print(f"Revisione semplice: {url}")
    print(f"Risultati salvati in: {store.output_path}")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
