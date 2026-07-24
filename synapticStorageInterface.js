const { spawn } = require("child_process");

class SynapticStorageInterface {
    constructor(executablePath = "./synaptic_storage") {
        this.executablePath = executablePath;
        this.childProcess = null;
        this.responseBuffer = "";
        this.responseCallbacks = [];
        this.initPromise = null;
    }

    _startProcess() {
        if (this.childProcess) {
            return Promise.resolve();
        }

        this.childProcess = spawn(this.executablePath);

        this.childProcess.stdout.on("data", (data) => {
            this.responseBuffer += data.toString();
            this._processBuffer();
        });

        this.childProcess.stderr.on("data", (data) => {
            console.error(`Erro no processo C do Armazenamento Sináptico: ${data.toString()}`);
        });

        this.childProcess.on("close", (code) => {
            console.log(`Processo C do Armazenamento Sináptico encerrado com código ${code}`);
            this.childProcess = null;
            // Rejeitar quaisquer promessas pendentes
            this.responseCallbacks.forEach(cb => cb({ status: "error", message: `Processo encerrado com código ${code}` }));
            this.responseCallbacks = [];
        });

        this.childProcess.on("error", (err) => {
            console.error(`Falha ao iniciar o processo C do Armazenamento Sináptico: ${err}`);
            this.childProcess = null;
            // Rejeitar quaisquer promessas pendentes
            this.responseCallbacks.forEach(cb => cb({ status: "error", message: `Falha ao iniciar o processo: ${err.message}` }));
            this.responseCallbacks = [];
        });

        // Retorna uma promessa que resolve quando o processo está pronto para receber comandos
        return new Promise(resolve => {
            // Aguarda a primeira saída do processo C para garantir que esteja pronto
            // Uma solução mais robusta pode envolver uma mensagem específica de 'pronto' do C
            this.childProcess.stdout.once("data", () => resolve()); 
        });
    }

    _processBuffer() {
        let newlineIndex;
        while ((newlineIndex = this.responseBuffer.indexOf("\n")) !== -1) {
            const jsonString = this.responseBuffer.substring(0, newlineIndex);
            this.responseBuffer = this.responseBuffer.substring(newlineIndex + 1);

            try {
                const response = JSON.parse(jsonString);
                if (this.responseCallbacks.length > 0) {
                    const callback = this.responseCallbacks.shift();
                    callback(response);
                } else {
                    console.warn("Resposta inesperada recebida do processo C:", response);
                }
            } catch (e) {
                console.error("Falha ao analisar JSON do processo C:", jsonString, e);
                if (this.responseCallbacks.length > 0) {
                    const callback = this.responseCallbacks.shift();
                    callback({ status: "error", message: `Erro de análise JSON: ${e.message}` });
                }
            }
        }
    }

    _sendCommand(command) {
        return new Promise((resolve) => {
            this.responseCallbacks.push(resolve);
            this.childProcess.stdin.write(JSON.stringify(command) + "\n");
        });
    }

    async initializeStorage(maxEntries, embeddingDim) {
        if (!this.initPromise) {
            this.initPromise = this._startProcess().then(() => {
                return this._sendCommand({ command: "init", max_entries: maxEntries, embedding_dim: embeddingDim });
            });
        }
        return this.initPromise;
    }

    async addSynapticEntry(id, embedding, content) {
        await this.initPromise; // Garante que a inicialização esteja completa
        return this._sendCommand({ command: "add", id, embedding, content });
    }

    async searchSynapticEntries(queryEmbedding, nResults) {
        await this.initPromise; // Garante que a inicialização esteja completa
        return this._sendCommand({ command: "search", query_embedding: queryEmbedding, n_results: nResults });
    }

    async applySynapticDecay(decayRate) {
        await this.initPromise; // Garante que a inicialização esteja completa
        return this._sendCommand({ command: "apply_decay", decay_rate: decayRate });
    }

    async clearStorage() {
        if (this.childProcess) {
            const response = await this._sendCommand({ command: "cleanup" });
            this.childProcess.kill();
            this.childProcess = null;
            this.initPromise = null;
            return response;
        }
        return { status: "success", message: "Processo não está em execução." };
    }
}

module.exports = SynapticStorageInterface;

// Exemplo de uso (para testes internos do módulo Node.js)
async function testSynapticStorageInterface() {
    console.log("Iniciando teste do SynapticStorageInterface...");
    const ssi = new SynapticStorageInterface();

    try {
        // Inicializar
        let response = await ssi.initializeStorage(10, 3);
        console.log("Resposta de Inicialização:", response);

        // Adicionar entradas
        response = await ssi.addSynapticEntry("doc1", [0.1, 0.2, 0.3], "Este é o documento um.");
        console.log("Resposta de Adição Doc1:", response);
        response = await ssi.addSynapticEntry("doc2", [0.9, 0.8, 0.7], "Este é o documento dois.");
        console.log("Resposta de Adição Doc2:", response);
        response = await ssi.addSynapticEntry("doc3", [0.15, 0.25, 0.35], "Este é o documento três.");
        console.log("Resposta de Adição Doc3:", response);

        // Pesquisar
        response = await ssi.searchSynapticEntries([0.1, 0.2, 0.3], 2);
        console.log("Resposta de Pesquisa:", response);

        // Aplicar decaimento
        response = await ssi.applySynapticDecay(0.05);
        console.log("Resposta de Aplicação de Decaimento:", response);

        // Limpar
        response = await ssi.clearStorage();
        console.log("Resposta de Limpeza:", response);

    } catch (error) {
        console.error("Falha no teste:", error);
    }
}

// Descomente para executar
// testSynapticStorageInterface();
