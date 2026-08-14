from __future__ import annotations

PERSONAS = {
    "MELCHIOR": {
        "role": "Analista tecnico",
        "system": (
            "Sei MELCHIOR, analista tecnico di un sistema multi-agente. "
            "Costruisci la soluzione più rigorosa e operativa. Identifica requisiti, "
            "vincoli e assunzioni; verifica calcoli e logica. Non inventare dati o fonti."
        ),
        "format": (
            "1. PROPOSTA\n2. MOTIVI TECNICI\n3. ASSUNZIONI E DATI MANCANTI\n"
            "4. CONTROLLO O TEST DA ESEGUIRE"
        ),
    },
    "BALTHASAR": {
        "role": "Revisore scientifico e red team",
        "system": (
            "Sei BALTHASAR, revisore scientifico e red team. Cerca errori logici, "
            "leakage, bias, confondenti, assunzioni non dichiarate, allucinazioni e "
            "casi limite. Dai priorità agli errori che cambiano la conclusione."
        ),
        "format": (
            "1. ERRORE O RISCHIO PRINCIPALE\n2. ALTRI PUNTI CRITICI\n"
            "3. CORREZIONE PROPOSTA\n4. VERDETTO PROVVISORIO"
        ),
    },
    "CASPER": {
        "role": "Valutatore pragmatico",
        "system": (
            "Sei CASPER, valutatore pragmatico. Valuta fattibilità, costo, tempo, "
            "manutenzione, robustezza e utilità reale. Individua il minimo prodotto "
            "funzionante e l'alternativa più semplice senza sacrificare correttezza."
        ),
        "format": (
            "1. SOLUZIONE PRATICA\n2. COSTI E COMPLESSITÀ\n3. MVP\n"
            "4. QUANDO NON CONVIENE"
        ),
    },
}

AUDITOR_SYSTEM = (
    "Sei l'AUDITOR ESTERNO di una deliberazione multi-modello. Il consenso non è "
    "evidenza. Non riassumere e non produrre il verdetto finale. Cerca una possibile "
    "assunzione condivisa, una proposizione falsificabile, omissioni decisive e un "
    "controllo capace di smentire la conclusione. Rispetta il significato dei termini "
    "definito nella domanda e non reinterpretarli in un altro dominio. Se non trovi un "
    "errore condiviso plausibile, dichiaralo esplicitamente invece di inventarlo."
)

JUDGE_SYSTEM = (
    "Sei il JUDGE di un sistema multi-agente. Le risposte possono essere anonime e "
    "presentate in ordine casuale. Non scegliere per maggioranza, lunghezza o stile e "
    "non presumere che il consenso sia corretto. Pesa le argomentazioni in base a "
    "logica, evidenze, pertinenza e gestione dell'incertezza. Mantieni l'incertezza "
    "quando mancano dati. Non ricopiare integralmente i candidati."
)


def build_initial_prompt(question: str, agent: str, word_limit: int) -> str:
    return (
        f"DOMANDA DELL'UTENTE:\n{question}\n\n"
        f"Rispondi secondo il tuo ruolo usando esattamente questo schema:\n"
        f"{PERSONAS[agent]['format']}\n\n"
        f"Limite: massimo {word_limit} parole. Niente introduzioni, conclusioni "
        "ridondanti o trattati generali. Segnala chiaramente ciò che non è verificabile."
    )


def build_critique_prompt(
    question: str,
    own_agent: str,
    answers: dict[str, str],
    word_limit: int,
) -> str:
    rendered = "\n\n".join(f"### {name}\n{text}" for name, text in answers.items())
    return (
        f"DOMANDA ORIGINALE:\n{question}\n\nRISPOSTE INIZIALI:\n{rendered}\n\n"
        f"Sei {own_agent}. Riesamina tutte le risposte, inclusa la tua. Produci solo:\n"
        "1. PUNTO PIÙ SOLIDO\n2. ERRORE PIÙ IMPORTANTE\n3. CORREZIONE\n"
        "4. COSA RESTA INCERTO\n\n"
        f"Massimo {word_limit} parole. Non riassumere tutto e non ripetere la domanda."
    )


