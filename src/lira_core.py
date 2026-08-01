import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from pathlib import Path
from uuid import uuid4

@dataclass
class CognitiveStep:
    """Um passo individual na cadeia cognitiva do DragonBRX."""
    step_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: float = field(default_factory=time.time)
    intent: str = ""
    interpretation: str = ""
    domains_activated: List[str] = field(default_factory=list)
    knowledge_retrieved: List[str] = field(default_factory=list)
    gaps_identified: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    evidence_observed: List[Any] = field(default_factory=list)
    decision_reason: str = ""
    method_result: str = ""
    candidate_learning: List[Dict[str, Any]] = field(default_factory=list)
    # Metacognição (Blueprint Codex)
    metacognition: Dict[str, Any] = field(default_factory=lambda: {
        "confidence": 0.0,
        "uncertainty_source": "",
        "strategy_adopted": "immediate", # immediate, careful, deep, experimental
        "self_correction_applied": False
    })

class LiraState:
    """
    Gerenciador do estado .lira (Persistent Self-Evolving General Cognitive Architecture).
    Mantém a linhagem de decisões e a evolução do sistema.
    """
    
    def __init__(self, storage_path: str = "lira_state.json"):
        self.storage_path = Path(storage_path)
        self.version = "1.0.0-lira"
        self.chain: List[CognitiveStep] = []
        self.metadata: Dict[str, Any] = {
            "created_at": time.time(),
            "last_updated": time.time(),
            "cycles_completed": 0,
            "classification": "P-SE-GCA"
        }
        self.load()

    def add_step(self, step: CognitiveStep):
        self.chain.append(step)
        self.metadata["last_updated"] = time.time()
        self.metadata["cycles_completed"] += 1
        self.save()

    def save(self):
        data = {
            "version": self.version,
            "metadata": self.metadata,
            "chain": [asdict(s) for s in self.chain]
        }
        self.storage_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load(self):
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                self.version = data.get("version", self.version)
                self.metadata = data.get("metadata", self.metadata)
                self.chain = [CognitiveStep(**s) for s in data.get("chain", [])]
            except Exception as e:
                print(f"[LIRA] Erro ao carregar estado: {e}. Iniciando novo estado.")

    def get_lineage(self) -> str:
        """Retorna uma representação textual da linhagem de evolução."""
        lines = [f"DragonBRX Lira Lineage - v{self.version}"]
        for i, step in enumerate(self.chain):
            lines.append(f"Cycle {i+1}: {step.intent[:50]}... -> {step.method_result}")
        return "\n".join(lines)

if __name__ == "__main__":
    # Teste rápido do LiraState
    lira = LiraState("test_lira.json")
    step = CognitiveStep(
        intent="Aprender sobre loops autônomos",
        interpretation="O usuário quer entender a diferença entre modelos estáticos e o DragonBRX",
        domains_activated=["autonomia", "arquitetura_ia"],
        method_result="Sucesso na criação do mapa de loops",
        decision_reason="Necessidade de visualização arquitetural"
    )
    lira.add_step(step)
    print(lira.get_lineage())
