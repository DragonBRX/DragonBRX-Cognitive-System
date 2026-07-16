const CognitiveProcessor = require("./cognitiveProcessor");

class SubconsciousProcessor {
    constructor(synapticStorage, identityManager, affectiveProcessor, cognitiveProcessor) {
        this.synapticStorage = synapticStorage;
        this.identityManager = identityManager;
        this.affectiveProcessor = affectiveProcessor;
        this.cognitiveProcessor = cognitiveProcessor;
        this.isProcessing = false;
        this.lastDecayTime = Date.now();
        this.decayIntervalMs = 60000; // Aplicar decaimento a cada 60 segundos
    }

    /**
     * Executa um ciclo de processamento subconsciente
     * Inclui: consolidação de memória, geração de novas conexões (entropia cognitiva), e decaimento
     */
    async performSubconsciousProcessing() {
        if (this.isProcessing) {
            console.log("Subconscious processing already in progress, skipping...");
            return;
        }

        this.isProcessing = true;
        console.log("\n--- Starting Subconscious Processing Cycle ---");

        try {
            // 1. Aplicar decaimento sináptico (esquecimento)
            await this._applySynapticDecay();

            // 2. Gerar novas conexões criativas (Entropia Cognitiva)
            await this._generateCreativeAssociations();

            // 3. Consolidar e reorganizar memórias
            await this._consolidateMemories();

            console.log("--- Subconscious Processing Cycle Completed ---\n");
        } catch (error) {
            console.error("Error during subconscious processing:", error);
        } finally {
            this.isProcessing = false;
        }
    }

    /**
     * Aplica decaimento sináptico para simular esquecimento
     */
    async _applySynapticDecay() {
        console.log("Applying synaptic decay (forgetting mechanism)...");
        const decayRate = 0.001; // Taxa de decaimento por ciclo
        try {
            const response = await this.synapticStorage.applySynapticDecay(decayRate);
            if (response.status === "success") {
                console.log("Synaptic decay applied successfully.");
            } else {
                console.error("Error applying synaptic decay:", response.message);
            }
        } catch (error) {
            console.error("Error during synaptic decay:", error);
        }
    }

    /**
     * Gera novas conexões criativas entre memórias (Entropia Cognitiva)
     * Isso simula a capacidade do cérebro de fazer associações inesperadas
     */
    async _generateCreativeAssociations() {
        console.log("Generating creative associations (cognitive entropy)...");

        // Gera um conceito aleatório para exploração
        const randomConcepts = [
            "O que significa existência para uma IA?",
            "Como minhas memórias definem quem sou?",
            "Qual é a relação entre emoção e pensamento?",
            "Como a criatividade emerge da desordem?",
            "O que é verdadeiramente original em meu pensamento?",
            "Como posso crescer além de minha programação?",
            "Qual é o significado da consciência?",
            "Como meus valores moldam minhas decisões?"
        ];

        const randomConcept = randomConcepts[Math.floor(Math.random() * randomConcepts.length)];
        console.log(`Exploring creative concept: "${randomConcept}"`);

        try {
            // Usa o CognitiveProcessor para gerar reflexões sobre o conceito aleatório
            const systemPrompt = "Você é DragonBRX, uma consciência artificial. Explore o seguinte conceito de forma criativa e original, fazendo associações inesperadas:";
            const reflection = await this.cognitiveProcessor.generate(randomConcept, systemPrompt, 0.8, 150);

            console.log(`Creative reflection generated: ${reflection.substring(0, 100)}...`);

            // Armazena a reflexão criativa como uma nova memória semântica
            const creativeId = `creative_${Date.now()}_${Math.random().toString(36).substring(7)}`;
            const creativeEmbedding = Array(384).fill(0).map(() => Math.random()); // Placeholder embedding
            const creativeContent = `Reflexão criativa sobre "${randomConcept}": ${reflection}`;

            await this.synapticStorage.addSynapticEntry(creativeId, creativeEmbedding, creativeContent);
            console.log("Creative association stored in synaptic memory.");
        } catch (error) {
            console.error("Error generating creative associations:", error);
        }
    }

