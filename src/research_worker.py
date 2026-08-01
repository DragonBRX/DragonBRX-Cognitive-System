import json
import time
from typing import Any, Dict, List, Mapping
from pathlib import Path

class ResearchWorker:
    """
    Worker especializado em coletar e sintetizar informações da web
    para alimentar o cérebro do DragonBRX.
    """
    
    def __init__(self, storage_path: str = "knowledge_base"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.capabilities = ["web_research", "data_synthesis", "scientific_analysis"]

    def handle_task(self, task_body: Mapping[str, Any], search_results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processa uma tarefa de pesquisa. 
        Nota: Em um ambiente real, este worker usaria ferramentas de busca.
        Aqui, ele processa os resultados fornecidos pelo sistema para criar 'conhecimento'.
        """
        capability = task_body.get("capability")
        action_id = task_body.get("action_id")
        inputs = task_body.get("inputs", {})
        topic = inputs.get("topic", "geral")
        
        if capability == "web_research":
            return self._process_research(action_id, topic, search_results)
        else:
            return {"ok": False, "error": f"Capacidade {capability} não suportada"}

    def _process_research(self, action_id: str, topic: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not results:
            return {"ok": False, "error": "Nenhum dado sensorial (resultados de busca) fornecido"}
            
        # O 'Cérebro' do Worker extrai conceitos-chave dos resultados
        extracted_concepts = []
        summary_points = []
        
        for res in results:
            content = res.get("snippet", "") + " " + res.get("title", "")
            # Simulação de extração de termos científicos importantes (palavras com > 5 letras)
            words = [w.lower() for w in content.split() if len(w) > 5 and w.isalnum()]
            extracted_concepts.extend(words[:5])
            summary_points.append(res.get("title"))

        # Salva o rascunho bruto do conhecimento
        timestamp = int(time.time())
        file_path = self.storage_path / f"research_{topic}_{timestamp}.json"
        
        knowledge_packet = {
            "topic": topic,
            "timestamp": timestamp,
            "raw_sources": len(results),
            "extracted_concepts": list(set(extracted_concepts)),
            "summary": summary_points[:3]
        }
        
        file_path.write_text(json.dumps(knowledge_packet, indent=2, ensure_ascii=False), encoding="utf-8")
        
        return {
            "ok": True,
            "action_id": action_id,
            "capability": "web_research",
            "output": {
                "knowledge_file": str(file_path),
                "concepts_learned": list(set(extracted_concepts)),
                "message": f"Pesquisa sobre '{topic}' concluída. {len(extracted_concepts)} novos conceitos identificados."
            },
            "confidence": 0.85,
            "load": 0.3
        }

if __name__ == "__main__":
    # Teste básico
    worker = ResearchWorker()
    dummy_results = [{"title": "Neurociência da Memória", "snippet": "A plasticidade sináptica é fundamental para o aprendizado."}]
    print(worker.handle_task({"capability": "web_research", "action_id": "r1", "inputs": {"topic": "memória"}}, dummy_results))
