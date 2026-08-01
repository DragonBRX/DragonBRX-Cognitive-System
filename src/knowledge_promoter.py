import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path

@dataclass
class KnowledgeCandidate:
    """Um candidato a conhecimento em quarentena."""
    id: str
    content: Any
    source: str
    timestamp: float = field(default_factory=time.time)
    confidence: float = 0.5
    status: str = "quarantine" # quarantine, experimental, candidate, staged, stable
    validation_logs: List[str] = field(default_factory=list)

class KnowledgePromoter:
    """
    Gerencia a evolução do conhecimento no DragonBRX.
    Impede que informações não confiáveis cheguem à memória estável sem validação.
    """
    
    def __init__(self, core, storage_path: str = "knowledge_quarantine.json"):
        self.core = core
        self.storage_path = Path(storage_path)
        self.candidates: Dict[str, KnowledgeCandidate] = {}
        self.load()

    def submit_candidate(self, content: Any, source: str, confidence: float = 0.5) -> str:
        """Submete nova informação para a quarentena."""
        cid = f"cand_{int(time.time())}_{len(self.candidates)}"
        candidate = KnowledgeCandidate(id=cid, content=content, source=source, confidence=confidence)
        self.candidates[cid] = candidate
        self.save()
        print(f"[PROMOTER] Novo candidato em quarentena: {cid} (Fonte: {source})")
        return cid

    def validate_candidate(self, cid: str, success: bool, log: str):
        """Registra o resultado de um teste de validação."""
        if cid in self.candidates:
            candidate = self.candidates[cid]
            candidate.validation_logs.append(f"{'[OK]' if success else '[FAIL]'} {log}")
            if success:
                candidate.confidence = min(1.0, candidate.confidence + 0.1)
            else:
                candidate.confidence = max(0.0, candidate.confidence - 0.2)
            self.save()

    def promote_if_ready(self, cid: str, threshold: float = 0.8):
        """Promove o conhecimento para o estado estável se a confiança for alta o suficiente."""
        if cid in self.candidates:
            candidate = self.candidates[cid]
            if candidate.confidence >= threshold and candidate.status != "stable":
                print(f"[PROMOTER] Promovendo {cid} para estado STABLE!")
                candidate.status = "stable"
                # Integra ao núcleo cognitivo real
                self.core.perceive("promoted_knowledge", {
                    "content": candidate.content,
                    "original_source": candidate.source,
                    "final_confidence": candidate.confidence
                }, salience=1.0)
                self.save()
                return True
        return False

    def save(self):
        data = {cid: cand.__dict__ for cid, cand in self.candidates.items()}
        self.storage_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load(self):
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for cid, cdata in data.items():
                    self.candidates[cid] = KnowledgeCandidate(**cdata)
            except Exception as e:
                print(f"[PROMOTER] Erro ao carregar quarentena: {e}")

if __name__ == "__main__":
    # Teste do Promoter
    from cognitive_fabric import CognitiveFabric
    core = CognitiveFabric()
    promoter = KnowledgePromoter(core, "test_quarantine.json")
    cid = promoter.submit_candidate({"info": "A Terra é redonda"}, "WebResearch", 0.7)
    promoter.validate_candidate(cid, True, "Confirmado por múltiplas fontes")
    promoter.promote_if_ready(cid)
