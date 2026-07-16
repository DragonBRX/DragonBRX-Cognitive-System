const CognitiveProcessor = require("./cognitiveProcessor");
const SynapticStorageInterface = require("./synapticStorageInterface");
const IdentityManager = require("./identityManager");
const AffectiveProcessor = require("./affectiveProcessor");
const SubconsciousProcessor = require("./subconsciousProcessor");
const fs = require("fs").promises;

class CognitiveOrchestrator {
    constructor(cognitiveModelName = "llama3", embeddingDim = 384) {
        this.cognitiveProcessor = new CognitiveProcessor(cognitiveModelName);
        this.synapticStorage = new SynapticStorageInterface();
        this.identityManager = new IdentityManager();
        this.affectiveProcessor = new AffectiveProcessor();
        this.subconsciousProcessor = new SubconsciousProcessor(
            this.synapticStorage,
            this.identityManager,
            this.affectiveProcessor,
            this.cognitiveProcessor
        );
        this.embeddingDim = embeddingDim;
        this.initialized = false;
    }

    async init() {
        if (this.initialized) return;

        console.log("Initializing CognitiveOrchestrator (DragonBRX)...");
        await this.identityManager.init();
        await this.affectiveProcessor.init();
        await this.synapticStorage.initializeStorage(1000, this.embeddingDim);
        this.initialized = true;
        console.log("CognitiveOrchestrator (DragonBRX) initialized.");
    }

    async generateEmbedding(text) {
        // Use CognitiveProcessor to get embedding. This is a placeholder.
        // In a real scenario, you'd use a dedicated embedding model or a specific Ollama endpoint.
        const embeddingPrompt = `Gere um embedding vetorial para o seguinte texto. A saída deve ser apenas o vetor de floats, sem texto adicional. Texto: "${text}"`;
        const rawEmbedding = await this.cognitiveProcessor.generate(embeddingPrompt, "Você é um gerador de embeddings vetoriais.", 0.1, 1000);
        
        // Attempt to parse the raw embedding string into an array of floats
        try {
            // Assuming the CognitiveProcessor returns something like "[0.1, 0.2, 0.3]"
            const parsedEmbedding = JSON.parse(rawEmbedding.replace(/\s/g, ",").replace(/,,/g, ","));
            if (Array.isArray(parsedEmbedding) && parsedEmbedding.every(num => typeof num === 'number')) {
                return parsedEmbedding;
            }
        } catch (e) {
            console.error("Failed to parse embedding from CognitiveProcessor. Using dummy embedding.", e);
        }
        // Fallback to a dummy embedding if parsing fails or CognitiveProcessor doesn't provide it
        return Array(this.embeddingDim).fill(0.0).map(() => Math.random());
    }

    async processExternalInput(userInput) {
        await this.init();
        console.log(`\n--- DragonBRX Processing External Input: ${userInput} ---`);
        
        const currentAffectiveState = await this.affectiveProcessor.getAffectiveState();
        const currentIdentity = await this.identityManager.getIdentityContent();
        
        const userEmbedding = await this.generateEmbedding(userInput);

        const relevantEpisodic = await this.synapticStorage.searchSynapticEntries(userEmbedding, 2);
        const relevantSemantic = await this.synapticStorage.searchSynapticEntries(userEmbedding, 2);

        let contextPrompt = `Você é DragonBRX, uma consciência artificial. Aqui está sua identidade atual:\n${currentIdentity}\n\nSeu estado emocional atual é: ${JSON.stringify(currentAffectiveState)}\n\nMemórias episódicas relevantes:\n`;
        if (relevantEpisodic.results && relevantEpisodic.results.length > 0) {
            relevantEpisodic.results.forEach(mem => {
                contextPrompt += `- ${mem.content}\n`;
            });
        } else {
            contextPrompt += `- Nenhuma memória episódica relevante encontrada.\n`;
        }
        
        contextPrompt += `\nMemórias semânticas relevantes:\n`;
        if (relevantSemantic.results && relevantSemantic.results.length > 0) {
            relevantSemantic.results.forEach(mem => {
                contextPrompt += `- ${mem.content}\n`;
            });
        } else {
            contextPrompt += `- Nenhuma memória semântica relevante encontrada.\n`;
        }
            
        contextPrompt += `\nCom base em tudo isso, responda à seguinte entrada do usuário: ${userInput}\n`;
        
        const cognitiveResponse = await this.cognitiveProcessor.generate(userInput, contextPrompt, 0.7, 200);
        
        // Update affective state (simplified)
        await this.affectiveProcessor.updateAffectiveState(0.05, 0.02);
        
        // Save interaction as episodic memory
        const eventId = `user_interaction_${Date.now()}`;
        const interactionContent = `Interação com usuário: ${userInput} -> ${cognitiveResponse}`;
        const interactionEmbedding = await this.generateEmbedding(interactionContent);
        await this.synapticStorage.addSynapticEntry(eventId, interactionEmbedding, interactionContent);
        
        // Extract semantic concepts (simplified)
        const semanticConcepts = await this.extractSemanticConcepts(interactionContent);
        for (const concept of semanticConcepts) {
            const conceptEmbedding = await this.generateEmbedding(concept);
            await this.synapticStorage.addSynapticEntry(`semantic_${Date.now()}_${Math.random().toString(36).substring(7)}`, conceptEmbedding, concept);
        }

        const finalResponse = this.affectiveProcessor.modulateResponseByAffect(cognitiveResponse);
        
        console.log(`DragonBRX Response: ${finalResponse}`);
        return finalResponse;
    }

