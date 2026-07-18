/**
 * Node Manager - Gerenciador de Nós Distribuídos para DragonBRX
 * 
 * Responsável por:
 * 1. Detectar o hardware do dispositivo (RAM, CPU, SO)
 * 2. Classificar o nó como "Córtex Central" (PC) ou "Sub-agente" (Termux/Celular)
 * 3. Configurar limites de recursos dinamicamente
 * 4. Preparar o dispositivo para se conectar à rede de agentes
 */

const os = require("os");
const fs = require("fs").promises;
const path = require("path");

class NodeManager {
    constructor() {
        this.nodeProfile = null;
        this.hardwareInfo = null;
        this.isTermux = this._detectTermux();
        this.configPath = path.join(os.homedir(), ".dragonbrx", "node_config.json");
    }

    /**
     * Detecta se está rodando no Termux (Android)
     */
    _detectTermux() {
        const prefix = process.env.PREFIX || "";
        return prefix.includes("com.termux") || process.env.TERMUX_VERSION !== undefined;
    }

    /**
     * Coleta informações de hardware do dispositivo
     */
    _collectHardwareInfo() {
        const cpus = os.cpus();
        const totalMemory = os.totalmem();
        const freeMemory = os.freemem();
        const platform = os.platform();
        const arch = os.arch();

        this.hardwareInfo = {
            platform,
            arch,
            cpuCount: cpus.length,
            cpuModel: cpus[0]?.model || "Unknown",
            totalMemoryGB: (totalMemory / (1024 ** 3)).toFixed(2),
            freeMemoryGB: (freeMemory / (1024 ** 3)).toFixed(2),
            usedMemoryGB: ((totalMemory - freeMemory) / (1024 ** 3)).toFixed(2),
            isTermux: this.isTermux,
            timestamp: new Date().toISOString()
        };

        return this.hardwareInfo;
    }

    /**
     * Classifica o nó em um perfil baseado no hardware
     */
    _classifyNodeProfile() {
        const info = this.hardwareInfo;
        const totalMemoryGB = parseFloat(info.totalMemoryGB);
        const cpuCount = info.cpuCount;

        let profile = {
            type: "UNKNOWN",
            tier: 0,
            maxSynapticEntries: 1000,
            embeddingDim: 384,
            maxConcurrentTasks: 1,
            recommendedModelSize: "small",
            role: "sub-agent"
        };

        // Classificação baseada em RAM e CPU
        if (totalMemoryGB >= 8 && cpuCount >= 4 && !info.isTermux) {
            // Córtex Central - PC potente
            profile = {
                type: "CORTEX_CENTRAL",
                tier: 1,
                maxSynapticEntries: 100000,
                embeddingDim: 768,
                maxConcurrentTasks: 8,
                recommendedModelSize: "large",
                role: "master",
                description: "Nó Mestre - Processamento Pesado e Orquestração"
            };
        } else if (totalMemoryGB >= 4 && cpuCount >= 2 && !info.isTermux) {
            // Agente Potente - PC moderado
            profile = {
                type: "AGENT_POTENT",
                tier: 2,
                maxSynapticEntries: 50000,
                embeddingDim: 512,
                maxConcurrentTasks: 4,
                recommendedModelSize: "medium",
                role: "agent",
                description: "Agente Potente - Processamento Moderado"
            };
        } else if (totalMemoryGB >= 2 && cpuCount >= 2) {
            // Sub-agente Padrão - Celular ou PC antigo
            profile = {
                type: "SUBAGENT_STANDARD",
                tier: 3,
                maxSynapticEntries: 10000,
                embeddingDim: 256,
                maxConcurrentTasks: 2,
                recommendedModelSize: "small",
                role: "sub-agent",
                description: "Sub-agente Padrão - Tarefas Leves"
            };
        } else {
            // Sub-agente Leve - Celular 2G RAM
            profile = {
                type: "SUBAGENT_LIGHT",
                tier: 4,
                maxSynapticEntries: 1000,
                embeddingDim: 128,
                maxConcurrentTasks: 1,
                recommendedModelSize: "tiny",
                role: "sub-agent",
                description: "Sub-agente Leve - Tarefas Muito Leves (2GB RAM)"
            };
        }

        this.nodeProfile = profile;
        return profile;
    }

