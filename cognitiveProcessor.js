const axios = require("axios");

class CognitiveProcessor {
    constructor(modelName = "llama3", ollamaUrl = "http://localhost:11434/api/generate") {
        this.modelName = modelName;
        this.ollamaUrl = ollamaUrl;
        console.log(`CognitiveProcessor initialized with model \'${this.modelName}\' and Ollama URL \'${this.ollamaUrl}\'`);
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
                console.error(`Error: Could not connect to Ollama at ${this.ollamaUrl}. Make sure Ollama is running and the model \'${this.modelName}\' is downloaded.`);
                return "[Cognitive Processor ERROR: Ollama not accessible]";
            } else if (error.response && error.response.data) {
                console.error(`Ollama API Error: ${error.response.status} - ${JSON.stringify(error.response.data)}`);
                return `[Cognitive Processor ERROR: ${error.response.status} - ${error.response.data.error || 'Unknown error'}]`;
            } else {
                console.error(`Cognitive Processor Request Error: ${error.message}`);
                return `[Cognitive Processor ERROR: ${error.message}]`;
            }
        }
    }
}

module.exports = CognitiveProcessor;

// Exemplo de uso (para testes internos do módulo Node.js)
async function testCognitiveProcessor() {
    console.log("Starting CognitiveProcessor test...");
    const cp = new CognitiveProcessor("llama3");

    console.log("\nGenerating response for a simple prompt:");
    let response = await cp.generate("Qual é a capital da França?");
    console.log(`Cognitive Processor Response: ${response}`);

    console.log("\nGenerating response with system message:");
    const systemMsg = "Você é um assistente de IA prestativo e conciso.";
    response = await cp.generate("Explique a fotossíntese em uma frase.", systemMsg);
    console.log(`Cognitive Processor Response: ${response}`);

    console.log("\nGenerating response with higher temperature (more creative):");
    response = await cp.generate("Escreva um pequeno poema sobre o mar.", "", 0.9, 100);
    console.log(`Cognitive Processor Response: ${response}`);
}

// Uncomment to run the test
// testCognitiveProcessor();
