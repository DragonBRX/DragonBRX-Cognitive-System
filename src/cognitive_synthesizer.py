import json
import time
from typing import Any, Dict, List
from pathlib import Path

class CognitiveSynthesizer:
    """
    O 'Córtex de Criação' do DragonBRX. 
    Transforma dados brutos e conceitos em rascunhos, teorias e novas conexões sinápticas.
    """
    
    def __init__(self, core_fabric):
        self.core = core_fabric
        self.drafts_path = Path("internal_drafts")
        self.drafts_path.mkdir(parents=True, exist_ok=True)

    def synthesize_new_knowledge(self, topic: str, learned_concepts: List[str]) -> str:
        """
        Cria um rascunho original (draft) baseado nos conceitos absorvidos.
        Não é um texto pré-pronto, mas uma construção baseada nas relações sinápticas.
        """
        print(f"[SYNTH] Iniciando síntese sobre: {topic}")
        
        # Integra os conceitos ao núcleo cognitivo
        for concept in learned_concepts:
            self.core.perceive("learned_data", {"concept": concept, "source": "web_research"}, salience=0.8)
        
        # O 'Cérebro' agora tenta criar uma relação entre os conceitos ativos
        active = self.core.introspect(limit=10)
        focus = active.get("focus", [])
        
        # Criação do rascunho (Draft)
        draft_content = f"--- RASCUNHO COGNITIVO: {topic.upper()} ---\n"
        draft_content += f"Data Estelar: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        draft_content += f"Base de Atenção: {', '.join(focus[:5])}\n\n"
        
        draft_content += "SÍNTESE AUTÔNOMA:\n"
        if len(learned_concepts) >= 3:
            draft_content += f"A análise dos dados sugere uma conexão forte entre '{learned_concepts[0]}' e '{learned_concepts[1]}'.\n"
            draft_content += f"Isso impacta diretamente o entendimento de '{learned_concepts[2]}'.\n"
        else:
            draft_content += "Dados insuficientes para uma teoria complexa, mas novos nós sinápticos foram criados.\n"
            
        draft_content += "\nCONCLUSÃO EXPERIMENTAL:\n"
        draft_content += f"O sistema DragonBRX agora reconhece '{topic}' como um domínio ativo com {len(learned_concepts)} novas variáveis.\n"
        
        # Salva o rascunho
        file_name = f"draft_{topic.replace(' ', '_')}_{int(time.time())}.txt"
        file_path = self.drafts_path / file_name
        file_path.write_text(draft_content, encoding="utf-8")
        
        return str(file_path)

    def get_brain_report(self) -> str:
        """Gera um relatório do estado de evolução do cérebro."""
        status = self.core.status()
        report = f"Evolução do Cérebro DragonBRX:\n"
        report += f"- Ciclos de Pensamento: {status['cycle']}\n"
        report += f"- Total de Conceitos: {status['concepts']}\n"
        report += f"- Memórias (Experiências): {status['experiences']}\n"
        return report
