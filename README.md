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

## Como notebook e Termux se conectam

CMD, PowerShell, Bash e o terminal do Termux apenas iniciam o programa. Depois
disso, a comunicação é a mesma em todos os sistemas: Python abre um socket TCP.

1. O notebook executa o núcleo central e escuta na porta configurada.
2. O agente Termux abre uma conexão de saída para o IPv4 local do notebook.
3. O agente envia identidade, plataforma e capacidades instaladas.
4. O núcleo autentica a mensagem com HMAC-SHA256.
5. Um heartbeat mantém o canal ativo mesmo quando não existem tarefas.
6. O núcleo envia tarefas pelo mesmo canal; o agente devolve resultados.
7. O resultado atualiza memória, plano e confiabilidade do celular.

Na mesma rede Wi-Fi isso é uma conexão local direta, não um túnel. O módulo do
agente cria um canal lógico persistente. Se os aparelhos estiverem em redes
diferentes, será necessária uma VPN como WireGuard/Tailscale ou um túnel
equivalente. Não exponha a porta diretamente à internet.

### Núcleo central no Windows

Requer Python 3.10 ou superior. No CMD:

```bat
py -c "import secrets,pathlib; p=pathlib.Path.home()/'.dragonbrx'/'network.key'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(secrets.token_hex(32))"
ipconfig
py src\distributed_runtime.py central --host 0.0.0.0 --port 9999 --secret-file "%USERPROFILE%\.dragonbrx\network.key"
```

Use no celular o endereço `IPv4` mostrado pelo `ipconfig`, normalmente
`192.168.x.x`. Quando o Windows perguntar, permita o Python somente em redes
privadas. Se necessário, crie uma regra no PowerShell como Administrador:

```powershell
New-NetFirewallRule -DisplayName "DragonBRX Local" -Direction Inbound -Protocol TCP -LocalPort 9999 -Action Allow -Profile Private
```

### Núcleo central no Linux

```bash
mkdir -p ~/.dragonbrx
python3 -c "import secrets,pathlib; pathlib.Path.home().joinpath('.dragonbrx/network.key').write_text(secrets.token_hex(32))"
hostname -I
python3 src/distributed_runtime.py central \
  --host 0.0.0.0 --port 9999 \
  --secret-file ~/.dragonbrx/network.key
```

Copie o conteúdo exato de `network.key` para o mesmo caminho no Termux. Não
gere outra chave no celular, pois ela seria diferente.

### Agente no Termux

```bash
pkg update
pkg install python git
git clone https://github.com/DragonBRX/DragonBRX-Cognitive-System.git
cd DragonBRX-Cognitive-System
mkdir -p ~/.dragonbrx
nano ~/.dragonbrx/network.key
python3 src/distributed_runtime.py agent \
  --host 192.168.1.10 --port 9999 \
  --agent-id celular-01 \
  --secret-file ~/.dragonbrx/network.key \
  --capability system_info \
  --capability text_statistics
```

Substitua `192.168.1.10` pelo IPv4 real do notebook. Alguns roteadores possuem
“isolamento de clientes/AP”; essa opção precisa estar desativada para aparelhos
do mesmo Wi-Fi conversarem.

O console central aceita comandos JSON. Exemplos:

```json
{"type":"status"}
{"type":"introspect"}
{"type":"recall","query":{"energia":"baixa"},"limit":5}
{"type":"prompt","request":"cria um jogo 3D de aventura offline para Android"}
{"type":"plan","plan_id":"ID_RETORNADO"}
{"type":"plan_dispatch","plan_id":"ID_RETORNADO"}
{"type":"goal","description":"mapear recursos dos agentes","desired":["hardware","disponível"],"priority":0.9}
{"type":"perceive","kind":"ordem","payload":{"ação":"inventariar celulares"},"salience":0.8}
{"type":"task","name":"ler hardware do celular","capability":"system_info","inputs":{},"expected":["hardware","disponível"],"cost":0.1,"risk":0.0}
{"type":"save"}
{"type":"exit"}
```

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
