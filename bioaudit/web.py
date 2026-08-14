from __future__ import annotations

import argparse
import json
import threading
from typing import Any
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from magi.config import Settings
from magi.providers import PROVIDER_NAMES, build_providers

from .orchestrator import BioAuditOrchestrator

HTML = r'''<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BioAudit</title><style>
:root{color-scheme:dark;--bg:#081016;--card:#101d25;--line:#28404c;--text:#ecf6f7;--muted:#9fb6bd;--cyan:#5ce1e6;--red:#ff6b6b;--amber:#ffcf5c;--green:#6ee7a8}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top,#12303a,var(--bg) 42%);font:15px system-ui;color:var(--text)}
main{max-width:1120px;margin:auto;padding:24px}.brand{display:flex;align-items:end;gap:14px;margin-bottom:18px}.brand h1{font-size:34px;margin:0;letter-spacing:.08em}.brand span{color:var(--cyan)}
.grid{display:grid;grid-template-columns:1fr .95fr;gap:18px}.card{background:rgba(16,29,37,.95);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 18px 50px #0007}
textarea{width:100%;min-height:430px;resize:vertical;background:#071117;border:1px solid var(--line);border-radius:12px;padding:14px;color:var(--text);line-height:1.5}
label{display:block;margin:12px 0 6px;color:var(--muted)}select,button{border:1px solid var(--line);border-radius:10px;background:#122630;color:var(--text);padding:10px 12px}
.providers{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 16px}.providers label{margin:0;padding:8px 10px;border:1px solid var(--line);border-radius:10px;color:var(--text)}
button.primary{width:100%;background:linear-gradient(135deg,#087c89,#1251a0);font-weight:800;font-size:16px;cursor:pointer}.status{min-height:24px;color:var(--muted);margin-top:10px}
.badge{display:inline-block;padding:6px 10px;border-radius:999px;font-weight:800}.PASS{background:#153d2b;color:var(--green)}.REVISE{background:#443817;color:var(--amber)}.BLOCK{background:#491f24;color:var(--red)}
.issue{border-left:3px solid var(--red);padding:10px 12px;margin:12px 0;background:#0b161c;border-radius:6px}.moderate{border-color:var(--amber)}h2,h3{margin-top:12px}.muted{color:var(--muted)}ol,ul{padding-left:22px}.empty{color:var(--muted);font-style:italic}
@media(max-width:800px){main{padding:10px}.grid{grid-template-columns:1fr}.brand h1{font-size:26px}textarea{min-height:300px}}
</style></head><body><main>
<div class="brand"><h1>BIO<span>AUDIT</span></h1><div class="muted">MAGI methodological review</div></div>
<div class="grid"><section class="card"><h2>Metodo o pipeline da revisionare</h2>
<textarea id="text" placeholder="Incolla Methods, protocollo, pipeline ML o descrizione dell'esperimento..."></textarea>
<label>Profilo</label><select id="profile"><option value="eeg_ml">EEG + Machine Learning</option><option value="biomedical">Ricerca biomedica</option><option value="general_ml">Machine Learning generale</option></select>
<label>Provider reali</label><div class="providers" id="providers"></div>
<label><input type="checkbox" id="auditor" checked> Auditor esterno Groq</label>
<button class="primary" id="run">AVVIA AUDIT</button><div class="status" id="status"></div></section>
<section class="card" id="result"><h2>Report</h2><p class="empty">Il report comparirà qui.</p></section></div>
</main><script>
const $=id=>document.getElementById(id);let timer=null;
async function api(url,opt={}){const r=await fetch(url,opt);let p;try{p=await r.json()}catch{p={}}if(!r.ok)throw new Error(p.detail||'Errore');return p}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function issue(item,moderate=false){return `<div class="issue ${moderate?'moderate':''}"><h3>${esc(item.title)}</h3><p><b>Evidenza:</b> ${esc(item.evidence_from_input)}</p><p><b>Perché conta:</b> ${esc(item.why_it_matters)}</p><p><b>Correzione:</b> ${esc(item.recommended_fix)}</p><p><b>Verifica:</b> ${esc(item.verification)}</p></div>`}
function list(title,items){return `<h3>${title}</h3>${items?.length?`<ol>${items.map(x=>`<li>${esc(x)}</li>`).join('')}</ol>`:'<p class="empty">Nessuno.</p>'}`}
function render(r,path){$('result').innerHTML=`<h2><span class="badge ${esc(r.verdict)}">${esc(r.verdict)}</span></h2><p>${esc(r.summary)}</p><p class="muted">Confidenza interna: ${esc(r.internal_confidence)}% · ${esc(path)}</p><h2>Problemi critici</h2>${r.critical_issues?.length?r.critical_issues.map(x=>issue(x)).join(''):'<p class="empty">Nessuno identificato.</p>'}<h2>Problemi moderati</h2>${r.moderate_issues?.length?r.moderate_issues.map(x=>issue(x,true)).join(''):'<p class="empty">Nessuno identificato.</p>'}${list('Punti solidi',r.strengths)}${list('Informazioni mancanti',r.missing_information)}${list('Prossime azioni',r.next_actions)}`}
async function config(){const c=await api('/api/config');$('providers').innerHTML=Object.entries(c.available).map(([p,on])=>`<label><input type="checkbox" value="${p}" ${on?'checked':'disabled'}> ${p}${on?'':' (chiave assente)'}</label>`).join('')}
async function run(){const text=$('text').value.trim();if(text.length<20){$('status').textContent='Inserisci almeno qualche riga significativa.';return}$('run').disabled=true;$('status').textContent='I modelli stanno revisionando...';const real=[...document.querySelectorAll('#providers input:checked')].map(x=>x.value);try{const j=await api('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,profile:$('profile').value,real_providers:real,auditor:$('auditor').checked})});timer=setInterval(async()=>{try{const s=await api('/api/jobs/'+j.job_id);$('status').textContent=s.message;if(s.status==='completed'){clearInterval(timer);render(s.result.report,s.output_path);$('run').disabled=false}else if(s.status==='error'){clearInterval(timer);throw new Error(s.error)}}catch(e){clearInterval(timer);$('status').textContent=e.message;$('run').disabled=false}},1000)}catch(e){$('status').textContent=e.message;$('run').disabled=false}}
$('run').onclick=run;config().catch(e=>$('status').textContent=e.message)
</script></body></html>'''


