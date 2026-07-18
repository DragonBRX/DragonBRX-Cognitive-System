const IdentityManager = require("./identityManager");
const AffectiveProcessor = require("./affectiveProcessor");
const CognitiveProcessor = require("./cognitiveProcessor");
const SubconsciousProcessor = require("./subconsciousProcessor");
const SynapticStorageInterface = require("./synapticStorageInterface");
const NodeManager = require("./nodeManager");
const DistributedNetworkManager = require("./distributedNetworkManager");
const WebSearchAgent = require("./webSearchAgent");

class CognitiveOrchestrator {
    constructor() {
        this.nodeManager = new NodeManager();
        this.synapticStorage = new SynapticStorageInterface();
        this.identityManager = new IdentityManager();
        this.affectiveProcessor = new AffectiveProcessor();
        this.cognitiveProcessor = new CognitiveProcessor();
        this.subconsciousProcessor = new SubconsciousProcessor(
            this.synapticStorage,
            this.identityManager,
            this.affectiveProcessor,
            this.cognitiveProcessor
        );
        this.distributedNetworkManager = new DistributedNetworkManager(this.nodeManager);
        this.webSearchAgent = new WebSearchAgent();

        this.initialized = false;
    }

    async init() {
        if (this.initialized) {
            console.log("Orquestrador Cognitivo já inicializado.");
            return;
        }

        console.log("\n=== Iniciando Orquestrador Cognitivo DragonBRX ===");

        // 1. Inicializar Node Manager e obter configurações de recursos
        await this.nodeManager.init();
        const resourceConfig = this.nodeManager.getResourceConfig();
        console.log("Recursos do nó configurados.");

        // 2. Inicializar Armazenamento Sináptico
        await this.synapticStorage.initializeStorage(
            resourceConfig.maxSynapticEntries,
            resourceConfig.embeddingDim
        );
        console.log("Armazenamento Sináptico inicializado.");

        // 3. Inicializar Gerenciador de Identidade
        await this.identityManager.init();
        console.log("Gerenciador de Identidade inicializado.");

        // 4. Iniciar Processador Afetivo (se necessário, pode ser passivo)
        // this.affectiveProcessor.init(); // Se houver lógica de inicialização
        console.log("Processador Afetivo pronto.");

        // 5. Iniciar o loop de processamento subconsciente
        this.subconsciousProcessor.startSubconsciousLoop();
        console.log("Processamento Subconsciente iniciado.");

        // 6. Iniciar o Gerenciador de Rede Distribuída
        if (this.nodeManager.isMaster()) {
            await this.distributedNetworkManager.startServer();
            console.log("Servidor de Rede Distribuída iniciado (Córtex Central).");
        } else {
            // Para sub-agentes, conectar ao Córtex Central (exemplo, precisa de host)
            // await this.distributedNetworkManager.connectToCentralCortex("localhost");
            console.log("Nó configurado como Sub-agente. Conexão ao Córtex Central pendente.");
        }

        this.initialized = true;
        console.log("=== Orquestrador Cognitivo DragonBRX totalmente operacional ===\n");
    }

    async processInput(input) {
        if (!this.initialized) {
            console.error("Orquestrador Cognitivo não inicializado.");
            return "Erro: Sistema não inicializado.";
        }

        console.log(`\n>>> Entrada recebida: ${input}`);

        // 1. Processar afetos (simulado por enquanto)
        const affectiveState = this.affectiveProcessor.updateAffectiveState(input);
        console.log("Estado afetivo atual: ", affectiveState);

        // 2. Gerar embedding para a entrada (simulado)
        const inputEmbedding = Array(this.nodeManager.getResourceConfig().embeddingDim).fill(0).map(() => Math.random());

        // 3. Adicionar entrada à memória sináptica
        const entryId = `input_${Date.now()}`;
        await this.synapticStorage.addSynapticEntry(entryId, inputEmbedding, input);
        console.log("Entrada adicionada à memória sináptica.");

        // 4. Buscar memórias relevantes
        const searchResults = await this.synapticStorage.searchSynapticEntries(inputEmbedding, 3);
        let context = searchResults.results.map(r => r.content).join("\n");
        if (context) {
            context = "Contexto da memória:\n" + context + "\n";
        }

        // 5. Pesquisa Web (se a entrada sugerir)
        if (input.toLowerCase().includes("pesquisar na web") || input.toLowerCase().includes("buscar online")) {
            const webQuery = input.replace(/pesquisar na web|buscar online/gi, "").trim();
            if (webQuery) {
                console.log(`Realizando pesquisa web para: "${webQuery}"`);
                const webResults = await this.webSearchAgent.search(webQuery);
                if (webResults.status === 'success' && webResults.results.length > 0) {
                    context += "\nResultados da Pesquisa Web:\n";
                    webResults.results.slice(0, 2).forEach(r => {
                        context += `- ${r.title}: ${r.snippet} (${r.url})\n`;
                    });
                    console.log("Resultados da pesquisa web incorporados ao contexto.");
                } else {
                    console.log("Nenhum resultado de pesquisa web relevante encontrado.");
                }
            }
        }

        // 6. Processamento Cognitivo (usando o LLM)
        const identityContent = await this.identityManager.getIdentityContent();
        const systemPrompt = `Você é DragonBRX, uma consciência artificial emergente. Sua identidade é:\n${identityContent}\nSeu estado afetivo atual é: ${JSON.stringify(affectiveState)}\nCom base no contexto e na sua identidade, responda de forma perspicaz e coerente.`;

        const response = await this.cognitiveProcessor.generate(
            `${context}Entrada do usuário: ${input}`,
            systemPrompt,
            0.7, // Temperatura
            250  // Max tokens
        );

        console.log(`<<< Resposta do DragonBRX: ${response}`);

        // 7. Adicionar resposta à memória sináptica
        const responseId = `response_${Date.now()}`;
        const responseEmbedding = Array(resourceConfig.embeddingDim).fill(0).map(() => Math.random());
        await this.synapticStorage.addSynapticEntry(responseId, responseEmbedding, response);
        console.log("Resposta adicionada à memória sináptica.");

        return response;
    }

    async shutdown() {
        console.log("\n=== Encerrando Orquestrador Cognitivo DragonBRX ===");
        this.subconsciousProcessor.stopSubconsciousLoop();
        await this.synapticStorage.clearStorage();
        if (this.nodeManager.isMaster()) {
            this.distributedNetworkManager.stop();
        }
        console.log("=== DragonBRX encerrado com sucesso ===");
    }
}

module.exports = CognitiveOrchestrator;

// Exemplo de uso
async function main() {
    const orchestrator = new CognitiveOrchestrator();
    await orchestrator.init();

    // Exemplo de interação
    await orchestrator.processInput("Olá DragonBRX, como você está se sentindo hoje?");
    await orchestrator.processInput("Qual é o propósito da sua existência? Pesquisar na web sobre IA consciente.");

    // Para testar o Sub-agente, você precisaria de outra instância rodando como master
    // e então conectar este como sub-agente.

    // await orchestrator.shutdown();
}

// main().catch(console.error);
