const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
let activeJob = null;
let pollTimer = null;
let startedAt = null;
let config = null;

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

function setSystem(status, label) {
  const node = $("#systemStatus");
  node.className = `system-status ${status || ""}`;
  node.innerHTML = `<i></i> ${escapeHtml(label)}`;
}

function setAgentState(name, state, label) {
  const card = document.querySelector(`[data-agent="${name}"]`);
  card.classList.remove("processing", "complete", "failed");
  if (state) card.classList.add(state);
  card.querySelector(".agent-state").textContent = label;
}

function resetOutput() {
  ["MELCHIOR", "BALTHASAR", "CASPER"].forEach(name => {
    setAgentState(name, "", "IN ATTESA");
    document.querySelector(`[data-agent="${name}"] .agent-output`).innerHTML = "";
  });
  ["auditorPanel", "verdictPanel", "scorePanel", "telemetryPanel"].forEach(id => $("#" + id).classList.add("hidden"));
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
  config = await fetch("/api/config").then(r => r.json());
  for (const provider of ["openai", "anthropic", "gemini", "groq"]) {
    const input = document.querySelector(`.provider[value="${provider}"]`);
    input.disabled = !config.available[provider];
    input.checked = config.available[provider] && (provider === "openai" || provider === "gemini");
    $("#" + provider + "Model").textContent = config.models[provider] || "";
  }
  $("#judgeInfo").textContent = `JUDGE: ${config.judge_provider.toUpperCase()} · reale solo se selezionato`;
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
  setSystem("running", "DELIBERATING");
  startedAt = performance.now();
  ["MELCHIOR", "BALTHASAR", "CASPER"].forEach(name => setAgentState(name, "processing", "ANALISI IN CORSO"));

  try {
    const response = await fetch("/api/jobs", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question, real_providers: realProviders, critique, score, auditor})
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
  setSystem("error", "ERROR");
  ["MELCHIOR", "BALTHASAR", "CASPER"].forEach(name => setAgentState(name, "failed", "ERRORE"));
}

async function pollJob() {
  if (!activeJob) return;
  try {
    const job = await fetch(`/api/jobs/${activeJob}`).then(r => {
      if (!r.ok) throw new Error("Job non trovato");
      return r.json();
    });
    $("#progressMessage").textContent = job.message || job.phase;
    const elapsed = (performance.now() - startedAt) / 1000;
    $("#elapsed").textContent = `${elapsed.toFixed(1)} s`;
    phaseProgress(job.phase);

    if (["initial_done", "critique", "critique_done", "auditor", "auditor_done", "judge", "judge_done", "score", "score_done", "saved"].includes(job.phase)) {
      ["MELCHIOR", "BALTHASAR", "CASPER"].forEach(name => setAgentState(name, "complete", job.phase.startsWith("critique") ? "REVISIONE" : "COMPLETATO"));
    }
    if (job.status === "completed") {
      renderRun(job.result);
      $("#runButton").disabled = false;
      setSystem("", "COMPLETE");
      phaseProgress("completed");
      loadHistory();
      return;
    }
    if (job.status === "error") {
      failRun(job.error || "Errore sconosciuto");
      return;
    }
    pollTimer = setTimeout(pollJob, 850);
  } catch (error) {
    failRun(error.message);
  }
}

function resultMeta(result) {
  const tokens = (result.input_tokens != null || result.output_tokens != null)
    ? ` · ${result.input_tokens || 0}/${result.output_tokens || 0} tok`
    : "";
  return `${result.provider}/${result.model} · ${Number(result.latency_seconds || 0).toFixed(2)} s${tokens}`;
}

