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

}