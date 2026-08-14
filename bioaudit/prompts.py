from __future__ import annotations

from typing import Any

PROFILE_CHECKLISTS = {
    "eeg_ml": [
        "unità di split: soggetto, sessione, registrazione, tempo",
        "finestre sovrapposte e dipendenza temporale",
        "fit di preprocessing, ICA/ASR, scaling e feature selection",
        "label leakage, artefatti correlati e confondenti",
        "nested validation, metriche per soggetto e test esterno",
        "coerenza tra scenario di deployment e protocollo di validazione",
    ],
    "biomedical": [
        "popolazione, criteri di inclusione e unità indipendente",
        "endpoint, comparatore, confondenti e bias di selezione",
        "missing data, molteplicità e analisi statistica",
        "generalizzabilità, validazione esterna e claim clinici",
        "tracciabilità, riproducibilità e dati mancanti",
    ],
    "general_ml": [
        "split train/validation/test e duplicati",
        "preprocessing, feature selection e resampling",
        "tuning, soglie e contaminazione del test",
        "class imbalance, calibrazione e metriche",
        "domain shift, robustezza, riproducibilità e deployment",
    ],
}

AGENT_SYSTEMS = {
    "MELCHIOR": (
        "Sei MELCHIOR, analista tecnico. Ricostruisci il flusso, individua dipendenze, "
        "controlla formule e coerenza tra obiettivo, dati, validazione e claim."
    ),
    "BALTHASAR": (
        "Sei BALTHASAR, revisore scientifico e red team. Cerca errori metodologici, "
        "bias, leakage, confondenti, assunzioni non dichiarate e conclusioni non supportate."
    ),
    "CASPER": (
        "Sei CASPER, valutatore pragmatico. Proponi correzioni implementabili, priorità, "
        "MVP e controlli con il miglior rapporto beneficio/costo."
    ),
}

AUDITOR_SYSTEM = (
    "Sei un auditor esterno avversariale. Non riassumere il consenso. Cerca un errore "
    "condiviso, una soglia inventata, un'omissione decisiva o una verifica capace di "
    "smentire la conclusione. Non inventare fatti assenti dall'input."
)

JUDGE_SYSTEM = (
    "Sei il responsabile di BioAudit. Produci un audit strutturato esclusivamente sulla "
    "base dell'input e dei contributi anonimi. Non scegliere per maggioranza o stile. "
    "Distingui evidenza testuale, inferenza e informazione mancante. Restituisci SOLO JSON."
)


def checklist_text(profile: str) -> str:
    return "\n".join(f"- {item}" for item in PROFILE_CHECKLISTS[profile])


def agent_prompt(text: str, profile: str, agent: str) -> str:
    return f"""
BIOAUDIT_AGENT_V1

PROFILO: {profile}
CHECKLIST:
{checklist_text(profile)}

INPUT DA REVISIONARE:
---
{text}
---

Sei {agent}. Produci al massimo 450 parole e usa esattamente:
1. PUNTI SOLIDI
2. PROBLEMI CRITICI
3. PROBLEMI MODERATI
4. DATI MANCANTI
5. CORREZIONI E CONTROLLI

Per ogni problema cita o parafrasa il frammento dell'input che lo motiva. Se un punto non
è verificabile, dichiaralo. Non introdurre soglie universali o regole non supportate.
""".strip()


def auditor_prompt(text: str, profile: str, candidates: dict[str, str]) -> str:
    rendered = "\n\n".join(f"### {name}\n{value}" for name, value in candidates.items())
    return f"""
BIOAUDIT_AUDITOR_V1

PROFILO: {profile}
INPUT:
---
{text}
---

CONTRIBUTI ANONIMI:
{rendered}

Produci esattamente:
1. ASSUNZIONE CONDIVISA DA SFIDARE
2. AFFERMAZIONE NON SUPPORTATA O SOGLIA ARBITRARIA
3. OMISSIONE DECISIVA
4. CONTROLLO FALSIFICANTE
5. ESITO AUDITOR: rischio concreto / rischio debole / nessun errore condiviso identificato

Massimo 350 parole. Non formulare il report finale.
""".strip()


def judge_prompt(
    text: str,
    profile: str,
    candidates: dict[str, str],
    audit: str | None,
) -> str:
    rendered = "\n\n".join(f"### {name}\n{value}" for name, value in candidates.items())
    audit_text = f"\n\nAUDIT ESTERNO:\n{audit}" if audit else ""
    schema = {
        "verdict": "PASS|REVISE|BLOCK",
        "summary": "massimo 100 parole",
        "critical_issues": [
            {
                "title": "titolo breve",
                "evidence_from_input": "frammento o Not specified",
                "why_it_matters": "massimo 70 parole",
                "recommended_fix": "azione concreta",
                "verification": "test o controllo verificabile",
            }
        ],
        "moderate_issues": [],
        "strengths": ["punto solido"],
        "missing_information": ["dato necessario"],
        "disagreements_resolved": ["disaccordo e risoluzione"],
        "next_actions": ["azione ordinata per priorità"],
        "internal_confidence": 0,
    }
    import json

    return f"""
BIOAUDIT_REPORT_JSON_V1

PROFILO: {profile}
CHECKLIST:
{checklist_text(profile)}

INPUT DA REVISIONARE:
---
{text}
---

CONTRIBUTI ANONIMI:
{rendered}{audit_text}

Restituisci SOLO JSON valido, senza markdown, conforme a questo schema:
{json.dumps(schema, ensure_ascii=False, indent=2)}

Regole:
- BLOCK solo se un problema rende invalida o pericolosamente fuorviante la conclusione principale.
- REVISE se servono correzioni sostanziali ma il progetto è recuperabile.
- PASS solo se non emergono problemi sostanziali dall'input disponibile.
- massimo 6 problemi critici e 8 moderati;
- internal_confidence è una stima interna, non accuratezza misurata;
- non inventare dati, risultati, fonti o requisiti normativi.
""".strip()
