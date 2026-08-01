import sys
import io
import json
import random
from typing import Any, Dict, List, Optional
from pathlib import Path

# Adiciona o diretório src ao path para importar os módulos locais
sys.path.insert(0, str(Path(__file__).parent))

from cognitive_fabric import CognitiveFabric, Action
from interpreter import BRXInterpreter

class SynapticLearningLab:
    """
    Ambiente de experimentação onde o DragonBRX testa combinações de tokens
    para aprender o significado de comandos e atingir objetivos sozinho.
    """
    
    def __init__(self, core: CognitiveFabric):
        self.core = core
        self.interpreter = BRXInterpreter()
        self.vocabulary = ["run", "out", '"Olá"', "var", "end"] # Conceitos iniciais
        self.history = []

    def teach_concept(self, concept: str, meaning: str):
        """Ensina o 'significado' de um conceito adicionando-o à rede sináptica."""
        print(f"[LAB] Ensinando conceito: '{concept}' significa '{meaning}'")
        self.core.perceive("teaching", {"concept": concept, "meaning": meaning}, salience=1.0)
        if concept not in self.vocabulary:
            self.vocabulary.append(concept)

    def run_experiment(self, goal_description: str, target_output: str):
        """
        O DragonBRX tenta gerar código até que a saída do interpretador 
        corresponda ao target_output.
        """
        print(f"\n[LAB] Novo Objetivo: {goal_description}")
        print(f"[LAB] Resultado esperado: '{target_output}'")
        
        goal = self.core.add_goal(goal_description, desired=[target_output, "sucesso"], priority=1.0)
        
        attempts = 0
        max_attempts = 20
        success = False
        
        while attempts < max_attempts and not success:
            attempts += 1
            # O sistema "pensa" em uma combinação baseada no que sabe
            # Aqui simulamos a geração experimental baseada em ativação sináptica
            trial_code = self._generate_trial_code()
            
            print(f"[Tentativa {attempts}] Código: {trial_code}")
            
            # Captura a saída do interpretador
            output = self._test_code(trial_code)
            print(f"       Saída: '{output}'")
            
            if output.strip() == target_output:
                print(f"[LAB] SUCESSO! O sistema aprendeu a sequência correta.")
                # Reforço positivo: aprende o resultado
                self.core.learn_outcome(
                    Action("experiment", "testar_codigo", "coding", expected=[target_output, "sucesso"]),
                    success=1.0,
                    evidence={"code": trial_code, "output": output}
                )
                success = True
            else:
                # Reforço negativo/ajuste: aprende que essa combinação não serviu
                self.core.learn_outcome(
                    Action("experiment", "testar_codigo", "coding", expected=[target_output]),
                    success=0.0,
                    evidence={"code": trial_code, "output": output}
                )
        
        if not success:
            print("[LAB] O sistema não conseguiu atingir o objetivo nesta sessão.")
        
        return success

    def _generate_trial_code(self) -> str:
        """
        Gera código experimental simulando a ativação sináptica.
        O sistema tenta combinar conceitos que foram ensinados.
        """
        # O sistema aprendeu que programas precisam de 'run'
        code = 'run "experiment"\n'
        
        # Simula a "escolha" baseada em probabilidade de conceitos ensinados
        # Quanto mais o sistema falha, mais ele tenta variações
        potential_commands = [v for v in self.vocabulary if v not in ["run", '"Olá"', '"Mundo"']]
        potential_values = [v for v in self.vocabulary if '"' in v]
        
        if not potential_commands:
            return code + random.choice(self.vocabulary)

        cmd = random.choice(potential_commands)
        val = random.choice(potential_values) if potential_values else ""
        
        # Simula o erro comum de iniciante: esquecer o valor ou usar o comando errado
        dice = random.random()
        if dice < 0.3:
            code += f"{cmd}" # Comando sem valor (erro)
        elif dice < 0.6:
            code += f"{val}" # Valor sem comando (erro)
        else:
            code += f"{cmd} {val}" # Estrutura correta (aprendizado)
            
        return code

    def _test_code(self, code: str) -> str:
        """Executa o código e retorna a saída do console."""
        old_stdout = sys.stdout
        new_stdout = io.StringIO()
        sys.stdout = new_stdout
        
        try:
            # O interpretador do DragonBRX imprime no stdout
            self.interpreter.run(code)
            result = new_stdout.getvalue()
        except Exception as e:
            result = f"Error: {str(e)}"
        finally:
            sys.stdout = old_stdout
            
        return result.strip()

if __name__ == "__main__":
    # Demonstração do ciclo de aprendizado
    core = CognitiveFabric()
    lab = SynapticLearningLab(core)
    
    # 1. Ensinar significados
    lab.teach_concept("run", "iniciar programa")
    lab.teach_concept("out", "mostrar mensagem")
    lab.teach_concept('"Olá"', "texto de saudação")
    
    # 2. Deixar o sistema testar sozinho até acertar o primeiro desafio
    lab.run_experiment("Mostrar a saudação 'Olá' no console", "Olá")
    
    # 3. Novo desafio: O sistema deve usar o que aprendeu para um novo texto
    lab.teach_concept('"Mundo"', "o mundo inteiro")
    lab.run_experiment("Mostrar a mensagem 'Mundo' no console", "Mundo")
