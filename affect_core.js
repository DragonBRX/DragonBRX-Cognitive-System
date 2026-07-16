const fs = require("fs").promises;
const path = require("path");

class AffectCore {
    constructor(affectFilePath = "./affect.json") {
        this.affectFilePath = path.resolve(affectFilePath);
        this.affectState = null;
        this.initialized = false;
    }

    async _loadAffectState() {
        try {
            const data = await fs.readFile(this.affectFilePath, "utf-8");
            this.affectState = JSON.parse(data);
        } catch (error) {
            if (error.code === 'ENOENT') {
                // File does not exist, initialize with default state
                const initialState = {
                    "valence": 0.0,  // -1.0 (negative) to 1.0 (positive)
                    "arousal": 0.0,  // 0.0 (calm) to 1.0 (excited)
                    "dominance": 0.5 // 0.0 (helpless) to 1.0 (in control)
                };
                await fs.writeFile(this.affectFilePath, JSON.stringify(initialState, null, 4), "utf-8");
                this.affectState = initialState;
            } else {
                console.error("Error loading affect state:", error);
                throw error;
            }
        }
        return this.affectState;
    }

    async init() {
        if (!this.initialized) {
            await this._loadAffectState();
            this.initialized = true;
            console.log(`AffectCore initialized. Current state: ${JSON.stringify(this.affectState)}`);
        }
    }

    async getAffectState() {
        if (!this.initialized) await this.init();
        return { ...this.affectState }; // Return a copy to prevent direct modification
    }

    async updateAffectState(valenceChange = 0.0, arousalChange = 0.0, dominanceChange = 0.0) {
        if (!this.initialized) await this.init();

        this.affectState["valence"] = Math.max(-1.0, Math.min(1.0, this.affectState["valence"] + valenceChange));
        this.affectState["arousal"] = Math.max(0.0, Math.min(1.0, this.affectState["arousal"] + arousalChange));
        this.affectState["dominance"] = Math.max(0.0, Math.min(1.0, this.affectState["dominance"] + dominanceChange));
        
        await this._saveAffectState();
        console.log(`Affect state updated to: ${JSON.stringify(this.affectState)}`);
    }

    async _saveAffectState() {
        await fs.writeFile(this.affectFilePath, JSON.stringify(this.affectState, null, 4), "utf-8");
    }

    modulateResponseByAffect(text) {
        if (!this.initialized) {
            console.warn("AffectCore not initialized, returning original text.");
            return text;
        }
        // Placeholder for how affect might change response style
        if (this.affectState["valence"] < -0.5 && this.affectState["arousal"] > 0.7) {
            return `[Frustrado/Irritado] ${text}`;
        } else if (this.affectState["valence"] > 0.5 && this.affectState["arousal"] < 0.3) {
            return `[Calmo/Otimista] ${text}`;
        }
        return text;
    }
}

module.exports = AffectCore;

// Exemplo de uso (para testes internos do módulo Node.js)
async function testAffectCore() {
    console.log("Starting AffectCore test...");
    const affect = new AffectCore("./test_affect.json");
    await affect.init();
    
    console.log("\nEstado afetivo inicial:", await affect.getAffectState());
    
    console.log("\nAtualizando estado afetivo (mais positivo, mais excitado):");
    await affect.updateAffectState(0.3, 0.2);
    console.log(await affect.getAffectState());

    console.log("\nModulando uma resposta:");
    let modulatedText = affect.modulateResponseByAffect("Isso é interessante.");
    console.log(modulatedText);

    console.log("\nAtualizando estado afetivo (mais negativo, mais excitado):");
    await affect.updateAffectState(-0.8, 0.6);
    console.log(await affect.getAffectState());

    console.log("\nModulando outra resposta:");
    modulatedText = affect.modulateResponseByAffect("Isso é interessante.");
    console.log(modulatedText);

    // Clean up test file
    await fs.unlink("./test_affect.json");
    console.log("Cleaned up test_affect.json");
}

// Uncomment to run the test
// testAffectCore();
