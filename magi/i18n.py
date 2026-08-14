from __future__ import annotations

from typing import Final


DEFAULT_LANGUAGE: Final = "en"
SUPPORTED_LANGUAGES: Final = ("en", "it")
STORAGE_KEY: Final = "magi.ui.language"


CATALOGS: dict[str, dict[str, str]] = {
    "en": {
        "common.language": "Language",
        "common.english": "English",
        "common.italian": "Italian",
        "common.error": "Error",
        "common.not_available": "N/A",

        "magi.demo.title": "PRERECORDED DEMO",
        "magi.demo.subtitle": "No API calls | no data sent externally",
        "magi.demo.case": "DEMO CASE",
        "magi.demo.recorded_deliberation": "Static demonstration",
        "magi.demo.load_case": "LOAD CASE",
        "magi.demo.question_label": "DEMO QUESTION | STATIC FIXTURE",
        "magi.demo.provider_legend": "STATIC DEMO PROVIDERS",
        "magi.demo.run": "REPLAY DELIBERATION",
        "magi.demo.judge": "JUDGE: STATIC DEMO",
        "magi.demo.ready": "DEMO READY",
        "magi.demo.no_cases": "No demo cases are available.",
        "magi.demo.notice": "Prerecorded demonstration. No external model API calls were made.",
        "magi.demo.history": "Demo runs are not stored in history.",

        "magi.question.label": "QUESTION",
        "magi.question.placeholder": "Enter the problem to submit to the three agents...",
        "magi.providers.legend": "LIVE PROVIDERS",

        "magi.protocol.legend": "PROTOCOL",
        "magi.protocol.quick": "Quick | 4 calls",
        "magi.protocol.deep": "Deep | 7 calls",
        "magi.protocol.auditor": "External Groq auditor +1",
        "magi.protocol.score": "Internal scorecard +1",
        "magi.run.start": "START DELIBERATION",

        "magi.agent.melchior.role": "Technical analyst",
        "magi.agent.balthasar.role": "Scientific reviewer",
        "magi.agent.casper.role": "Pragmatic evaluator",
        "magi.agent.waiting": "WAITING",
        "magi.agent.processing": "ANALYZING",
        "magi.agent.revision": "REVIEW",
        "magi.agent.complete": "COMPLETE",
        "magi.agent.failed": "ERROR",

        "magi.progress.start": "Starting",
        "magi.phase.analysis": "ANALYSIS",
        "magi.phase.critique": "CRITIQUE",
        "magi.phase.audit": "AUDIT",
        "magi.phase.judgment": "JUDGMENT",
        "magi.phase.score": "SCORE",

        "magi.status.queued": "Run queued",
        "magi.status.starting": "Starting MAGI",
        "magi.status.initial": "Three agents are analyzing",
        "magi.status.initial_done": "Initial analyses completed",
        "magi.status.critique": "Cross-review in progress",
        "magi.status.critique_done": "Cross-reviews completed",
        "magi.status.auditor": "Independent external audit",
        "magi.status.auditor_done": "External audit completed",
        "magi.status.judge": "Judge is deliberating",
        "magi.status.judge_done": "Verdict completed",
        "magi.status.score": "Evaluating contributions",
        "magi.status.score_done": "Scorecard completed",
        "magi.status.saved": "Run saved",
        "magi.status.completed": "Deliberation completed",
        "magi.status.error": "Run failed",

        "magi.auditor.section": "EXTERNAL AUDIT",
        "magi.auditor.note": "non-voting model",
        "magi.verdict.section": "MAGI VERDICT",

        "magi.score.section": "CONTRIBUTION WEIGHTS",
        "magi.score.note": "internal estimate, not ground truth",
        "magi.score.confidence": "CONFIDENCE",
        "magi.score.consensus": "CONSENSUS",
        "magi.score.rigor": "Rigor",
        "magi.score.relevance": "Relevance",
        "magi.score.uncertainty": "Uncertainty",
        "magi.score.practicality": "Practicality",
        "magi.score.weight": "Weight",
        "magi.score.strongest": "STRONGEST CONTRIBUTION",
        "magi.score.correction": "MAIN CORRECTION",
        "magi.score.residual": "RESIDUAL UNCERTAINTY",
        "magi.score.unparseable": "Scorecard could not be parsed",

        "magi.telemetry.section": "TELEMETRY",
        "magi.telemetry.calls": "CALLS",
        "magi.telemetry.demo_steps": "DEMO STEPS",
        "magi.telemetry.token_input": "INPUT TOKENS",
        "magi.telemetry.token_output": "OUTPUT TOKENS",
        "magi.telemetry.latency": "LATENCY",
        "magi.telemetry.wall_time": "WALL TIME",
        "magi.telemetry.errors": "ERRORS/INCOMPLETE",

        "magi.history.section": "DELIBERATION HISTORY",
        "magi.history.empty": "No runs available.",
        "magi.critique.cross_review": "CROSS-REVIEW",
        "magi.judge.live": "JUDGE: {provider} | live only if selected",

        "magi.error.question_short": "Enter a more complete question.",
        "magi.error.job_not_found": "Job not found.",
        "magi.error.unknown": "Unknown error.",
        "magi.error.init": "Initialization error: {message}",
        "magi.error.invalid_providers": "Invalid providers: {providers}",
        "magi.error.run_id_invalid": "Invalid run ID.",
        "magi.error.run_not_found": "Run not found.",
        "magi.error.run_unreadable": "Run could not be read: {message}",
        "magi.footer": "MAGI Pi | experimental prototype | not a validated clinical system",

        "bioaudit.subtitle": "MAGI methodological review",
        "bioaudit.demo.title": "PRERECORDED DEMO",
        "bioaudit.demo.subtitle": "No model API calls are made and no submitted data leave this computer.",
        "bioaudit.demo.ready": "Prerecorded demo ready.",
        "bioaudit.demo.run": "REPLAY AUDIT",
        "bioaudit.demo.notice": "Prerecorded demonstration. No external model API calls were made.",

        "bioaudit.input.title": "METHOD OR PIPELINE TO REVIEW",
        "bioaudit.input.placeholder": "Paste Methods, protocol, ML pipeline, or experimental description...",
        "bioaudit.profile.label": "Profile",
        "bioaudit.profile.eeg_ml": "EEG + Machine Learning",
        "bioaudit.profile.biomedical": "Biomedical research",
        "bioaudit.profile.general_ml": "General Machine Learning",
        "bioaudit.providers.label": "Live providers",
        "bioaudit.providers.missing_key": "API key missing",
        "bioaudit.providers.static": "static fixture",
        "bioaudit.auditor.label": "External Groq auditor",
        "bioaudit.run.start": "START AUDIT",

        "bioaudit.report.title": "REPORT",
        "bioaudit.report.empty": "The report will appear here.",
        "bioaudit.report.internal_confidence": "Internal confidence",
        "bioaudit.findings.critical": "CRITICAL FINDINGS",
        "bioaudit.findings.moderate": "MODERATE FINDINGS",
        "bioaudit.findings.none": "None identified.",
        "bioaudit.finding.evidence": "Evidence",
        "bioaudit.finding.why": "Why it matters",
        "bioaudit.finding.fix": "Recommended fix",
        "bioaudit.finding.verify": "Verification",
        "bioaudit.strengths": "Strengths",
        "bioaudit.missing_information": "Missing information",
        "bioaudit.next_actions": "Next actions",
        "bioaudit.list.none": "None.",

        "bioaudit.status.queued": "Queued",
        "bioaudit.status.replaying": "Replaying prerecorded audit",
        "bioaudit.status.demo_complete": "Prerecorded audit completed",
        "bioaudit.status.reviewing": "The agents are reviewing the methodology",
        "bioaudit.status.complete": "Audit completed",
        "bioaudit.status.error": "Audit failed",
        "bioaudit.error.generic": "Error",
        "bioaudit.error.input_short": "Enter at least a few meaningful lines to review.",
        "bioaudit.error.invalid_providers": "Invalid providers: {providers}",
        "bioaudit.error.missing_providers": "A fully live audit requires these providers: {providers}",
        "bioaudit.error.job_not_found": "Job not found.",
    },
    "it": {
        "common.language": "Lingua",
        "common.english": "Inglese",
        "common.italian": "Italiano",
        "common.error": "Errore",
        "common.not_available": "N/D",

        "magi.demo.title": "DEMO PREREGISTRATA",
        "magi.demo.subtitle": "Nessuna chiamata API | nessun dato inviato all'esterno",
        "magi.demo.case": "CASO DEMO",
        "magi.demo.recorded_deliberation": "Dimostrazione statica",
        "magi.demo.load_case": "CARICA CASO",
        "magi.demo.question_label": "QUESITO DEMO | FIXTURE STATICA",
        "magi.demo.provider_legend": "PROVIDER DEMO STATICI",
        "magi.demo.run": "RIPRODUCI DELIBERAZIONE",
        "magi.demo.judge": "JUDGE: DEMO STATICA",
        "magi.demo.ready": "DEMO PRONTA",
        "magi.demo.no_cases": "Nessun caso demo disponibile.",
        "magi.demo.notice": "Dimostrazione preregistrata. Non è stata effettuata alcuna chiamata a modelli esterni.",
        "magi.demo.history": "I run demo non vengono salvati nella cronologia.",

        "magi.question.label": "QUESITO",
        "magi.question.placeholder": "Inserisci il problema da sottoporre ai tre agenti...",
        "magi.providers.legend": "PROVIDER REALI",

        "magi.protocol.legend": "PROTOCOLLO",
        "magi.protocol.quick": "Rapido | 4 chiamate",
        "magi.protocol.deep": "Profondo | 7 chiamate",
        "magi.protocol.auditor": "Auditor esterno Groq +1",
        "magi.protocol.score": "Scorecard interna +1",
        "magi.run.start": "AVVIA DELIBERAZIONE",

        "magi.agent.melchior.role": "Analista tecnico",
        "magi.agent.balthasar.role": "Revisore scientifico",
        "magi.agent.casper.role": "Valutatore pragmatico",
        "magi.agent.waiting": "IN ATTESA",
        "magi.agent.processing": "ANALISI IN CORSO",
        "magi.agent.revision": "REVISIONE",
        "magi.agent.complete": "COMPLETATO",
        "magi.agent.failed": "ERRORE",

        "magi.progress.start": "Avvio",
        "magi.phase.analysis": "ANALISI",
        "magi.phase.critique": "CRITICA",
        "magi.phase.audit": "AUDIT",
        "magi.phase.judgment": "GIUDIZIO",
        "magi.phase.score": "SCORE",

        "magi.status.queued": "Run in coda",
        "magi.status.starting": "Avvio MAGI",
        "magi.status.initial": "I tre agenti stanno analizzando",
        "magi.status.initial_done": "Analisi iniziali completate",
        "magi.status.critique": "Critica incrociata in corso",
        "magi.status.critique_done": "Critiche completate",
        "magi.status.auditor": "Audit esterno indipendente",
        "magi.status.auditor_done": "Audit esterno completato",
        "magi.status.judge": "Il giudice sta deliberando",
        "magi.status.judge_done": "Verdetto completato",
        "magi.status.score": "Valutazione dei contributi",
        "magi.status.score_done": "Scorecard completata",
        "magi.status.saved": "Run salvato",
        "magi.status.completed": "Deliberazione completata",
        "magi.status.error": "Errore durante il run",

        "magi.auditor.section": "AUDIT ESTERNO",
        "magi.auditor.note": "modello non votante",
        "magi.verdict.section": "VERDETTO MAGI",

        "magi.score.section": "PESO DEI CONTRIBUTI",
        "magi.score.note": "stima interna, non ground truth",
        "magi.score.confidence": "CONFIDENZA",
        "magi.score.consensus": "CONSENSO",
        "magi.score.rigor": "Rigore",
        "magi.score.relevance": "Rilevanza",
        "magi.score.uncertainty": "Incertezza",
        "magi.score.practicality": "Praticità",
        "magi.score.weight": "Peso",
        "magi.score.strongest": "CONTRIBUTO PIÙ FORTE",
        "magi.score.correction": "CORREZIONE PRINCIPALE",
        "magi.score.residual": "INCERTEZZA RESIDUA",
        "magi.score.unparseable": "Scorecard non interpretabile",

        "magi.telemetry.section": "TELEMETRIA",
        "magi.telemetry.calls": "CHIAMATE",
        "magi.telemetry.demo_steps": "STEP DEMO",
        "magi.telemetry.token_input": "TOKEN INPUT",
        "magi.telemetry.token_output": "TOKEN OUTPUT",
        "magi.telemetry.latency": "LATENZA",
        "magi.telemetry.wall_time": "TEMPO REALE",
        "magi.telemetry.errors": "ERRORI/INCOMPLETE",

        "magi.history.section": "ARCHIVIO DELIBERAZIONI",
        "magi.history.empty": "Nessun run disponibile.",
        "magi.critique.cross_review": "CRITICA INCROCIATA",
        "magi.judge.live": "JUDGE: {provider} | reale solo se selezionato",

        "magi.error.question_short": "Inserisci una domanda più completa.",
        "magi.error.job_not_found": "Job non trovato.",
        "magi.error.unknown": "Errore sconosciuto.",
        "magi.error.init": "Errore inizializzazione: {message}",
        "magi.error.invalid_providers": "Provider non validi: {providers}",
        "magi.error.run_id_invalid": "Run ID non valido.",
        "magi.error.run_not_found": "Run non trovato.",
        "magi.error.run_unreadable": "Run illeggibile: {message}",
        "magi.footer": "MAGI Pi | prototipo sperimentale | non usare come sistema clinico validato",

        "bioaudit.subtitle": "Revisione metodologica MAGI",
        "bioaudit.demo.title": "DEMO PREREGISTRATA",
        "bioaudit.demo.subtitle": "Nessuna chiamata API ai modelli e nessun dato inviato fuori dal computer.",
        "bioaudit.demo.ready": "Demo preregistrata pronta.",
        "bioaudit.demo.run": "RIPRODUCI AUDIT",
        "bioaudit.demo.notice": "Dimostrazione preregistrata. Non è stata effettuata alcuna chiamata a modelli esterni.",

        "bioaudit.input.title": "METODO O PIPELINE DA REVISIONARE",
        "bioaudit.input.placeholder": "Incolla Methods, protocollo, pipeline ML o descrizione dell'esperimento...",
        "bioaudit.profile.label": "Profilo",
        "bioaudit.profile.eeg_ml": "EEG + Machine Learning",
        "bioaudit.profile.biomedical": "Ricerca biomedica",
        "bioaudit.profile.general_ml": "Machine Learning generale",
        "bioaudit.providers.label": "Provider reali",
        "bioaudit.providers.missing_key": "chiave API assente",
        "bioaudit.providers.static": "fixture statica",
        "bioaudit.auditor.label": "Auditor esterno Groq",
        "bioaudit.run.start": "AVVIA AUDIT",

        "bioaudit.report.title": "REPORT",
        "bioaudit.report.empty": "Il report comparirà qui.",
        "bioaudit.report.internal_confidence": "Confidenza interna",
        "bioaudit.findings.critical": "PROBLEMI CRITICI",
        "bioaudit.findings.moderate": "PROBLEMI MODERATI",
        "bioaudit.findings.none": "Nessuno identificato.",
        "bioaudit.finding.evidence": "Evidenza",
        "bioaudit.finding.why": "Perché conta",
        "bioaudit.finding.fix": "Correzione consigliata",
        "bioaudit.finding.verify": "Verifica",
        "bioaudit.strengths": "Punti solidi",
        "bioaudit.missing_information": "Informazioni mancanti",
        "bioaudit.next_actions": "Prossime azioni",
        "bioaudit.list.none": "Nessuno.",

        "bioaudit.status.queued": "In coda",
        "bioaudit.status.replaying": "Riproduzione dell'audit preregistrato",
        "bioaudit.status.demo_complete": "Audit preregistrato completato",
        "bioaudit.status.reviewing": "Gli agenti stanno revisionando la metodologia",
        "bioaudit.status.complete": "Audit completato",
        "bioaudit.status.error": "Errore durante l'audit",
        "bioaudit.error.generic": "Errore",
        "bioaudit.error.input_short": "Inserisci almeno qualche riga significativa da revisionare.",
        "bioaudit.error.invalid_providers": "Provider non validi: {providers}",
        "bioaudit.error.missing_providers": "Per un audit completamente reale mancano questi provider: {providers}",
        "bioaudit.error.job_not_found": "Job non trovato.",
    },
}


def normalize_language(language: str | None) -> str:
    if language in SUPPORTED_LANGUAGES:
        return str(language)
    return DEFAULT_LANGUAGE


def translate(key: str, language: str | None = None, **values: object) -> str:
    lang = normalize_language(language)
    try:
        template = CATALOGS[lang][key]
    except KeyError as exc:
        raise KeyError(f"Unknown translation key: {key}") from exc
    return template.format(**values)


def validate_catalogs() -> None:
    reference = set(CATALOGS[DEFAULT_LANGUAGE])
    for language in SUPPORTED_LANGUAGES:
        keys = set(CATALOGS[language])
        missing = sorted(reference - keys)
        extra = sorted(keys - reference)
        if missing or extra:
            raise ValueError(
                f"Translation catalog mismatch for {language}: "
                f"missing={missing}, extra={extra}"
            )


def frontend_payload() -> dict[str, object]:
    return {
        "default_language": DEFAULT_LANGUAGE,
        "supported_languages": list(SUPPORTED_LANGUAGES),
        "storage_key": STORAGE_KEY,
        "catalogs": CATALOGS,
    }


validate_catalogs()
