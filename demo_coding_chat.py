import sys
import json
from pathlib import Path
sys.path.insert(0, "src")

from cognitive_fabric import CognitiveFabric
from prompt_system import PromptSystem
from distributed_runtime import AgentRegistry
from coding_worker import CodingWorker
from conversational_bridge import ConversationalBridge
import io

def run_demo():
    print("="*60)
    print("DEMONSTRAÇÃO: DRAGONBRX PROGRAMADOR E COMUNICATIVO")
    print("="*60)
    
    # 1. Inicialização dos Sistemas
    core = CognitiveFabric()
    prompt_system = PromptSystem()
    bridge = ConversationalBridge()
    coding_worker = CodingWorker(workspace="dragon_workspace")
    
    registry = AgentRegistry(core)
    registry.server_secret = b"secret"
    registry.prompt_system = prompt_system
    
    # 2. Entrada do Usuário
    user_request = "Desenvolver um software básico de boas-vindas"
    print(f"\nUsuário: {user_request}")
    
    # 3. Planejamento
    plan = prompt_system.create_plan(user_request)
    prompt_system.activate(core, plan)
    
    # DragonBRX responde sobre o plano
    status_report = core.status()
    print(f"\n{bridge.articulate_status(status_report)}")
    
    # 4. Execução da Tarefa de Programação
    # No PromptSystem, 'implementation' depende de 'architecture' e 'experience'
    # Vamos completar as tarefas iniciais para liberar a implementação
    print("\n--- [Simulando conclusão de requisitos e arquitetura...] ---")
    for task_key in ["requirements", "architecture", "experience"]:
        task = plan.task_map()[task_key]
        prompt_system.complete_task(plan.plan_id, task.task_id, {"ok": True})
        print(f"Tarefa {task_key} concluída.")

    # Agora a tarefa de implementação deve estar pronta
    impl_task = plan.task_map()["implementation"]
    
    # DragonBRX decide o que fazer
    ready_actions = prompt_system.actions_for_ready_tasks(plan.plan_id)
    action = next(a for a in ready_actions if a.action_id == impl_task.task_id)
    decision = core.choose([action])
    
    # DragonBRX explica sua decisão
    # Simulamos que ele escolheu o CodingWorker
    decision.delegated_to = "CodingWorker-Alpha"
    print(f"{bridge.articulate_decision(json.loads(json.dumps(decision, default=lambda o: o.__dict__)))}")
    
    # 5. O Worker trabalha
    print(f"--- [CodingWorker-Alpha está processando...] ---")
    result = coding_worker.handle_task({
        "capability": impl_task.capability,
        "action_id": impl_task.task_id,
        "inputs": {"request": user_request}
    })
    
    # 6. DragonBRX recebe o resultado e comunica
    prompt_system.complete_task(plan.plan_id, impl_task.task_id, result, success=result["ok"])
    print(f"{bridge.articulate_completion(impl_task.title, result)}")
    
    # 7. Verificação do arquivo gerado
    generated_file = Path(result["output"]["file"])
    if generated_file.exists():
        print(f"\n[SISTEMA] Conteúdo do arquivo gerado ({generated_file.name}):")
        print("-" * 20)
        print(generated_file.read_text())
        print("-" * 20)

if __name__ == "__main__":
    run_demo()
