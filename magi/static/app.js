const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
let activeJob = null;
let pollTimer = null;
let startedAt = null;
let config = null;

let i18n = null;
let language = "en";
let lastRenderedRun = null;
let lastJobPhase = null;
let currentSystem = {
  status: "",
  key: "magi.system.standby",
  values: {}
};

const PHASE_KEYS = {
  queued: "magi.status.queued",
  starting: "magi.status.starting",
  initial: "magi.status.initial",
  initial_done: "magi.status.initial_done",
  critique: "magi.status.critique",
  critique_done: "magi.status.critique_done",
  auditor: "magi.status.auditor",
  auditor_done: "magi.status.auditor_done",
  judge: "magi.status.judge",
  judge_done: "magi.status.judge_done",
  score: "magi.status.score",
  score_done: "magi.status.score_done",
  saved: "magi.status.saved",
  completed: "magi.status.completed",
  error: "magi.status.error"
};

function formatTemplate(template, values = {}) {
  return String(template).replace(/\{(\w+)\}/g, (_, key) =>
    Object.prototype.hasOwnProperty.call(values, key) ? values[key] : `{${key}}`
  );
}

function t(key, values = {}) {
  const catalogs = i18n?.catalogs || {};
  const catalog = catalogs[language] || catalogs[i18n?.default_language] || {};
  return formatTemplate(catalog[key] ?? key, values);
}

function phaseLabel(phase) {
  if (config?.demo_mode && phase === "starting") {
    return t("magi.demo.replaying");
  }
  if (config?.demo_mode && phase === "completed") {
    return t("magi.demo.completed");
  }
  return t(PHASE_KEYS[phase] || "magi.status.starting");
}

function applyLanguage() {
  document.documentElement.lang = language;

  $$("[data-i18n]").forEach(node => {
    node.textContent = t(node.dataset.i18n);
  });

  $$("[data-i18n-placeholder]").forEach(node => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });

  $$("[data-i18n-aria-label]").forEach(node => {
    node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
  });

  $("#languageSelect").value = language;
}

function applyConfigText() {
  if (!config) return;

  if (config.demo_mode) {
    $("#demoCaseSelect").querySelectorAll("option").forEach(option => {
      option.textContent = t(`demo.case.${option.value}`);
    });

    $("#providerLegend").textContent = t("magi.demo.provider_legend");
    $("#questionLabel").textContent = t("magi.demo.question_label");
    $("#runButton").textContent = t("magi.demo.run");
    $("#judgeInfo").textContent = t("magi.demo.judge");
  } else {
    $("#providerLegend").textContent = t("magi.providers.legend");
    $("#questionLabel").textContent = t("magi.question.label");
    $("#runButton").textContent = t("magi.run.start");
    $("#judgeInfo").textContent = t("magi.judge.live", {
      provider: config.judge_provider.toUpperCase()
    });
  }
}

async function setLanguage(nextLanguage) {
  if (!i18n?.supported_languages?.includes(nextLanguage)) return;

  language = nextLanguage;
  localStorage.setItem(i18n.storage_key, language);

  applyLanguage();
  applyConfigText();
  refreshSystem();

  if (lastJobPhase) {
    $("#progressMessage").textContent = phaseLabel(lastJobPhase);
  }

  if (lastRenderedRun) {
    renderRun(lastRenderedRun, false);
  }

  if (config) {
    await loadHistory();
  }
}

async function loadI18n() {
  i18n = await fetch("/api/i18n").then(response => {
    if (!response.ok) throw new Error("Could not load localization catalog");
    return response.json();
  });

  const stored = localStorage.getItem(i18n.storage_key);
  language = i18n.supported_languages.includes(stored)
    ? stored
    : i18n.default_language;

  $("#languageSelect").addEventListener("change", event => {
    setLanguage(event.target.value);
  });

  applyLanguage();
}


