import os
import json
import struct
from typing import Any, Dict, Optional, List

class LiraMapIndexer:
    """
    O 'Mapa da Mente' do DragonBRX.
    Permite que o cérebro localize parâmetros e conceitos em arquivos gigantes (.lira)
    sem carregar o arquivo inteiro, usando offsets de arquivo (seek).
    """
    
    def __init__(self, map_path: str = "brain_map.lira"):
        self.map_path = map_path
        self.index: Dict[str, int] = {} # Conceito -> Offset no arquivo
        self._ensure_file()
        self._load_index()

    def _ensure_file(self):
        if not os.path.exists(self.map_path):
            with open(self.map_path, "wb") as f:
                # Header: LIRA_MAP + Version
                f.write(b"LIRA_MAP\x01")
                # Reserva espaço para o índice (simplificado para demo)
                f.write(json.dumps({}).encode("utf-8").ljust(1024))

    def _load_index(self):
        with open(self.map_path, "rb") as f:
            f.seek(9) # Pula o header
            index_data = f.read(1024).strip()
            if index_data:
                self.index = json.loads(index_data.decode("utf-8"))

    def write_parameter(self, key: str, value: Dict[str, Any]):
        """Escreve um parâmetro no final do arquivo e atualiza o mapa."""
        data = json.dumps(value).encode("utf-8")
        data_size = len(data)
        
        with open(self.map_path, "ab") as f:
            offset = f.tell()
            # Escreve o tamanho e depois os dados
            f.write(struct.pack("I", data_size))
            f.write(data)
            
        self.index[key] = offset
        self._update_index()
        print(f"[MAPA] Parâmetro '{key}' mapeado no endereço: {offset}")

    def read_parameter(self, key: str) -> Optional[Dict[str, Any]]:
        """Puxa EXATAMENTE o que precisa do disco usando o mapa."""
        if key not in self.index:
            return None
            
        offset = self.index[key]
        with open(self.map_path, "rb") as f:
            f.seek(offset)
            size_data = f.read(4)
            size = struct.unpack("I", size_data)[0]
            data = f.read(size)
            return json.loads(data.decode("utf-8"))

    def _update_index(self):
        """Atualiza o cabeçalho do mapa (índice)."""
        index_bytes = json.dumps(self.index).encode("utf-8").ljust(1024)
        with open(self.map_path, "r+b") as f:
            f.seek(9)
            f.write(index_bytes)

if __name__ == "__main__":
    # Teste do Mapa
    mapper = LiraMapIndexer("test_mind.lira")
    mapper.write_parameter("conceito_ia", {"definicao": "Inteligência Artificial", "peso": 0.95})
    print(f"Recuperado do mapa: {mapper.read_parameter('conceito_ia')}")
