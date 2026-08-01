# Lira: Formato Binário Evolutivo para Agentes de IA

O **Lira** (`.lira`) é um ecossistema de execução híbrida e um formato de contêiner binário projetado para agentes de inteligência artificial que necessitam de aprendizado contínuo e alta performance.

## Arquitetura Técnica

O Lira utiliza uma abordagem multi-linguagem para maximizar a eficiência do hardware:
- **Performance**: Rust e C++ garantem acesso de baixa latência e processamento matemático otimizado.
- **Escalabilidade**: Go gerencia a sincronização de estados em rede.
- **Flexibilidade**: Python orquestra a lógica e integrações.

## Diferenciais do Formato

1.  **Evolução Recursiva**: O agente pode realizar ciclos autônomos de pesquisa e auto-atualização de parâmetros.
2.  **Eficiência em Nuvem**: Otimizado para execução de longa duração em ambientes como Google Colab.
3.  **Aprendizado em Tempo Real**: Atualização de parâmetros durante a inferência sem reescrita total.
4.  **Expansão Dinâmica**: Crescimento orgânico do arquivo conforme novas habilidades são integradas.
5.  **Transparência Categórica**: Organização semântica do conhecimento para auditoria e tradução.
6.  **Acesso Zero-Copy**: Uso de `mmap` para máxima eficiência de memória RAM.
7.  **Protocolo de Injeção Aberta (LKIF)**: Formato aberto (JSONL) que permite que *outros modelos* — não apenas o runtime que criou o arquivo — leiam e escrevam conhecimento declarativo (pares pergunta/resposta) diretamente nas categorias semânticas do agente, com proveniência obrigatória e deduplicação automática. Ver Seção 3.6 de `lira_final_spec.md`.
8.  **Compilador de Conhecimento (palavras → parâmetros)**: O conhecimento injetado via LKIF começa como texto puro. O `KnowledgeCompiler` treina, por regressão de Ridge em forma fechada, um adaptador auxiliar de recuperação associativa (`W`) que mapeia pergunta → resposta no espaço vetorizado, e grava esse parâmetro binário no `.lira` — sem precisar de acesso aos gradientes de nenhum LLM. A matriz `W` tem tamanho fixo; `answer_vectors`, payloads e índices crescem conforme a quantidade de conhecimento ativo. Ver Seção 3.7 de `lira_final_spec.md`.

### Nota sobre uma tentativa que NÃO deu certo (documentada por transparência)

Foi testada uma arquitetura de "biblioteca" com dois formatos — um catálogo
legível (texto) e um cofre de parâmetros treinados (LSA: TF-IDF + SVD) —
na tentativa de tornar o conhecimento tão eficiente quanto pesos de rede
neural, mas ainda traduzível. Testado em escala real (20, 40 e 80 fatos):
o cofre ficou entre **7x e 25x mais pesado que simplesmente comprimir o
texto com gzip**, e sua acurácia caía conforme o corpus crescia, só
recuperando com mais dimensões latentes — o que piorava ainda mais o
tamanho. Não foi encontrado nenhum ponto de operação onde a técnica fosse
simultaneamente menor E mais confiável que compressão simples. Por isso,
**a recomendação de produção é comprimir a seção `knowledge` com
zlib/zstd**, não usar o cofre LSA. Código do experimento preservado em
`lira_library_compiler.py` para referência futura (ex: se um dia houver
acesso a embeddings neurais reais, pré-treinados).

## Estrutura do Repositório

- `bin/lira`: Executor unificado para arquivos `.lira`.
- `src/core/`: Implementação do núcleo de segurança e memória (Rust).
- `src/numerical/`: Processamento de tensores e GPU (C++/CUDA).
- `src/sync/`: Sincronização e rede (Go).
- `src/logic/`: Orquestração e lógica de estado (Python).
  - `lira_binary.py`: implementação binária real do container (superbloco, mmap, commit dual-slot).
  - `lira_open_injection.py`: Protocolo de Injeção Aberta — leitura/escrita de conhecimento em formato LKIF.
- `lira_final_spec.md`: Especificação técnica detalhada do formato.
- `lkif_schema.json`: Schema JSON formal (draft 2020-12) de uma entrada de conhecimento LKIF.
- `exemplo_conhecimento.lkif.jsonl`: Exemplo de arquivo de intercâmbio que qualquer modelo pode gerar como texto puro.

## Como Utilizar

O executor permite carregar e interagir com o estado de um agente:

```bash
lira run agente.lira
lira info agente.lira
lira verify agente.lira
```

### Protocolo de Injeção Aberta (cross-model)

```bash
# Ver o que já foi ensinado (evita redundância antes de injetar)
lira read-knowledge agente.lira
lira read-knowledge agente.lira programacao/python

# Um outro modelo escreve conhecimento em texto puro (.jsonl) seguindo
# lkif_schema.json, e você injeta no container:
lira inject agente.lira novo_conhecimento.lkif.jsonl

# Exporta o conhecimento acumulado para outro modelo ler:
lira export-knowledge agente.lira saida.jsonl

# Gera o schema formal para qualquer ferramenta validar seu próprio JSONL:
lira schema lkif_schema.json
```

### Compilador de Conhecimento (palavras → parâmetros)

```bash
# Treina um adaptador real (Ridge) sobre o texto de uma categoria e grava
# como parâmetro binário no .lira. Parâmetros padrão: n_features=256, ridge_lambda=1.0
lira compile-knowledge agente.lira programacao/python

# Compila todas as categorias que ainda estão só em texto
lira compile-all-knowledge agente.lira

# Consulta o PARÂMETRO treinado (inferência, não busca em texto)
lira query-knowledge agente.lira programacao/python "explica o que é generator"
```

Via API Python:

```python
from lira_binary import LiraBinary
from lira_open_injection import OpenInjectionProtocol
from lira_knowledge_compiler import KnowledgeCompiler

lb = LiraBinary("agente.lira")
oip = OpenInjectionProtocol(lb)
compiler = KnowledgeCompiler(lb)  # n_features=256, ridge_lambda=1.0 por padrão

report = compiler.compile_category("programacao/python", oip)
print(report)  # bytes ativos/órfãos, tensores, payload, ajuste médio (cosseno), etc.

resultado = compiler.query("programacao/python", "explica o que é generator")
```

Via API Python:

```python
from lira_binary import LiraBinary
from lira_open_injection import OpenInjectionProtocol

lb = LiraBinary("agente.lira")
oip = OpenInjectionProtocol(lb)

# 1. Ler antes de escrever
print(oip.read_category("fisica/mecanica_quantica"))

# 2. Injetar conhecimento novo, com proveniência obrigatória
oip.inject(
    category="fisica/mecanica_quantica",
    question="O que é o princípio da incerteza de Heisenberg?",
    answer="...",
    source_model="Claude Sonnet 5",
    confidence=0.95,
)
```

Este projeto foca na criação de um padrão técnico robusto e eficiente para a próxima geração de agentes inteligentes.
