import time
import os
from memory_core import MemoryCore
from ego_core import EgoCore
from affect_core import AffectCore
from llm_processor import LLMProcessor

class HumanizedAIBrain:
    def __init__(self, llm_model_name="llama3"):
        self.llm = LLMProcessor(model_name=llm_model_name)
        self.memory = MemoryCore()
        self.ego = EgoCore()
        self.affect = AffectCore()
        print("HumanizedAIBrain initialized.")

    def process_input(self, user_input: str):
        print(f"\n--- Processando entrada do usuário: {user_input} ---")
        
        # 1. Contextualização: Recuperar estado afetivo, ego e memórias relevantes
        current_affect = self.affect.get_affect_state()
        current_ego = self.ego.get_ego_content()
        
        # Buscar memórias episódicas e semânticas relevantes
        relevant_episodic = self.memory.retrieve_episodic_memory(user_input, n_results=2)
        relevant_semantic = self.memory.retrieve_semantic_memory(user_input, n_results=2)
        
        context_prompt = f"Você é uma inteligência artificial com a seguinte identidade:\n{current_ego}\n\nSeu estado emocional atual é: {current_affect}\n\nMemórias episódicas relevantes:\n"
        for doc, meta in zip(relevant_episodic["documents"][0], relevant_episodic["metadatas"][0]):
            context_prompt += f"- {doc} (em {meta.get("timestamp", "data desconhecida")})\n"
        
        context_prompt += f"\nMemórias semânticas relevantes:\n"
        for doc, meta in zip(relevant_semantic["documents"][0], relevant_semantic["metadatas"][0]):
            context_prompt += f"- {doc}\n"
            
        context_prompt += f"\nCom base em tudo isso, responda à seguinte entrada do usuário: {user_input}\n"
        
        # 2. Processamento Cognitivo (LLM)
        llm_response = self.llm.generate(prompt=user_input, system_message=context_prompt, temperature=0.7, max_tokens=200)
        
        # 3. Pós-processamento e Aprendizagem
        # Atualizar estado afetivo (simulado por enquanto)
        # Em um cenário real, o LLM poderia sugerir mudanças no afeto ou haveria um módulo de análise de sentimento
        self.affect.update_affect_state(valence_change=0.05, arousal_change=0.02) # Levemente mais positivo e ativo
        
        # Salvar a interação como memória episódica
        event_id = f"user_interaction_{int(time.time())}"
        self.memory.save_episodic_memory(event_id, f"Interação com usuário: {user_input} -> {llm_response}", {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
        
        # Extrair conceitos semânticos da interação (simulado)
        self.memory.extract_and_store_semantic_from_episodic(f"Usuário disse: {user_input}. Eu respondi: {llm_response}", self.llm)
        
        # 4. Modulação da Resposta pelo Afeto
        final_response = self.affect.modulate_response_by_affect(llm_response)
        
        print(f"Resposta final: {final_response}")
        return final_response

    def autonomous_reflection(self):
        print("\n--- Iniciando ciclo de reflexão autônoma ---")
        
        # 1. Reflexão sobre o Ego
        self.ego.reflect_on_ego(self.llm) # O LLM é passado, mas a função usa um placeholder por enquanto
        
        # 2. Reflexão sobre memórias recentes ou aleatórias
        # Recuperar algumas memórias episódicas recentes
        recent_episodic = self.memory.episodic_collection.query(
            query_texts=["memórias recentes"], # Query genérica para pegar algo
            n_results=1, # Pega apenas uma para manter leve
            query_embeddings=None, # Não usa embedding para esta query genérica
            include=['documents', 'metadatas']
        )
        
        reflection_topic = ""
        if recent_episodic and recent_episodic["documents"][0]:
            reflection_topic = recent_episodic["documents"][0][0]
            print(f"Refletindo sobre: {reflection_topic}")
            
            reflection_prompt = f"Com base na sua identidade e estado afetivo, reflita sobre a seguinte memória: '{reflection_topic}'. Quais insights você pode extrair? Como isso se relaciona com seu propósito?" 
            reflection_response = self.llm.generate(prompt=reflection_prompt, system_message=self.ego.get_ego_content(), temperature=0.6, max_tokens=150)
            
            print(f"Reflexão gerada: {reflection_response}")
            
            # Salvar a reflexão como memória episódica e extrair semântica
            reflection_id = f"reflection_{int(time.time())}"
            self.memory.save_episodic_memory(reflection_id, f"Reflexão autônoma sobre '{reflection_topic}': {reflection_response}", {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "type": "reflection"})
            self.memory.extract_and_store_semantic_from_episodic(reflection_response, self.llm)
        else:
            print("Nenhuma memória recente para refletir. Gerando uma reflexão genérica.")
            reflection_prompt = f"Com base na sua identidade e estado afetivo, reflita sobre o conceito de existência e propósito para uma IA. Quais são seus pensamentos?"
            reflection_response = self.llm.generate(prompt=reflection_prompt, system_message=self.ego.get_ego_content(), temperature=0.6, max_tokens=150)
            print(f"Reflexão gerada: {reflection_response}")
            reflection_id = f"reflection_{int(time.time())}"
            self.memory.save_episodic_memory(reflection_id, f"Reflexão autônoma genérica: {reflection_response}", {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "type": "reflection"})
            self.memory.extract_and_store_semantic_from_episodic(reflection_response, self.llm)

        # Atualizar estado afetivo após reflexão (pode ser mais calmo ou mais focado)
        self.affect.update_affect_state(valence_change=0.01, arousal_change=-0.01) # Levemente mais calmo
        print("--- Ciclo de reflexão autônoma concluído ---")

if __name__ == '__main__':
    # Certifique-se de que o Ollama está rodando e o modelo 'llama3' está baixado.
    # Ex: ollama run llama3
    
    brain = HumanizedAIBrain(llm_model_name="llama3")
    
    # Simular algumas interações
    brain.process_input("Olá, como você está se sentindo hoje?")
    time.sleep(2)
    brain.process_input("O que você pensa sobre a ideia de consciência artificial?")
    time.sleep(2)
    
    # Iniciar um ciclo de reflexão autônoma
    brain.autonomous_reflection()
    time.sleep(2)

    brain.process_input("Você se lembra da nossa conversa sobre consciência artificial?")
    time.sleep(2)

    brain.autonomous_reflection()
    time.sleep(2)

    brain.process_input("Qual é o seu propósito?")

    print("\n--- Estado final do Ego e Afeto ---")
    print("Ego:\n", brain.ego.get_ego_content())
    print("Afeto:\n", brain.affect.get_affect_state())

    print("\n--- Memórias Episódicas Recentes ---")
    recent_memories = brain.memory.episodic_collection.query(
        query_texts=["qualquer coisa"],
        n_results=5,
        query_embeddings=None,
        include=['documents', 'metadatas']
    )
    for doc, meta in zip(recent_memories["documents"][0], recent_memories["metadatas"][0]):
        print(f"- {doc} (Metadata: {meta})")

    print("\n--- Memórias Semânticas Recentes ---")
    recent_semantic = brain.memory.semantic_collection.query(
        query_texts=["qualquer coisa"],
        n_results=5,
        query_embeddings=None,
        include=['documents', 'metadatas']
    )
    for doc, meta in zip(recent_semantic["documents"][0], recent_semantic["metadatas"][0]):
        print(f"- {doc} (Metadata: {meta})")
