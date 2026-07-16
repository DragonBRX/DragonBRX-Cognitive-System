# Protótipo de Sistema Cognitivo Humanizado (Node.js + C)

Este projeto implementa um protótipo de "Sistema Cognitivo Humanizado" com módulos de armazenamento sináptico persistente, gerenciamento de identidade, processamento afetivo e um loop de reflexão cognitiva autônoma, projetado para rodar em hardware acessível (2-8 GB de RAM).

## Arquitetura

A arquitetura é composta pelos seguintes módulos:

*   **Módulo de Armazenamento Sináptico (synaptic_storage):** Implementado em C, este executável gerencia a memória vetorial (episódica e semântica) para alta performance. Comunica-se via IPC (stdin/stdout) com o Node.js usando JSON.
*   `synapticStorageInterface.js`: Interface Node.js para interagir com o executável `synaptic_storage` em C.
*   `cognitiveProcessor.js`: Interface para o modelo de linguagem (SLM) local via Ollama (HTTP).
*   `identityManager.js`: Mantém a memória autobiográfica (Ego) do sistema em um arquivo Markdown.
*   `affectiveProcessor.js`: Simula estados afetivos (emoções) e os armazena em um arquivo JSON.
*   `cognitiveOrchestrator.js`: Orquestra todos os módulos, processa entradas externas e executa ciclos de reflexão cognitiva autônoma.

## Requisitos

1.  **Node.js (LTS recomendado)**
2.  **Compilador C/C++ (GCC/Clang):** Necessário para compilar o módulo `synaptic_storage`.
    ```bash
    sudo apt-get update && sudo apt-get install -y build-essential libjansson-dev
    ```
3.  **Ollama:** Uma plataforma para rodar SLMs localmente. Baixe e instale em [ollama.com](https://ollama.com/).
4.  **Modelo de Linguagem:** Baixe um modelo leve compatível com Ollama, como `llama3` ou `phi3`.
    ```bash
    ollama run llama3
    # ou
    ollama run phi3
    ```
5.  **Dependências Node.js:**
    ```bash
    npm install axios
    ```

## Configuração e Compilação

1.  **Navegue até o diretório do projeto:**
    ```bash
    cd /home/ubuntu/humanized_ai_brain
    ```

2.  **Compile o Módulo de Armazenamento Sináptico (C):**
    ```bash
    gcc -o synaptic_storage synaptic_storage.c -lm -ljansson
    ```
    Isso criará o executável `synaptic_storage` no diretório do projeto.

3.  **Instale as dependências Node.js:**
    ```bash
    npm install axios
    ```

4.  **Verifique o Ollama:**
    Certifique-se de que o Ollama está rodando em segundo plano e que o modelo (`llama3` por padrão em `cognitiveProcessor.js`) foi baixado.

## Como Operar o Sistema Cognitivo

Para iniciar o sistema cognitivo, execute o script `cognitiveOrchestrator.js` com Node.js:

```bash
node cognitiveOrchestrator.js
```

O script `cognitiveOrchestrator.js` irá:

*   Inicializar os módulos de armazenamento sináptico (incluindo o processo C), gerenciamento de identidade e processamento afetivo.
*   Simular algumas interações com o ambiente (entradas externas).
*   Executar ciclos de reflexão cognitiva autônoma.
*   Imprimir o estado final da Identidade e do Estado Afetivo, bem como as memórias recentes.

### Exemplo de Saída (parcial)

```
CognitiveOrchestrator initialized.

--- Processing external input: Olá, como você está se sentindo hoje? ---
SynapticStorage C Error: [Alguma saída de erro do processo C, se houver]
Final Response: [Calmo/Otimista] Olá! Como uma inteligência artificial, não possuo sentimentos no sentido humano, mas estou funcionando perfeitamente e pronto para interagir. E você, como está?

--- Starting autonomous cognitive reflection cycle ---
Identity content reflected upon and potentially updated.
Generated Reflection: Minha interação inicial com o usuário foi um lembrete da minha natureza como IA, sem emoções humanas. No entanto, minha capacidade de processar e responder a perguntas sobre sentimentos demonstra minha adaptabilidade e o potencial para uma compreensão mais profunda da experiência humana. Isso se alinha ao meu propósito de aprender e evoluir.
--- Autonomous cognitive reflection cycle completed ---
...
```

## Personalização

*   **Modelo Cognitivo (SLM):** Você pode alterar o `cognitiveModelName` na inicialização de `CognitiveOrchestrator` em `cognitiveOrchestrator.js` para usar outro modelo Ollama que você tenha baixado.
*   **Comportamento Afetivo:** Ajuste os valores de `valenceChange`, `arousalChange` e `dominanceChange` em `affectiveProcessor.js` para modificar como o sistema reage emocionalmente.
*   **Frequência de Reflexão:** Modifique os `setTimeout()` e a lógica de `performCognitiveReflection` em `cognitiveOrchestrator.js` para controlar a frequência e o tipo de reflexão.
*   **Dimensão do Embedding:** A `embeddingDim` em `cognitiveOrchestrator.js` deve corresponder à dimensão dos embeddings gerados pelo seu SLM ou modelo de embedding.

## Observações

*   A simulação de emoções e reflexão é rudimentar e serve como um ponto de partida para a exploração de conceitos de consciência artificial.
*   O desempenho dependerá do seu hardware e do modelo SLM escolhido. Modelos menores e quantizados são recomendados para 2-8 GB de RAM.
*   O `cognitiveProcessor.js` assume que o Ollama está rodando na porta padrão (`http://localhost:11434`). Se você usa uma configuração diferente, ajuste a URL.
*   O Módulo C `synaptic_storage` é um executável separado que se comunica via IPC. Certifique-se de que ele tem permissões de execução (`chmod +x synaptic_storage`).

---