    /**
     * Inicializa o Node Manager
     */
    async init() {
        console.log("\n=== Inicializando Node Manager do DragonBRX ===");
        
        // Coletar informações de hardware
        this._collectHardwareInfo();
        console.log("\nHardware Detectado:");
        console.log(`   Plataforma: ${this.hardwareInfo.platform} (${this.hardwareInfo.arch})`);
        console.log(`   CPU: ${this.hardwareInfo.cpuCount} núcleos - ${this.hardwareInfo.cpuModel}`);
        console.log(`   RAM Total: ${this.hardwareInfo.totalMemoryGB} GB`);
        console.log(`   RAM Livre: ${this.hardwareInfo.freeMemoryGB} GB`);
        console.log(`   Termux: ${this.hardwareInfo.isTermux ? "SIM" : "NÃO"}`);

        // Classificar o nó
        this._classifyNodeProfile();
        console.log(`\nPerfil do Nó Classificado:`);
        console.log(`   Tipo: ${this.nodeProfile.type}`);
        console.log(`   Tier: ${this.nodeProfile.tier}`);
        console.log(`   Descrição: ${this.nodeProfile.description}`);
        console.log(`   Papel: ${this.nodeProfile.role}`);
        console.log(`   Tamanho Recomendado do Modelo: ${this.nodeProfile.recommendedModelSize}`);
        console.log(`   Entradas Sinápticas Máximas: ${this.nodeProfile.maxSynapticEntries}`);
        console.log(`   Dimensão de Embedding: ${this.nodeProfile.embeddingDim}`);
        console.log(`   Tarefas Concorrentes Máximas: ${this.nodeProfile.maxConcurrentTasks}`);

        // Salvar configuração
        await this._saveNodeConfig();
        console.log(`\nConfiguração salva em: ${this.configPath}`);
    }

    /**
     * Salva a configuração do nó em arquivo
     */
    async _saveNodeConfig() {
        try {
            const configDir = path.dirname(this.configPath);
            await fs.mkdir(configDir, { recursive: true });

            const config = {
                hardware: this.hardwareInfo,
                profile: this.nodeProfile,
                savedAt: new Date().toISOString()
            };

            await fs.writeFile(this.configPath, JSON.stringify(config, null, 2), "utf-8");
        } catch (error) {
            console.error("Erro ao salvar configuração do nó:", error);
        }
    }

    /**
     * Carrega a configuração do nó do arquivo
     */
    async loadNodeConfig() {
        try {
            const configContent = await fs.readFile(this.configPath, "utf-8");
            const config = JSON.parse(configContent);
            this.hardwareInfo = config.hardware;
            this.nodeProfile = config.profile;
            return config;
        } catch (error) {
            console.warn("Configuração anterior não encontrada. Executando detecção de hardware...");
            await this.init();
        }
    }

    /**
     * Retorna as configurações de recursos para o Orquestrador Cognitivo
     */
    getResourceConfig() {
        return {
            maxSynapticEntries: this.nodeProfile.maxSynapticEntries,
            embeddingDim: this.nodeProfile.embeddingDim,
            maxConcurrentTasks: this.nodeProfile.maxConcurrentTasks,
            modelSize: this.nodeProfile.recommendedModelSize,
            role: this.nodeProfile.role,
            tier: this.nodeProfile.tier
        };
    }

    /**
     * Retorna informações sobre o nó para a rede distribuída
     */
    getNodeInfo() {
        return {
            profile: this.nodeProfile,
            hardware: this.hardwareInfo,
            status: "online",
            timestamp: new Date().toISOString()
        };
    }

    /**
     * Verifica se este nó é o Córtex Central (Mestre)
     */
    isMaster() {
        return this.nodeProfile.role === "master";
    }

    /**
     * Verifica se este nó é um Sub-agente
     */
    isSubAgent() {
        return this.nodeProfile.role === "sub-agent";
    }

    /**
     * Retorna o status de saúde do nó
     */
    getHealthStatus() {
        const freeMemoryGB = parseFloat(this.hardwareInfo.freeMemoryGB);
        const totalMemoryGB = parseFloat(this.hardwareInfo.totalMemoryGB);
        const memoryUsagePercent = ((totalMemoryGB - freeMemoryGB) / totalMemoryGB) * 100;

        return {
            memoryUsagePercent: memoryUsagePercent.toFixed(2),
            isHealthy: memoryUsagePercent < 80,
            freeMemoryGB: freeMemoryGB.toFixed(2),
            warning: memoryUsagePercent > 70 ? "Uso de memória alto" : null
        };
    }
}

// Teste do módulo
async function testNodeManager() {
    console.log("Iniciando teste do NodeManager...\n");
    const nodeManager = new NodeManager();
    await nodeManager.init();

    console.log("\nConfiguração de Recursos:");
    console.log(JSON.stringify(nodeManager.getResourceConfig(), null, 2));

    console.log("\nStatus de Saúde:");
    console.log(JSON.stringify(nodeManager.getHealthStatus(), null, 2));

    console.log("\nInformações do Nó:");
    console.log(JSON.stringify(nodeManager.getNodeInfo(), null, 2));
}

module.exports = NodeManager;

// Descomente para testar
// testNodeManager().catch(console.error);
