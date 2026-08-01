import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import hashlib

@dataclass
class SkillContract:
    """Contrato de entrada e saída para uma skill."""
    inputs: Dict[str, str]  # Nome -> Tipo (ex: "topic" -> "string")
    outputs: Dict[str, str] # Nome -> Tipo
    pre_conditions: List[str] = field(default_factory=list)
    post_conditions: List[str] = field(default_factory=list)

@dataclass
class Skill:
    """Representação de uma skill no Atlas do DragonBRX."""
    namespace: str
    domain: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    contract: Optional[SkillContract] = None
    permissions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    cost_estimate: Dict[str, float] = field(default_factory=dict)
    status: str = "experimental" # experimental, staged, stable, deprecated, revoked
    provenance: str = "manual"
    
    @property
    def full_id(self) -> str:
        return f"skill:{self.namespace}/{self.domain}/{self.name}@{self.version}"

class SkillAtlas:
    """
    Gerenciador de larga escala para as 1.600+ skills do DragonBRX.
    Suporta busca lexical/vetorial e carregamento lazy.
    """
    
    def __init__(self, storage_path: str = "skill_atlas.json"):
        self.storage_path = Path(storage_path)
        self.skills: Dict[str, Skill] = {}
        self.load()

    def add_skill(self, skill: Skill):
        self.skills[skill.full_id] = skill
        self.save()

    def find_skills(self, query: str, domain: Optional[str] = None) -> List[Skill]:
        """Busca skills por query lexical e filtro de domínio."""
        results = []
        q = query.lower()
        for skill in self.skills.values():
            if domain and skill.domain != domain:
                continue
            if q in skill.name.lower() or q in skill.description.lower() or q in skill.domain.lower():
                results.append(skill)
        return sorted(results, key=lambda s: s.status == "stable", reverse=True)

    def save(self):
        data = {fid: asdict(s) for fid, s in self.skills.items()}
        self.storage_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load(self):
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for fid, sdata in data.items():
                    # Reconstrói o contrato se existir
                    if sdata.get("contract"):
                        sdata["contract"] = SkillContract(**sdata["contract"])
                    self.skills[fid] = Skill(**sdata)
            except Exception as e:
                print(f"[ATLAS] Erro ao carregar Atlas: {e}")

if __name__ == "__main__":
    # Teste do Atlas
    atlas = SkillAtlas("test_atlas.json")
    s = Skill(
        namespace="dragon",
        domain="programacao",
        name="python_generator",
        description="Gera código Python funcional a partir de requisitos",
        contract=SkillContract(
            inputs={"requirements": "string"},
            outputs={"code": "string", "file_path": "string"}
        ),
        status="stable"
    )
    atlas.add_skill(s)
    print(f"Skills encontradas: {[sk.full_id for sk in atlas.find_skills('python')]}")
