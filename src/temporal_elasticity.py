import time
import psutil
import os

class TemporalElasticity:
    """
    Gerencia o tempo de pensamento do DragonBRX.
    Se o processamento for baixo, ele estende o tempo (deliberação profunda).
    Se for alto, ele acelera (resposta rápida).
    """
    
    def __init__(self, base_delay: float = 1.0):
        self.base_delay = base_delay
        self.last_process_time = time.process_time()
        self.last_real_time = time.time()

    def get_deliberation_time(self) -> float:
        """Calcula o tempo necessário para o próximo ciclo baseado na carga do sistema."""
        cpu_usage = psutil.cpu_percent(interval=None)
        memory_usage = psutil.virtual_memory().percent
        
        # Fator de carga (0.0 a 1.0)
        load_factor = (cpu_usage + memory_usage) / 200.0
        
        # Se a carga for alta (> 80%), aumentamos o tempo de deliberação para não travar o dispositivo
        if load_factor > 0.4: # Equivalente a 80% de carga total
            multiplier = 2.0 + (load_factor * 5.0)
        else:
            multiplier = 1.0
            
        return self.base_delay * multiplier

    def simulate_thought_pause(self):
        """Simula a pausa de pensamento proporcional à complexidade e recursos."""
        delay = self.get_deliberation_time()
        if delay > self.base_delay:
            print(f"[ELASTICIDADE] Dispositivo sob carga. Deliberando por {delay:.2f}s para manter estabilidade...")
        time.sleep(delay)

if __name__ == "__main__":
    # Teste rápido
    te = TemporalElasticity(base_delay=0.5)
    print(f"Tempo de deliberação sugerido: {te.get_deliberation_time():.2f}s")
