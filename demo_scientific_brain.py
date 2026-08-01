import sys
import json
from pathlib import Path
sys.path.insert(0, "src")

from cognitive_fabric import CognitiveFabric
from research_worker import ResearchWorker
from cognitive_synthesizer import CognitiveSynthesizer
from conversational_bridge import ConversationalBridge

def run_scientific_demo():
    print("="*60)
    print("DEMONSTRAÇÃO: DRAGONBRX - CÉREBRO CIENTÍFICO AUTÔNOMO")
    print("="*60)
    
    # 1. Inicialização
    core = CognitiveFabric()
    researcher = ResearchWorker()
    synthesizer = CognitiveSynthesizer(core)
    bridge = ConversationalBridge()
    
    topic = "Plasticidade Sináptica"
    print(f"\n[SISTEMA] Objetivo: Aprender sobre '{topic}' e criar uma síntese original.")
    
    # 2. Dados Sensoriais (Simulando o que veio da busca web)
    # Em um fluxo real, os snippets da busca seriam passados aqui
    raw_data = [
        {"title": "Neurociência da Memória", "snippet": "A plasticidade sináptica é a capacidade do cérebro de modificar suas conexões."},
        {"title": "Aprendizado e Adaptação", "snippet": "As sinapses se fortalecem ou enfraquecem em resposta aos estímulos percebidos."},
        {"title": "Base da Memória", "snippet": "Mudanças nas conexões neuronais são o mecanismo primário para o aprendizado e memória."}
    ]
    
    # 3. Fase de Pesquisa e Digestão
    print("\n[DragonBRX] Iniciando pesquisa científica...")
    research_task = {"capability": "web_research", "action_id": "res_001", "inputs": {"topic": topic}}
    result = researcher.handle_task(research_task, raw_data)
    
    learned_concepts = result["output"]["concepts_learned"]
    print(f"[DragonBRX] Absorvi {len(learned_concepts)} novos conceitos científicos.")
    
    # 4. Fase de Síntese e Criação (Cérebro criando do zero)
    print("\n[DragonBRX] Processando rascunho interno baseado no conhecimento adquirido...")
    draft_file = synthesizer.synthesize_new_knowledge(topic, learned_concepts)
    
    # 5. Resposta em Linguagem Natural
    print("\n" + "="*40)
    print("RESPOSTA DO CÉREBRO DRAGONBRX")
    print("="*40)
    
    status = core.status()
    print(bridge.articulate_status(status))
    
    print(f"\n[DragonBRX] Concluí minha análise sobre {topic}.")
    print(f"Gerei um rascunho original com minhas conclusões em: `{draft_file}`")
    
    # 6. Exibir o Rascunho Criado
    print("\n--- CONTEÚDO DO RASCUNHO GERADO ---")
    print(Path(draft_file).read_text())
    print("-" * 35)

if __name__ == "__main__":
    run_scientific_demo()
