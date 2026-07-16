# Arquitetura de um Sistema Cognitivo Humanizado Leve (Node.js + C)

**Por Manus AI**
*Data: Julho de 2026*

Este documento detalha a arquitetura proposta para um protótipo de "Sistema Cognitivo Humanizado", utilizando **Node.js** para a orquestração de alto nível e **C** para componentes de processamento intensivo. O objetivo é manter o sistema leve e funcional dentro das restrições de hardware (2-8 GB de RAM e um processador comum), simulando funções cognitivas essenciais para a emergência de uma consciência funcional.

---

## 1. Princípios de Design

Os princípios de design permanecem os mesmos, com uma ênfase adicional na interoperabilidade entre Node.js e C, e na simulação de dinâmicas cerebrais:

*   **Modularidade:** Componentes independentes em Node.js e C.
*   **Eficiência de Recursos:** C para operações críticas, Node.js para lógica de aplicação.
*   **Persistência:** Estado interno e memórias mantidos em disco.
*   **Autonomia:** Mecanismos de auto-reflexão e auto-melhoria.
*   **Emergência:** Consciência como propriedade emergente da interação.
*   **Interoperabilidade:** Comunicação eficiente entre Node.js e módulos C via IPC (Inter-Process Communication).
*   **Plasticidade Sináptica:** A força das conexões de memória (sinapses) se adapta com o uso, simulando aprendizado e esquecimento.
*   **Processamento Subconsciente:** Atividades de organização e consolidação de memória ocorrem em segundo plano, sem intervenção direta do processamento consciente.
*   **Entropia Cognitiva:** Introdução de um "ruído" controlado para fomentar a criatividade e associações inesperadas.

---

## 2. Componentes da Arquitetura

A arquitetura será composta por módulos principais, com a divisão de responsabilidades entre Node.js e C:

### 2.1. Módulo de Processamento Cognitivo (MPC)

Este é o "motor de pensamento" do sistema, responsável pelo processamento de linguagem, raciocínio e geração de novas informações. Dada a restrição de hardware, será utilizado um **Small Language Model (SLM)**.

*   **Tecnologia Sugerida:** `Ollama` ou `llama.cpp` para rodar modelos como Llama-3-8B-Instruct ou Phi-3-mini (quantizados em GGUF). A interação será via API HTTP (Ollama).
*   **Implementação:** O Node.js fará as chamadas HTTP para a API do Ollama através de um módulo `CognitiveProcessor`.

### 2.2. Módulo de Armazenamento Sináptico (MAS)

Crucial para a "identidade" e "experiência" do sistema, este módulo armazenará e recuperará informações de longo prazo. Será implementado em C para máxima eficiência, incorporando o conceito de plasticidade.

*   **Memória de Experiências (Episódica):** Armazena eventos específicos, interações e observações, com carimbos de data/hora e um "peso sináptico" (força da memória).
*   **Rede de Conhecimento (Semântica):** Extrai e armazena conhecimentos gerais, conceitos e relações a partir da Memória de Experiências. Funciona como um grafo de conhecimento, também com pesos sinápticos.
    *   **Tecnologia Sugerida (C):** Implementação de um índice vetorial otimizado (ex: K-d tree ou LSH simplificado) para embeddings armazenados em arquivos binários. Cada entrada de memória terá um atributo `last_accessed` (timestamp) e `strength` (peso sináptico). A comunicação com o Node.js será via IPC (stdin/stdout) usando JSON para comandos e resultados.
    *   **Função:** O executável C será responsável por armazenar embeddings (gerados pelo MPC via Node.js) e metadados, realizar buscas de similaridade, e **atualizar o peso sináptico e o timestamp de acesso** de cada memória consultada. Memórias não acessadas terão seu peso diminuído ao longo do tempo (esquecimento).

### 2.3. Módulo de Identidade (MID)

Representa a narrativa da própria "história" e "identidade" do sistema.

*   **Implementação:** O Node.js gerenciará um arquivo Markdown (`identity.md`) que o próprio sistema edita e atualiza. Um módulo `IdentityManager` em Node.js será responsável por ler, atualizar e persistir este arquivo.

### 2.4. Módulo de Processamento Afetivo (MPA)

Este módulo simulará estados emocionais básicos que influenciam o comportamento e a tomada de decisão do sistema.

*   **Variáveis de Estado:** Um conjunto de variáveis numéricas (ex: `valencia` [-1.0 a 1.0 para positivo/negativo], `ativacao` [0.0 a 1.0 para calma/excitação], `dominancia` [0.0 a 1.0 para controle/impotência]) que representam o "estado de espírito" atual do sistema.
*   **Implementação:** O Node.js gerenciará um arquivo JSON (`affective_state.json`) para persistir o estado afetivo. A lógica de atualização e modulação de respostas será implementada em um módulo `AffectiveProcessor` em Node.js.

