import sys
import json
from pathlib import Path
sys.path.insert(0, "src")

from cognitive_fabric import CognitiveFabric, Action
from prompt_system import PromptSystem
from distributed_runtime import AgentRegistry
import io

def run_simulation():
    print("=== SIMULAÇÃO DE PROJETO COMPLEXO: JOGO 3D PARA ANDROID ===")
    
    # 1. Inicialização
    core = CognitiveFabric()
    prompt_system = PromptSystem()
    registry = AgentRegistry(core)
    registry.server_secret = b"dragonbrx_secret_key_simulation"
    registry.prompt_system = prompt_system
    
    # 2. Criar Plano
    request = "Cria um jogo 3D de aventura offline para Android"
    plan = prompt_system.create_plan(request)
    prompt_system.activate(core, plan)
    
    print(f"Projeto: {plan.project_type}")
    print(f"Descrição: {plan.description}")
    print(f"Tasks totais: {len(plan.tasks)}")
    
    # 3. Simular Agentes
    # Agente 1: Designer (iPhone)
    stream_iphone = io.BytesIO()
    registry.attach("iphone-designer", stream_iphone, ["game_design", "game_mechanics"], "ios")
    
    # Agente 2: Artista (Termux)
    stream_termux = io.BytesIO()
    registry.attach("termux-artist", stream_termux, ["game_art", "game_ui"], "termux")
    
    # 4. Executar Ciclo de Trabalho
    # Task 1: Vision (Design)
    vision_task = plan.task_map()["vision"]
    print(f"\n[Fase 1] Iniciando: {vision_task.title}")
    
    action_vision = next(a for a in prompt_system.actions_for_ready_tasks(plan.plan_id) if a.action_id == vision_task.task_id)
    msg_id = registry.dispatch(action_vision)
    prompt_system.start_task(plan.plan_id, vision_task.task_id)
    
    # Simular resultado do iPhone
    # Adicionando os conceitos esperados para fechar o objetivo: "projeto", "game", "concluído"
    registry.complete("iphone-designer", {
        "reply_to": msg_id,
        "ok": True,
        "output": {"projeto": "iniciado", "game": "ativo", "visão": "Aventura em Marte", "escopo": "Pequeno"},
        "action_id": vision_task.task_id,
        "capability": vision_task.capability
    })
    print(f"Status Vision: {vision_task.status}")
    
    # Task 2: Mechanics (Depende de Vision)
    mechanics_task = plan.task_map()["mechanics"]
    print(f"\n[Fase 2] Iniciando: {mechanics_task.title}")
    
    action_mech = next(a for a in prompt_system.actions_for_ready_tasks(plan.plan_id) if a.action_id == mechanics_task.task_id)
    msg_id = registry.dispatch(action_mech)
    prompt_system.start_task(plan.plan_id, mechanics_task.task_id)
    
    registry.complete("iphone-designer", {
        "reply_to": msg_id,
        "ok": True,
        "output": {"mecânica": "Salto gravitacional"},
        "action_id": mechanics_task.task_id,
        "capability": mechanics_task.capability
    })
    print(f"Status Mechanics: {mechanics_task.status}")
    
    # Task 3: Art (Pode rodar agora)
    art_task = plan.task_map()["art"]
    print(f"\n[Fase 3] Iniciando: {art_task.title}")
    
    action_art = next(a for a in prompt_system.actions_for_ready_tasks(plan.plan_id) if a.action_id == art_task.task_id)
    msg_id = registry.dispatch(action_art)
    prompt_system.start_task(plan.plan_id, art_task.task_id)
    
    registry.complete("termux-artist", {
        "reply_to": msg_id,
        "ok": True,
        "output": {"assets": ["rover.png", "mars_ground.png"], "concluído": "sim"},
        "action_id": art_task.task_id,
        "capability": art_task.capability
    })
    print(f"Status Art: {art_task.status}")
    
    # 5. Introspecção do Estado
    print("\n" + "="*40)
    print("ESTADO COGNITIVO FINAL DA SIMULAÇÃO")
    print("="*40)
    
    report = core.introspect()
    print(f"Ciclos: {report['cycle']}")
    print(f"Foco de Atenção: {', '.join(report['focus'])}")
    
    print("\nAssociações Fortes:")
    for assoc in report['strongest_associations']:
        print(f"  {assoc['from']} -> {assoc['to']} ({assoc['strength']})")
        
    print("\nObjetivos em Aberto:")
    for goal in report['unresolved_goals']:
        print(f"  {goal['description']} - Progresso: {goal['progress']*100:.1f}%")
        if goal['missing']:
            print(f"    Faltando: {', '.join(goal['missing'])}")
            
    print("\nObjetivos Completados:")
    status = core.status()
    for goal in status['goals']:
        if goal['status'] == 'completed':
            print(f"  ✅ {goal['description']}")

if __name__ == "__main__":
    run_simulation()
