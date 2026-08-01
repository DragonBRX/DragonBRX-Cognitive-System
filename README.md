# DragonBRX Cognitive System

O DragonBRX é um experimento de **arquitetura cognitiva artificial leve**, criado do zero para investigar memória, objetivos, atenção, decisão, aprendizagem e trabalho distribuído sem copiar literalmente a anatomia do cérebro humano.

O núcleo ativo **não usa modelo de linguagem, Ollama, API de IA ou serviço externo**. Ele é o próprio mecanismo experimental de cognição. No futuro, outras fontes de parâmetros poderão ser conectadas como ferramentas opcionais, sem substituir o cérebro central.

> O projeto pesquisa uma consciência funcional experimental. Não afirma ter demonstrado consciência subjetiva.

## Princípios

- **A Livraria de Lira:** O conhecimento é uma livraria infinita. O cérebro não carrega tudo, ele acessa o que precisa no momento exato através de um mapa de endereçamento direto.
- **Aprendizado Intrínseco:** Não existe "modo treino". Conversar é aprender. Cada interação atualiza os parâmetros do mapa em tempo real.
- **Elasticidade Temporal:** O sistema adapta seu tempo de pensamento ao hardware disponível. Em dispositivos fracos, ele delibera mais devagar para manter a qualidade.
- **Cérebro Leve e Eterno:** O *Cognitive Pruning* (Gari Cognitivo) remove o irrelevante, permitindo que o sistema evolua por meses sem ficar pesado ou lento.
- **Identidade canônica:** seu nome é `DragonBRX`; descrições de arquitetura não substituem esse nome.
- **Sem modelo central:** nenhuma decisão depende de LLM, SLM ou API.
- **Arquitetura P-SE-GCA:** Arquitetura Cognitiva Geral Autoevolutiva Persistente baseada no padrão `.lira`.

## Arquitetura atual

| Componente | Função |
| --- | --- |
| `src/lira_core.py` | Núcleo Lira: Persistência binária, linhagem histórica e metacognição |
| `src/lira_map_indexer.py` | O Mapa: Endereçamento direto de parâmetros em disco (Livraria de Lira) |
| `src/intrinsic_learner.py` | Aprendizado Intrínseco: Conversão de diálogo em parâmetros binários em tempo real |
| `src/skill_atlas.py` | Atlas de Skills: Gerenciador de 1.600+ habilidades com contratos e versionamento |
| `src/knowledge_promoter.py` | Quarentena: Pipeline de promoção de conhecimento (Experimental -> Stable) |
| `src/cognitive_fabric.py` | Núcleo cognitivo: conceitos, relações, objetivos e Gari Cognitivo (Pruning) |
| `src/temporal_elasticity.py` | Elasticidade: Ajuste dinâmico do tempo de pensamento ao hardware |
| `src/autonomous_loop.py` | Motor de Autonomia: Ciclo infinito de pesquisa, rascunho, teste e evolução |
| `src/research_worker.py` | Pesquisador: Extração de dados científicos e rascunhos originais |
| `src/coding_worker.py` | Programador: Geração de código funcional baseada em tarefas cognitivas |
| `src/conversational_bridge.py` | Voz do DragonBRX: Tradução de estados cognitivos para linguagem natural |
| `tests/test_cognitive_system.py` | Testes da suíte P-SE-GCA (100% OK) |

Os componentes antigos ligados a `llmProcessor`, `cognitiveProcessor`, Ollama, pesquisa web e chamadas HTTP **não foram restaurados**.

## Identidade

`DragonBRX` é o nome integral e canônico do projeto e do sistema. Essa
identidade possui um registro próprio com SHA-256, aparece no estado público,
é persistida no checkpoint e, quando o Lira está habilitado, permanece ativa
como a skill `core_identity::DragonBRX`. Frases comuns da conversa não podem
renomeá-lo. “Sistema cognitivo artificial experimental” descreve o tipo de
arquitetura; não faz parte do nome.

## O ciclo cognitivo