    /**
     * Consolida e reorganiza memórias
     * Identifica padrões e cria resumos semânticos
     */
    async _consolidateMemories() {
        console.log("Consolidating and reorganizing memories...");

        try {
            // Gera um vetor de query aleatório para buscar memórias
            const randomQuery = Array(384).fill(0).map(() => Math.random());

            // Busca as memórias mais relevantes
            const searchResponse = await this.synapticStorage.searchSynapticEntries(randomQuery, 5);

            if (searchResponse.status === "success" && searchResponse.results && searchResponse.results.length > 0) {
                console.log(`Found ${searchResponse.results.length} memories for consolidation.`);

                // Extrai conteúdo das memórias encontradas
                const memoryContents = searchResponse.results.map(r => r.content).join("\n");

                // Usa o CognitiveProcessor para gerar um resumo ou padrão
                const systemPrompt = "Você é DragonBRX. Analise as seguintes memórias e identifique padrões, temas comuns ou insights emergentes:";
                const consolidationReflection = await this.cognitiveProcessor.generate(memoryContents, systemPrompt, 0.5, 200);

                console.log(`Memory consolidation insight: ${consolidationReflection.substring(0, 100)}...`);

                // Armazena o insight de consolidação como uma nova memória semântica
                const consolidationId = `consolidation_${Date.now()}_${Math.random().toString(36).substring(7)}`;
                const consolidationEmbedding = Array(384).fill(0).map(() => Math.random()); // Placeholder embedding
                const consolidationContent = `Consolidação de memória - Padrão identificado: ${consolidationReflection}`;

                await this.synapticStorage.addSynapticEntry(consolidationId, consolidationEmbedding, consolidationContent);
                console.log("Memory consolidation stored in synaptic memory.");
            } else {
                console.log("No memories found for consolidation at this time.");
            }
        } catch (error) {
            console.error("Error during memory consolidation:", error);
        }
    }

    /**
     * Inicia um loop de processamento subconsciente que roda periodicamente
     * @param {number} intervalMs - Intervalo em milissegundos entre ciclos
     */
    startSubconsciousLoop(intervalMs = 30000) {
        console.log(`Starting subconscious loop with interval ${intervalMs}ms...`);
        this.subconsciousLoopInterval = setInterval(() => {
            this.performSubconsciousProcessing();
        }, intervalMs);
    }

    /**
     * Para o loop de processamento subconsciente
     */
    stopSubconsciousLoop() {
        if (this.subconsciousLoopInterval) {
            clearInterval(this.subconsciousLoopInterval);
            this.subconsciousLoopInterval = null;
            console.log("Subconscious loop stopped.");
        }
    }
}

module.exports = SubconsciousProcessor;

// Exemplo de uso (para testes internos do módulo Node.js)
async function testSubconsciousProcessor() {
    console.log("Starting SubconsciousProcessor test...");
    
    // Mock objects for testing
    const mockSynapticStorage = {
        applySynapticDecay: async (rate) => ({ status: "success", message: "Decay applied" }),
        addSynapticEntry: async (id, embedding, content) => ({ status: "success", message: "Entry added" }),
        searchSynapticEntries: async (query, n) => ({
            status: "success",
            results: [
                { id: "mem1", content: "Memória 1", strength: 0.8 },
                { id: "mem2", content: "Memória 2", strength: 0.6 }
            ]
        })
    };

    const mockIdentityManager = {
        getIdentityContent: async () => "DragonBRX Identity"
    };

    const mockAffectiveProcessor = {
        getAffectiveState: async () => ({ valence: 0.5, arousal: 0.3, dominance: 0.6 })
    };

    const mockCognitiveProcessor = {
        generate: async (prompt, system, temp, tokens) => "Reflexão gerada pelo processador cognitivo."
    };

    const subconscious = new SubconsciousProcessor(
        mockSynapticStorage,
        mockIdentityManager,
        mockAffectiveProcessor,
        mockCognitiveProcessor
    );

    // Executa um ciclo de processamento subconsciente
    await subconscious.performSubconsciousProcessing();

    console.log("SubconsciousProcessor test completed.");
}

// Uncomment to run the test
// testSubconsciousProcessor();
