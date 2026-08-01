# Lira Specification 3.0: Formato Binário Evolutivo Multi-linguagem

## 1. Introdução
O formato `.lira` é um contêiner binário projetado para armazenar o estado completo de agentes de inteligência artificial. Ele se diferencia de formatos estáticos pela sua capacidade de atualização incremental, aprendizado em tempo real e execução híbrida multi-linguagem.

## 2. Arquitetura do Executor
O Executor Lira opera através de uma federação de linguagens, otimizando cada tarefa para o ambiente de execução mais eficiente:
- **Core (Rust)**: Gerenciamento de memória, segurança de threads e acesso via `mmap` (zero-copy).
- **Numerical (C++/CUDA)**: Processamento de tensores, operações matemáticas de alta performance e inferência em GPU.
- **Sync (Go)**: Comunicação em rede, sincronização de estados e atualizações assíncronas.
- **Logic (Python)**: Orquestração de alto nível e interface de integração.

## 3. Funcionalidades Técnicas

### 3.1. Aprendizado em Tempo Real (Live State Update)
O formato permite que novos parâmetros (deltas e adaptadores LoRA) sejam gerados e anexados ao arquivo binário durante o processo de inferência. Isso possibilita que o agente acumule conhecimento de forma persistente sem a necessidade de reescrever o modelo base.

### 3.2. Expansão Dinâmica e Evolução Recursiva
O contêiner `.lira` é estruturado para permitir o crescimento orgânico e a **Evolução de Estado Recursiva**. O runtime permite que o agente execute ciclos autônomos de pesquisa e síntese de informação, convertendo novos conhecimentos em parâmetros binários e habilidades procedurais que são anexadas dinamicamente ao arquivo.

### 3.3. Otimização para Ambientes de Nuvem
O formato é projetado para ser ultra-leve e eficiente, facilitando a execução em ambientes como Google Colab. Através da gestão híbrida de memória, o `.lira` permite processos de aprendizado autodidata de longa duração com baixo consumo de recursos computacionais.

### 3.4. Transparência Categórica e Auditabilidade
Diferente de formatos monolíticos, o `.lira` organiza o conhecimento aprendido em **Categorias Semânticas**. 
- **Mapeamento de Aprendizado**: Todo novo parâmetro ou módulo adicionado é vinculado a uma categoria específica no índice do arquivo.
- **Tradutibilidade**: A estrutura categorizada permite que o aprendizado do modelo seja extraído, analisado e traduzido para formatos compreensíveis, garantindo que o processo evolutivo não seja uma "caixa preta".

### 3.5. Integridade e Persistência
Utiliza um sistema de commit transacional dual-slot (A/B) com hashing SHA-512 no superbloco para garantir que falhas durante a escrita não corrompam o estado do agente. Cada tensor individual é validado via SHA-256 no momento do carregamento.

### 3.6. Protocolo de Injeção Aberta (Open Injection Protocol / LKIF)
Enquanto as Seções 3.1–3.5 descrevem como o `.lira` guarda **pesos** (tensores,
deltas, LoRAs — dados binários, opacos, eficientes), esta seção descreve como
ele guarda **conhecimento declarativo**: pares pergunta/resposta que qualquer
modelo — não apenas o runtime que criou o arquivo — pode ler e escrever.

Isso é o que diferencia o `.lira` de um formato puramente de pesos como o
`safetensors`: o `safetensors` só sabe descrever tensores; o `.lira`, através
do LKIF (**Lira Knowledge Injection Format**), descreve *o que o agente
entendeu*, organizado por categoria semântica, de um jeito que outro modelo
consegue ler sem entender nada do container binário.

**3.6.1. Camada de metadata `knowledge`.** Um novo campo `knowledge` é
adicionado à metadata JSON já existente (junto de `categories`, `modules`,
`skills`, `memory`, `experiences`, `history`), mapeando cada categoria a uma
lista de entradas:

