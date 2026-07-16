const axios = require("axios");

class LLMProcessor {
    constructor(modelName = "llama3", ollamaUrl = "http://localhost:11434/api/generate") {
        this.modelName = modelName;
        this.ollamaUrl = ollamaUrl;
        console.log(`LLMProcessor initialized with model '${this.modelName}' and Ollama URL '${this.ollamaUrl}'`);
    }

    async generate(prompt, systemMessage = "", temperature = 0.7, maxTokens = 500) {
        const headers = { "Content-Type": "application/json" };
        const data = {
            model: this.modelName,
            prompt: prompt,
            system: systemMessage,
            options: {
                temperature: temperature,
                num_predict: maxTokens,
            },
            stream: false, // Request full response, not streaming
        };

        try {
            const response = await axios.post(this.ollamaUrl, data, { headers });
            return response.data.response.trim();
        } catch (error) {
            if (error.code === 'ECONNREFUSED') {
                console.error(`Error: Could not connect to Ollama at ${this.ollamaUrl}. Make sure Ollama is running and the model '${this.modelName}' is downloaded.`);
                return "[LLM ERROR: Ollama not accessible]";
            } else if (error.response && error.response.data) {
                console.error(`Ollama API Error: ${error.response.status} - ${JSON.stringify(error.response.data)}`);
                return `[LLM ERROR: ${error.response.status} - ${error.response.data.error || 'Unknown error'}]`;
            } else {
                console.error(`LLM Request Error: ${error.message}`);
                return `[LLM ERROR: ${error.message}]`;
            }
        }
    }
}

module.exports = LLMProcessor;

// Exemplo de uso (para testes internos do módulo Node.js)
async function testLLMProcessor() {
    console.log("Starting LLMProcessor test...");
    const llm = new LLMProcessor("llama3");

    console.log("\nGenerating response for a simple prompt:");
    let response = await llm.generate("Qual é a capital da França?");
    console.log(`LLM Response: ${response}`);

    console.log("\nGenerating response with system message:");
    const systemMsg = "Você é um assistente de IA prestativo e conciso.";
    response = await llm.generate("Explique a fotossíntese em uma frase.", systemMsg);
    console.log(`LLM Response: ${response}`);

    console.log("\nGenerating response with higher temperature (more creative):");
    response = await llm.generate("Escreva um pequeno poema sobre o mar.", "", 0.9, 100);
    console.log(`LLM Response: ${response}`);
}

// Uncomment to run the test
// testLLMProcessor();