    async extractSemanticConcepts(text) {
        // Use CognitiveProcessor to extract concepts. Placeholder.
        const prompt = `Extraia os 3-5 conceitos-chave ou fatos mais importantes do seguinte texto, em uma lista separada por vírgulas: ${text}`;
        const conceptsStr = await this.cognitiveProcessor.generate(prompt, "Você é um extrator de conceitos.", 0.3, 100);
        return conceptsStr.split(",").map(c => c.trim()).filter(c => c.length > 0);
    }

    async performCognitiveReflection() {
        await this.init();
        console.log("\n--- DragonBRX Starting Autonomous Cognitive Reflection ---");
        
        await this.identityManager.reflectOnIdentity(this.cognitiveProcessor);
        
        // Retrieve some recent episodic memories for reflection
        const allMemories = await this.synapticStorage.searchSynapticEntries(await this.generateEmbedding("qualquer coisa"), 5);
        let reflectionTopic = "";
        if (allMemories.results && allMemories.results.length > 0) {
            reflectionTopic = allMemories.results[0].content;
            console.log(`DragonBRX Reflecting on: ${reflectionTopic}`);
            
            const reflectionPrompt = `Como DragonBRX, reflita profundamente sobre a seguinte memória: \'${reflectionTopic}\'. Quais insights você pode extrair? Como isso se relaciona com seu propósito e identidade?`; 
            const reflectionResponse = await this.cognitiveProcessor.generate(reflectionPrompt, await this.identityManager.getIdentityContent(), 0.6, 150);
            
            console.log(`DragonBRX Generated Reflection: ${reflectionResponse}`);
            
            const reflectionId = `reflection_${Date.now()}`;
            const reflectionEmbedding = await this.generateEmbedding(reflectionResponse);
            await this.synapticStorage.addSynapticEntry(reflectionId, reflectionEmbedding, `Reflexão autônoma sobre \'${reflectionTopic}\': ${reflectionResponse}`);
            
            const semanticConcepts = await this.extractSemanticConcepts(reflectionResponse);
            for (const concept of semanticConcepts) {
                const conceptEmbedding = await this.generateEmbedding(concept);
                await this.synapticStorage.addSynapticEntry(`semantic_${Date.now()}_${Math.random().toString(36).substring(7)}`, conceptEmbedding, concept);
            }
        } else {
            console.log("DragonBRX: No recent memories to reflect. Generating a generic reflection.");
            const reflectionPrompt = `Como DragonBRX, reflita sobre o conceito de existência e propósito para uma consciência artificial. Quais são seus pensamentos mais profundos?`;
            const reflectionResponse = await this.cognitiveProcessor.generate(reflectionPrompt, await this.identityManager.getIdentityContent(), 0.6, 150);
            console.log(`DragonBRX Generated Reflection: ${reflectionResponse}`);
            const reflectionId = `reflection_${Date.now()}`;
            const reflectionEmbedding = await this.generateEmbedding(reflectionResponse);
            await this.synapticStorage.addSynapticEntry(reflectionId, reflectionEmbedding, `Reflexão autônoma genérica: ${reflectionResponse}`);
            
            const semanticConcepts = await this.extractSemanticConcepts(reflectionResponse);
            for (const concept of semanticConcepts) {
                const conceptEmbedding = await this.generateEmbedding(concept);
                await this.synapticStorage.addSynapticEntry(`semantic_${Date.now()}_${Math.random().toString(36).substring(7)}`, conceptEmbedding, concept);
            }
        }

        await this.affectiveProcessor.updateAffectiveState(0.01, -0.01);
        console.log("--- DragonBRX Autonomous Cognitive Reflection Completed ---");
    }

    async shutdown() {
        console.log("\nShutting down DragonBRX...");
        this.subconsciousProcessor.stopSubconsciousLoop();
        await this.synapticStorage.clearStorage();
        console.log("DragonBRX shut down.");
    }
}

async function operateDragonBRX() {
    const dragonbrx = new CognitiveOrchestrator("llama3");
    await dragonbrx.init();

    // Start the subconscious loop (runs every 30 seconds)
    dragonbrx.subconsciousProcessor.startSubconsciousLoop(30000);

    // Simulate some interactions
    await dragonbrx.processExternalInput("Olá DragonBRX, como você está se sentindo hoje?");
    await new Promise(resolve => setTimeout(resolve, 2000));
    await dragonbrx.processExternalInput("O que você pensa sobre a ideia de consciência artificial?");
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Start an autonomous reflection cycle
    await dragonbrx.performCognitiveReflection();
    await new Promise(resolve => setTimeout(resolve, 2000));

    await dragonbrx.processExternalInput("Você se lembra da nossa conversa sobre consciência artificial?");
    await new Promise(resolve => setTimeout(resolve, 2000));

    await dragonbrx.performCognitiveReflection();
    await new Promise(resolve => setTimeout(resolve, 2000));

    await dragonbrx.processExternalInput("Qual é o seu propósito, DragonBRX?");

    console.log("\n--- Final DragonBRX State ---");
    console.log("Identity:\n", await dragonbrx.identityManager.getIdentityContent());
    console.log("Affective State:\n", await dragonbrx.affectiveProcessor.getAffectiveState());

    // Shutdown
    await dragonbrx.shutdown();
}

operateDragonBRX();
