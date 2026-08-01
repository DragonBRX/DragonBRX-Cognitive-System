import time
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
from temporal_elasticity import TemporalElasticity

class AutonomousFeedbackLoop:
    """
    O motor de autonomia do DragonBRX. 
    Mantém o sistema em um ciclo constante de:
    Observação -> Deliberação -> Ação -> Aprendizado -> Evolução.
    """
    
    def __init__(self, core, synthesizer, researcher, lab):
        self.core = core
        self.synthesizer = synthesizer
        self.researcher = researcher
        self.lab = lab
        self.elasticity = TemporalElasticity(base_delay=0.5)
        self.running = False
        self.cycle_count = 0

    def start(self, initial_goal: str, max_cycles: int = 3):
        """Inicia o loop de autonomia."""
        print(f"\n[AUTONOMIA] Iniciando Loop de Autonomia para o objetivo: '{initial_goal}'")
        self.running = True
        current_goal = initial_goal
        
        while self.running and self.cycle_count < max_cycles:
            self.cycle_count += 1
            print(f"\n--- CICLO DE AUTONOMIA #{self.cycle_count} ---")
            
            # 1. OBSERVAÇÃO E PESQUISA (Sentidos)
            print("[1] Pesquisando e observando o mundo...")
            # Simulamos a coleta de novos dados baseada no objetivo
            dummy_search = [
                {"title": f"Avanço em {current_goal}", "snippet": f"Novas descobertas sobre {current_goal} indicam padrões complexos."}
            ]
            research_task = {"capability": "web_research", "action_id": f"auto_{self.cycle_count}", "inputs": {"topic": current_goal}}
            res_result = self.researcher.handle_task(research_task, dummy_search)
            concepts = res_result["output"]["concepts_learned"]
            
            # 2. DELIBERAÇÃO E SÍNTESE (Pensamento)
            print("[2] Deliberando e criando rascunhos internos...")
            draft_path = self.synthesizer.synthesize_new_knowledge(current_goal, concepts)
            
            # 3. EXPERIMENTAÇÃO (Ação)
            print("[3] Testando conhecimentos no laboratório experimental...")
            # O sistema tenta criar um pequeno código .brx baseado no que aprendeu
            success = self.lab.run_experiment(f"Validar aprendizado do ciclo {self.cycle_count}", "Sucesso")
            
            # 4. APRENDIZADO E EVOLUÇÃO (Memória)
            print("[4] Integrando resultados à rede sináptica...")
            outcome_msg = "Sucesso na experimentação" if success else "Falha, ajustando conexões"
            self.core.perceive("loop_feedback", {
                "cycle": self.cycle_count,
                "outcome": outcome_msg,
                "concepts_active": len(concepts)
            }, salience=0.9)
            
            # O sistema decide o foco do próximo ciclo sozinho
            if concepts:
                current_goal = concepts[0] # Evolui o objetivo para um sub-conceito aprendido
                print(f"[5] Evolução: Próximo foco autônomo será '{current_goal}'")
            
            # Pausa elástica: ajusta o tempo de pensamento ao hardware disponível
            self.elasticity.simulate_thought_pause()

        self.running = False
        print("\n[AUTONOMIA] Loop concluído. O cérebro evoluiu através de múltiplos ciclos.")

if __name__ == "__main__":
    # Teste rápido do loop
    from cognitive_fabric import CognitiveFabric
    from research_worker import ResearchWorker
    from cognitive_synthesizer import CognitiveSynthesizer
    from synaptic_learning_lab import SynapticLearningLab
    
    core = CognitiveFabric()
    loop = AutonomousFeedbackLoop(
        core, 
        CognitiveSynthesizer(core), 
        ResearchWorker(), 
        SynapticLearningLab(core)
    )
    loop.start("Inteligência Artificial Autônoma", max_cycles=2)
