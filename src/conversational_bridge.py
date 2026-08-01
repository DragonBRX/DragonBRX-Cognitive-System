import json
from typing import Any, Dict, List

class ConversationalBridge:
    """Converte o estado e decisões do DragonBRX em linguagem natural humana."""
    
    def __init__(self, identity: str = "DragonBRX"):
        self.identity = identity

    def articulate_decision(self, decision: Dict[str, Any]) -> str:
        """Explica uma decisão tomada pelo núcleo."""
        action = decision.get("action")
        if not action:
            return f"[{self.identity}] No momento, estou analisando o contexto e não identifiquei uma ação imediata necessária."
        
        name = action.get("name", "uma tarefa")
        agent = decision.get("delegated_to")
        reasons = decision.get("reasons", [])
        
        msg = f"[{self.identity}] Decidi que o próximo passo é: **{name}**.\n"
        if agent:
            msg += f"Vou delegar essa tarefa para o agente **{agent}**.\n"
        else:
            msg += "Vou executar essa tarefa localmente.\n"
            
        if reasons:
            msg += "\n**Motivos da minha decisão:**\n"
            for reason in reasons:
                msg += f"- {reason}\n"
        
        return msg

    def articulate_status(self, status: Dict[str, Any]) -> str:
        """Descreve o estado atual da 'mente' do sistema."""
        cycle = status.get("cycle", 0)
        concepts = status.get("concepts", 0)
        goals = status.get("goals", [])
        
        msg = f"[{self.identity}] Atualmente estou no ciclo cognitivo nº {cycle}.\n"
        msg += f"Minha rede sináptica contém {concepts} conceitos ativos.\n"
        
        if goals:
            msg += "\n**Meus objetivos atuais:**\n"
            for goal in goals:
                status_icon = "✅" if goal['status'] == 'completed' else "⏳"
                msg += f"- {status_icon} {goal['description']} ({goal['progress']*100:.1f}% concluído)\n"
        
        return msg

    def articulate_completion(self, task_name: str, result: Dict[str, Any]) -> str:
        """Comunica a conclusão de uma tarefa e o que foi aprendido."""
        ok = result.get("ok", False)
        output = result.get("output", {})
        
        if ok:
            msg = f"[{self.identity}] Concluí com sucesso a tarefa: **{task_name}**.\n"
            if "file" in output:
                msg += f"O resultado foi salvo em: `{output['file']}`.\n"
            msg += "Isso reforçou minha base de conhecimento sobre este domínio."
        else:
            msg = f"[{self.identity}] Houve um problema ao executar **{task_name}**. Vou reavaliar minha estratégia."
            
        return msg

if __name__ == "__main__":
    # Teste rápido da ponte
    bridge = ConversationalBridge()
    sample_decision = {
        "action": {"name": "Implementar Código Principal"},
        "delegated_to": "CodingWorker-01",
        "reasons": ["ganho_de_objetivo=0.950", "contexto=0.400"]
    }
    print(bridge.articulate_decision(sample_decision))