function renderRun(run) {
  for (const agent of run.agents || []) {
    const card = document.querySelector(`[data-agent="${agent.agent}"]`);
    const initial = agent.initial || {};
    setAgentState(agent.agent, initial.error ? "failed" : "complete", resultMeta(initial));
    let html = initial.error ? `<p class="error-message">${escapeHtml(initial.error)}</p>` : renderText(initial.text);
    if (agent.critique && agent.critique.text) {
      html += `<details><summary>CRITICA INCROCIATA</summary><div class="rich-text">${renderText(agent.critique.text)}</div></details>`;
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
  setTimeout(() => $("#verdictPanel").scrollIntoView({behavior:"smooth", block:"start"}), 120);
}

function metric(label, value) {
  const v = Math.max(0, Math.min(100, Number(value || 0)));
  return `<div class="metric"><span>${label}</span><div class="metric-track"><div class="metric-fill" style="width:${v}%"></div></div><b>${v}</b></div>`;
}

function renderScorecard(scorecard) {
  $("#scorePanel").classList.remove("hidden");
  if (!scorecard.parsed) {
    $("#scoreCards").innerHTML = `<p class="error-message">Scorecard non interpretabile: ${escapeHtml(scorecard.parse_error || "errore")}</p>`;
    return;
  }
  $("#globalConfidence").textContent = `${scorecard.global_confidence}%`;
  $("#consensusLevel").textContent = `${scorecard.consensus_level}%`;
  $("#scoreCards").innerHTML = (scorecard.agents || []).map(agent => `
    <article class="score-card">
      <h3>${escapeHtml(agent.agent)}</h3>
      ${metric("Rigore", agent.technical_rigor)}
      ${metric("Rilevanza", agent.relevance)}
      ${metric("Incertezza", agent.uncertainty_handling)}
      ${metric("Praticità", agent.practical_value)}
      ${metric("Peso", agent.decision_weight)}
      <p>${escapeHtml(agent.rationale)}</p>
    </article>`).join("");
  $("#scoreNotes").innerHTML = `
    <div><b>CONTRIBUTO PIÙ FORTE</b>${escapeHtml(scorecard.strongest_contribution)}</div>
    <div><b>CORREZIONE PRINCIPALE</b>${escapeHtml(scorecard.main_correction)}</div>
    <div><b>INCERTEZZA RESIDUA</b>${escapeHtml(scorecard.residual_uncertainty)}</div>`;
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
  const input = calls.reduce((a,c) => a + Number(c.input_tokens || 0), 0);
  const output = calls.reduce((a,c) => a + Number(c.output_tokens || 0), 0);
  const errors = calls.filter(c => c.error).length;
  const incomplete = calls.filter(c => c.status === "incomplete" || c.incomplete_reason).length;
  $("#telemetryPanel").classList.remove("hidden");
  $("#telemetry").innerHTML = [
    [calls.length, "CHIAMATE"], [input, "TOKEN INPUT"], [output, "TOKEN OUTPUT"],
    [`${Number(run.wall_time_seconds || 0).toFixed(1)}s`, "TEMPO REALE"],
    [`${errors}/${incomplete}`, "ERRORI/INCOMPLETE"]
  ].map(([value,label]) => `<div><strong>${escapeHtml(value)}</strong><span>${label}</span></div>`).join("");
}

async function loadHistory() {
  try {
    const runs = await fetch("/api/runs?limit=10").then(r => r.json());
    if (!runs.length) return;
    $("#history").innerHTML = runs.map(run => `
      <article class="history-item" data-run="${escapeHtml(run.run_id)}">
        <div class="history-meta"><span>${escapeHtml(run.run_id)}</span><span>${run.global_confidence != null ? run.global_confidence + "%" : "—"}</span></div>
        <p>${escapeHtml(run.question)}</p>
      </article>`).join("");
    $$(".history-item").forEach(item => item.addEventListener("click", async () => {
      const run = await fetch(`/api/runs/${item.dataset.run}`).then(r => r.json());
      $("#question").value = run.question || "";
      resetOutput();
      renderRun(run);
    }));
  } catch (_) {}
}

$("#runButton").addEventListener("click", submitRun);
$("#question").addEventListener("keydown", event => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") submitRun();
});

(async function boot() {
  try {
    await loadConfig();
    await loadHistory();
  } catch (error) {
    $("#errorMessage").textContent = `Errore inizializzazione: ${error.message}`;
    setSystem("error", "CONFIG ERROR");
  }
})();
