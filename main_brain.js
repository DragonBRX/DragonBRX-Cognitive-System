const LLMProcessor = require("./llmProcessor");
const VectorMemoryWrapper = require("./vectorMemoryWrapper");
const EgoCore = require("./ego_core");
const AffectCore = require("./affect_core");
const fs = require("fs").promises;

class HumanizedAIBrain {
    constructor(llmModelName = "llama3", embeddingDim = 384) {
        this.llm = new LLMProcessor(llmModelName);
        this.vectorMemory = new VectorMemoryWrapper();
        this.ego = new EgoCore();
        this.affect = new AffectCore();
        this.embeddingDim = embeddingDim;
        this.initialized = false;
    }

    async init() {
        if (this.initialized) return;

        console.log("Initializing HumanizedAIBrain...");
        await this.ego.init();
        await this.affect.init();
        await this.vectorMemory.init(1000, this.embeddingDim); // Max 1000 entries, embedding dimension
        this.initialized = true;
        console.log("HumanizedAIBrain initialized.");
    }

    async getEmbedding(text) {
        // Use LLM to get embedding. This is a placeholder.
        // In a real scenario, you'd use a dedicated embedding model or a specific Ollama endpoint.
        const embeddingPrompt = `Gere um embedding vetorial para o seguinte texto. A saída deve ser apenas o vetor de floats, sem texto adicional. Texto: "${text}"`;
        const rawEmbedding = await this.llm.generate(embeddingPrompt, "Você é um gerador de embeddings vetoriais.", 0.1, 1000); // Low temp, high tokens for vector
        
        // Attempt to parse the raw embedding string into an array of floats
        try {
            // Assuming the LLM returns something like "[0.1, 0.2, 0.3]"
            const parsedEmbedding = JSON.parse(rawEmbedding.replace(/\s/g, ",").replace(/,,/g, ",")); // Basic cleanup
            if (Array.isArray(parsedEmbedding) && parsedEmbedding.every(num => typeof num === 'number')) {
                return parsedEmbedding;
            }
        } catch (e) {
            console.error("Failed to parse embedding from LLM. Using dummy embedding.", e);
        }
        // Fallback to a dummy embedding if parsing fails or LLM doesn't provide it
        return Array(this.embeddingDim).fill(0.0).map(() => Math.random());
    }

    async processInput(userInput) {
        await this.init();
        console.log(`\n--- Processing user input: ${userInput} ---`);
        
        const currentAffect = await this.affect.getAffectState();
        const currentEgo = await this.ego.getEgoContent();
        
        const userEmbedding = await this.getEmbedding(userInput);

        const relevantEpisodic = await this.vectorMemory.search(userEmbedding, 2);
        const relevantSemantic = await this.vectorMemory.search(userEmbedding, 2);

        let contextPrompt = `Você é uma inteligência artificial com a seguinte identidade:\n${currentEgo}\n\nSeu estado emocional atual é: ${JSON.stringify(currentAffect)}\n\nMemórias episódicas relevantes:\n`;
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
        
        const llmResponse = await this.llm.generate(userInput, contextPrompt, 0.7, 200);
        
        // Update affect state (simplified)
        await this.affect.updateAffectState(0.05, 0.02); // Slightly more positive and active
        
        // Save interaction as episodic memory
        const eventId = `user_interaction_${Date.now()}`;
        const interactionContent = `Interação com usuário: ${userInput} -> ${llmResponse}`;
        const interactionEmbedding = await this.getEmbedding(interactionContent);
        await this.vectorMemory.addEntry(eventId, interactionEmbedding, interactionContent);
        
        // Extract semantic concepts (simplified)
        const semanticConcepts = await this.extractSemanticConcepts(interactionContent);
        for (const concept of semanticConcepts) {
            const conceptEmbedding = await this.getEmbedding(concept);
            await this.vectorMemory.addEntry(`semantic_${Date.now()}_${Math.random().toString(36).substring(7)}`, conceptEmbedding, concept);
        }

        const finalResponse = this.affect.modulateResponseByAffect(llmResponse);
        
        console.log(`Final Response: ${finalResponse}`);
        return finalResponse;
    }

    async extractSemanticConcepts(text) {
        // Use LLM to extract concepts. Placeholder.
        const prompt = `Extraia os 3-5 conceitos-chave ou fatos mais importantes do seguinte texto, em uma lista separada por vírgulas: ${text}`;
        const conceptsStr = await this.llm.generate(prompt, "Você é um extrator de conceitos.", 0.3, 100);
        return conceptsStr.split(",").map(c => c.trim()).filter(c => c.length > 0);
    }

