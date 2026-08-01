import sys
import os
import json

# Adiciona src ao path
sys.path.append(os.path.abspath("src"))

from cognitive_fabric import CognitiveFabric, Action
from cognitive_synthesizer import CognitiveSynthesizer

def run_deep_thought_demo():
    print("=== DragonBRX: Demonstração de Pensamento Profundo e Metacognição ===")
    
    # Inicializa o núcleo com um novo estado .lira
    core = CognitiveFabric(lira_path="deep_thought.lira.json")
    synth = CognitiveSynthesizer(core)
    
    # Define um objetivo complexo e incerto
    print("\n[OBJETIVO] Resolver um paradoxo de engenharia de software.")
    core.add_goal(
        "Otimizar performance vs Manter legibilidade extrema",
        desired=["performance", "legibilidade", "equilibrio"],
        priority=0.95
    )
    
    # Ações candidatas com scores variados para forçar diferentes estratégias
    actions = [
        Action("opt_01", "Micro-otimização em Assembly", "coding", inputs={}, expected=["performance"], cost=0.8, risk=0.9),
        Action("ref_01", "Refatoração para Clean Code", "coding", inputs={}, expected=["legibilidade"], cost=0.2, risk=0.1),
        Action("eq_01", "Implementar Padrão de Design Híbrido", "coding", inputs={}, expected=["performance", "legibilidade", "equilibrio"], cost=0.5, risk=0.3)
    ]
    
    # Ciclo 1: Decisão com baixa confiança inicial (deve ativar 'careful' ou 'deep')
    print("\n[PENSAMENTO] Analisando opções...")
    decision = core.choose(actions, intent="Resolver conflito de arquitetura")
    
    strategy = decision.action.name if decision.action else "Nenhuma"
    print(f"Decisão: {strategy}")
    print(f"Metacognição: {json.dumps(core.lira.chain[-1].metacognition, indent=2)}")
    
    # Ciclo 2: Geração de Rascunho com a estratégia adotada
    print("\n[SÍNTESE] Gerando rascunho baseado na estratégia metacognitiva...")
    strat_name = core.lira.chain[-1].metacognition["strategy_adopted"]
    draft_path = synth.synthesize_new_knowledge(
        "Equilíbrio Performance-Legibilidade", 
        ["latência", "manutenibilidade", "abstração"],
        strategy=strat_name
    )
    
    print(f"Rascunho gerado em: {draft_path}")
    
    # Exibe a linhagem histórica expandida
    print("\n=== LINHAGEM COGNITIVA EXPANDIDA ===")
    for step in core.lira.chain:
        print(f"[{step.metacognition['strategy_adopted'].upper()}] {step.intent}")
        print(f"  └─ Interpretação: {step.interpretation}")
        print(f"  └─ Confiança: {step.metacognition['confidence']:.2f}")

if __name__ == "__main__":
    run_deep_thought_demo()
