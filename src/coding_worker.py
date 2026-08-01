import os
import json
import time
from typing import Any, Dict, Mapping, Optional
from pathlib import Path

class CodingWorker:
    """Worker especializado em gerar código e documentação técnica."""
    
    def __init__(self, workspace: str = "workspace"):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.capabilities = ["software_implementation", "code_generation", "technical_documentation"]

    def handle_task(self, task_body: Mapping[str, Any]) -> Dict[str, Any]:
        capability = task_body.get("capability")
        action_id = task_body.get("action_id")
        inputs = task_body.get("inputs", {})
        
        if capability == "software_implementation":
            return self._implement_code(action_id, inputs)
        elif capability == "technical_documentation":
            return self._generate_docs(action_id, inputs)
        else:
            return {"ok": False, "error": f"Capacidade {capability} não suportada pelo CodingWorker"}

    def _implement_code(self, action_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        request = inputs.get("request", "projeto_generico")
        # Simulação de geração de código baseada em regras simples para o protótipo
        # Em um cenário real, aqui haveria lógica de templates ou integração com LLM local
        
        filename = "main.py"
        code_content = f'# Gerado por DragonBRX CodingWorker\n# Projeto: {request}\n\ndef main():\n    print("Hello from DragonBRX!")\n\nif __name__ == "__main__":\n    main()\n'
        
        file_path = self.workspace / filename
        file_path.write_text(code_content, encoding="utf-8")
        
        return {
            "ok": True,
            "action_id": action_id,
            "capability": "software_implementation",
            "output": {
                "file": str(file_path),
                "status": "Código implementado com sucesso",
                "lines": len(code_content.splitlines())
            },
            "confidence": 0.95,
            "load": 0.2
        }

    def _generate_docs(self, action_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        filename = "README.md"
        doc_content = f"# Documentação do Projeto\n\nGerado automaticamente pelo CodingWorker.\n"
        
        file_path = self.workspace / filename
        file_path.write_text(doc_content, encoding="utf-8")
        
        return {
            "ok": True,
            "action_id": action_id,
            "capability": "technical_documentation",
            "output": {
                "file": str(file_path),
                "status": "Documentação gerada"
            },
            "confidence": 0.9,
            "load": 0.1
        }

if __name__ == "__main__":
    # Teste rápido do worker
    worker = CodingWorker()
    result = worker.handle_task({
        "capability": "software_implementation",
        "action_id": "test-123",
        "inputs": {"request": "Sistema de Teste"}
    })
    print(json.dumps(result, indent=2))