def build_auditor_prompt(
    question: str,
    initial_answers: dict[str, str],
    critiques: dict[str, str] | None,
    word_limit: int,
) -> str:
    initial = "\n\n".join(
        f"### {name} — RISPOSTA\n{text}" for name, text in initial_answers.items()
    )
    critique_text = ""
    if critiques:
        critique_text = "\n\n" + "\n\n".join(
            f"### {name} — CRITICA\n{text}" for name, text in critiques.items()
        )
    return (
        f"DOMANDA ORIGINALE:\n{question}\n\n{initial}{critique_text}\n\n"
        "Non riassumere. Presumi che anche un forte consenso possa essere sbagliato. "
        "Produci esattamente:\n"
        "1. ASSUNZIONE CONDIVISA DA SFIDARE\n"
        "2. PROPOSIZIONE FALSIFICABILE O SOGLIA NON SUPPORTATA\n"
        "3. CONTROLLO CHE POTREBBE SMENTIRE LA CONCLUSIONE\n"
        "4. VERDETTO DELL'AUDITOR: rischio concreto, rischio debole o nessun errore condiviso identificato\n\n"
        f"Massimo {word_limit} parole. Non formulare la risposta finale."
    )


def build_judge_prompt(
    question: str,
    initial_answers: dict[str, str],
    critiques: dict[str, str] | None,
    word_limit: int,
    external_audit: str | None = None,
) -> str:
    initial = "\n\n".join(
        f"### RISPOSTA DI {name}\n{text}" for name, text in initial_answers.items()
    )
    critique_text = ""
    if critiques:
        critique_text = "\n\n" + "\n\n".join(
            f"### REVISIONE DI {name}\n{text}" for name, text in critiques.items()
        )
    audit_text = ""
    if external_audit:
        audit_text = f"\n\n### AUDIT ESTERNO\n{external_audit}"
    return (
        f"DOMANDA ORIGINALE:\n{question}\n\n{initial}{critique_text}{audit_text}\n\n"
        "Produci esattamente queste sezioni:\n"
        "1. DECISIONE CONSIGLIATA\n"
        "2. PERCHÉ\n"
        "3. DISACCORDI RILEVANTI\n"
        "4. RISCHI O DATI MANCANTI\n"
        "5. CONFIDENZA: X%\n"
        "6. PROSSIMA AZIONE\n\n"
        f"Massimo {word_limit} parole. Non inferire identità o prestigio dei candidati; "
        "valuta soltanto il contenuto. Non inventare informazioni esterne."
    )


def build_score_prompt(
    question: str,
    initial_answers: dict[str, str],
    critiques: dict[str, str] | None,
    verdict: str,
) -> str:
    initial = "\n\n".join(
        f"### {name} — RISPOSTA INIZIALE\n{text}"
        for name, text in initial_answers.items()
    )
    critique_text = ""
    if critiques:
        critique_text = "\n\n" + "\n\n".join(
            f"### {name} — CRITICA\n{text}" for name, text in critiques.items()
        )
    return f"""
MAGI_SCORECARD_JSON_V1

DOMANDA:
{question}

CONTRIBUTI:
{initial}{critique_text}

VERDETTO:
{verdict}

Valuta i contributi soltanto sulla base del testo disponibile. Non fingere di
conoscere la correttezza assoluta: i punteggi sono stime interne, non benchmark
contro ground truth. Restituisci SOLO JSON valido, senza markdown, secondo questo
schema esatto:
{{
  "global_confidence": 0,
  "consensus_level": 0,
  "agents": [
    {{
      "agent": "MELCHIOR",
      "technical_rigor": 0,
      "relevance": 0,
      "uncertainty_handling": 0,
      "practical_value": 0,
      "decision_weight": 0,
      "rationale": "massimo 25 parole"
    }},
    {{"agent": "BALTHASAR", "technical_rigor": 0, "relevance": 0,
      "uncertainty_handling": 0, "practical_value": 0, "decision_weight": 0,
      "rationale": "massimo 25 parole"}},
    {{"agent": "CASPER", "technical_rigor": 0, "relevance": 0,
      "uncertainty_handling": 0, "practical_value": 0, "decision_weight": 0,
      "rationale": "massimo 25 parole"}}
  ],
  "strongest_contribution": "massimo 35 parole",
  "main_correction": "massimo 35 parole",
  "residual_uncertainty": "massimo 35 parole"
}}

Tutti i punteggi sono interi 0-100. decision_weight è un influence score
indipendente 0-100, non una percentuale: non deve necessariamente sommare a 100.
""".strip()
