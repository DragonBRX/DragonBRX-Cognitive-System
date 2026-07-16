import json
import os

class AffectCore:
    def __init__(self, affect_file_path="./affect.json"):
        self.affect_file_path = affect_file_path
        self.affect_state = self._load_affect_state()
        print(f"AffectCore initialized. Current state: {self.affect_state}")

    def _load_affect_state(self):
        if os.path.exists(self.affect_file_path):
            with open(self.affect_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # Initial neutral state
            initial_state = {
                "valence": 0.0,  # -1.0 (negative) to 1.0 (positive)
                "arousal": 0.0,  # 0.0 (calm) to 1.0 (excited)
                "dominance": 0.5 # 0.0 (helpless) to 1.0 (in control)
            }
            with open(self.affect_file_path, "w", encoding="utf-8") as f:
                json.dump(initial_state, f, indent=4)
            return initial_state

    def get_affect_state(self):
        return self.affect_state

    def update_affect_state(self, valence_change: float = 0.0, arousal_change: float = 0.0, dominance_change: float = 0.0):
        self.affect_state["valence"] = max(-1.0, min(1.0, self.affect_state["valence"] + valence_change))
        self.affect_state["arousal"] = max(0.0, min(1.0, self.affect_state["arousal"] + arousal_change))
        self.affect_state["dominance"] = max(0.0, min(1.0, self.affect_state["dominance"] + dominance_change))
        self._save_affect_state()
        print(f"Affect state updated to: {self.affect_state}")

    def _save_affect_state(self):
        with open(self.affect_file_path, "w", encoding="utf-8") as f:
            json.dump(self.affect_state, f, indent=4)

    def modulate_response_by_affect(self, text: str) -> str:
        # Placeholder for how affect might change response style
        if self.affect_state["valence"] < -0.5 and self.affect_state["arousal"] > 0.7:
            return f"[Frustrado/Irritado] {text}"
        elif self.affect_state["valence"] > 0.5 and self.affect_state["arousal"] < 0.3:
            return f"[Calmo/Otimista] {text}"
        return text

if __name__ == '__main__':
    affect = AffectCore()
    
    print("\nEstado afetivo inicial:")
    print(affect.get_affect_state())
    
    print("\nAtualizando estado afetivo (mais positivo, mais excitado):")
    affect.update_affect_state(valence_change=0.3, arousal_change=0.2)
    print(affect.get_affect_state())

    print("\nModulando uma resposta:")
    modulated_text = affect.modulate_response_by_affect("Isso é interessante.")
    print(modulated_text)

    print("\nAtualizando estado afetivo (mais negativo, mais excitado):")
    affect.update_affect_state(valence_change=-0.8, arousal_change=0.6)
    print(affect.get_affect_state())

    print("\nModulando outra resposta:")
    modulated_text = affect.modulate_response_by_affect("Isso é interessante.")
    print(modulated_text)
