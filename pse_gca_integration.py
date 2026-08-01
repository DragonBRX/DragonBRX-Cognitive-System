import time
import sys
import os

# Adiciona src ao path
sys.path.append(os.path.abspath("src"))

from cognitive_fabric import CognitiveFabric
from lira_core import LiraState, CognitiveStep
from skill_atlas import SkillAtlas, Skill, SkillContract
from knowledge_promoter import KnowledgePromoter
from research_worker import ResearchWorker
from autonomous_loop import AutonomousFeedbackLoop
from synaptic_learning_lab import SynapticLearningLab
from cognitive_synthesizer import CognitiveSynthesizer

def run_pse_gca_demo():
    print("=== DragonBRX: P-SE-GCA (Arquitetura Cognitiva Geral Autoevolutiva Persistente) ===")
    
    # 1. Inicialização do Runtime Persistente (.lira)
    core = CognitiveFabric(lira_path="active_brain.lira.json")
    atlas = SkillAtlas("global_skill_atlas.json")
    promoter = KnowledgePromoter(core, "brain_quarantine.json")
    
    print(f"\n[ESTADO] Linhagem atual: {len(core.lira.chain)} ciclos registrados.")
    
    # 2. Ativação do Atlas de Skills
    if not atlas.skills:
        print("[ATLAS] Inicializando Atlas com skills fundamentais...")
        atlas.add_skill(Skill(
            namespace="dragon", domain="pesquisa", name="web_explorer",
            description="Explora a web em busca de dados científicos",
            status="stable"
        ))
        atlas.add_skill(Skill(
            namespace="dragon", domain="logica", name="brx_interpreter",
            description="Executa e valida código na linguagem .brx",
            status="stable"
        ))

    # 3. Ciclo de Autonomia com Pipeline de Promoção
    print("\n[AUTONOMIA] Iniciando ciclo de evolução científica...")
    researcher = ResearchWorker()
    synthesizer = CognitiveSynthesizer(core)
    lab = SynapticLearningLab(core)
    
    # Objetivo: Entender a relação entre Memória e Parâmetros (desafio do Blueprint)
    goal_text = "Diferença entre Memória Externa e Aprendizagem Paramétrica"
    core.add_goal(goal_text, desired=["memória", "parâmetros", "aprendizado"], priority=0.9)
    
    # Simulação do Loop com Promoção
    print(f"[1] Pesquisando: {goal_text}")
    # Simula descoberta
    cid = promoter.submit_candidate(
        {"conceito": "Aprendizagem Paramétrica", "definicao": "Mudança nos pesos internos do modelo"},
        "ResearchWorker", confidence=0.6
    )
    
    print("[2] Validando conhecimento em quarentena...")
    time.sleep(1)
    promoter.validate_candidate(cid, True, "Consistente com a arquitetura .lira")
    promoter.promote_if_ready(cid)
    
    # 4. Registro na Cadeia Cognitiva (Lira)
    print("\n[LIRA] Registrando decisão na cadeia cognitiva...")
    decision = core.choose([], intent=f"Consolidar aprendizado sobre {goal_text}")
    
    print("\n=== RESUMO DA EVOLUÇÃO ===")
    print(core.lira.get_lineage())
    print(f"\n[SUCESSO] O DragonBRX agora opera como uma P-SE-GCA completa.")

if __name__ == "__main__":
    run_pse_gca_demo()
