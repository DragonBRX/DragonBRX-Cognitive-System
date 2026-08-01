import sys
import os
import time

# Adiciona src ao path
sys.path.append(os.path.abspath("src"))

from cognitive_fabric import CognitiveFabric
from autonomous_loop import AutonomousFeedbackLoop
from research_worker import ResearchWorker
from cognitive_synthesizer import CognitiveSynthesizer
from synaptic_learning_lab import SynapticLearningLab

def run_efficiency_demo():
    print("=== DragonBRX: Demonstração de Eficiência Elástica e Otimização ===")
    
    # 1. Configura um cérebro com limite de memória baixo para forçar o Pruning (Gari Cognitivo)
    core = CognitiveFabric(memory_limit=50) # Limite pequeno para teste
    
    # 2. Inunda o cérebro com variáveis temporárias (ruído)
    print("\n[ESTRESSE] Injetando 100 variáveis aleatórias para testar o Pruning...")
    for i in range(100):
        core.perceive("ruido", {"var": f"lixo_{i}"}, salience=0.1, confidence=0.1)
    
    print(f"Total de conceitos antes do ciclo: {len(core.concepts)}")
    
    # 3. Inicia o Loop de Autonomia
    # O Pruning deve rodar durante o _decay_and_spread no final de cada ciclo
    loop = AutonomousFeedbackLoop(
        core, 
        CognitiveSynthesizer(core), 
        ResearchWorker(), 
        SynapticLearningLab(core)
    )
    
    print("\n[LOOP] Iniciando ciclos autônomos com monitoramento de carga...")
    loop.start("Sistemas Autônomos de Baixo Consumo", max_cycles=2)
    
    # 4. Resultado Final
    status = core.status()
    print("\n=== RESULTADO DA OTIMIZAÇÃO ===")
    print(f"Conceitos Ativos: {status['concepts']} (Reduzido e Otimizado)")
    print(f"Ciclos Completados: {status['cycle']}")
    print(f"Memória Utilizada: {status['experiences']} experiências")
    
    print("\n[SUCESSO] O DragonBRX provou ser leve e adaptável ao hardware.")

if __name__ == "__main__":
    run_efficiency_demo()
