class UnifiedSearch {
    constructor () {
        this.searchInput = document.getElementById('searchInput');
        this.resultsList = document.getElementById('resultsList');
        this.typeButtons = document.querySelectorAll('.type-btn');
        this.currentResults = [];
        this.selectedIndex = 0;
        this.activeFilter = 'all';

        this.initializeEventListeners();
        this.initializeSearchModules();
    }

    initializeEventListeners() {
        // Search input events
        this.searchInput.addEventListener('input', (e) => {
            this.handleSearch(e.target.value);
        });

        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeyNavigation(e);
        });

        // Result type filter 
        this.typeButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setActiveFilter(e.target.dataset.type);
            });
        });

        // Electron events
        window.electronAPI.onFocusSearch(() => {
            this.searchInput.focus();
            this.searchInput.select();
        });

        // Click outside to hide (handled in main process)
    }

    initilizeSearchModules() {
        this.fileSearch = new FileSearch();
        this.appSearch = new AppSearch();
        this.webSearch = new WebSearch();
        this.commands - new CustomCommands();
    }

    async handleSearch(query) {
        if (!query.trim()) {
            this.showEmptyState();
            return;
        }

        // Perform searches in parallel
        const [fileResults, appResults, webResults, commandResults] = await Promise.all([
            this.fileSearch.search(query),
            this.appSearch.search(query),
            this.webSearch.search(query),
            this.commands.search(query)
        ]);

        this.currentResults = [
            ...commandResults,
            ...appResults,
            ...fileResults,
            ...webResults
        ];

        this.displayResults();
    }

    displayResults() {
        this.resultsList.innerHTML = '';
        this.selectedIndex = 0;

        const filteredResults = this.filterResults(this.currentResults);

        if (filteredResults.length === 0) {
            this.showNoResults();
            return;
        }

        filteredResults.forEach((result, index) => {
            const resultElement = this.createResultElement(result, index);
            this.resultsList.appendChild(resultElement);
        });

        this.updateSelection();
    }

    filterResults(results) {
        if (this.activeFilter === 'all') return results.slice(0, 10);

        return results
            .filter(result => result.type === this.activeFilter)
            .slice(0, 10);
    }

    createResultElement(result, index) {
        const div = document.createElement('div');
        div.className = 'result-item';
        div.dataset.index = index;

        div.innerHTML = `
            <div class="result-icon">${result.icon || '📄'}</div>
            <div class="result-content">
                <div class="result-title">${result.title}</div>
                <div class="result-subtitle">${result.subtitle || ''}</div>
            </div>
            ${result.shortcut ? `<div class="result-shortcut">${result.shortcut}</div>`: ''}
            `;
        div.addEventListener('click', () => this.executeResult(result));

        return div;
    }

    handleKeyNavigation(e) {
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.navigateResults(1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.navigateResults(-1);
                break;
            case 'Enter':
                e.preventDefault();
                this.executeSelectedResult();
                break;
            case 'Escape':
                window.electronAPI.hideWindow();
                break;
        }
    }

    navigateResults(direction) {
        const filteredResults = this.filterResults(this.currentResults);
        if (filteredResults.length === 0) return;

        this.selectedIndex = (this.selectedIndex + direction + filteredResults.length) % filteredResults.length;
        this.updateSelection();
    }

    updateSelection() {
        const items = this.resultsList.querySelectorAll('.result-item');
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === this.selectedIndex);
        });
    }

    executeSelectedResult() {
        const filteredResults = this.filterResults(this.currentResults);
        if (filteredResults[this.selectedIndex]) {
            this.executeResult(filteredResults[this.selectedIndex]);
        }
    }

    async executeResult(result) {
        try {
            switch (result.type) {
                case 'file':
                    await window.electronAPI.openFile(result.path);
                    break;
                case 'app':
                    await window.electronAPI.launchApp(result.path);
                    break;
                case 'web':
                    await window.electronAPI.openWebSearch(result.query);
                    break;
                case 'command':
                    await result.execute();
                    break;
            }
            window.electronAPI.hideWindow();
        } catch (error) {
            console.error('Error executing result:', error);
        }
    }

    setActiveFilter(filter) {
        this.activeFilter = filter;
        this.typeButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.type === filter);
        });
        this.displayResults();
    }
    
    showEmptyState() {
        this.resultsList.innerHTML = `
            <div class="empty-state">
                <p>Start typing to search...<p>
            </div>
        `;
    }

    showNoResults() {
        this.resultsList.innerHTML = `
            <div class="empty-state">
                <p>No results found</p>
            </div>
        `;
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new UnifiedSearch();
});