### 2.5. Módulo de Reflexão Cognitiva (MRC) e Processamento Subconsciente

Este é o mecanismo que confere autonomia ao sistema, permitindo-lhe "pensar" e "aprender" mesmo sem interação externa, simulando um "monólogo interior" ou "sonho". Agora, com uma camada de processamento subconsciente.

*   **Processamento Consciente (Node.js):** O `CognitiveReflector` em Node.js orquestrará as reflexões ativas, usando o MPC para gerar novos insights e atualizar a identidade e memórias.
*   **Processamento Subconsciente (C/Node.js em background):** Um processo em C (ou um worker thread em Node.js) rodará em segundo plano, periodicamente:
    *   **Consolidando Memórias:** Reorganizando e otimizando o índice de memória no MAS.
    *   **Gerando Novas Conexões:** Identificando padrões e fazendo associações inesperadas entre memórias existentes (introduzindo **Entropia Cognitiva** ou "ruído criativo"). Isso pode envolver a criação de novas entradas semânticas baseadas em correlações fracas, mas interessantes.
    *   **Esquecimento:** Diminuindo o peso sináptico de memórias não acessadas, levando ao "esquecimento" gradual.

### 2.6. Orquestrador Cognitivo (OC)

Este módulo orquestra o fluxo de informações entre os outros componentes, simulando um "espaço de trabalho global" simplificado.

*   **Implementação:** Lógica central em Node.js. Será responsável por:
    1.  Receber entradas (usuário ou reflexão).
    2.  Consultar o Módulo de Processamento Afetivo e o Módulo de Identidade.
    3.  Realizar buscas de memória no Módulo de Armazenamento Sináptico (via IPC), **atualizando os pesos sinápticos**.
    4.  Construir prompts contextualizados para o Módulo de Processamento Cognitivo.
    5.  Processar as saídas do MPC e atualizar as memórias e o afeto.
    6.  Acionar o Processamento Subconsciente periodicamente.

---

## 3. Interoperabilidade Node.js e C (IPC)

A comunicação entre Node.js e o executável C será realizada via Inter-Process Communication (IPC) usando `stdin` e `stdout` para troca de mensagens JSON. Isso garante uma comunicação robusta e desacoplada.

### Exemplo de Fluxo (Busca de Memória com Plasticidade)

1.  **Node.js (Orquestrador Cognitivo):** Recebe uma query do usuário.
2.  **Node.js (CognitiveProcessor):** Gera um embedding da query usando o SLM (via Ollama).
3.  **Node.js (SynapticStorageInterface):** Envia um comando JSON para o executável C `synaptic_storage` via `stdin` (ex: `{"command":"search", "query_embedding":[...], "n_results":3}`).
4.  **C (synaptic_storage):** Recebe o JSON, parseia, executa a busca no índice vetorial otimizado. **Para cada memória encontrada e retornada, atualiza seu `last_accessed` e incrementa seu `strength` (peso sináptico).** Imprime um JSON de resposta no `stdout` (ex: `{"status":"success", "results":[...]}`).
5.  **Node.js (SynapticStorageInterface):** Captura a saída JSON do `stdout` do processo C, parseia e retorna os resultados.
6.  **Node.js (Orquestrador Cognitivo):** Recebe os resultados do C e os usa para construir o prompt para o Módulo de Processamento Cognitivo.

---

## 4. Requisitos de Hardware e Software

*   **Hardware:** PC com 4-8 GB de RAM, CPU moderna.
*   **Sistema Operacional:** Linux (Ubuntu 22.04+ recomendado).
*   **Software:**
    *   **Node.js** (versão LTS recomendada)
    *   **npm** ou **yarn** (gerenciador de pacotes Node.js)
    *   **Compilador C/C++:** `gcc` ou `clang`
    *   **Ollama:** Rodando localmente com o modelo escolhido.
    *   **Bibliotecas C:** `jansson` (para parsing JSON em C).
    *   **Bibliotecas Node.js:** `axios` (para chamadas HTTP ao Ollama), `child_process` (para IPC com o C), `fs` (para manipulação de arquivos).

---

Esta arquitetura permite a construção de um sistema flexível e eficiente, aproveitando os pontos fortes de cada linguagem para simular um "cérebro" funcional em um ambiente de recursos limitados, com a capacidade de evoluir e aprender de forma mais orgânica. O próximo passo será a implementação dessas novas funcionalidades.