1. A entrada é classificada por intenção, assunto e restrições.
2. Um mapa já aprendido pode selecionar um caminho direto.
3. Sem mapa suficiente, o sistema recupera memória de trabalho, episódios e conhecimento Lira.
4. O pedido é decomposto nas capacidades necessárias.
5. Ferramentas locais são inventariadas antes de criar ou instalar qualquer coisa.
6. Um grafo proporcional ao problema seleciona perspectivas como evidência,
   restrições, contraexemplo, segurança, viabilidade, eficiência e verificação.
7. Alternativas viram rascunhos e são criticadas sob essas perspectivas.
8. Falhas locais geram revisão; falhas estruturais descartam o rascunho e
   reiniciam por outra abordagem, dentro de limites rígidos.
9. Se uma capacidade ainda não existe, o sistema admite a lacuna e pode abrir
   um currículo local de microexperimentos com prazo e cancelamento.
10. A decisão é executada, observada e avaliada por evidências combinadas.
11. Repetições estáveis e competências com transferência validada viram mapas.
12. Um replay de casos recentes bloqueia promoções que atingiriam uma rota
    semelhante com estratégia contraditória.
13. Mapas, erros resumidos, skills e conhecimento são persistidos no `.lira`.
14. Regressões retiram o mapa e preservam a geração anterior.
15. O orçamento de memória, ramos e ciclos se adapta ao hardware.

## Evolução que reduz trabalho

O DragonBRX mede evolução como **qualidade preservada com menos trabalho**.
Depois de execuções consistentes, um mapa cognitivo pode evitar busca,
recuperação de memória ou crítica redundante. Os mapas são fragmentados por
assinatura para acesso direto e registrados como skills versionadas no Lira.

Tentativas descartadas não ficam inteiras na memória. O sistema preserva apenas
uma abstração: classe da falha, sintomas, premissa incorreta, motivo do reinício
e abordagem que resolveu o problema.

Uma correção explícita do usuário pode criar uma memória negativa. Respostas
semelhantes recebem penalidade em deliberações futuras. Mapas que reduzam a
qualidade ou aumentem custos relevantes são retirados automaticamente. A skill
correspondente também é desativada em uma nova geração do `.lira`, sem apagar o
histórico que permite auditoria ou rollback.

Isso é pesquisa experimental. Os mecanismos não demonstram consciência, AGI,
criação autônoma de conhecimento científico ou superioridade sobre modelos de
fronteira.

Veja também o [roteiro de pesquisa](docs/RESEARCH_ROADMAP.md) e o
[relatório validado do laboratório](docs/LAB_REPORT_2026-07-29.md). O fluxo de
variantes está documentado em
[Laboratório de autoaperfeiçoamento verificável](docs/VARIANT_LAB.md). O grafo
multiperspectiva e o currículo local estão descritos em
[Aprendizado de competências e grafo cognitivo](docs/COMPETENCE_LEARNING.md).
A topologia SSD/HD está em
[Conexão DragonBRX ↔ BRX SYSTEM](docs/DATACENTER_CONNECTION.md).

## Testar o núcleo

Requer apenas Python 3.10 ou superior:

```bash
py -m unittest discover -s tests -v
py src/cognitive_fabric.py
py benchmarks/benchmark_cognitive_evolution_suite.py --assert-pass
py benchmarks/benchmark_improvement_lab.py --assert-pass
py benchmarks/benchmark_competence_transfer.py --assert-pass
py benchmarks/benchmark_datacenter_connection.py --assert-pass
```

A suíte atual cobre o núcleo anterior e as novas camadas adaptativas. O
benchmark reprodutível mede retenção, interferência, memória negativa,
promoção/rollback, replay de não-regressão, persistência de ferramentas e
redução estrutural de trabalho. Ele não mede consciência, AGI ou superioridade
geral.

## Executar a mente cognitiva

O runtime Lira é localizado automaticamente quando o projeto `lira` está ao
lado deste diretório. Também pode ser indicado com `--lira-runtime`.

