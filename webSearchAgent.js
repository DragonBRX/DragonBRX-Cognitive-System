const axios = require('axios');
const cheerio = require('cheerio');

class WebSearchAgent {
    constructor() {
        this.searchUrl = 'https://duckduckgo.com/html/?q=';
    }

    async search(query) {
        console.log(`Iniciando pesquisa web no DuckDuckGo para: "${query}"`);
        try {
            const response = await axios.get(`${this.searchUrl}${encodeURIComponent(query)}`, {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            });

            const $ = cheerio.load(response.data);
            const results = [];

            $('div.result').each((i, element) => {
                const title = $(element).find('a.result__a').text().trim();
                const url = $(element).find('a.result__a').attr('href');
                const snippet = $(element).find('a.result__snippet').text().trim();

                if (title && url && snippet) {
                    results.push({
                        title,
                        url,
                        snippet
                    });
                }
            });
            console.log(`Pesquisa web concluída. Encontrados ${results.length} resultados.`);
            return { status: 'success', results };

        } catch (error) {
            console.error(`Erro ao realizar pesquisa web: ${error.message}`);
            return { status: 'error', message: error.message };
        }
    }
}

module.exports = WebSearchAgent;

// Exemplo de uso (para testes internos do módulo Node.js)
async function testWebSearchAgent() {
    console.log("Iniciando teste do WebSearchAgent...");
    const agent = new WebSearchAgent();
    const query = "inteligência artificial consciente";
    const searchResults = await agent.search(query);

    if (searchResults.status === 'success') {
        console.log("Resultados da Pesquisa:");
        searchResults.results.forEach((result, index) => {
            console.log(`\n${index + 1}. Título: ${result.title}`);
            console.log(`   URL: ${result.url}`);
            console.log(`   Snippet: ${result.snippet}`);
        });
    } else {
        console.error("Falha no teste de pesquisa web:", searchResults.message);
    }
}

// Descomente para executar o teste
// testWebSearchAgent().catch(console.error);
