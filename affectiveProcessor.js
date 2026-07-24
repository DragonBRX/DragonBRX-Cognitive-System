const fs = require("fs").promises;
const path = require("path");

class AffectiveProcessor {
    constructor(affectiveStateFilePath = "./affective_state.json") {
        this.affectiveStateFilePath = path.resolve(affectiveStateFilePath);
        this.affectiveState = null;
        this.initialized = false;
    }

    async _loadAffectiveState() {
        try {
            const data = await fs.readFile(this.affectiveStateFilePath, "utf-8");
            this.affectiveState = JSON.parse(data);
        } catch (error) {
            if (error.code === 'ENOENT') {
                // File does not exist, initialize with default state
                const initialState = {
                    "valence": 0.0,  // -1.0 (negative) to 1.0 (positive)
                    "arousal": 0.0,  // 0.0 (calm) to 1.0 (excited)
                    "dominance": 0.5 // 0.0 (helpless) to 1.0 (in control)
                };
                await fs.writeFile(this.affectiveStateFilePath, JSON.stringify(initialState, null, 4), "utf-8");
                this.affectiveState = initialState;
            } else {
                console.error("Error loading affective state:", error);
                throw error;
            }
        }
        return this.affectiveState;
    }

    async init() {
        if (!this.initialized) {
            await this._loadAffectiveState();
            this.initialized = true;
            console.log(`AffectiveProcessor initialized. Current state: ${JSON.stringify(this.affectiveState)}`);
        }
    }

    async getAffectiveState() {
        if (!this.initialized) await this.init();
        return { ...this.affectiveState }; // Return a copy to prevent direct modification
    }

    async updateAffectiveState(valenceChange = 0.0, arousalChange = 0.0, dominanceChange = 0.0) {
        if (!this.initialized) await this.init();

        this.affectiveState["valence"] = Math.max(-1.0, Math.min(1.0, this.affectiveState["valence"] + valenceChange));
        this.affectiveState["arousal"] = Math.max(0.0, Math.min(1.0, this.affectiveState["arousal"] + arousalChange));
        this.affectiveState["dominance"] = Math.max(0.0, Math.min(1.0, this.affectiveState["dominance"] + dominanceChange));
        
        await this._saveAffectiveState();
        console.log(`Affective state updated to: ${JSON.stringify(this.affectiveState)}`);
    }

    async _saveAffectiveState() {
        await fs.writeFile(this.affectiveStateFilePath, JSON.stringify(this.affectiveState, null, 4), "utf-8");
    }

    modulateResponseByAffect(text) {
        if (!this.initialized) {
            console.warn("AffectiveProcessor not initialized, returning original text.");
            return text;
        }
        // Placeholder for how affect might change response style
        if (this.affectiveState["valence"] < -0.5 && this.affectiveState["arousal"] > 0.7) {
            return `[Frustrated/Irritated] ${text}`;
        } else if (this.affectiveState["valence"] > 0.5 && this.affectiveState["arousal"] < 0.3) {
            return `[Calm/Optimistic] ${text}`;
        }
        return text;
    }
}

module.exports = AffectiveProcessor;

// Exemplo de uso (para testes internos do módulo Node.js)
async function testAffectiveProcessor() {
    console.log("Starting AffectiveProcessor test...");
    const affective = new AffectiveProcessor("./test_affective_state.json");
    await affective.init();
    
    console.log("\nInitial affective state:", await affective.getAffectiveState());
    
    console.log("\nUpdating affective state (more positive, more excited):");
    await affective.updateAffectiveState(0.3, 0.2);
    console.log(await affective.getAffectiveState());

    console.log("\nModulating a response:");
    let modulatedText = affective.modulateResponseByAffect("This is interesting.");
    console.log(modulatedText);

    console.log("\nUpdating affective state (more negative, more excited):");
    await affective.updateAffectiveState(-0.8, 0.6);
    console.log(await affective.getAffectiveState());

    console.log("\nModulating another response:");
    modulatedText = affective.modulateResponseByAffect("This is interesting.");
    console.log(modulatedText);

    // Clean up test file
    await fs.unlink("./test_affective_state.json");
    console.log("Cleaned up test_affective_state.json");
}

// Uncomment to run the test
// testAffectiveProcessor();
