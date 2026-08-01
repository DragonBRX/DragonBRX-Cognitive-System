import sys
import os

# Adiciona src ao path
sys.path.append(os.path.abspath("src"))

from lira_map_indexer import LiraMapIndexer
from intrinsic_learner import IntrinsicLearner

def run_lira_map_demo():
    print("=== DragonBRX: Demonstração do Mapa Lira e Aprendizado Intrínseco ===")
    
    # 1. Inicializa o Mapa (O arquivo pode ter gigabytes, mas o acesso é instantâneo)
    mapper = LiraMapIndexer("global_mind.lira")
    learner = IntrinsicLearner(mapper)
    
    # 2. Simula uma conversa (Aprendizado Real)
    print("\n[CONVERSA] Usuário: 'O DragonBRX usa parâmetros binários para mapear o conhecimento.'")
    learner.process_interaction("O DragonBRX usa parâmetros binários para mapear o conhecimento.", "Entendido.")
    
    print("\n[CONVERSA] Usuário: 'A autonomia é a base da inteligência.'")
    learner.process_interaction("A autonomia é a base da inteligência.", "Correto.")
    
    # 3. Puxa do Mapa (Endereçamento Direto)
    print("\n[MAPA] Puxando exatamente o que foi aprendido (sem carregar tudo):")
    for key in ["autonomia", "binários", "mapear"]:
        print(f"-> {learner.get_parameter_as_text(key)}")
        
    # 4. Transcrição de Parâmetros
    print("\n[TRANSCRIÇÃO] O formato .lira transcreve parâmetros para palavras:")
    param_ia = mapper.read_parameter("inteligência")
    if param_ia:
        print(f"Parâmetro 'inteligência' -> Categoria: {param_ia['categoria']}, Relevância: {param_ia['peso']*100}%")

    print("\n[SUCESSO] O DragonBRX provou que o tamanho não importa: o mapa guia o pensamento.")

if __name__ == "__main__":
    run_lira_map_demo()
