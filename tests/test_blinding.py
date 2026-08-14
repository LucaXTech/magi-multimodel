from pathlib import Path
from magi.config import Settings
from magi.orchestrator import MagiOrchestrator
from magi.providers import build_providers


def test_blind_candidate_map(tmp_path: Path):
    settings=Settings(
        openai_api_key=None,anthropic_api_key=None,gemini_api_key=None,groq_api_key=None,
        openai_model="mock",anthropic_model="mock",gemini_model="mock",groq_model="mock",
        auditor_provider="groq",anthropic_thinking="disabled",judge_provider="openai",
        max_output_tokens=500,agent_word_limit=120,judge_word_limit=180,
        openai_reasoning_effort="low",openai_verbosity="low",runs_dir=tmp_path,
    )
    run,_=MagiOrchestrator(settings,build_providers(settings,mock=True)).run("Test",blind_judge=True,random_seed=7)
    assert set(run.candidate_map.values()) == {"MELCHIOR","BALTHASAR","CASPER"}
    assert set(run.candidate_map) == {"CANDIDATE_A","CANDIDATE_B","CANDIDATE_C"}
