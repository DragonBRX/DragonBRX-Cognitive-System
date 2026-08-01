import time
from typing import Any, Dict
from lira_map_indexer import LiraMapIndexer

class IntrinsicLearner:
    """
    Aprendizado Intrínseco: O DragonBRX aprende conversando.
    Toda interação gera ou atualiza um parâmetro no Mapa Lira.
    """
    
    def __init__(self, mapper: LiraMapIndexer):
        self.mapper = mapper

    def process_interaction(self, user_input: str, response: str):
        """Aprende com a conversa e transcreve para parâmetros."""
        print(f"[APRENDIZADO] Extraindo parâmetros da conversa...")
        
        # Simula a extração de conceitos e pesos da conversa
        words = user_input.lower().split()
        for word in words:
            if len(word) > 3:
                # Se o conceito já existe, reforça o peso. Se não, cria.
                existing = self.mapper.read_parameter(word)
                if existing:
                    existing["peso"] = min(1.0, existing["peso"] + 0.05)
                    existing["last_talk"] = time.time()
                    self.mapper.write_parameter(word, existing)
                else:
                    new_param = {
                        "categoria": "conversa",
                        "peso": 0.5,
                        "contexto": user_input,
                        "last_talk": time.time()
                    }
                    self.mapper.write_parameter(word, new_param)

    def get_parameter_as_text(self, key: str) -> str:
        """Transcreve os parâmetros binários de volta para palavras/categorias."""
        param = self.mapper.read_parameter(key)
        if not param:
            return f"Parâmetro '{key}' não encontrado no mapa."
            
        return f"CONCEITO: {key} | CATEGORIA: {param.get('categoria')} | PESO: {param.get('peso'):.2f} | CONTEXTO: {param.get('contexto')}"

if __name__ == "__main__":
    mapper = LiraMapIndexer("brain_talk.lira")
    learner = IntrinsicLearner(mapper)
    learner.process_interaction("O DragonBRX é um cérebro autônomo", "Sim, eu aprendo conversando.")
    print(learner.get_parameter_as_text("cérebro"))