```bash
python3 src/cognitive_system.py \
  --state .dragonbrx/mind-state.json \
  --lira .dragonbrx/knowledge.lira \
  --trace
```

Uma única entrada:

```bash
python3 src/cognitive_system.py --once "oi" --json
```

Interface visual local:

```powershell
py src\cognitive_system.py --dashboard
```

Nesta máquina, o launcher recomendado conecta automaticamente o datacenter no
HD e mantém o checkpoint pequeno no SSD:

```powershell
.\start-dragonbrx-datacenter.ps1
```

O painel mostra conversa, trilha estruturada de decisões, mapas, gerações,
ferramentas e trabalhos locais de aprendizado.
Quando iniciado com `--lab-root` e `--lab-key`, também mostra uma aba de
observação do laboratório de variantes. A chave permanece externa ao
laboratório e as transições continuam restritas à CLI do operador.
Instalações ficam desativadas por padrão; para habilitá-las explicitamente use
`--allow-install`. A interface não tenta aceitar janelas UAC nem elevar a própria
permissão. Uma ação administrativa continua sendo uma decisão visível do
operador do Windows.

Para consolidar memória e conhecimento uma vez após cada período de atividade,
fora do caminho crítico das respostas:

```powershell
py src\cognitive_system.py --dashboard --background-maintenance
```

O intervalo padrão é 30 segundos e pode ser alterado com
`--maintenance-interval`. O worker é cancelável, limitado a uma thread e não
repete commits quando nenhum estado novo apareceu.

Comandos interativos:

- `/estado`: estado cognitivo, recursos, ferramentas e política;
- `/recursos`: perfil detectado e orçamento ativo;
- `/capacidades <pedido>`: mostra se o sistema usaria, adaptaria, criaria ou instalaria;
- `/executar <pedido> :: <json>`: executa a capacidade após inventário e resolução;
- `/evolucao`: mapas, gerações, rollbacks e trabalho economizado;
- `/laboratorio`: baseline, canário e variantes autenticadas, quando configurado;
- `/datacenter`: mostra a conexão SSD/HD, Lira, componentes e espaço livre;
- `/aprender <tempo> :: <pedido>`: inicia um currículo local cancelável;
- `/aprendizado [id]`: mostra progresso, tentativas, scores e artefatos;
- `/parar-aprendizado <id>`: interrompe e salva o trabalho;
- `/pensamentos`: trilha cognitiva estruturada;
- `/consolidar`: checkpoint dos mapas e compilação do conhecimento Lira;
- `/sono`: executa uma rodada medida de manutenção ociosa;
- `/salvar` e `/sair`.

Uso instrumental pela API:

```python
from cognitive_system import CognitiveSystem

mind = CognitiveSystem(lira_path=".dragonbrx/knowledge.lira")

plan = mind.capability_plan("renderizar imagem")
result = mind.execute_capability(
    "renderizar imagem",
    {
        "path": ".dragonbrx/render.png",
        "width": 512,
        "height": 512,
        "color": "#172033",
    },
    allow_install=False,
)
```

O resolvedor consulta primeiro módulos, executáveis e ferramentas registradas.
No Windows testado, captura de tela, renderização e análise básica reutilizam
Pillow quando ele já está instalado. Receitas pequenas e determinísticas podem
ser materializadas como ferramentas Python; código, contrato e SHA-256 ficam em
um catálogo e são verificados antes da recarga em outro processo.

Exemplo interativo sem permitir instalações:

```text
/executar criar slug de texto :: {"text":"Memória Lira"}
```

Para autorizar a instalação isolada de uma dependência conhecida durante
`/executar`, inicie o runtime com `--allow-install`. Essa opção não autoriza
efeitos que estejam na política imutável.

## Como notebook e celulares se conectam

CMD, PowerShell, Bash e o terminal do Termux apenas iniciam o programa. Depois
disso, a comunicação é a mesma em todos os sistemas: Python abre um socket TCP.

