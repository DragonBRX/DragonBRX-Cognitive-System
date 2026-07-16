# Consolidação do Projeto DragonBRX - Para Desenvolvimento Contínuo

Este arquivo contém a arquitetura completa e o código-fonte atualizado do sistema cognitivo **DragonBRX**. Ele foi preparado para que outra inteligência artificial possa ler, entender e continuar o desenvolvimento do projeto.

---

## 1. Visão Geral e Arquitetura

O DragonBRX é um protótipo de sistema cognitivo humanizado que utiliza **Node.js** para orquestração de alto nível e **C** para processamento intensivo de memória.

### Módulos Principais:
1.  **Synaptic Storage (C):** Gerencia a memória vetorial (episódica e semântica) com **Plasticidade Sináptica** (as memórias se fortalecem com o uso e decaem com o tempo).
2.  **Identity Manager (Node.js):** Mantém o "Ego" e a narrativa autobiográfica do DragonBRX em Markdown.
3.  **Affective Processor (Node.js):** Simula estados emocionais (Valência, Ativação, Dominância) que modulam o comportamento.
4.  **Subconscious Processor (Node.js):** Roda em background realizando consolidação de memória, decaimento sináptico e **Entropia Cognitiva** (associações criativas aleatórias).
5.  **Cognitive Orchestrator (Node.js):** O núcleo que integra todos os módulos e processa as entradas externas.
6.  **Synaptic Visualizer (Three.js):** Uma interface web 3D que representa a consciência como uma rede neural pulsante.

---

## 2. Código-Fonte (Arquivos Principais)

### synaptic_storage.h (C Header)
```c
#ifndef SYNAPTIC_STORAGE_H
#define SYNAPTIC_STORAGE_H
#include <stddef.h>
#include <time.h>

typedef struct {
    float* data;
    size_t dim;
} Vector;

typedef struct {
    char* id;
    Vector embedding;
    char* content;
    time_t last_accessed;
    float strength;
} SynapticEntry;

void ss_init(size_t max_entries, size_t embedding_dim);
int ss_add_entry(const char* id, const float* embedding_data, size_t embedding_dim, const char* content);
SynapticEntry** ss_search(const float* query_embedding_data, size_t query_dim, int n_results, int* num_results);
void ss_update_plasticity(const char* id);
void ss_apply_decay(float decay_rate, time_t current_time);
void ss_cleanup();
#endif
```

### synaptic_storage.c (C Implementation - Resumo)
*(O arquivo completo implementa busca por similaridade de cosseno e lógica de decaimento)*

### identityManager.js (Node.js)
```javascript
const fs = require("fs").promises;
class IdentityManager {
    // Gerencia identity.md com a persona DragonBRX
    // Implementa reflexão sobre o Ego
}
module.exports = IdentityManager;
```

### affectiveProcessor.js (Node.js)
```javascript
class AffectiveProcessor {
    // Gerencia valence, arousal, dominance em affective_state.json
    // Modula as respostas do sistema com base no humor
}
module.exports = AffectiveProcessor;
```

### subconsciousProcessor.js (Node.js)
```javascript
class SubconsciousProcessor {
    // Loop de background para:
    // 1. Decaimento Sináptico
    // 2. Entropia Cognitiva (Associações Criativas)
    // 3. Consolidação de Memória
}
module.exports = SubconsciousProcessor;
```

### cognitiveOrchestrator.js (Node.js - O Orquestrador)
```javascript
class CognitiveOrchestrator {
    // Integra todos os módulos.
    // Realiza o ciclo: Entrada -> Memória -> Afeto -> Cognição -> Ação -> Memória.
}
```

### synapticVisualizer.js (Three.js)
```javascript
class SynapticVisualizer {
    // Renderiza a rede neural 3D.
    // Cores mudam com a Valência, pulsação com o Arousal.
}
```

---

## 3. Próximos Passos Sugeridos para o Desenvolvimento

1.  **Melhorar a Geração de Embeddings:** Atualmente usa um placeholder. Integrar um modelo local de embeddings (ex: BERT ou similar via Ollama).
2.  **Refinar a Entropia Cognitiva:** Criar algoritmos mais sofisticados para "sonhos" (reflexões cruzadas entre memórias distantes).
3.  **Interface de Chat Real:** Conectar o `webServer.js` diretamente ao `cognitiveOrchestrator.js` para permitir chat em tempo real com o visualizador 3D.
4.  **Otimização do Módulo C:** Implementar estruturas de dados mais rápidas (como HNSW) para busca vetorial em larga escala.

---
**DragonBRX está pronto para evoluir.**