function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderText(text) {
  const safe = escapeHtml(text);
  const lines = safe.split(/\r?\n/);
  let html = "";
  let inList = false;
  for (let line of lines) {
    line = line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    line = line.replace(/`(.+?)`/g, "<code>$1</code>");
    if (/^#{1,4}\s+/.test(line)) {
      if (inList) { html += "</ul>"; inList = false; }
      html += `<h3>${line.replace(/^#{1,4}\s+/, "")}</h3>`;
    } else if (/^\s*[-*]\s+/.test(line)) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${line.replace(/^\s*[-*]\s+/, "")}</li>`;
    } else if (/^\s*\d+\.\s+/.test(line)) {
      if (inList) { html += "</ul>"; inList = false; }
      html += `<h3>${line}</h3>`;
    } else if (line.trim()) {
      if (inList) { html += "</ul>"; inList = false; }
      html += `<p>${line}</p>`;
    }
  }
  if (inList) html += "</ul>";
  return html;
}

function setSystem(status, key, values = {}) {
  currentSystem = {status, key, values};

  const node = $("#systemStatus");
  node.className = `system-status ${status || ""}`;
  node.innerHTML = `<i></i> ${escapeHtml(t(key, values))}`;
}

function refreshSystem() {
  setSystem(
    currentSystem.status,
    currentSystem.key,
    currentSystem.values
  );
}

function setAgentState(name, state, label) {
  const card = document.querySelector(`[data-agent="${name}"]`);
  card.classList.remove("processing", "complete", "failed");
  if (state) card.classList.add(state);
  card.querySelector(".agent-state").textContent = label;
}

function resetOutput() {
  ["MELCHIOR", "BALTHASAR", "CASPER"].forEach(name => {
    setAgentState(name, "", t("magi.agent.waiting"));
    document.querySelector(`[data-agent="${name}"] .agent-output`).innerHTML = "";
  });
  ["auditorPanel", "verdictPanel", "scorePanel", "telemetryPanel", "demoNotice"].forEach(id => $("#" + id).classList.add("hidden"));
  $("#errorMessage").textContent = "";
}

function phaseProgress(phase) {
  const map = {
    queued: 3, starting: 6, initial: 18, initial_done: 38,
    critique: 42, critique_done: 56, auditor: 62, auditor_done: 70, judge: 76, judge_done: 86,
    score: 90, score_done: 96, saved: 98, completed: 100, error: 100
  };
  $("#progressBar").style.width = `${map[phase] ?? 8}%`;
  const order = ["initial", "critique", "auditor", "judge", "score"];
  const current = phase.startsWith("initial") ? 0 : phase.startsWith("critique") ? 1 : phase.startsWith("auditor") ? 2 : phase.startsWith("judge") ? 3 : phase.startsWith("score") ? 4 : -1;
  $$("#phaseSteps span").forEach((node, index) => {
    node.classList.toggle("active", index === current && !phase.endsWith("done"));
    node.classList.toggle("done", index < current || (index === current && phase.endsWith("done")) || phase === "completed");
  });
}


async function loadConfig() {
  config = await fetch("/api/config").then(response => {
    if (!response.ok) throw new Error("Could not load MAGI configuration");
    return response.json();
  });

  const providers = ["openai", "anthropic", "gemini", "groq"];

  if (config.demo_mode) {
    $("#demoBanner").classList.remove("hidden");
    $("#demoControls").classList.remove("hidden");
    $("#question").readOnly = true;

    for (const provider of providers) {
      const input = document.querySelector(`.provider[value="${provider}"]`);
      input.disabled = true;
      input.checked = true;
      $("#" + provider + "Model").textContent =
        config.models[provider] || "recorded-demo";
    }

    const cases = config.demo_cases || [];
    if (!cases.length) {
      throw new Error(t("magi.demo.no_cases"));
    }

    const select = $("#demoCaseSelect");
    select.innerHTML = cases.map(item =>
      `<option value="${escapeHtml(item.id)}">${escapeHtml(t(`demo.case.${item.id}`))}</option>`
    ).join("");

    const loadDemoCase = () => {
      const selected = cases.find(item => item.id === select.value);
      if (selected) {
        $("#question").value = selected.question;
        resetOutput();
      }
    };

    select.addEventListener("change", loadDemoCase);
    $("#loadDemoButton").addEventListener("click", loadDemoCase);

    loadDemoCase();
    applyConfigText();
    setSystem("", "magi.demo.ready");
    return;
  }

  for (const provider of providers) {
    const input = document.querySelector(`.provider[value="${provider}"]`);
    input.disabled = !config.available[provider];
    input.checked = config.available[provider] &&
      (provider === "openai" || provider === "gemini");
    $("#" + provider + "Model").textContent =
      config.models[provider] || "";
  }

  applyConfigText();
  setSystem("", "magi.system.standby");
}

async function submitRun() {
  const question = $("#question").value.trim();
  if (question.length < 3) {
    $("#errorMessage").textContent = "Inserisci una domanda più completa.";
    return;
  }
  resetOutput();
  const realProviders = $$(".provider:checked").map(node => node.value);
  const critique = document.querySelector('input[name="mode"]:checked').value === "deep";
  const score = $("#score").checked;
  const auditor = $("#auditor").checked;
  $("#runButton").disabled = true;
  $("#progressPanel").classList.remove("hidden");
  setSystem("running", "magi.system.deliberating");
  startedAt = performance.now();
  ["MELCHIOR", "BALTHASAR", "CASPER"].forEach(name => setAgentState(name, "processing", t("magi.agent.processing")));

  try {
    const response = await fetch("/api/jobs", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        question,
        real_providers: realProviders,
        critique,
        score,
        auditor,
        demo_case: config?.demo_mode ? $("#demoCaseSelect").value : null
      })
    });
    if (!response.ok) throw new Error(await response.text());
    activeJob = (await response.json()).job_id;
    await pollJob();
  } catch (error) {
    failRun(error.message);
  }
}


function failRun(message) {
  clearTimeout(pollTimer);
  $("#runButton").disabled = false;
  $("#errorMessage").textContent = message;
  setSystem("error", "magi.system.error");

  ["MELCHIOR", "BALTHASAR", "CASPER"].forEach(name =>
    setAgentState(name, "failed", t("magi.agent.failed"))
  );
}


async function pollJob() {
  if (!activeJob) return;

  try {
    const job = await fetch(`/api/jobs/${activeJob}`).then(response => {
      if (!response.ok) throw new Error(t("magi.error.job_not_found"));
      return response.json();
    });

    lastJobPhase = job.phase;
    $("#progressMessage").textContent = phaseLabel(job.phase);

    const elapsed = (performance.now() - startedAt) / 1000;
    $("#elapsed").textContent = `${elapsed.toFixed(1)} s`;
    phaseProgress(job.phase);

    if ([
      "initial_done", "critique", "critique_done", "auditor",
      "auditor_done", "judge", "judge_done", "score",
      "score_done", "saved"
    ].includes(job.phase)) {
      const stateLabel = job.phase.startsWith("critique")
        ? t("magi.agent.revision")
        : t("magi.agent.complete");

      ["MELCHIOR", "BALTHASAR", "CASPER"].forEach(name =>
        setAgentState(name, "complete", stateLabel)
      );
    }

    if (job.status === "completed") {
      lastJobPhase = "completed";
      renderRun(job.result);
      $("#runButton").disabled = false;
      setSystem("", "magi.system.complete");
      phaseProgress("completed");
      await loadHistory();
      return;
    }

    if (job.status === "error") {
      failRun(job.error || t("magi.error.unknown"));
      return;
    }

    pollTimer = setTimeout(pollJob, 850);
  } catch (error) {
    failRun(error.message);
  }
}


function resultMeta(result) {
  if (result.demo_recording) {
    return `${result.provider} / ${t("magi.demo.static_fixture")}`;
  }

  const tokens = (result.input_tokens != null || result.output_tokens != null)
    ? ` | ${result.input_tokens || 0}/${result.output_tokens || 0} tok`
    : "";

  return `${result.provider}/${result.model} | ${Number(result.latency_seconds || 0).toFixed(2)} s${tokens}`;
}


function renderRun(run, scroll = true) {
  lastRenderedRun = run;

  if (run.demo_mode) {
    $("#demoNotice").classList.remove("hidden");
    $("#demoNotice").textContent = t("magi.demo.notice");
  }

  for (const agent of run.agents || []) {
    const card = document.querySelector(`[data-agent="${agent.agent}"]`);
    const initial = agent.initial || {};

    setAgentState(
      agent.agent,
      initial.error ? "failed" : "complete",
      resultMeta(initial)
    );

    let html = initial.error
      ? `<p class="error-message">${escapeHtml(initial.error)}</p>`
      : renderText(initial.text);

    if (agent.critique && agent.critique.text) {
      html += `
        <details>
          <summary>${escapeHtml(t("magi.critique.cross_review"))}</summary>
          <div class="rich-text">${renderText(agent.critique.text)}</div>
        </details>`;
    }

    card.querySelector(".agent-output").innerHTML = html;
  }

  if (run.auditor) {
    $("#auditorPanel").classList.remove("hidden");
    $("#auditorText").innerHTML = run.auditor.error
      ? `<p class="error-message">${escapeHtml(run.auditor.error)}</p>`
      : renderText(run.auditor.text);
  }

  if (run.verdict) {
    $("#verdictPanel").classList.remove("hidden");
    $("#verdictText").innerHTML = run.verdict.error
      ? `<p class="error-message">${escapeHtml(run.verdict.error)}</p>`
      : renderText(run.verdict.text);
  }

  if (run.scorecard) renderScorecard(run.scorecard);
  renderTelemetry(run);

  if (scroll) {
    setTimeout(() =>
      $("#verdictPanel").scrollIntoView({
        behavior: "smooth",
        block: "start"
      }), 120
    );
  }
}

function metric(label, value) {
  const v = Math.max(0, Math.min(100, Number(value || 0)));
  return `<div class="metric"><span>${label}</span><div class="metric-track"><div class="metric-fill" style="width:${v}%"></div></div><b>${v}</b></div>`;
}


function renderScorecard(scorecard) {
  $("#scorePanel").classList.remove("hidden");

  if (!scorecard.parsed) {
    $("#scoreCards").innerHTML =
      `<p class="error-message">${escapeHtml(t("magi.score.unparseable"))}: ${escapeHtml(scorecard.parse_error || t("common.error"))}</p>`;
    return;
  }

  $("#globalConfidence").textContent = `${scorecard.global_confidence}%`;
  $("#consensusLevel").textContent = `${scorecard.consensus_level}%`;

  $("#scoreCards").innerHTML = (scorecard.agents || []).map(agent => `
    <article class="score-card">
      <h3>${escapeHtml(agent.agent)}</h3>
      ${metric(t("magi.score.rigor"), agent.technical_rigor)}
      ${metric(t("magi.score.relevance"), agent.relevance)}
      ${metric(t("magi.score.uncertainty"), agent.uncertainty_handling)}
      ${metric(t("magi.score.practicality"), agent.practical_value)}
      ${metric(t("magi.score.weight"), agent.decision_weight)}
      <p>${escapeHtml(agent.rationale)}</p>
    </article>`).join("");

  $("#scoreNotes").innerHTML = `
    <div><b>${escapeHtml(t("magi.score.strongest"))}</b>${escapeHtml(scorecard.strongest_contribution)}</div>
    <div><b>${escapeHtml(t("magi.score.correction"))}</b>${escapeHtml(scorecard.main_correction)}</div>
    <div><b>${escapeHtml(t("magi.score.residual"))}</b>${escapeHtml(scorecard.residual_uncertainty)}</div>`;
}


function renderTelemetry(run) {
  const calls = [];

  for (const agent of run.agents || []) {
    if (agent.initial) calls.push(agent.initial);
    if (agent.critique) calls.push(agent.critique);
  }

  if (run.auditor) calls.push(run.auditor);
  if (run.verdict) calls.push(run.verdict);
  if (run.scorecard?.evaluator) calls.push(run.scorecard.evaluator);

  const errors = calls.filter(call => call.error).length;
  const incomplete = calls.filter(
    call => call.status === "incomplete" || call.incomplete_reason
  ).length;

  $("#telemetryPanel").classList.remove("hidden");

  if (run.demo_mode) {
    $("#telemetry").innerHTML = [
      [calls.length, t("magi.telemetry.demo_steps")],
      [t("common.not_available"), t("magi.telemetry.token_input")],
      [t("common.not_available"), t("magi.telemetry.token_output")],
      [t("common.not_available"), t("magi.telemetry.latency")],
      [`${errors}/${incomplete}`, t("magi.telemetry.errors")]
    ].map(([value, label]) =>
      `<div><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`
    ).join("");

    return;
  }

  const input = calls.reduce(
    (total, call) => total + Number(call.input_tokens || 0),
    0
  );

  const output = calls.reduce(
    (total, call) => total + Number(call.output_tokens || 0),
    0
  );

  $("#telemetry").innerHTML = [
    [calls.length, t("magi.telemetry.calls")],
    [input, t("magi.telemetry.token_input")],
    [output, t("magi.telemetry.token_output")],
    [`${Number(run.wall_time_seconds || 0).toFixed(1)}s`, t("magi.telemetry.wall_time")],
    [`${errors}/${incomplete}`, t("magi.telemetry.errors")]
  ].map(([value, label]) =>
    `<div><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`
  ).join("");
}


async function loadHistory() {
  if (config?.demo_mode) {
    $("#history").innerHTML =
      `<span class="muted">${escapeHtml(t("magi.demo.history"))}</span>`;
    return;
  }

  try {
    const runs = await fetch("/api/runs?limit=10").then(response => {
      if (!response.ok) throw new Error();
      return response.json();
    });

    if (!runs.length) {
      $("#history").innerHTML =
        `<span class="muted">${escapeHtml(t("magi.history.empty"))}</span>`;
      return;
    }

    $("#history").innerHTML = runs.map(run => `
      <article class="history-item" data-run="${escapeHtml(run.run_id)}">
        <div class="history-meta">
          <span>${escapeHtml(run.run_id)}</span>
          <span>${run.global_confidence != null ? run.global_confidence + "%" : "?"}</span>
        </div>
        <p>${escapeHtml(run.question)}</p>
      </article>`).join("");

    $$(".history-item").forEach(item =>
      item.addEventListener("click", async () => {
        const response = await fetch(`/api/runs/${item.dataset.run}`);

        if (!response.ok) {
          throw new Error(t("magi.error.run_not_found"));
        }

        const run = await response.json();
        $("#question").value = run.question || "";
        resetOutput();
        renderRun(run);
      })
    );
  } catch (_) {
    $("#history").innerHTML =
      `<span class="muted">${escapeHtml(t("magi.history.empty"))}</span>`;
  }
}

$("#runButton").addEventListener("click", submitRun);
$("#question").addEventListener("keydown", event => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") submitRun();
});

(async function boot() {
  try {
    await loadI18n();
    await loadConfig();
    await loadHistory();
  } catch (error) {
    $("#errorMessage").textContent = t("magi.error.init", {
      message: error.message
    });
    setSystem("error", "magi.system.config_error");
  }
})();