```json
"knowledge": {
  "fisica/mecanica_quantica": [
    {
      "id": "47d33f7ccd4a493d",
      "category": "fisica/mecanica_quantica",
      "question": "O que é o princípio da incerteza de Heisenberg?",
      "answer": "...",
      "source_model": "Claude Sonnet 5",
      "confidence": 0.95,
      "tags": ["fisica", "quantica"],
      "evidence": null,
      "created_at": 1783342862.26,
      "format_version": "1.0",
      "content_hash": "sha256(...)"
    }
  ]
}
```

Cada entrada é gravada através do mesmo mecanismo de commit dual-slot A/B da
Seção 3.5 — ou seja, injeção de conhecimento herda a mesma garantia de
crash-safety que já existe para módulos e pesos.

**3.6.2. Formato de intercâmbio: LKIF/JSONL.** Para que um modelo externo
(Claude, GPT, Gemini, um agente local, etc.) consiga *escrever* conhecimento
sem tocar no binário, o LKIF define um formato de texto puro: um arquivo
`.jsonl` com uma entrada JSON por linha, opcionalmente precedido por uma linha
de manifesto (`lkif_manifest: true`). É o formato mais simples que um LLM
consegue gerar como saída de texto — sem SDK, sem biblioteca binária, sem
depender de nenhum fornecedor. O schema formal (JSON Schema, draft 2020-12)
está publicado em `lkif_schema.json` e exige apenas quatro campos
obrigatórios: `category`, `question`, `answer` e `source_model` (proveniência
é obrigatória — todo conhecimento injetado é auditável).

**3.6.3. Interface de Leitura Cognitiva (read-before-write).** Antes de
injetar, qualquer modelo pode chamar `read_category(categoria)` (ou o
comando `lira read-knowledge`) para ver o que já está armazenado naquela
gaveta semântica. Isso implementa o item de "Transparência para Agentes":
um modelo não precisa reensinar o que outro já ensinou, e pode auditar quem
disse o quê antes de decidir contribuir.

**3.6.4. Deduplicação determinística.** Cada entrada carrega um
`content_hash = sha256(categoria + pergunta_normalizada + resposta_normalizada)`.
Isso não é similaridade semântica (o container não roda embeddings) — é uma
comparação exata pós-normalização (minúsculas, espaços colapsados, pontuação
de borda removida). Duas injeções de modelos diferentes com a mesma
pergunta/resposta normalizada resultam em uma única entrada; a proveniência
do primeiro que escreveu é preservada. Duplicatas genuinamente diferentes
(reformuladas) não são detectadas por esta camada — cabe ao modelo que
injeta usar `search()`/`read_category()` antes de escrever.

**3.6.5. Fluxo cross-model típico:**
1. Modelo A chama `lira export-knowledge agente.lira saida.jsonl` (ou
   `oip.export_jsonl(...)` via API) para obter o estado atual do
   conhecimento em formato legível.
2. Modelo A lê `saida.jsonl`, identifica lacunas, e escreve novas entradas
   em um novo `.jsonl` seguindo `lkif_schema.json`.
3. Modelo A (ou qualquer processo com acesso ao arquivo) chama
   `lira inject agente.lira novo.jsonl`, que valida cada entrada contra o
   schema, deduplica, e commita via o mesmo mecanismo transacional A/B.
4. Modelo B, mais tarde, repete o passo 1 e já vê o que o Modelo A
   contribuiu — incluindo a proveniência (`source_model`).
5. Periodicamente (ou sob demanda), qualquer processo com acesso ao arquivo
   roda `lira compile-knowledge agente.lira <categoria>` para transformar o
   texto acumulado daquela categoria em um parâmetro binário real — ver
   Seção 3.7. Isso não substitui os passos 1–4 (a leitura/escrita em texto
   continua sendo a interface entre modelos); é uma etapa adicional que
   comprime o que já foi ensinado em algo mais próximo de um tensor.

Isso torna o `.lira` não apenas um formato de pesos, mas uma "língua franca"
de conhecimento entre modelos diferentes que compartilham o mesmo arquivo.

### 3.7. Compilador de Conhecimento (palavras → parâmetros reais)

