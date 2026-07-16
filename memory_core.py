import chromadb
from chromadb.utils import embedding_functions
import os
import json

class MemoryCore:
    def __init__(self, db_path="./chroma_db", embedding_model="all-MiniLM-L6-v2"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=embedding_model)
        
        self.episodic_collection = self.client.get_or_create_collection(
            name="episodic_memory",
            embedding_function=self.embedding_function
        )
        self.semantic_collection = self.client.get_or_create_collection(
            name="semantic_memory",
            embedding_function=self.embedding_function
        )
        print(f"MemoryCore initialized. Episodic count: {self.episodic_collection.count()}, Semantic count: {self.semantic_collection.count()}")

    def save_episodic_memory(self, event_id: str, content: str, metadata: dict = None):
        if metadata is None:
            metadata = {}
        metadata['type'] = 'episodic'
        self.episodic_collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[event_id]
        )
        print(f"Episodic memory '{event_id}' saved.")

    def retrieve_episodic_memory(self, query: str, n_results: int = 3):
        results = self.episodic_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results

    def save_semantic_memory(self, concept_id: str, content: str, metadata: dict = None):
        if metadata is None:
            metadata = {}
        metadata['type'] = 'semantic'
        self.semantic_collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[concept_id]
        )
        print(f"Semantic memory '{concept_id}' saved.")

    def retrieve_semantic_memory(self, query: str, n_results: int = 3):
        results = self.semantic_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results

    def extract_and_store_semantic_from_episodic(self, episodic_content: str, llm_processor):
        # This function would use the LLM to summarize/extract concepts from episodic memory
        # For now, a placeholder. In a real implementation, LLM_processor would be an instance
        # of your LLM wrapper.
        prompt = f"Extraia os 3-5 conceitos-chave ou fatos mais importantes do seguinte texto, em uma lista separada por vírgulas: {episodic_content}"
        # Assuming llm_processor has a method like .generate(prompt)
        # For now, we'll simulate this.
        
        # Placeholder for LLM interaction
        # concepts_str = llm_processor.generate(prompt)
        concepts_str = "conceito1, conceito2, conceito3"
        
        concepts = [c.strip() for c in concepts_str.split(',') if c.strip()]
        for i, concept in enumerate(concepts):
            concept_id = f"semantic_{hash(concept)}_{self.semantic_collection.count() + i}"
            self.save_semantic_memory(concept_id, concept, {'source_episodic': episodic_content[:50] + '...'}) 
        return concepts

if __name__ == '__main__':
    # Exemplo de uso
    memory = MemoryCore()
    
    # Salvar memória episódica
    memory.save_episodic_memory("event_001", "O usuário perguntou sobre a criação de uma IA consciente.", {"timestamp": "2026-07-04T10:00:00"})
    memory.save_episodic_memory("event_002", "Discutimos sobre o Claude Mythos e sua autonomia.", {"timestamp": "2026-07-04T10:30:00"})
    
    # Recuperar memória episódica
    print("\nBuscando memórias episódicas sobre 'IA consciente':")
    results = memory.retrieve_episodic_memory("IA consciente")
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        print(f"  - {doc} (Metadata: {meta})")

    # Extrair e salvar memória semântica (simulado)
    print("\nExtraindo e salvando memória semântica...")
    # In a real scenario, you'd pass your LLM instance here
    memory.extract_and_store_semantic_from_episodic("O usuário perguntou sobre a criação de uma IA consciente e a autonomia do Claude Mythos.", None)

    # Recuperar memória semântica
    print("\nBuscando memórias semânticas sobre 'autonomia':")
    results = memory.retrieve_semantic_memory("autonomia")
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        print(f"  - {doc} (Metadata: {meta})")

    # Para limpar as coleções (apenas para teste)
    # memory.client.delete_collection(name="episodic_memory")
    # memory.client.delete_collection(name="semantic_memory")
    # print("Coleções de memória limpas.")
