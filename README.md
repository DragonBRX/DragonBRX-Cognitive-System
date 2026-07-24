# DragonBRX Cognitive System

O DragonBRX é um experimento de **arquitetura cognitiva artificial leve**, criado do zero para investigar memória, objetivos, atenção, decisão, aprendizagem e trabalho distribuído sem copiar literalmente a anatomia do cérebro humano.

O núcleo ativo **não usa modelo de linguagem, Ollama, API de IA ou serviço externo**. Ele é o próprio mecanismo experimental de cognição. No futuro, outras fontes de parâmetros poderão ser conectadas como ferramentas opcionais, sem substituir o cérebro central.

> O projeto pesquisa uma consciência funcional experimental. Não afirma ter demonstrado consciência subjetiva.

## Princípios

- **Motor próprio:** perceber, integrar, priorizar, decidir, delegar e aprender.
- **Sem modelo central:** nenhuma decisão depende de LLM, SLM ou API.
- **Memória persistente:** conceitos, relações, experiências, objetivos e resultados.
- **Arquitetura original:** unidades simbólicas adaptativas em vez de uma cópia de neurônios biológicos.
- **Distribuição:** notebook como núcleo central e celulares Termux como agentes trabalhadores.
- **Inspeção:** decisões registram pontuações e motivos; o estado é serializável em JSON.
- **Segurança:** agentes executam apenas capacidades instaladas e autorizadas localmente.

## Arquitetura atual

| Componente | Função |
| --- | --- |
| `src/cognitive_fabric.py` | Núcleo cognitivo: conceitos, relações, objetivos, memória, escolha, delegação e aprendizagem por resultado |
| `src/distributed_runtime.py` | Rede autenticada entre o núcleo e agentes de notebook/Termux |
| `synaptic_storage.c/.h` | Memória sináptica recuperada do projeto original |
| `vector_memory.c/.h` | Memória vetorial em C recuperada do histórico |
| `nodeManager.js` | Detecção e classificação de hardware recuperada |
| `distributedNetworkManager.js` | Protótipo histórico de distribuição em Node.js |
| `affectiveProcessor.js` | Estado afetivo persistente recuperado |
| `synapticStorageInterface.js` | Ponte histórica entre Node.js e armazenamento C |
| `tests/test_cognitive_system.py` | Testes do ciclo cognitivo e protocolo autenticado |

Os componentes antigos ligados a `llmProcessor`, `cognitiveProcessor`, Ollama, pesquisa web e chamadas HTTP **não foram restaurados**.

## O ciclo cognitivo

1. Uma percepção entra como evento JSON.
2. O núcleo extrai conceitos e atualiza ativações.
3. Conceitos observados juntos fortalecem suas relações.
4. A atenção se espalha de forma limitada pelas relações aprendidas.
5. Objetivos acumulam evidências ao longo de experiências diferentes.
6. Custo, risco, contexto, novidade e conflitos alteram a pontuação das ações.
7. A melhor ação pode ser executada localmente ou enviada a um agente compatível.
8. O resultado real fecha a tarefa, atualiza a memória e ajusta a confiabilidade do agente.
9. Memórias podem ser recuperadas por contexto e recência.
10. O estado pode ser salvo e retomado sem reconstruir a identidade do zero.

## Testar o núcleo

Requer apenas Python 3.10 ou superior:

```bash
python3 -m unittest tests/test_cognitive_system.py -v
python3 src/cognitive_fabric.py
```

## Preparar a chave da rede

Crie o mesmo arquivo secreto no notebook central e em cada celular por um canal seguro:

```bash
mkdir -p ~/.dragonbrx
python3 -c "import secrets,pathlib; pathlib.Path.home().joinpath('.dragonbrx/network.key').write_text(secrets.token_hex(32))"
chmod 600 ~/.dragonbrx/network.key
```

Não publique esse arquivo no GitHub.

## Executar o núcleo no notebook

Para aceitar agentes na rede local:

```bash
python3 src/distributed_runtime.py central \
  --host 0.0.0.0 \
  --port 9999 \
  --secret-file ~/.dragonbrx/network.key
```

O console central aceita comandos JSON. Exemplos:

```json
{"type":"status"}
{"type":"introspect"}
{"type":"recall","query":{"energia":"baixa"},"limit":5}
{"type":"goal","description":"mapear recursos dos agentes","desired":["hardware","disponível"],"priority":0.9}
{"type":"perceive","kind":"ordem","payload":{"ação":"inventariar celulares"},"salience":0.8}
{"type":"task","name":"ler hardware do celular","capability":"system_info","inputs":{},"expected":["hardware","disponível"],"cost":0.1,"risk":0.0}
{"type":"save"}
{"type":"exit"}
```

## Instalar um agente no Termux

No celular:

```bash
pkg update
pkg install python git
git clone https://github.com/DragonBRX/DragonBRX-Cognitive-System.git
cd DragonBRX-Cognitive-System
python3 src/distributed_runtime.py agent \
  --host IP_DO_NOTEBOOK \
  --port 9999 \
  --agent-id celular-01 \
  --secret-file ~/.dragonbrx/network.key \
  --capability system_info \
  --capability text_statistics
```

O firewall do notebook deve permitir a porta escolhida somente na rede confiável. Não exponha o serviço diretamente à internet.

## Capacidades dos agentes

O runtime inicial inclui somente capacidades inofensivas:

- `system_info`: informa plataforma, arquitetura, Python e quantidade de CPUs;
- `text_statistics`: calcula contagem e SHA-256 de um texto.

Novas capacidades devem ser funções explícitas registradas no agente. O protocolo não aceita comandos de shell enviados pelo núcleo, reduzindo o risco de transformar os celulares em execução remota arbitrária.

## Memória nativa recuperada

O armazenamento em C original pode ser compilado separadamente:

```bash
# Debian/Ubuntu
sudo apt install build-essential libjansson-dev
gcc -O2 -o synaptic_storage synaptic_storage.c -lm -ljansson
```

Essa implementação histórica ainda trabalha com vetores numéricos. Ela será adaptada progressivamente para o novo formato categorizado do DragonBRX; não é o motor de pensamento e não exige um modelo.

## Próximas etapas

- definir formalmente o novo formato de conhecimento/parâmetros;
- substituir vetores aleatórios por codificação própria, determinística e categorizada;
- criar atenção concorrente e memória de trabalho;
- implementar planejamento com sequências de ações e revisão de erros;
- adicionar consolidação subconsciente sem geração por modelo;
- criar mais capacidades Termux com permissões mínimas;
- integrar os módulos C ao núcleo Python por um contrato estável;
- medir memória, CPU, latência, aprendizagem e estabilidade em testes reproduzíveis.

## Licença

MIT.