A Seção 3.6 resolve a troca de conhecimento *em texto* entre modelos, mas
texto puro tem uma limitação: cresce linearmente com o número de fatos e
nunca generaliza — é um banco de dados anexado, não algo que foi realmente
"aprendido" no sentido de parâmetro treinado. O `KnowledgeCompiler`
(`lira_knowledge_compiler.py`) resolve essa parte, sem exigir acesso aos
gradientes internos de nenhum LLM (isso não é fine-tuning de Claude, GPT,
etc. — é o treino de um adaptador auxiliar guardado dentro do `.lira`):

1. **Vetorização determinística.** Cada pergunta e cada resposta são
   convertidas em um vetor de tamanho fixo via *feature hashing* (hashing
   trick, com unigramas + bigramas) — a mesma técnica usada por
   ferramentas como Vowpal Wabbit / `sklearn.HashingVectorizer`. Não
   depende de baixar nenhum modelo de embeddings externo.
2. **Treino real, forma fechada.** Resolve
   `W = argmin_W ||Q·W - A||² + λ||W||²` (regressão de Ridge), obtendo a
   matriz `W` que melhor mapeia pergunta → resposta no espaço vetorizado.
   O ajuste é medido por similaridade de cosseno real entre previsto e
   alvo (`mean_cosine_fit`), não é uma métrica decorativa.
3. **Parâmetro `W` de tamanho fixo.** `W` é uma matriz `d × d` (por padrão
   `d = 256`) que não cresce conforme mais fatos são injetados. Ela é
   gravada como módulo binário (`DELTA`), do mesmo jeito que um LoRA já é
   gravado (Seção 3.1). Isso não significa que o arquivo inteiro tenha
   tamanho fixo.
4. **Payload e vetores crescem com o conhecimento ativo.** As respostas,
   perguntas e metadados LKIF precisam continuar reconstruíveis. Por isso
   o compilador grava `answer_vectors`, índices compactos e um payload
   comprimido com zlib contendo os campos públicos completos. Esses blocos
   crescem conforme o número de conhecimentos, e recompilações substituem
   o container por uma versão compactada para remover payloads e tensores
   órfãos.
5. **Relatórios de armazenamento.** Os relatórios distinguem bytes ativos,
   bytes órfãos, bytes de metadados, bytes de tensores, bytes de payload e
   tamanho real do arquivo. Assim fica claro o que é capacidade fixa (`W`)
   e o que é corpus ativo (`answer_vectors` + payload).
6. **Consulta por inferência sobre o parâmetro.** `compiler.query(...)`
   vetoriza a pergunta nova, multiplica por `W`, e busca o vetor-resposta
   mais próximo por cosseno — isto é inferência sobre um parâmetro
   treinado, não busca textual (`grep`) como em `search()`.

**Uso via CLI** (parâmetros padrão: `n_features=256`, `ridge_lambda=1.0` —
os mesmos usados nos testes de referência do projeto):

```bash
# Compila uma única categoria (palavras -> parâmetro)
lira compile-knowledge agente.lira programacao/python

# Compila todas as categorias de conhecimento ainda não compiladas
lira compile-all-knowledge agente.lira

# Consulta o PARÂMETRO treinado (não faz grep em texto)
lira query-knowledge agente.lira programacao/python "explica o que é generator"
```

**Limitação explícita.** Isto treina um adaptador de recuperação associativa
*auxiliar* dentro do arquivo `.lira`. Não modifica os pesos internos de
nenhum LLM real — isso exigiria acesso aos gradientes daquele modelo
específico. O que fica genuinamente mais "parâmetro e menos palavra" é a
representação armazenada no arquivo, não o modelo que está lendo o arquivo.

## 4. Eficiência e Otimização
- **Acesso Aleatório**: O uso de `mmap` permite carregar apenas as seções necessárias do arquivo para a memória RAM.
- **Baixo Consumo**: Suporta pesos quantizados (int8, NF4) nativamente, permitindo a execução de modelos complexos em hardware com recursos limitados.
- **Síntese de Ferramentas**: O runtime permite a criação e anexação de novos scripts e lógicas funcionais diretamente ao contêiner.

## 5. Conclusão
O `.lira` estabelece um padrão técnico para inteligências artificiais que necessitam de evolução constante e alta performance, unindo segurança, velocidade e flexibilidade em um único formato binário.
