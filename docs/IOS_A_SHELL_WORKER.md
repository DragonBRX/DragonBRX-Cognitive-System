# Worker DragonBRX no iPhone com a-Shell

Este módulo transforma um iPhone em worker temporário do DragonBRX na rede
local. O notebook continua sendo o coordenador e dono dos checkpoints. O
iPhone recebe somente tarefas declarativas de capacidades instaladas, salva o
resultado antes de enviá-lo e retoma a entrega depois de uma suspensão.

O código é público. A chave de cada instalação é privada e nunca deve entrar no
GitHub.

## Limites do iOS

Use o a-Shell completo e mantenha-o aberto em primeiro plano. O iOS suspende a
maioria dos aplicativos pouco depois que saem do primeiro plano; não existe uma
permissão geral para um terminal da App Store executar CPU e sockets
indefinidamente em segundo plano.

O worker foi desenhado para essa interrupção:

1. o notebook conserva um lease da tarefa;
2. o iPhone salva o resultado em JSON por substituição atômica;
3. ao reconectar, o notebook reenvia o lease ainda válido;
4. o iPhone reconhece o ID e devolve o resultado salvo sem recalcular;
5. o arquivo só é limpo após um `result_ack` autenticado.

Referências: [a-Shell oficial](https://github.com/holzschu/a-Shell) e
[limites de execução em segundo plano explicados pela Apple](https://developer.apple.com/forums/thread/685525).

## Segurança local

Estar no mesmo Wi-Fi não é autenticação. A proteção usa duas barreiras:

- alcance restrito à LAN, sem encaminhamento da porta `9999` no roteador;
- HMAC-SHA256 em toda mensagem com uma chave aleatória de no mínimo 32 bytes.

Uma pessoa na mesma rede consegue tentar abrir a porta, mas não consegue
registrar um nó nem enviar resultado válido sem a chave. O protocolo também
vincula o resultado ao agente, ação e capacidade atribuídos, usa janela contra
replay e não oferece execução remota de shell.

Use uma rede privada confiável. Não use Wi-Fi público, rede de convidados,
redirecionamento de porta, DMZ ou exposição direta à internet. Se a chave
vazar, gere outra e substitua nos dois dispositivos.

Arquivos como `*.key`, `.dragonbrx/` e o checkpoint do worker estão no
`.gitignore`.

## 1. Preparar o notebook Windows

No PowerShell, dentro do projeto:

```powershell
Get-NetConnectionProfile
.\start-dragonbrx-lan.ps1
```

A rede usada precisa aparecer como `Private`. O launcher inicia o coordenador
e a descoberta automática; não é necessário copiar o IPv4 nem uma chave.

No primeiro uso, o PowerShell pede uma frase-senha duas vezes. Use pelo menos
12 caracteres; `99` é recusada porque seria trivial testar todas as
possibilidades. A senha não é gravada. O PC salva somente:

- `pairing.json`: salt e parâmetros públicos do PBKDF2;
- `network.key`: chave de 256 bits derivada da senha.

Ambos ficam em `%USERPROFILE%\.dragonbrx`, fora do repositório. Nas próximas
execuções o PowerShell não pede novamente. O terminal mantém TCP `9999` e o anúncio
autenticado UDP `9998` ativos enquanto estiver aberto.

Se o Firewall do Windows pedir permissão, autorize somente para redes privadas.
Não autorize redes públicas. Se nenhuma janela aparecer e a conexão for
bloqueada, uma regra restrita ao perfil privado pode ser criada em um
PowerShell elevado:

```powershell
New-NetFirewallRule `
  -DisplayName "DragonBRX LAN 9999" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 9999 `
  -Action Allow `
  -Profile Private

New-NetFirewallRule `
  -DisplayName "DragonBRX Discovery 9998" `
  -Direction Inbound `
  -Protocol UDP `
  -LocalPort 9998 `
  -Action Allow `
  -Profile Private
```

Essa regra é uma ação administrativa visível. O DragonBRX não tenta aceitar a
janela de elevação sozinho.

## 2. Instalar e preparar o a-Shell

Instale apenas o **a-Shell completo** pela App Store. Em um iPhone novo, cole
este bloco inteiro:

```sh
cd ~/Documents
lg2 clone https://github.com/DragonBRX/DragonBRX-Cognitive-System.git
cd DragonBRX-Cognitive-System
sh scripts/bootstrap-ios.sh
```

O script verifica o Python incluído no a-Shell, valida os módulos e informa que
o worker não possui dependências externas. Na primeira execução ele encontra o
PC, pede a mesma frase-senha e deriva a chave localmente. A senha não atravessa
a rede. Depois ele valida o beacon e abre a conexão.

Somente a chave derivada é salva fora do repositório em
`~/Documents/.dragonbrx/network.key`; a senha não aparece no histórico nem é
persistida.

Não publique a senha, não a envie em issue e não a coloque no repositório.

## 3. Iniciar o worker

Nas próximas vezes, basta:

```sh
cd ~/Documents/DragonBRX-Cognitive-System
sh scripts/bootstrap-ios.sh
```

Se o iOS pedir acesso à rede local, permita para o a-Shell. O iPhone e o
notebook precisam estar no mesmo SSID normal. Redes de convidados costumam
ativar isolamento de clientes e impedir que os dispositivos se enxerguem.

Mantenha:

- a tela do a-Shell aberta;
- o iPhone conectado à energia em trabalhos maiores;
- o bloqueio automático desativado somente durante o teste, se desejar;
- lotes pequenos, para que uma suspensão perca pouco tempo.

Ao voltar ao a-Shell depois de uma suspensão, execute o mesmo comando. Não
apague `ios-worker-state.json`: ele contém apenas resultados pendentes, não a
chave, e permite a retomada idempotente.

## 4. Testar a conexão

No console do notebook:

```json
{"type":"status"}
```

Depois envie uma tarefa de inventário:

```json
{"type":"task","name":"inventariar iPhone","capability":"system_info","inputs":{},"expected":["worker","ios-a-shell"],"cost":0.01,"risk":0.0}
```

Teste a primitiva numérica real:

```json
{"type":"task","name":"calcular gradiente de microlote","capability":"linear_gradient","inputs":{"features":[[1,2],[3,4]],"targets":[1,2],"weights":[0,0],"bias":0},"expected":["loss","gradient"],"cost":0.05,"risk":0.0}
```

O resultado esperado contém loss MSE `2.5`, gradiente `[-7.0, -10.0]` e
gradiente do bias `-3.0`.

## Capacidades iniciais

- `system_info`: plataforma, Python, arquitetura e CPUs;
- `text_statistics`: contagem e SHA-256 de texto;
- `sha256_chunks`: hashes de até 1024 fragmentos, limitados a 512 KiB;
- `linear_gradient`: loss e gradiente MSE de regressão linear, limitado a 512
  amostras por 128 parâmetros.

`linear_gradient` é uma primitiva comprovável de treinamento distribuído, não
um treinador completo de LLM. Novas capacidades precisam ser funções
explícitas, limitadas e testadas. O notebook nunca envia comandos de shell.

## Diagnóstico

- **Timeout:** confirme IPv4, mesma rede, perfil `Private` e firewall.
- **Descoberta falhou:** permita rede local para o a-Shell e libere UDP `9998`
  no perfil privado; como fallback execute
  `sh scripts/bootstrap-ios.sh --host IP_DO_NOTEBOOK`.
- **Registro recusado:** as chaves diferem ou o relógio de um dispositivo está
  fora da janela do protocolo.
- **Conecta e pausa:** comportamento esperado quando o a-Shell sai do primeiro
  plano; reabra e execute o mesmo comando.
- **Nenhum agente disponível:** a capacidade pedida não foi habilitada no
  worker ou o iPhone está suspenso.
- **Rede de convidados:** desative `AP/client isolation` ou use o SSID principal.
