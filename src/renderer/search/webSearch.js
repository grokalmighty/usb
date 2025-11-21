class WebSearch {
    constructor() {
        this.searchEngines = {
            google: {name: 'Google', url: 'https://google.com/search?q=' },
            duckduckgo: {name: 'DuckDuckGo', url: 'https://duckduckgo.com/?q='},
            github: {name: 'GitHub', url: 'https://github.com/search?q='}
            };
        }

        async search(query) {
            if (!query || query.length < 2) return [];

            const results = Object.entries(this.searchEngines).map(([key, engine]) => ({
                title: `Search ${engine.name} for "${query}`,
                subtitle: `Web search using ${engine.name}`,
                query: query,
                type: 'web',
                icon: '🌐',
                engine: key,
                shortcut: 'Enter to search'
            }));
            
            return results;
        }
    }