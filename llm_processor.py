import requests
import json

class LLMProcessor:
    def __init__(self, model_name="llama3", ollama_url="http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.ollama_url = ollama_url
        print(f"LLMProcessor initialized with model '{self.model_name}' and Ollama URL '{self.ollama_url}'")

    def generate(self, prompt: str, system_message: str = "", temperature: float = 0.7, max_tokens: int = 500) -> str:
        headers = {"Content-Type": "application/json"}
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_message,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            response = requests.post(self.ollama_url, headers=headers, data=json.dumps(data), stream=True)
            response.raise_for_status() # Raise an exception for HTTP errors
            
            full_response_content = ""
            for chunk in response.iter_lines():
                if chunk:
                    decoded_chunk = json.loads(chunk.decode("utf-8"))
                    full_response_content += decoded_chunk.get("response", "")
                    if decoded_chunk.get("done"): # Check if the response is complete
                        break
            return full_response_content.strip()
        except requests.exceptions.ConnectionError:
            print(f"Erro: Não foi possível conectar ao Ollama em {self.ollama_url}. Certifique-se de que o Ollama está rodando e o modelo '{self.model_name}' está baixado.")
            return "[ERRO LLM: Ollama não acessível]"
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição Ollama: {e}")
            return f"[ERRO LLM: {e}]"
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON da resposta do Ollama: {e}")
            return f"[ERRO LLM: JSON inválido]"

if __name__ == '__main__':
    # Exemplo de uso (requer Ollama rodando localmente com o modelo 'llama3' baixado)
    # Para baixar o modelo: ollama run llama3
    llm = LLMProcessor(model_name="llama3")
    
    print("\nGerando resposta para um prompt simples:")
    response = llm.generate("Qual é a capital da França?")
    print(f"Resposta do LLM: {response}")

    print("\nGerando resposta com mensagem de sistema:")
    system_msg = "Você é um assistente de IA prestativo e conciso."
    response = llm.generate("Explique a fotossíntese em uma frase.", system_message=system_msg)
    print(f"Resposta do LLM: {response}")

    print("\nGerando resposta com temperatura mais alta (mais criativa):")
    response = llm.generate("Escreva um pequeno poema sobre o mar.", temperature=0.9, max_tokens=100)
    print(f"Resposta do LLM: {response}")
