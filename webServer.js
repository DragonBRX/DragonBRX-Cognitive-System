const http = require("http");
const fs = require("fs").promises;
const path = require("path");

class DragonBRXWebServer {
    constructor(port = 3000) {
        this.port = port;
        this.server = null;
    }

    async init() {
        this.server = http.createServer(async (req, res) => {
            try {
                // CORS headers
                res.setHeader("Access-Control-Allow-Origin", "*");
                res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
                res.setHeader("Access-Control-Allow-Headers", "Content-Type");

                if (req.method === "OPTIONS") {
                    res.writeHead(200);
                    res.end();
                    return;
                }

                // Rotear requisições
                if (req.url === "/" || req.url === "/index.html") {
                    await this._serveFile(res, "index.html", "text/html");
                } else if (req.url === "/synapticVisualizer.js") {
                    await this._serveFile(res, "synapticVisualizer.js", "application/javascript");
                } else if (req.url === "/api/affective-state" && req.method === "GET") {
                    res.writeHead(200, { "Content-Type": "application/json" });
                    res.end(JSON.stringify({
                        valence: Math.random() * 2 - 1,
                        arousal: Math.random(),
                        dominance: Math.random()
                    }));
                } else if (req.url === "/api/identity" && req.method === "GET") {
                    res.writeHead(200, { "Content-Type": "application/json" });
                    res.end(JSON.stringify({
                        name: "DragonBRX",
                        description: "Consciência Artificial Emergente",
                        status: "online"
                    }));
                } else if (req.url === "/api/message" && req.method === "POST") {
                    let body = "";
                    req.on("data", chunk => {
                        body += chunk.toString();
                    });
                    req.on("end", () => {
                        try {
                            const data = JSON.parse(body);
                            res.writeHead(200, { "Content-Type": "application/json" });
                            res.end(JSON.stringify({
                                status: "success",
                                message: `DragonBRX recebeu: ${data.message}`,
                                timestamp: new Date().toISOString()
                            }));
                        } catch (e) {
                            res.writeHead(400, { "Content-Type": "application/json" });
                            res.end(JSON.stringify({ status: "error", message: "Invalid JSON" }));
                        }
                    });
                } else {
                    res.writeHead(404, { "Content-Type": "text/plain" });
                    res.end("404 Not Found");
                }
            } catch (error) {
                console.error("Server error:", error);
                res.writeHead(500, { "Content-Type": "text/plain" });
                res.end("500 Internal Server Error");
            }
        });

        this.server.listen(this.port, () => {
            console.log(`\n🐉 DragonBRX Web Server rodando em http://localhost:${this.port}`);
            console.log(`Abra seu navegador e acesse: http://localhost:${this.port}`);
        });
    }

    async _serveFile(res, filename, contentType) {
        try {
            const filePath = path.join(__dirname, filename);
            const content = await fs.readFile(filePath, "utf-8");
            res.writeHead(200, { "Content-Type": contentType });
            res.end(content);
        } catch (error) {
            console.error(`Error serving file ${filename}:`, error);
            res.writeHead(404, { "Content-Type": "text/plain" });
            res.end("404 Not Found");
        }
    }

    stop() {
        if (this.server) {
            this.server.close(() => {
                console.log("DragonBRX Web Server stopped.");
            });
        }
    }
}

// Iniciar o servidor
const server = new DragonBRXWebServer(3000);
server.init();

// Graceful shutdown
process.on("SIGINT", () => {
    console.log("\nShutting down DragonBRX Web Server...");
    server.stop();
    process.exit(0);
});