class AuditRequest(BaseModel):
    text: str = Field(min_length=20, max_length=50000)
    profile: str = "eeg_ml"
    real_providers: list[str] = Field(default_factory=list)
    auditor: bool = True


class Jobs:
    def __init__(self) -> None:
        self.data: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()

    def create(self) -> str:
        job_id = uuid4().hex[:12]
        with self.lock:
            self.data[job_id] = {"status": "queued", "message": "In coda", "result": None, "error": None}
        return job_id

    def update(self, job_id: str, **fields: Any) -> None:
        with self.lock:
            self.data[job_id].update(fields)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self.lock:
            item = self.data.get(job_id)
            return json.loads(json.dumps(item)) if item else None


jobs = Jobs()
app = FastAPI(title="BioAudit", version="0.7.0")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return HTML


@app.get("/api/config")
def config() -> dict[str, Any]:
    settings = Settings.from_env()
    return {"available": {
        "openai": bool(settings.openai_api_key),
        "anthropic": bool(settings.anthropic_api_key),
        "gemini": bool(settings.gemini_api_key),
        "groq": bool(settings.groq_api_key),
    }}


def worker(job_id: str, request: AuditRequest) -> None:
    try:
        settings = Settings.from_env()
        real = list(dict.fromkeys(p.lower() for p in request.real_providers))
        unknown = set(real) - set(PROVIDER_NAMES)
        if unknown:
            raise ValueError(f"Provider non validi: {sorted(unknown)}")
        required = {"openai", "anthropic", "gemini", settings.judge_provider}
        if request.auditor:
            required.add(settings.auditor_provider)
        missing = required - set(real)
        if missing:
            raise ValueError(f"Per un audit completamente reale mancano: {sorted(missing)}")
        jobs.update(job_id, status="running", message="Analisi dei tre agenti")
        providers = build_providers(settings, mock=False, real_providers=real)
        result, directory = BioAuditOrchestrator(settings, providers).run(
            request.text,
            profile=request.profile,
            auditor=request.auditor,
            source_name="web_input",
        )
        jobs.update(job_id, status="completed", message="Audit completato", result=result, output_path=str(directory))
    except Exception as exc:
        jobs.update(job_id, status="error", message="Errore", error=f"{type(exc).__name__}: {exc}")


@app.post("/api/jobs")
def create_job(request: AuditRequest) -> dict[str, str]:
    job_id = jobs.create()
    threading.Thread(target=worker, args=(job_id, request), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    item = jobs.get(job_id)
    if item is None:
        raise HTTPException(404, "Job non trovato")
    return item


def main() -> None:
    parser = argparse.ArgumentParser(description="BioAudit web console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    uvicorn.run("bioaudit.web:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
