/**
 * Distributed Network Manager - Gerenciador de Rede Distribuída para DragonBRX
 * 
 * Responsável por:
 * 1. Gerenciar conexões entre nós (Córtex Central e Sub-agentes)
 * 2. Distribuir tarefas baseado na capacidade de cada nó
 * 3. Sincronizar memórias entre nós
 * 4. Monitorar a saúde da rede
 */

const net = require("net");
const EventEmitter = require("events");

class DistributedNetworkManager extends EventEmitter {
    constructor(nodeManager, port = 9999) {
        super();
        this.nodeManager = nodeManager;
        this.port = port;
        this.server = null;
        this.connectedNodes = new Map();
        this.taskQueue = [];
        this.isMaster = nodeManager.isMaster();
    }

    /**
     * Inicia o servidor de rede (para o Córtex Central)
     */
    async startServer() {
        if (!this.isMaster) {
            console.log("Aviso: Este nó não é o Córtex Central. Use connectToCentralCortex() para se conectar.");
            return;
        }

        this.server = net.createServer((socket) => {
            console.log(`\nConexão estabelecida com Sub-agente: ${socket.remoteAddress}:${socket.remotePort}`);

            const nodeId = `node_${socket.remoteAddress}_${socket.remotePort}`;
            this.connectedNodes.set(nodeId, {
                socket,
                info: null,
                status: "connected",
                lastHeartbeat: Date.now(),
                tasksCompleted: 0
            });

            // Receber informações do nó
            socket.on("data", (data) => {
                this._handleNodeMessage(nodeId, data);
            });

            socket.on("end", () => {
                console.log(`\nSub-agente desconectado: ${nodeId}`);
                this.connectedNodes.delete(nodeId);
            });

            socket.on("error", (error) => {
                console.error(`Erro na conexão ${nodeId}:`, error);
                this.connectedNodes.delete(nodeId);
            });
        });

        this.server.listen(this.port, () => {
            console.log(`\nServidor de Rede Distribuída iniciado na porta ${this.port}`);
            console.log(`   Aguardando conexões de Sub-agentes...`);
        });
    }

    /**
     * Conecta este nó a um Córtex Central (para Sub-agentes)
     */
    async connectToCentralCortex(masterHost, masterPort = 9999) {
        if (this.isMaster) {
            console.log("Aviso: Este nó é o Córtex Central. Use startServer() para aceitar conexões.");
            return;
        }

        return new Promise((resolve, reject) => {
            const socket = net.createConnection(masterPort, masterHost, () => {
                console.log(`\nConectado ao Córtex Central em ${masterHost}:${masterPort}`);

                // Enviar informações do nó
                const nodeInfo = this.nodeManager.getNodeInfo();
                socket.write(JSON.stringify({
                    type: "node_info",
                    data: nodeInfo
                }) + "\n");

                // Receber tarefas do Córtex Central
                socket.on("data", (data) => {
                    this._handleMasterMessage(data);
                });

                socket.on("end", () => {
                    console.log("Desconectado do Córtex Central");
                });

                socket.on("error", (error) => {
                    console.error("Erro na conexão com o Córtex Central:", error);
                    reject(error);
                });

                resolve(socket);
            });

            socket.on("error", (error) => {
                console.error("Erro ao conectar ao Córtex Central:", error);
                reject(error);
            });
        });
    }

    /**
     * Processa mensagens recebidas de um Sub-agente
     */
    _handleNodeMessage(nodeId, data) {
        try {
            const message = JSON.parse(data.toString().trim());

            if (message.type === "node_info") {
                const node = this.connectedNodes.get(nodeId);
                if (node) {
                    node.info = message.data;
                    console.log(`Informações recebidas de ${nodeId}:`);
                    console.log(`   Tipo: ${message.data.profile.type}`);
                    console.log(`   RAM: ${message.data.hardware.totalMemoryGB} GB`);
                }
            } else if (message.type === "task_result") {
                console.log(`Resultado de tarefa recebido de ${nodeId}`);
                this.emit("task_result", { nodeId, result: message.data });
            } else if (message.type === "heartbeat") {
                const node = this.connectedNodes.get(nodeId);
                if (node) {
                    node.lastHeartbeat = Date.now();
                }
            }
        } catch (error) {
            console.error("Erro ao processar mensagem do nó:", error);
        }
    }

    /**
     * Processa mensagens recebidas do Córtex Central
     */
    _handleMasterMessage(data) {
        try {
            const message = JSON.parse(data.toString().trim());

            if (message.type === "task_assignment") {
                console.log(`Tarefa recebida do Córtex Central: ${message.data.taskId}`);
                this.emit("task_assigned", message.data);
            } else if (message.type === "sync_memory") {
                console.log(`Sincronização de memória recebida`);
                this.emit("memory_sync", message.data);
            }
        } catch (error) {
            console.error("Erro ao processar mensagem do Córtex Central:", error);
        }
    }

    /**
     * Distribui uma tarefa para um Sub-agente apropriado
     */
    async assignTask(task) {
        // Encontrar o nó mais adequado para a tarefa
        let bestNode = null;
        let bestScore = -1;

        for (const [nodeId, node] of this.connectedNodes) {
            if (node.status !== "connected") continue;

            // Calcular score baseado em capacidade e carga
            const capacity = node.info?.profile?.maxSynapticEntries || 1000;
            const taskRequirement = task.requiredCapacity || 1000;
            const score = capacity / taskRequirement;

            if (score > bestScore) {
                bestScore = score;
                bestNode = { nodeId, node };
            }
        }

        if (!bestNode) {
            console.warn("Nenhum Sub-agente disponível para a tarefa");
            return false;
        }

        // Enviar tarefa para o nó
        const taskMessage = JSON.stringify({
            type: "task_assignment",
            data: task
        }) + "\n";

        bestNode.node.socket.write(taskMessage);
        console.log(`Tarefa ${task.taskId} atribuída a ${bestNode.nodeId}`);
        return true;
    }

    /**
     * Retorna o status da rede
     */
    getNetworkStatus() {
        const nodes = Array.from(this.connectedNodes.values()).map(node => ({
            type: node.info?.profile?.type || "UNKNOWN",
            status: node.status,
            tasksCompleted: node.tasksCompleted,
            lastHeartbeat: new Date(node.lastHeartbeat).toISOString()
        }));

        return {
            isMaster: this.isMaster,
            connectedNodesCount: this.connectedNodes.size,
            nodes,
            timestamp: new Date().toISOString()
        };
    }

    /**
     * Para o servidor de rede
     */
    stop() {
        if (this.server) {
            this.server.close(() => {
                console.log("Servidor de rede distribuída encerrado.");
            });
        }
    }
}

module.exports = DistributedNetworkManager;

// Teste do módulo
async function testDistributedNetwork() {
    console.log("Teste do DistributedNetworkManager...\n");
    // Este teste seria mais complexo e requer múltiplos processos
    console.log("Veja a documentação para exemplos de uso.");
}

// Descomente para testar
// testDistributedNetwork().catch(console.error);