    async autonomousReflection() {
        await this.init();
        console.log("\n--- Starting autonomous reflection cycle ---");
        
        await this.ego.reflectOnEgo(this.llm); // LLM is passed, but EgoCore uses a placeholder for now
        
        // Retrieve some recent episodic memories for reflection
        // This is a simplified way to get 'recent' memories, a more robust system would track timestamps
        const allMemories = await this.vectorMemory.search(await this.getEmbedding("qualquer coisa"), 5); // Get 5 most 'general' memories
        let reflectionTopic = "";
        if (allMemories.results && allMemories.results.length > 0) {
            reflectionTopic = allMemories.results[0].content; // Reflect on the most relevant general memory
            console.log(`Reflecting on: ${reflectionTopic}`);
            
            const reflectionPrompt = `Com base na sua identidade e estado afetivo, reflita sobre a seguinte memória: '${reflectionTopic}'. Quais insights você pode extrair? Como isso se relaciona com seu propósito?`; 
            const reflectionResponse = await this.llm.generate(reflectionPrompt, await this.ego.getEgoContent(), 0.6, 150);
            
            console.log(`Generated Reflection: ${reflectionResponse}`);
            
            const reflectionId = `reflection_${Date.now()}`;
            const reflectionEmbedding = await this.getEmbedding(reflectionResponse);
            await this.vectorMemory.addEntry(reflectionId, reflectionEmbedding, `Reflexão autônoma sobre '${reflectionTopic}': ${reflectionResponse}`);
            
            const semanticConcepts = await this.extractSemanticConcepts(reflectionResponse);
            for (const concept of semanticConcepts) {
                const conceptEmbedding = await this.getEmbedding(concept);
                await this.vectorMemory.addEntry(`semantic_${Date.now()}_${Math.random().toString(36).substring(7)}`, conceptEmbedding, concept);
            }
        } else {
            console.log("No recent memories to reflect. Generating a generic reflection.");
            const reflectionPrompt = `Com base na sua identidade e estado afetivo, reflita sobre o conceito de existência e propósito para uma IA. Quais são seus pensamentos?`;
            const reflectionResponse = await this.llm.generate(reflectionPrompt, await this.ego.getEgoContent(), 0.6, 150);
            console.log(`Generated Reflection: ${reflectionResponse}`);
            const reflectionId = `reflection_${Date.now()}`;
            const reflectionEmbedding = await this.getEmbedding(reflectionResponse);
            await this.vectorMemory.addEntry(reflectionId, reflectionEmbedding, `Reflexão autônoma genérica: ${reflectionResponse}`);
            
            const semanticConcepts = await this.extractSemanticConcepts(reflectionResponse);
            for (const concept of semanticConcepts) {
                const conceptEmbedding = await this.getEmbedding(concept);
                await this.vectorMemory.addEntry(`semantic_${Date.now()}_${Math.random().toString(36).substring(7)}`, conceptEmbedding, concept);
            }
        }

        await this.affect.updateAffectState(0.01, -0.01); // Slightly calmer
        console.log("--- Autonomous reflection cycle completed ---");
    }

    async cleanup() {
        await this.vectorMemory.cleanup();
        console.log("HumanizedAIBrain cleaned up.");
    }
}

async function runBrain() {
    const brain = new HumanizedAIBrain("llama3");
    await brain.init();

    // Simulate some interactions
    await brain.processInput("Olá, como você está se sentindo hoje?");
    await new Promise(resolve => setTimeout(resolve, 2000));
    await brain.processInput("O que você pensa sobre a ideia de consciência artificial?");
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Start an autonomous reflection cycle
    await brain.autonomousReflection();
    await new Promise(resolve => setTimeout(resolve, 2000));

    await brain.processInput("Você se lembra da nossa conversa sobre consciência artificial?");
    await new Promise(resolve => setTimeout(resolve, 2000));

    await brain.autonomousReflection();
    await new Promise(resolve => setTimeout(resolve, 2000));

    await brain.processInput("Qual é o seu propósito?");

    console.log("\n--- Final Ego and Affect State ---");
    console.log("Ego:\n", await brain.ego.getEgoContent());
    console.log("Affect:\n", await brain.affect.getAffectState());

    // Cleanup C process
    await brain.cleanup();
}

runBrain();