1. O notebook executa o núcleo central e escuta na porta configurada.
2. O worker Termux ou a-Shell abre uma conexão de saída para o IPv4 local do notebook.
3. O agente envia identidade, plataforma e capacidades instaladas.
4. O núcleo autentica a mensagem com HMAC-SHA256.
5. Um heartbeat mantém o canal ativo mesmo quando não existem tarefas.
6. O núcleo envia tarefas pelo mesmo canal; o worker devolve resultados.
7. O resultado atualiza memória, plano e confiabilidade do celular.
8. Se um iPhone for suspenso, leases vivos são reenviados e resultados salvos
   são entregues sem repetir o cálculo.

Na mesma rede Wi-Fi isso é uma conexão local direta, não um túnel. O módulo do
agente cria um canal lógico persistente. Se os aparelhos estiverem em redes
diferentes, será necessária uma VPN como WireGuard/Tailscale ou um túnel
equivalente. Não exponha a porta diretamente à internet.

O repositório é público, mas a chave de rede não é. Estar no mesmo Wi-Fi apenas
permite alcançar o notebook; toda mensagem ainda precisa de HMAC-SHA256 válido.
Arquivos `*.key`, `.dragonbrx/` e checkpoints locais estão ignorados pelo Git.

Para configurar um iPhone com o a-Shell completo, consulte
[Worker DragonBRX no iPhone com a-Shell](docs/IOS_A_SHELL_WORKER.md).

O fluxo curto é:

```powershell
.\start-dragonbrx-lan.ps1
```

No primeiro uso do a-Shell:

```sh
cd ~/Documents
lg2 clone https://github.com/DragonBRX/DragonBRX-Cognitive-System.git
cd DragonBRX-Cognitive-System
sh scripts/bootstrap-ios.sh
```

Na primeira execução, o PC pede uma frase-senha de no mínimo 12 caracteres; o
iPhone pede a mesma senha uma vez. Ela nunca é transmitida nem armazenada.
Depois disso, o bootstrap detecta por broadcast autenticado o coordenador que
estiver no mesmo Wi-Fi.

### Núcleo central no Windows

Requer Python 3.10 ou superior. No CMD:

```powershell
.\start-dragonbrx-lan.ps1
```

Na primeira execução, defina uma senha com pelo menos 12 caracteres. Ela não é
transmitida nem gravada; o PC guarda somente uma chave derivada em
`%USERPROFILE%\.dragonbrx`. O iPhone encontra o PC automaticamente pelo anúncio
autenticado na mesma rede Wi-Fi. Quando o Windows perguntar, permita o Python
somente em redes privadas. Se necessário, crie regras no PowerShell como
Administrador:

```powershell
New-NetFirewallRule -DisplayName "DragonBRX Local" -Direction Inbound -Protocol TCP -LocalPort 9999 -Action Allow -Profile Private
New-NetFirewallRule -DisplayName "DragonBRX Discovery" -Direction Inbound -Protocol UDP -LocalPort 9998 -Action Allow -Profile Private
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

- ampliar a deliberação para artefatos, código e planos executáveis;
- criar adaptadores para vídeo, áudio, navegador e ferramentas científicas;
- validar criação automática de ferramentas em tarefas reais repetidas;
- ampliar o laboratório declarativo com incerteza estatística e tráfego canário integrado;
- adicionar AppContainer, Job Objects e broker antes de aceitar variantes executáveis;
- executar consolidação ociosa para pré-computar mapas sem aumentar a latência;
- ampliar replay de não-regressão com amostragem de casos mais interferidos;
- melhorar o compilador de mapas para produzir programas cognitivos tipados;
- separar latência de inferência, checkpoint e compactação nas métricas;
- criar orquestrador multiagente com leases, idempotência e verificação;
- integrar os módulos C ao núcleo Python por um contrato estável;
- criar suites públicas de qualidade, segurança, memória e regressão;
- medir crescimento do Lira contra capacidade real, não apenas número de entradas.

## Licença

MIT.
