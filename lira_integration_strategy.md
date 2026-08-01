# Estratégia de Integração DragonBRX + Lira (.lira)

## 1. Visão Geral
A integração transforma o DragonBRX em uma **Arquitetura Cognitiva Geral Autoevolutiva Persistente (P-SE-GCA)**. O estado cognitivo deixa de ser apenas um JSON em memória e passa a ser um container binário `.lira` com suporte a:
- **Acesso Zero-Copy (mmap)**: Eficiência de memória.
- **Atomicidade**: Dual-slot commits para evitar corrupção de dados.
- **Integridade**: Verificação de hashes (SHA-256/512) em cada leitura.
- **Evolução Paramétrica**: Compilação de conhecimento (texto) em parâmetros binários (Ridge Regression).

## 2. Mapeamento de Componentes
| DragonBRX (Original) | Lira (.lira) | Função na Integração |
|---|---|---|
| `CognitiveFabric` | `LiraBinary` + `LiraCore` | O motor de decisão agora escreve no container binário. |
| `perceive` | `Experiences` | Cada percepção vira um evento na seção de experiências do `.lira`. |
| `choose` | `CognitiveChain` | Cada decisão registra um `CognitiveStep` na linhagem do `.lira`. |
| `PromptSystem` | `Skills` | Receitas e planos são versionados como Skills no Atlas. |
| `KnowledgeBase` | `LKIF` + `KnowledgeCompiler` | Conhecimento web é injetado via LKIF e compilado em `W` (pesos). |

## 3. Estrutura do Arquivo .lira
O arquivo binário conterá:
- **Superblock**: Controle de versão e slots de commit.
- **Model Base**: Pesos base (imutáveis).
- **Modules**: Deltas e LoRA adapters aprendidos.
- **Metadata (JSON)**: Categorias, Skills, Memória (RAG), Experiências e Linhagem Cognitiva.

## 4. Próximos Passos
1. **Migrar `CognitiveFabric`**: Alterar para que use `LiraBinary` como backend de persistência.
2. **Implementar `Atlas de Skills`**: Converter as 1.600+ skills para o formato de namespace `skill:<namespace>/<domain>/<name>`.
3. **Ativar o `KnowledgeCompiler`**: Permitir que o DragonBRX compile o que aprendeu na web em parâmetros binários.
