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
            console.error(`SynapticStorage C Error: ${data.toString()}`);
        });

        this.childProcess.on("close", (code) => {
            console.log(`SynapticStorage C process exited with code ${code}`);
            this.childProcess = null;
            // Reject any pending promises
            this.responseCallbacks.forEach(cb => cb({ status: "error", message: `Process exited with code ${code}` }));
            this.responseCallbacks = [];
        });

        this.childProcess.on("error", (err) => {
            console.error(`Failed to start SynapticStorage C process: ${err}`);
            this.childProcess = null;
            // Reject any pending promises
            this.responseCallbacks.forEach(cb => cb({ status: "error", message: `Failed to start process: ${err.message}` }));
            this.responseCallbacks = [];
        });

        // Return a promise that resolves when the process is ready to receive commands
        return new Promise(resolve => {
            // Wait for the first output from the C process to ensure it's ready
            // A more robust solution might involve a specific 'ready' message from C
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
                    console.warn("Received unexpected response from C process:", response);
                }
            } catch (e) {
                console.error("Failed to parse JSON from C process:", jsonString, e);
                if (this.responseCallbacks.length > 0) {
                    const callback = this.responseCallbacks.shift();
                    callback({ status: "error", message: `JSON parse error: ${e.message}` });
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
        await this.initPromise; // Ensure init is complete
        return this._sendCommand({ command: "add", id, embedding, content });
    }

    async searchSynapticEntries(queryEmbedding, nResults) {
        await this.initPromise; // Ensure init is complete
        return this._sendCommand({ command: "search", query_embedding: queryEmbedding, n_results: nResults });
    }

    async applySynapticDecay(decayRate) {
        await this.initPromise; // Ensure init is complete
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
        return { status: "success", message: "Process not running." };
    }
}

module.exports = SynapticStorageInterface;

// Exemplo de uso (para testes internos do módulo Node.js)
async function testSynapticStorageInterface() {
    console.log("Starting SynapticStorageInterface test...");
    const ssi = new SynapticStorageInterface();

    try {
        // Initialize
        let response = await ssi.initializeStorage(10, 3);
        console.log("Init Response:", response);

        // Add entries
        response = await ssi.addSynapticEntry("doc1", [0.1, 0.2, 0.3], "Este é o documento um.");
        console.log("Add Doc1 Response:", response);
        response = await ssi.addSynapticEntry("doc2", [0.9, 0.8, 0.7], "Este é o documento dois.");
        console.log("Add Doc2 Response:", response);
        response = await ssi.addSynapticEntry("doc3", [0.15, 0.25, 0.35], "Este é o documento três.");
        console.log("Add Doc3 Response:", response);

        // Search
        response = await ssi.searchSynapticEntries([0.1, 0.2, 0.3], 2);
        console.log("Search Response:", response);

        // Apply decay
        response = await ssi.applySynapticDecay(0.05);
        console.log("Apply Decay Response:", response);

        // Cleanup
        response = await ssi.clearStorage();
        console.log("Cleanup Response:", response);

    } catch (error) {
        console.error("Test failed:", error);
    }
}

// Uncomment to run the test
// testSynapticStorageInterface();
