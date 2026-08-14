from __future__ import annotations

import argparse
import json
import threading
import time
from typing import Any
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from magi.config import Settings
from magi.i18n import frontend_payload, normalize_language, translate
from magi.providers import PROVIDER_NAMES, build_providers

from .demo import build_demo_report, list_demo_cases
from .orchestrator import BioAuditOrchestrator

DEMO_MODE = False

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BioAudit</title>
<style>
:root{
  color-scheme:dark;
  --bg:#081016;
  --card:#101d25;
  --line:#28404c;
  --text:#ecf6f7;
  --muted:#9fb6bd;
  --cyan:#5ce1e6;
  --red:#ff6b6b;
  --amber:#ffcf5c;
  --green:#6ee7a8
}
*{box-sizing:border-box}
body{
  margin:0;
  background:radial-gradient(circle at top,#12303a,var(--bg) 42%);
  font:15px system-ui;
  color:var(--text)
}
main{max-width:1120px;margin:auto;padding:24px}
.brand-row{
  display:flex;
  align-items:end;
  justify-content:space-between;
  gap:16px;
  margin-bottom:18px
}
.brand{display:flex;align-items:end;gap:14px}
.brand h1{font-size:34px;margin:0;letter-spacing:.08em}
.brand span{color:var(--cyan)}
.language-control select{
  border:1px solid var(--line);
  border-radius:8px;
  background:#071117;
  color:var(--text);
  padding:8px 10px;
  font-weight:800;
  cursor:pointer
}
.grid{display:grid;grid-template-columns:1fr .95fr;gap:18px}
.card{
  background:rgba(16,29,37,.95);
  border:1px solid var(--line);
  border-radius:16px;
  padding:18px;
  box-shadow:0 18px 50px #0007
}
textarea{
  width:100%;
  min-height:430px;
  resize:vertical;
  background:#071117;
  border:1px solid var(--line);
  border-radius:12px;
  padding:14px;
  color:var(--text);
  line-height:1.5
}
label{display:block;margin:12px 0 6px;color:var(--muted)}
select,button{
  border:1px solid var(--line);
  border-radius:10px;
  background:#122630;
  color:var(--text);
  padding:10px 12px
}
.providers{
  display:flex;
  flex-wrap:wrap;
  gap:8px;
  margin:8px 0 16px
}
.providers label{
  margin:0;
  padding:8px 10px;
  border:1px solid var(--line);
  border-radius:10px;
  color:var(--text)
}
button.primary{
  width:100%;
  background:linear-gradient(135deg,#087c89,#1251a0);
  font-weight:800;
  font-size:16px;
  cursor:pointer
}
button:disabled{opacity:.55;cursor:wait}
.status{min-height:24px;color:var(--muted);margin-top:10px}
.badge{
  display:inline-block;
  padding:6px 10px;
  border-radius:999px;
  font-weight:800
}
.PASS{background:#153d2b;color:var(--green)}
.REVISE{background:#443817;color:var(--amber)}
.BLOCK{background:#491f24;color:var(--red)}
.issue{
  border-left:3px solid var(--red);
  padding:10px 12px;
  margin:12px 0;
  background:#0b161c;
  border-radius:6px
}
.moderate{border-color:var(--amber)}
h2,h3{margin-top:12px}
.muted{color:var(--muted)}
ol,ul{padding-left:22px}
.empty{color:var(--muted);font-style:italic}
.demo-box{
  display:none;
  border:1px solid var(--cyan);
  background:#092029;
  padding:12px 14px;
  margin-bottom:16px;
  border-radius:12px
}
.demo-box.active{display:block}
.demo-box strong{color:var(--cyan);letter-spacing:.08em}
.demo-box p{margin:6px 0 12px;color:var(--muted)}
.demo-box select{
  width:100%;
  background:#071117;
  border:1px solid var(--line);
  color:var(--text);
  padding:10px;
  border-radius:8px
}
.demo-note{
  border-left:3px solid var(--cyan);
  background:#091c23;
  padding:10px 12px;
  color:var(--muted);
  margin-bottom:14px
}
.sr-only{
  position:absolute;
  width:1px;
  height:1px;
  padding:0;
  margin:-1px;
  overflow:hidden;
  clip:rect(0,0,0,0);
  white-space:nowrap;
  border:0
}
@media(max-width:800px){
  main{padding:10px}
  .grid{grid-template-columns:1fr}
  .brand h1{font-size:26px}
  textarea{min-height:300px}
}
</style>
</head>
<body>
<main>

<div class="brand-row">
  <div class="brand">
    <h1>BIO<span>AUDIT</span></h1>
    <div class="muted" data-i18n="bioaudit.subtitle">
      MAGI methodological review
    </div>
  </div>

  <label class="language-control">
    <span class="sr-only" data-i18n="common.language">Language</span>
    <select
      id="languageSelect"
      aria-label="Language"
      data-i18n-aria-label="common.language"
    >
      <option value="en">EN</option>
      <option value="it">IT</option>
    </select>
  </label>
</div>

<div id="demoBox" class="demo-box">
  <strong data-i18n="bioaudit.demo.title">PRERECORDED DEMO</strong>
  <p data-i18n="bioaudit.demo.subtitle">
    No model API calls are made and no submitted data leave this computer.
  </p>
  <select id="demoCase"></select>
</div>

<div class="grid">

<section class="card">
  <h2 data-i18n="bioaudit.input.title">METHOD OR PIPELINE TO REVIEW</h2>

  <textarea
    id="text"
    placeholder="Paste Methods, protocol, ML pipeline, or experimental description..."
    data-i18n-placeholder="bioaudit.input.placeholder"
  ></textarea>

  <label data-i18n="bioaudit.profile.label">Profile</label>
  <select id="profile">
    <option value="eeg_ml" data-i18n="bioaudit.profile.eeg_ml">
      EEG + Machine Learning
    </option>
    <option value="biomedical" data-i18n="bioaudit.profile.biomedical">
      Biomedical research
    </option>
    <option value="general_ml" data-i18n="bioaudit.profile.general_ml">
      General Machine Learning
    </option>
  </select>

  <label data-i18n="bioaudit.providers.label">Live providers</label>
  <div class="providers" id="providers"></div>

  <label>
    <input type="checkbox" id="auditor" checked>
    <span data-i18n="bioaudit.auditor.label">External Groq auditor</span>
  </label>

  <button
    class="primary"
    id="run"
    data-i18n="bioaudit.run.start"
  >START AUDIT</button>

  <div class="status" id="status"></div>
</section>

<section class="card" id="result">
  <h2 data-i18n="bioaudit.report.title">REPORT</h2>
  <p class="empty" data-i18n="bioaudit.report.empty">
    The report will appear here.
  </p>
</section>

</div>
</main>

<script>
const $ = id => document.getElementById(id);

let timer = null;
let i18n = null;
let language = "en";
let bioauditConfig = null;
let lastReport = null;
let lastOutputPath = null;
let lastReportDemo = false;

const PROVIDER_LABELS = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  gemini: "Gemini",
  groq: "Groq"
};

function esc(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    char => ({
      "&":"&amp;",
      "<":"&lt;",
      ">":"&gt;",
      '"':"&quot;",
      "'":"&#39;"
    }[char])
  );
}

function formatTemplate(template, values = {}) {
  return String(template).replace(
    /\{(\w+)\}/g,
    (_, key) => Object.prototype.hasOwnProperty.call(values, key)
      ? values[key]
      : `{${key}}`
  );
}

function t(key, values = {}) {
  const catalogs = i18n?.catalogs || {};
  const catalog =
    catalogs[language] ||
    catalogs[i18n?.default_language] ||
    {};

  return formatTemplate(catalog[key] ?? key, values);
}

async function api(url, options = {}) {
  const response = await fetch(url, options);

  let payload;
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  if (!response.ok) {
    throw new Error(payload.detail || t("bioaudit.error.generic"));
  }

  return payload;
}

function applyLanguage() {
  document.documentElement.lang = language;

  document.querySelectorAll("[data-i18n]").forEach(node => {
    node.textContent = t(node.dataset.i18n);
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach(node => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });

  document.querySelectorAll("[data-i18n-aria-label]").forEach(node => {
    node.setAttribute(
      "aria-label",
      t(node.dataset.i18nAriaLabel)
    );
  });

  $("languageSelect").value = language;
}

function issue(item, moderate = false) {
  return `
    <div class="issue ${moderate ? "moderate" : ""}">
      <h3>${esc(item.title)}</h3>
      <p><b>${esc(t("bioaudit.finding.evidence"))}:</b>
        ${esc(item.evidence_from_input)}</p>
      <p><b>${esc(t("bioaudit.finding.why"))}:</b>
        ${esc(item.why_it_matters)}</p>
      <p><b>${esc(t("bioaudit.finding.fix"))}:</b>
        ${esc(item.recommended_fix)}</p>
      <p><b>${esc(t("bioaudit.finding.verify"))}:</b>
        ${esc(item.verification)}</p>
    </div>`;
}

function list(titleKey, items) {
  return `
    <h3>${esc(t(titleKey))}</h3>
    ${
      items?.length
        ? `<ol>${items.map(item => `<li>${esc(item)}</li>`).join("")}</ol>`
        : `<p class="empty">${esc(t("bioaudit.list.none"))}</p>`
    }`;
}

function render(report, path, demo = false) {
  lastReport = report;
  lastOutputPath = path;
  lastReportDemo = demo;

  $("result").innerHTML = `
    ${
      demo
        ? `<div class="demo-note">${esc(t("bioaudit.demo.notice"))}</div>`
        : ""
    }

    <h2>
      <span class="badge ${esc(report.verdict)}">
        ${esc(report.verdict)}
      </span>
    </h2>

    <p>${esc(report.summary)}</p>

    <p class="muted">
      ${esc(t("bioaudit.report.internal_confidence"))}:
      ${esc(report.internal_confidence)}%
      | ${esc(demo ? t("bioaudit.demo.source") : path)}
    </p>

    <h2>${esc(t("bioaudit.findings.critical"))}</h2>
    ${
      report.critical_issues?.length
        ? report.critical_issues.map(item => issue(item)).join("")
        : `<p class="empty">${esc(t("bioaudit.findings.none"))}</p>`
    }

    <h2>${esc(t("bioaudit.findings.moderate"))}</h2>
    ${
      report.moderate_issues?.length
        ? report.moderate_issues
            .map(item => issue(item, true))
            .join("")
        : `<p class="empty">${esc(t("bioaudit.findings.none"))}</p>`
    }

    ${list("bioaudit.strengths", report.strengths)}
    ${list("bioaudit.missing_information", report.missing_information)}
    ${list("bioaudit.next_actions", report.next_actions)}
  `;
}

function applyDynamicText() {
  if (!bioauditConfig) return;

  if (bioauditConfig.demo_mode) {
    $("demoCase").querySelectorAll("option").forEach(option => {
      option.textContent = t(`demo.case.${option.value}`);
    });

    $("run").textContent = t("bioaudit.demo.run");

    if (!$("run").disabled) {
      $("status").textContent = t("bioaudit.demo.ready");
    }
  } else {
    $("run").textContent = t("bioaudit.run.start");
  }

  if (lastReport) {
    render(lastReport, lastOutputPath, lastReportDemo);
  }
}

async function setLanguage(nextLanguage) {
  if (!i18n?.supported_languages?.includes(nextLanguage)) {
    return;
  }

  language = nextLanguage;
  localStorage.setItem(i18n.storage_key, language);

  applyLanguage();
  applyDynamicText();

  if (bioauditConfig) {
    renderProviders();
  }
}

async function loadI18n() {
  i18n = await api("/api/i18n");

  const stored = localStorage.getItem(i18n.storage_key);

  language = i18n.supported_languages.includes(stored)
    ? stored
    : i18n.default_language;

  $("languageSelect").addEventListener(
    "change",
    event => setLanguage(event.target.value)
  );

  applyLanguage();
}

function renderProviders() {
  const config = bioauditConfig;
  if (!config) return;

  if (config.demo_mode) {
    $("providers").innerHTML = Object.keys(config.available)
      .map(provider => `
        <label>
          <input
            type="checkbox"
            value="${esc(provider)}"
            checked
            disabled
          >
          ${esc(PROVIDER_LABELS[provider] || provider)} |
          ${esc(t("bioaudit.providers.static"))}
        </label>
      `)
      .join("");

    return;
  }

  $("providers").innerHTML = Object.entries(config.available)
    .map(([provider, available]) => `
      <label>
        <input
          type="checkbox"
          value="${esc(provider)}"
          ${available ? "checked" : "disabled"}
        >
        ${esc(PROVIDER_LABELS[provider] || provider)}
        ${
          available
            ? ""
            : ` (${esc(t("bioaudit.providers.missing_key"))})`
        }
      </label>
    `)
    .join("");
}

async function loadConfig() {
  const config = await api("/api/config");
  bioauditConfig = config;

  renderProviders();

  if (config.demo_mode) {
    $("demoBox").classList.add("active");
    $("text").readOnly = true;
    $("profile").disabled = true;

    const select = $("demoCase");

    select.innerHTML = config.demo_cases
      .map(item => `
        <option value="${esc(item.id)}">
          ${esc(t(`demo.case.${item.id}`))}
        </option>
      `)
      .join("");

    function loadCase() {
      const item = config.demo_cases.find(
        candidate => candidate.id === select.value
      );

      if (!item) return;

      $("text").value = item.text;
      $("profile").value = item.profile;
      $("status").textContent = t("bioaudit.demo.ready");
      lastReport = null;
    }

    select.onchange = loadCase;
    loadCase();
  }

  applyDynamicText();
}

async function run() {
  const text = $("text").value.trim();

  if (text.length < 20) {
    $("status").textContent = t("bioaudit.error.input_short");
    return;
  }

  $("run").disabled = true;

  $("status").textContent = bioauditConfig?.demo_mode
    ? t("bioaudit.status.replaying")
    : t("bioaudit.status.reviewing");

  const realProviders = [
    ...document.querySelectorAll("#providers input:checked")
  ].map(input => input.value);

  try {
    const job = await api("/api/jobs", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        text,
        profile: $("profile").value,
        real_providers: realProviders,
        auditor: $("auditor").checked,
        demo_case: bioauditConfig?.demo_mode
          ? $("demoCase").value
          : null,
        language
      })
    });

    timer = setInterval(async () => {
      try {
        const state = await api(
          `/api/jobs/${job.job_id}?language=${encodeURIComponent(language)}`
        );

        if (state.status === "running") {
          $("status").textContent = bioauditConfig?.demo_mode
            ? t("bioaudit.status.replaying")
            : t("bioaudit.status.reviewing");
        }

        if (state.status === "completed") {
          clearInterval(timer);

          render(
            state.result.report,
            state.output_path,
            Boolean(state.result.demo_mode)
          );

          $("status").textContent = bioauditConfig?.demo_mode
            ? t("bioaudit.status.demo_complete")
            : t("bioaudit.status.complete");

          $("run").disabled = false;
        }

        if (state.status === "error") {
          clearInterval(timer);
          throw new Error(
            state.error || t("bioaudit.status.error")
          );
        }
      } catch (error) {
        clearInterval(timer);
        $("status").textContent = error.message;
        $("run").disabled = false;
      }
    }, 1000);

  } catch (error) {
    $("status").textContent = error.message;
    $("run").disabled = false;
  }
}

$("run").onclick = run;

(async function boot() {
  try {
    await loadI18n();
    await loadConfig();
  } catch (error) {
    $("status").textContent = error.message;
  }
})();
</script>
</body>
</html>"""




class AuditRequest(BaseModel):
    text: str = Field(min_length=20, max_length=50000)
    profile: str = "eeg_ml"
    real_providers: list[str] = Field(default_factory=list)
    auditor: bool = True
    demo_case: str | None = None
    language: str = "en"


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


@app.get("/api/i18n")
def i18n_config() -> dict[str, object]:
    return frontend_payload()


@app.get("/api/config")
def config() -> dict[str, Any]:
    if DEMO_MODE:
        return {
            "demo_mode": True,
            "demo_cases": list_demo_cases(),
            "available": {
                "openai": True,
                "anthropic": True,
                "gemini": True,
                "groq": True,
            },
        }

    settings = Settings.from_env()
    return {
        "demo_mode": False,
        "demo_cases": [],
        "available": {
        "openai": bool(settings.openai_api_key),
        "anthropic": bool(settings.anthropic_api_key),
        "gemini": bool(settings.gemini_api_key),
        "groq": bool(settings.groq_api_key),
    }}


def worker(job_id: str, request: AuditRequest) -> None:
    language = normalize_language(request.language)

    try:
        if DEMO_MODE:
            case_id = request.demo_case or "eeg_subject_leakage"
            jobs.update(
                job_id,
                status="running",
                message=translate("bioaudit.status.replaying", language),
            )
            time.sleep(0.8)

            report = build_demo_report(case_id)

            jobs.update(
                job_id,
                status="completed",
                message=translate("bioaudit.status.demo_complete", language),
                result={
                    "report": report,
                    "demo_mode": True,
                    "demo_case": case_id,
                    "demo_notice": (
                        "Prerecorded demonstration. "
                        "No external model API calls were made."
                    ),
                },
                output_path="prerecorded-demo",
            )
            return

        settings = Settings.from_env()
        real = list(dict.fromkeys(p.lower() for p in request.real_providers))
        unknown = set(real) - set(PROVIDER_NAMES)
        if unknown:
            raise ValueError(
                translate(
                    "bioaudit.error.invalid_providers",
                    language,
                    providers=sorted(unknown),
                )
            )
        required = {"openai", "anthropic", "gemini", settings.judge_provider}
        if request.auditor:
            required.add(settings.auditor_provider)
        missing = required - set(real)
        if missing:
            raise ValueError(
                translate(
                    "bioaudit.error.missing_providers",
                    language,
                    providers=sorted(missing),
                )
            )
        jobs.update(
            job_id,
            status="running",
            message=translate("bioaudit.status.reviewing", language),
        )
        providers = build_providers(settings, mock=False, real_providers=real)
        result, directory = BioAuditOrchestrator(settings, providers).run(
            request.text,
            profile=request.profile,
            auditor=request.auditor,
            source_name="web_input",
        )
        jobs.update(
            job_id,
            status="completed",
            message=translate("bioaudit.status.complete", language),
            result=result,
            output_path=str(directory),
        )
    except Exception as exc:
        jobs.update(
            job_id,
            status="error",
            message=translate("bioaudit.status.error", language),
            error=f"{type(exc).__name__}: {exc}",
        )


@app.post("/api/jobs")
def create_job(request: AuditRequest) -> dict[str, str]:
    job_id = jobs.create()
    threading.Thread(target=worker, args=(job_id, request), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(
    job_id: str,
    language: str = "en",
) -> dict[str, Any]:
    item = jobs.get(job_id)

    if item is None:
        raise HTTPException(
            404,
            translate(
                "bioaudit.error.job_not_found",
                normalize_language(language),
            ),
        )

    return item


def main() -> None:
    global DEMO_MODE

    parser = argparse.ArgumentParser(description="BioAudit web console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run prerecorded demonstrations without external API calls.",
    )
    args = parser.parse_args()

    DEMO_MODE = args.demo

    if DEMO_MODE:
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        uvicorn.run("bioaudit.web:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
