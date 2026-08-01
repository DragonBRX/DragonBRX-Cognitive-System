
import numpy as np
from lira_binary import LiraBinary
import os

def generate_example():
    print("Gerando arquivo de exemplo .lira...")
    
    # Pesos base fictícios
    base_weights = {
        "layer1.weight": np.random.randn(128, 128).astype(np.float32),
        "layer1.bias": np.zeros(128).astype(np.float32),
        "layer2.weight": np.random.randn(64, 128).astype(np.float32),
        "layer2.bias": np.zeros(64).astype(np.float32),
    }
    
    output_path = "projeto_exemplo.lira"
    
    # Se já existir, remove
    if os.path.exists(output_path):
        os.remove(output_path)
        
    # Cria o contêiner binário
    lira = LiraBinary.create(
        path=output_path,
        base_weights=base_weights,
        quantization="fp16",
        arch="transformer"
    )
    
    print(f"Arquivo '{output_path}' criado com sucesso!")
    print(f"Tamanho do arquivo: {os.path.getsize(output_path)} bytes")

if __name__ == "__main__":
    generate_example()
